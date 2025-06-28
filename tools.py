import os  # Import the os module for environment variables
from dotenv import load_dotenv
import logging
import time
from datetime import datetime
import httpx
import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token

# Import GenAI libraries
from google import genai
from google.genai import types
from google.cloud import storage


# Import Roborock libraries
from roborock import HomeDataProduct, DeviceData, RoborockCommand
from roborock.version_1_apis import RoborockMqttClientV1, RoborockLocalClientV1
from roborock.web_api import RoborockApiClient

# Import Video/Camera libraries
# import cv2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
            await mqtt_client.async_connect() # type: ignore
            logging.info("Roborock login successful.")
            return True
        except Exception as e:
            logging.error(f"Roborock login failed: {e}")
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
            await mqtt_client.async_disconnect() # type: ignore
            logging.info("MQTT client disconnected.")
        except Exception as e:
            logging.error(f"Error disconnecting MQTT client: {e}")
        finally:
            mqtt_client = None
            device = None
            logging.info("Roborock connection reset.")

# Get Roborock status
async def get_status():
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    try:
        status = await mqtt_client.get_status()
        logging.info("Current Roborock Status:")
        logging.info(status)
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
        logging.error(f"Error getting status: {e}")
        await reset_connection()
        return {"error": f"Error getting status: {e}. Connection reset."}

# Send basic Roborock commands that don't have parameters
async def send_basic_command(command: str) -> str:
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    try:
        await mqtt_client.send_command(command) # type: ignore
        logging.info(f"Command sent: {command}")
        return {"result": f"Command {command} sent successfully."}
    except Exception as e:
        logging.error(f"Error sending {command}: {e}")
        await reset_connection()
        return {"error": f"Error sending {command}: {e}. Connection reset."}

# cleans a specific room also known as segment. To Do is to make this dynamic based upon desired segment from instructions mapping in the Agent definition below. 
async def app_segment_clean(segment_number: dict) -> str:
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    command = "app_segment_clean"
    try: # type: ignore
        segment = await mqtt_client.send_command(command, [{"segments": segment_number, "repeat": 1}]) # type: ignore
        logging.info(f"Command sent: {command}")
        return segment
    except Exception as e:
        print(f"Error sending {command}: {e}")
        await reset_connection()
        return {"error": f"Error sending {command}: {e}. Connection reset."}

# Function to select the most recent file in a storage bucket folder
def get_most_recent_file_with_extension_check(bucket_name: str, folder: str):
  """Gets the most recent file in a GCS bucket folder and checks if its
  extension is one of .mov, .mp4, .jpg, .jpeg, .png, or .avi.

  Args:
    bucket_name: The name of the storage bucket (can be with or without 'gs://' prefix).
    folder: The path of the folder in the storage bucket (should NOT end with a '/').

  Returns:
    A tuple containing the GCS file path of the most recent file and its mime type.

  Raises:
    ValueError: If the folder does not exist, no files are found in the folder,
                or the most recent file's extension is not one of the allowed types.
  """
  client = storage.Client()
  # Ensure bucket_name does not have gs:// prefix for client.bucket()
  actual_bucket_name_for_api = bucket_name.replace("gs://", "")
  bucket = client.bucket(actual_bucket_name_for_api) # type: ignore
  print(f"Accessing GCS bucket: {bucket.name}")

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
  elif file_extension == ".avi":
    mime_type = "video/x-msvideo"
  else:
    raise ValueError(f"Unrecognized file extension: '{file_extension}' for file '{most_recent_blob.name}'. "
                     f"Allowed extensions are: .mov, .mp4, .jpg, .jpeg, .png, .avi")

  return f"gs://{actual_bucket_name_for_api}/{most_recent_blob.name}", mime_type

# Define a function to analyze the media and determine if cleaning is needed
async def check_if_dirty(room: str) -> str:
  from .prompts import check_if_dirty_instruction
  
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
        types.Part.from_text(text=check_if_dirty_instruction)
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

# Function to handle capturing a camera stream from a remote camera
# This function acts as a client, calling the dedicated Cloud Run service.
async def capture_camera_stream(room: str) -> str:
    """Makes an authenticated request to the camera tool service on Cloud Run."""
    logging.info(f"Calling camera tool service for room: {room}")
    service_url = get_env_var("CAMERA_TOOL_SERVICE_URL")
    if not service_url:
        return "Error: The CAMERA_TOOL_SERVICE_URL environment variable is not set for the agent. Cannot call the camera service."

    try:
        # Get default credentials from the environment (this works in Cloud Run,
        # Cloud Functions, and other GCP environments with a service account).
        creds, project = google.auth.default()

        # Create an authorized session to fetch an ID token.
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        # Get an ID token for the Cloud Run service URL (the audience).
        # This token will be used to authenticate the request.
        auth_token = id_token.fetch_id_token(auth_req, service_url)

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

        # The camera service can take a while to record, so we set a long timeout.
        # The service itself has a timeout of 0 (unlimited) in the Dockerfile CMD.
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(service_url, headers=headers, json={"room": room})
            response.raise_for_status()  # Raise an exception for 4xx/5xx status codes
            result = response.json()
            logging.info(f"Received response from camera service: {result.get('message')}")
            return result.get("message", "Received an empty response from the camera service.")
    except google.auth.exceptions.DefaultCredentialsError:
        logging.error("Authentication failed. Could not find default credentials.")
        return "Error: Authentication failed. The agent environment is not set up with credentials to call other Google Cloud services."
    except httpx.RequestError as e:
        logging.error(f"Error calling camera service: {e}")
        return f"Error: Could not connect to the camera service at {service_url}. Details: {e}"
    except Exception as e:
        logging.error(f"An unexpected error occurred when calling the camera service: {e}")
        return f"An unexpected error occurred when calling the camera service: {e}"
