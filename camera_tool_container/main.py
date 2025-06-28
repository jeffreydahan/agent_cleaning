import os
import datetime
import subprocess
import logging
from flask import Flask, request, jsonify
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Helper function to get environment variables safely
def get_env_var(var_name: str) -> str | None:
    value = os.environ.get(var_name)
    if not value:
        logging.warning(f"Environment variable '{var_name}' is not set.")
    return value

# Function to copy local file to folder in Google Cloud Storage
def copy_to_google_cloud_storage(source_file_name: str, room: str) -> bool:
  # GCS Configuration
  gcs_bucket_name = get_env_var("GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET")
  if gcs_bucket_name and gcs_bucket_name.startswith("gs://"):
    gcs_bucket_name = gcs_bucket_name[5:] # Remove "gs://" prefix
    logging.info(f"Note: Stripped 'gs://' prefix. Using GCS bucket name: {gcs_bucket_name}")

  # The destination blob name should be inside a folder named after the room.
  destination_blob_name = f"{room}/{os.path.basename(source_file_name)}"
      
  # Upload a file to the bucket.
  if not gcs_bucket_name:
    logging.error("Error: GCS bucket name (GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET) is not set. Skipping upload.")
    return False
  try:
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    logging.info(f"File {source_file_name} uploaded to {gcs_bucket_name}/{destination_blob_name}.")
    return True
  except Exception as e:
    logging.error(f"Error uploading file {source_file_name} to GCS: {e}")
    return False

# Function to handle capturing a camera stream from a remote camera
def capture_camera_stream(room: str) -> str:
  # --- Configuration ---
  logging.info("Attempting to capture camera stream...")
  # Retrieve RTSP credentials and path from environment variables
  rtsp_username = get_env_var("RTSP_USERNAME")
  rtsp_password = get_env_var("RTSP_PASSWORD")
  rtsp_ip_address = get_env_var("RTSP_IP_ADDRESS")
  rtsp_stream_path = get_env_var("RTSP_STREAM_PATH")
  recording_duration_seconds_str = get_env_var("RECORD_DURATION_SECONDS") # type: ignore

  logging.info(f"RTSP_USERNAME: {'Set' if rtsp_username else 'Not Set'}")
  # Avoid printing password directly, but check if it's set
  logging.info(f"RTSP_PASSWORD: {'Set' if rtsp_password else 'Not Set'}")
  logging.info(f"RTSP_IP_ADDRESS: {rtsp_ip_address}")
  logging.info(f"RTSP_STREAM_PATH: {rtsp_stream_path}")
  logging.info(f"RECORD_DURATION_SECONDS: {recording_duration_seconds_str}")

  # Basic validation for essential RTSP parameters
  if not all([rtsp_username, rtsp_password, rtsp_ip_address, rtsp_stream_path, recording_duration_seconds_str]):
      return "Error: One or more essential RTSP configuration environment variables are missing."

  try:
      recording_duration_seconds = int(recording_duration_seconds_str)
  except ValueError:
      return "Error: RECORD_DURATION_SECONDS must be an integer."

  rtsp_url = f"rtsp://{rtsp_username}:{rtsp_password}@{rtsp_ip_address}/{rtsp_stream_path}"
  # fps_target = 25 # Default FPS if stream doesn't provide it, or target FPS for recording

  rtsp_url_print = f"rtsp://{rtsp_username}:xxxxxxx@{rtsp_ip_address}/{rtsp_stream_path}" # type: ignore
  logging.info(f"RTSP URL: {rtsp_url_print}")

  output_folder = "/tmp" # Use the only writable directory in Cloud Run
  timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
  output_filename = f"capture_{timestamp}.mp4"
  output_path = os.path.join(output_folder, output_filename)

  # --- Video Capture ---
  logging.info(f"Attempting to connect to RTSP stream")
  ffmpeg_command = [
    "ffmpeg",
    "-rtsp_transport", "tcp",
    "-i", rtsp_url,
    "-t", str(recording_duration_seconds),
    "-c:v", "copy",
    "-c:a", "aac", # Re-encode audio to AAC
    "-b:a", "128k", # Set audio bitrate
    "-strict", "experimental", # May be needed for some AAC encoders
     output_path,
  ]

  # Execute the ffmpeg command using subprocess.
  logging.info(f"Starting capture of {rtsp_url_print} for {recording_duration_seconds} seconds...")
  logging.info(f"Output file: {output_path}")
  
  try:
    # We use subprocess.run to execute the command.
    # `check=True` will raise an exception if ffmpeg exits with an error.
    # A timeout is added to prevent the script from hanging indefinitely.
    result = subprocess.run(
        ffmpeg_command, check=True, capture_output=True, text=True, timeout=recording_duration_seconds + 30 # Added some buffer for setup
    )
    logging.info("\nCapture successful!")
    logging.info("ffmpeg output (from stderr):\n" + result.stderr)
  except FileNotFoundError:
    logging.error("\nError: 'ffmpeg' command not found. Please ensure ffmpeg is installed and in your system's PATH.")
    return "Error: 'ffmpeg' command not found inside the container."
  except subprocess.CalledProcessError as e:
    logging.error(f"\nError during capture. ffmpeg exited with return code: {e.returncode}")
    logging.error("\nffmpeg stderr:\n" + e.stderr)
    return f"Error during video capture: {e.stderr}"
  except subprocess.TimeoutExpired as e:
    logging.error("\nError: ffmpeg command timed out. This could be due to a network issue or a problem with the camera stream.")
    if e.stderr:
        logging.error("\nffmpeg stderr:\n" + e.stderr)
    return "Error: Video capture timed out."

  logging.info(f"Video capture process finished. Local file should be: {output_path}")

  if os.path.exists(output_path):
    logging.info(f"Confirmed: Local file '{output_path}' exists.")
    logging.info(f"File '{output_path}' successfully created with size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")

    # Upload to GCS
    file_copied_to_gcs = copy_to_google_cloud_storage(output_path, room)
    if file_copied_to_gcs:
       # Delete local file after successful upload
        try:
            os.remove(output_path)
            logging.info(f"Successfully deleted local file: {output_path}")
        except OSError as e:
            logging.error(f"Error deleting local file {output_path}: {e}")
            return f"Video captured and uploaded to GCS, but failed to delete local file: {output_path}. Error: {e}"
        return f"Video successfully captured, uploaded to GCS as {os.getenv('GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET')}/{room}/{os.path.basename(output_path)}, and local file deleted."
  else:
    logging.error(f"Error: File '{output_path}' was not created or found locally.")
    return f"Error: Video file '{output_path}' was not created locally after recording attempt. Stream might have opened but failed to write frames."

@app.route('/', methods=['POST'])
def handle_trigger():
    # Cloud Run jobs or HTTP triggers often send a POST request with a JSON body
    # A 'room' must be specified in the JSON payload.
    data = request.get_json()
    if not data:
        logging.error("Request is missing a valid JSON body.")
        return jsonify({"status": "error", "message": "Bad Request: Missing or invalid JSON body."}), 400

    room = data.get('room')
    if not room:
        logging.error("'room' not specified in request payload.")
        return jsonify({"status": "error", "message": "Bad Request: 'room' must be specified in the JSON payload."}), 400

    logging.info(f"Received trigger for room: {room}")
    result_message = capture_camera_stream(room)
    
    if "Error" in result_message:
        return jsonify({"status": "error", "message": result_message}), 500
    else:
        return jsonify({"status": "success", "message": result_message}), 200

if __name__ == '__main__':
    # Cloud Run injects the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)