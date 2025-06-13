
# Import ADK Agent and other libraries
from google.adk.agents import Agent

# Import Tools
from ...tools import get_status, send_basic_command, app_segment_clean

# Import prompts
from ...prompts import roborock_description, roborock_instruction

# root agent definition
roborock_agent = Agent(
    name="roborock_agent",
    model="gemini-2.0-flash",
    description=roborock_description,
    instruction=roborock_instruction,
    tools=[
        get_status,
        send_basic_command,
        app_segment_clean,
    ],
)
