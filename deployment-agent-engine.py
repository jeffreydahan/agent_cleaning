# In adk/agent_cleaning/deployment.py
from vertexai.preview import reasoning_engines



import vertexai
import os
from dotenv import load_dotenv

# Corrected import: Use a relative import since deployment.py is in the same package as agent.py
from .agent import root_agent
# If you need to explicitly load sub_agents for registration with LocalApp/AdkApp:
from .sub_agents.roborock_agent import roborock_agent
from .sub_agents.cleaning_checker import cleaning_checker

from vertexai import agent_engines
from pydantic import BaseModel

class ContentDict(BaseModel):
    content: str


load_dotenv()  # Load environment variables from .env file

# Helper function to get environment variables
def get_env_var(key):
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable '{key}' not found.")
    return value

PROJECT_ID = get_env_var("GOOGLE_CLOUD_PROJECT")
LOCATION = get_env_var("GOOGLE_CLOUD_LOCATION")
STAGING_BUCKET = "gs://" + get_env_var("GOOGLE_CLOUD_STORAGE_STAGING_BUCKET")


vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

from vertexai import agent_engines



remote_app = agent_engines.create(
    agent_engine=root_agent,
    requirements=[
        "google-cloud-aiplatform[adk,agent_engines]",
    ]
)

remote_app.resource_name

print(remote_app.resource_name)



