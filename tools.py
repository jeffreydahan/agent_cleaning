import os  # Import the os module for environment variables
from dotenv import load_dotenv

# Import GenAI libraries
from google import genai
from google.genai import types
from google.cloud import storage

# Import Roborock libraries
from roborock import HomeDataProduct, DeviceData, RoborockCommand
from roborock.version_1_apis import RoborockMqttClientV1, RoborockLocalClientV1
from roborock.web_api import RoborockApiClient


load_dotenv()  # Load environment variables from .env file

# Global variables to hold the MQTT client and device
mqtt_client = None
device = None

# Helper function to get environment variables
def get_env_var(key):
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable '{key}' not found.")
    return value

# Login to Roborock (will only run if mqtt_client is None)
async def ensure_login():
    global mqtt_client
    global device
    if mqtt_client is None:
        try:
            web_api = RoborockApiClient(username=get_env_var('ROBOROCK_USERNAME'))
            user_data = await web_api.pass_login(password=get_env_var('ROBOROCK_PASSWORD'))
            home_data = await web_api.get_home_data_v2(user_data)
            device_data = home_data.devices[0]
            product_info: dict[str, HomeDataProduct] = {
                product.id: product for product in home_data.products
            }
            device = DeviceData(device_data, product_info[device_data.product_id].model)
            mqtt_client = RoborockMqttClientV1(user_data, device)
            await mqtt_client.async_connect()
            print("Roborock login successful.")
            return True
        except Exception as e:
            print(f"Roborock login failed: {e}")
            mqtt_client = None
            device = None
            return False
    return True

# Resets Roborock login and session
async def reset_connection():
    global mqtt_client
    global device
    if mqtt_client:
        try:
            await mqtt_client.async_disconnect()
            print("MQTT client disconnected.")
        except Exception as e:
            print(f"Error disconnecting MQTT client: {e}")
        finally:
            mqtt_client = None
            device = None
            print("Roborock connection reset.")

# Get Roborock status
async def get_status():
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    try:
        status = await mqtt_client.get_status()
        print("Current Status:")
        print(status)
        return {
            "state": status.state_name,
            "battery": status.battery,
            "clean_time": status.clean_time,
            "clean_area": status.square_meter_clean_area,
            "error": status.error_code_name,
            "fan_speed": status.fan_power_name,
            "mop_mode": status.mop_mode_name,
            "docked": status.state_name == "charging"
        }
    except Exception as e:
        print(f"Error getting status: {e}")
        await reset_connection()
        return {"error": f"Error getting status: {e}. Connection reset."}

# Send basic Roborock commands that don't have parameters
async def send_basic_command(command: str) -> str:
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    try:
        await mqtt_client.send_command(command)
        print(f"Command sent: {command}")
        return {"result": f"Command {command} sent successfully."}
    except Exception as e:
        print(f"Error sending {command}: {e}")
        await reset_connection()
        return {"error": f"Error sending {command}: {e}. Connection reset."}

# cleans a specific room also known as segment. To Do is to make this dynamic based upon desired segment from instructions mapping in the Agent definition below. 
async def app_segment_clean(segment_number: dict) -> str:
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    command = "app_segment_clean"
    try:
        segment = await mqtt_client.send_command(command, [{"segments": segment_number, "repeat": 1}])
        print(f"Command sent: {command}")
        return segment
    except Exception as e:
        print(f"Error sending {command}: {e}")
        await reset_connection()
        return {"error": f"Error sending {command}: {e}. Connection reset."}

# Function to select the most recent file in a storage bucket folder
def get_most_recent_file_with_extension_check(bucket_name: str, folder: str):
  """Gets the most recent file in a GCS bucket folder and checks if its
  extension is one of .mov, .mp4, .jpg, .jpeg, or .png.

  Args:
    bucket_name: The name of the storage bucket.
    folder: The path of the folder in the storage bucket (should NOT end with a '/').

  Returns:
    A tuple containing the GCS file path of the most recent file and its mime type.

  Raises:
    ValueError: If the folder does not exist, no files are found in the folder,
                or the most recent file's extension is not one of the allowed types.
  """
  client = storage.Client()
  bucket = client.bucket(bucket_name)
  print(f"Bucket name: {bucket.name}")

  folder_prefix = folder + "/"

  # Check if the folder exists by listing blobs with the folder prefix and limiting to 1
  blobs = bucket.list_blobs(prefix=folder_prefix, max_results=1)
  if not any(blobs):
    raise ValueError(f"Folder '{folder}' does not exist in bucket '{bucket_name}'.")

  # Get all blobs within the specified folder
  blobs = bucket.list_blobs(prefix=folder_prefix)
  most_recent_blob = None

  for blob in blobs:
    if most_recent_blob is None or blob.updated > most_recent_blob.updated:
      most_recent_blob = blob

  if most_recent_blob is None:
    raise ValueError(f"No files found in folder '{folder}'.")

  _, file_extension = most_recent_blob.name.rsplit('.', 1) if '.' in most_recent_blob.name else ('', '')
  file_extension = "." + file_extension.lower()

  mime_type = None
  if file_extension == ".mov":
    mime_type = "video/quicktime"
  elif file_extension == ".mp4":
    mime_type = "video/mp4"
  elif file_extension == ".jpg":
    mime_type = "image/jpeg"
  elif file_extension == ".jpeg":
    mime_type = "image/jpeg"
  elif file_extension == ".png":
    mime_type = "image/png"
  else:
    raise ValueError(f"Unrecognized file extension: '{file_extension}' for file '{most_recent_blob.name}'. "
                     f"Allowed extensions are: .mov, .mp4, .jpg, .jpeg, .png")

  return f"gs://{bucket_name}/{most_recent_blob.name}", mime_type

# Define a function to analyze the media and determine if cleaning is needed
async def check_if_dirty(room: str) -> str:
  client = genai.Client(
      vertexai=True,
      project=get_env_var("GOOGLE_CLOUD_PROJECT"),
      location=get_env_var("GOOGLE_CLOUD_LOCATION"),
  )

  file, mime = get_most_recent_file_with_extension_check(get_env_var("GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET"), room)
   
  msg1_video1 = types.Part.from_uri(
    file_uri = file,
    mime_type = mime,
  )

  model = "gemini-2.0-flash-001"
  contents = [
    types.Content(
      role="user",
      parts=[
        msg1_video1,
        types.Part.from_text(text="""
          Please review the image or video.  If the floor is very dirty,
          - Respond that [roomname] is dirty, please clean it by using the roborock_agent subagent
              example:  The kitchen is dirty, please clean it
          If the floor is clean or a tiny bit dirty,
          - Respond that [roomname] is clean, get the vacuum status by using the roborock_agent subagent
              example:  The hallway is clean, please get the robot status
          """
        )
      ]
    ),
  ]
  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 8192,
    response_modalities = ["TEXT"],
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
  )

  response_text = ""
  for chunk in client.models.generate_content_stream(
    model = model,
    contents = contents,
    config = generate_content_config,
    ):
    response_text += chunk.text

  return response_text.strip()
