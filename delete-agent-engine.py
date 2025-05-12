import vertexai
from vertexai import agent_engines
from vertexai.preview import reasoning_engines  # Import reasoning_engines
from dotenv import load_dotenv
import os  # Import the 'os' module
from pydantic import BaseModel

# Corrected import: Use a relative import since deployment.py is in the same package as agent.py
from .agent import root_agent
# If you need to explicitly load sub_agents for registration with LocalApp/AdkApp:
from .sub_agents.roborock_agent import roborock_agent
from .sub_agents.cleaning_checker import cleaning_checker



load_dotenv()

# Helper function to get environment variables
def get_env_var(key):
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable '{key}' not found.")
    return value


# Replace with your project ID and location
PROJECT_ID = get_env_var("GOOGLE_CLOUD_PROJECT")
LOCATION = get_env_var("GOOGLE_CLOUD_LOCATION")

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# List all Agent Engines
agent_engines_list = agent_engines.AgentEngine.list()

if agent_engines_list:
    print("Existing Agent Engine deployments:")
    for engine in agent_engines_list:
        print(f"- {engine.resource_name}")

else:
    print("No Agent Engine deployments found in this project and location.")

########## be careful on which engine you are deleting!  
# engine to delete
engine_name_to_delete = ""
for engine in agent_engines_list:
    if engine.name == engine_name_to_delete:
        agent_engines.AgentEngine.delete(engine.name)
        print(f"Deleted Agent Engine: {engine.name}")
        break