# Deploys the agent.py root_agent (and all dependent agents)
# to Vertex AI Agent Engine

# Import everything from the agent.py
from .agent import root_agent

# Import Vertex AI
import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines

# Import Tools
from .tools import get_env_var


# Import packages to assist with writing/reading env variables
from dotenv import set_key, find_dotenv, load_dotenv, get_key
import os
load_dotenv()

# Set variables from env
project_id=get_env_var("GOOGLE_CLOUD_PROJECT")
staging_bucket=get_env_var("GOOGLE_CLOUD_STORAGE_STAGING_BUCKET")
location=get_env_var("GOOGLE_CLOUD_LOCATION")
agent_description=get_env_var("AGENT_DESCRIPTION")
agent_name=get_env_var("AGENT_NAME")
roborock_username=get_env_var("ROBOROCK_USERNAME")
roborock_password=get_env_var("ROBOROCK_PASSWORD")
cleaning_bucket=get_env_var("GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET")
camera_tool_service_url = get_env_var("CAMERA_TOOL_SERVICE_URL")



# initialitze vertexai
vertexai.init(
    project=project_id,
    location=location,
    staging_bucket=staging_bucket,
)


# Create app object and set tracing
app = reasoning_engines.AdkApp(
    agent=root_agent, # This is set to the root_agent from agent.py
    enable_tracing=True,
)


# Importing all requirements previously set with 
# pip freeze > requirements.txt
# print current directory
import os
print(os.getcwd())

requirements_path = "agent_cleaning/requirements.txt"
with open(requirements_path, "r") as f:
    requirements_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]


# Specific environment variables that you want to pass
# to be included with Agent Engine Deployment
env_vars = {
    "GOOGLE_CLOUD_STORAGE_STAGING_BUCKET": staging_bucket,
    "ROBOROCK_USERNAME": roborock_username,
    "ROBOROCK_PASSWORD": roborock_password,
    "GOOGLE_CLOUD_STORAGE_CLEANING_BUCKET": cleaning_bucket,
    "CAMERA_TOOL_SERVICE_URL": camera_tool_service_url,
    "AGENT_DESCRIPTION": agent_description,
    "AGENT_NAME": agent_name,
}

# Upload the ADK Agent to Agent Engine
remote_app = agent_engines.create(
    agent_engine=root_agent,
    requirements=requirements_list,
    display_name=agent_name,
    description=agent_description,
    extra_packages=[
        "agent_cleaning/agent.py", 
        "agent_cleaning/tools.py", 
        "agent_cleaning/prompts.py"
    ],
    env_vars=env_vars
)

print(remote_app.resource_name)

# Set the Agent Engine Agent ID to an env variable for use in the next phase of
# deploying to Agentspace if desired. This script updates the .env file with
# the new resource ID.
dotenv_path = "agent_cleaning/.env"  # Relative to project root
set_key(dotenv_path, "AGENT_ENGINE_APP_RESOURCE_ID", remote_app.resource_name)
print(f"AGENT_ENGINE_APP_RESOURCE_ID='{remote_app.resource_name}' has been set in {dotenv_path}")

# Verify the key was written correctly to the .env file
print(f"Verifying AGENT_ENGINE_APP_RESOURCE_ID in {dotenv_path}...")
written_value = get_key(dotenv_path, "AGENT_ENGINE_APP_RESOURCE_ID")
if written_value == remote_app.resource_name:
    print(f"Successfully verified AGENT_ENGINE_APP_RESOURCE_ID: {written_value}")
    # Update the current process's environment for consistency.
    os.environ["AGENT_ENGINE_APP_RESOURCE_ID"] = remote_app.resource_name
else:
    print(f"Error: AGENT_ENGINE_APP_RESOURCE_ID could not be verified in {dotenv_path}. Expected '{remote_app.resource_name}', got '{written_value}'")

# now setting the env variable in the current environment for AGENT_ENGINE_APP_RESOURCE_ID
os.environ["AGENT_ENGINE_APP_RESOURCE_ID"] = remote_app.resource_name

# You can see this agent inside of Vertex AI Agent Engine.  You can delete it from
# the Google Cloud Console if desired.  If you get an error, ensure you have
# deleted all sessions in the Agent first.