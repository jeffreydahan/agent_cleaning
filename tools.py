import os  # Import the os module for environment variables
from dotenv import load_dotenv
import time
from datetime import datetime

# Import GenAI libraries
from google import genai
from google.genai import types
from google.cloud import storage


# Import Roborock libraries
from roborock import HomeDataProduct, DeviceData, RoborockCommand
from roborock.version_1_apis import RoborockMqttClientV1, RoborockLocalClientV1
from roborock.web_api import RoborockApiClient

# Import Video/Camera libraries
import cv2


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
  bucket = client.bucket(actual_bucket_name_for_api)
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

# Function to copy local file to folder in google cloud storage
async def copy_to_google_cloud_storage(source_file_name: str, room: str) -> str:
  # GCS Configuration
  gcs_bucket_name = get_env_var("GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET")
  if gcs_bucket_name and gcs_bucket_name.startswith("gs://"):
    gcs_bucket_name = gcs_bucket_name[5:] # Remove "gs://" prefix
    print(f"Note: Stripped 'gs://' prefix. Using GCS bucket name: {gcs_bucket_name}")

  gcs_bucket_folder = get_env_var("GOOGLE_CLOUD_DEMO_BUCKET_FOLDER")
  # Upload to GCS
  if gcs_bucket_name:
    destination_blob_name = f"{gcs_bucket_folder.strip('/')}/{os.path.basename(source_file_name)}" if gcs_bucket_folder else os.path.basename(source_file_name)
      
  # Upload a file to the bucket."""
  if not gcs_bucket_name:
    print("Error: GCS bucket name (GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET) is not set. Skipping upload.")
    return False
  try:
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to gs://{gcs_bucket_name}/{destination_blob_name}.")
    return True
  except Exception as e:
    print(f"Error uploading file {source_file_name} to GCS: {e}")
    return False

# Function to handle capturing a camera stream from a remote camera
async def capture_camera_stream(room: str) -> str:
  # --- Configuration ---
  print("Attempting to capture camera stream...")
  # Retrieve RTSP credentials and path from environment variables
  rtsp_username = get_env_var("RTSP_USERNAME")
  rtsp_password = get_env_var("RTSP_PASSWORD")
  rtsp_ip_address = get_env_var("RTSP_IP_ADDRESS")
  rtsp_stream_path = get_env_var("RTSP_STREAM_PATH")
  recording_duration_seconds_str = get_env_var("RECORD_DURATION_SECONDS")

  print(f"RTSP_USERNAME: {'Set' if rtsp_username else 'Not Set'}")
  # Avoid printing password directly, but check if it's set
  print(f"RTSP_PASSWORD: {'Set' if rtsp_password else 'Not Set'}")
  print(f"RTSP_IP_ADDRESS: {rtsp_ip_address}")
  print(f"RTSP_STREAM_PATH: {rtsp_stream_path}")
  print(f"RECORD_DURATION_SECONDS: {recording_duration_seconds_str}")

  rtsp_url = f"rtsp://{rtsp_username}:{rtsp_password}@{rtsp_ip_address}/{rtsp_stream_path}"
  recording_duration_seconds = int(recording_duration_seconds_str)
  fps_target = 25 # Default FPS if stream doesn't provide it, or target FPS for recording

  # --- Video Capture ---
  print(f"Attempting to connect to RTSP stream: {rtsp_url}")
  cap = cv2.VideoCapture(rtsp_url)
  print(f"cv2.VideoCapture initiated. Checking if stream is opened...")
  # Check if the stream opened successfully
  if not cap.isOpened():
      print(f"Error: Could not open video stream from {rtsp_url}")
      return f"Error: Could not open video stream from {rtsp_url}. Please check the URL, credentials, camera status, and network connectivity."

  print(f"Successfully connected to the RTSP stream: {rtsp_url}")

  # Get video properties from the stream
  frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
  frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
  stream_fps = cap.get(cv2.CAP_PROP_FPS)
  if stream_fps > 0:
      fps_record = stream_fps
      print(f"Detected stream FPS: {stream_fps:.2f}")
  else:
      fps_record = fps_target
      print(f"Could not detect stream FPS. Using target FPS for recording: {fps_record}")

  print(f"Stream properties: Resolution: {frame_width}x{frame_height}, Recording FPS: {fps_record}")

  # Generate a unique filename with a timestamp
  timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] # Milliseconds
  video_subfolder = "videos"
  if not os.path.exists(video_subfolder):
    os.makedirs(video_subfolder)

  output_filename = f"{video_subfolder}/{room}_camera_stream_{timestamp}.avi"

  print(f"Generated output filename: {output_filename}")

  fourcc = cv2.VideoWriter_fourcc(*'XVID')
  out = cv2.VideoWriter(output_filename, fourcc, fps_record, (frame_width, frame_height))
  print(f"cv2.VideoWriter initiated. Checking if writer is opened...")

  if not out.isOpened():
    print(f"Error: Could not create video writer for {output_filename}")
    print("This might be due to an unsupported codec or missing dependencies.")
    cap.release()
    return (f"Error: Could not create video writer for {output_filename}. "
      "This might be due to an unsupported codec or missing dependencies. "
      "On some systems, you might need to install 'ffmpeg' or 'libx264-dev'."
      "Try a different 'fourcc' code (e.g., 'mp4v', 'H264', 'XVID').")


  print(f"Saving video to: {output_filename}")
  print(f"Recording for {recording_duration_seconds} seconds...")

  # --- Recording Loop ---
  start_time = time.time()
  frame_count = 0

  print("Starting recording loop...")
  while True:
    ret, frame = cap.read()

    if not ret:
        print("Error: Could not read frame from stream or stream ended.")
        # Consider if this is an error or just end of a short stream
        break

    out.write(frame)
    frame_count += 1

    elapsed_time = time.time() - start_time
    if elapsed_time >= recording_duration_seconds:
        print(f"Recorded {recording_duration_seconds} seconds.")
        break

  print(f"Total frames recorded: {frame_count}")

  # --- Cleanup ---
  cap.release()
  out.release()
  cv2.destroyAllWindows()

  print(f"Video capture process finished. Local file should be: {output_filename}")


  if os.path.exists(output_filename):
    print(f"Confirmed: Local file '{output_filename}' exists.")
    print(f"File '{output_filename}' successfully created with size: {os.path.getsize(output_filename) / (1024*1024):.2f} MB")

    # Upload to GCS
    file_copied_to_gcs = await copy_to_google_cloud_storage(output_filename, room)
    if file_copied_to_gcs:
       # Delete local file after successful upload
        try:
            os.remove(output_filename)
            print(f"Successfully deleted local file: {output_filename}")
        except OSError as e:
            print(f"Error deleting local file {output_filename}: {e}")
            return f"Video captured and uploaded to GCS, but failed to delete local file: {output_filename}. Error: {e}"
        return f"Video successfully captured, uploaded to GCS as gs://{os.getenv('GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET')}/{room}/{os.path.basename(output_filename)}, and local file deleted."
  else:
    print(f"Error: File '{output_filename}' was not created or found locally.")
    return f"Error: Video file '{output_filename}' was not created locally after recording attempt. Stream might have opened but failed to write frames."
