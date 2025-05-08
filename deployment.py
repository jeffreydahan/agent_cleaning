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


load_dotenv()  # Load environment variables from .env file

# Helper function to get environment variables
def get_env_var(key):
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable '{key}' not found.")
    return value

PROJECT_ID = get_env_var("GOOGLE_CLOUD_PROJECT")
LOCATION = get_env_var("GOOGLE_CLOUD_LOCATION")
STAGING_BUCKET = get_env_var("GOOGLE_CLOUD_STORAGE_STAGING_BUCKET")

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

app = reasoning_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

from vertexai.preview import reasoning_engines

app = reasoning_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

session = app.create_session(user_id="u_123")
session

app.list_sessions(user_id="u_123")

session = app.get_session(user_id="u_123", session_id=session.id)
session

for event in app.stream_query(
    user_id="u_123",
    session_id=session.id,
    message="what is the status of the vacuum",
):
    print(event)