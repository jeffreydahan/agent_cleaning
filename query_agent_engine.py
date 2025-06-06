from dotenv import load_dotenv
import vertexai.agent_engines

load_dotenv()


from google.adk.agents import Agent
import vertexai

from dotenv import load_dotenv, find_dotenv
import os
load_dotenv()


# Helper function to get environment variables
def get_env_var(key):
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable '{key}' not found.")
    return value


# Get environment variables
project_id=get_env_var("GOOGLE_CLOUD_PROJECT")
# Use the consistent staging bucket environment variable name
# and ensure it has the 'gs://' prefix for vertexai.init()
staging_bucket_name_from_env = get_env_var("GOOGLE_CLOUD_STORAGE_STAGING_BUCKET")
if not staging_bucket_name_from_env.startswith("gs://"):
    staging_bucket = f"gs://{staging_bucket_name_from_env}"
else:
    staging_bucket = staging_bucket_name_from_env
location=get_env_var("GOOGLE_CLOUD_LOCATION")



from dotenv import set_key, find_dotenv
# Find the .env file (usually in the current directory or project root)
dotenv_path = find_dotenv(usecwd=True)
if not dotenv_path: # If .env is not found, default to creating one in the current directory
    dotenv_path = ".env"
load_dotenv(dotenv_path=dotenv_path, override=True) # Force reload from the .env file
agent_engine_id = os.getenv("AGENT_ENGINE_APP_RESOURCE_ID")



# initialitze vertexai
vertexai.init(
    project=project_id,
    location=location,
    staging_bucket=staging_bucket,
)

remote_app = vertexai.agent_engines.get(agent_engine_id)
remote_app_resource_name = remote_app.resource_name
remote_app_resource_name

user_id = "u_458"

remote_session = remote_app.create_session(user_id=user_id)
remote_session

remote_app.list_sessions(user_id=user_id)

session_object = remote_app.get_session(user_id=user_id, session_id=remote_session["id"])
session_object

for event in remote_app.stream_query(
    user_id="u_456",
    session_id=remote_session["id"],
    message="get the status of the vacuum",
):
    print(event)
