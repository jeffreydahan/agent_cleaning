from google.adk.agents import Agent

# Import Tools
from ...tools import capture_camera_stream

# Import prompts
from ...prompts import ip_camera_description, ip_camera_instruction

# root agent definition
camera_streamer = Agent(
    name="camera_streamer", # ensure no spaces here
    model="gemini-2.0-flash",
    description=ip_camera_description,
    instruction=ip_camera_instruction,
    tools=[
       capture_camera_stream,
    ],
)
