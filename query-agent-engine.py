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
        print(f"- {engine.name}")
        print(engine)
else:
    print("No Agent Engine deployments found in this project and location.")


if agent_engines_list:
    # Get the resource name of the first deployed agent engine
    agent_engine_resource_name = agent_engines_list[0].name
    # Extract the agent ID from the resource name
    agent_engine_id = agent_engine_resource_name.split('/')[-1]
    print(f"Using Agent Engine ID: {agent_engine_id}")

    # Get the AgentEngine object by passing the resource name to the constructor
    agent_engine = agent_engines.AgentEngine(agent_engine_resource_name)

#     # Create an AdkApp from the deployed agent
#     app = reasoning_engines.AdkApp(agent=root_agent)  # Use root_agent here

#     # Now you can interact with the app (create sessions, query, etc.)

#     remote_session = app.create_session(user_id="u_456")
#     print(f"Created session: {remote_session}")


#     print("Querying the agent...")
#     for event in app.stream_query(
#         user_id="u_456",
#         session_id=remote_session.id,
#         message="Please clean the kitchen",
#     ):
#         print(event)  # Print the entire event
#         if event.get('role') == 'user':
#             print(f"Prompt: {event['content'][0]['text']}")
#         elif event.get('role') == 'agent' and event['content'][0].get('tool_use'):
#             tool_use = event['content'][0]['tool_use']
#             if tool_use['tool_name'] == 'roborock_agent':
#                 status = tool_use['output']['state']
#                 battery = tool_use['output']['battery']
#                 print(f"Status: {status}")
#                 print(f"Battery: {battery}")
#             else:
#                 print(f"Tool Use: {tool_use['tool_name']}")
#                 print(f"Tool Input: {tool_use['input']}")
#                 print(f"Tool Output: {tool_use['output']}")

# else:
#     print("No agent engines found. Cannot perform testing.")
