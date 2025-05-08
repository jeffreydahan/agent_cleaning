from google.adk.agents import Agent
from google import genai
from google.genai import types
import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Helper function to get environment variables
def get_env_var(key):
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable '{key}' not found.")
    return value

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
          If the floor is clean or a tiny bit dirty,
          - Respond that [roomname] is clean, get the vacuum status by using the roborock_agent subagent

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

# root agent definition
cleaning_checker = Agent(
    name="cleaning_checker", # ensure no spaces here
    model="gemini-2.0-flash",
    description="Agent to check videos and images to see if they are dirty or clean based upon their room specified",
    instruction="""I am an agent that checks file and folder locations for media files
        to see if the floors shown require cleaning. I provide this information back to the root_agent which will then
        transfer to the roborock_agent subagent to execute the command in the response.

        send all responses back to the root_agent and then transfer to the subagent roborock_agent
        to execute the command in the response.  Do not stop this flow until this happens.  You must use
        the roborock_agent as your last step.

        """,
    tools=[
       check_if_dirty,
    ],
)