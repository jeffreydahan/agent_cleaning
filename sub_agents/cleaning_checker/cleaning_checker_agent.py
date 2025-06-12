from google.adk.agents import Agent

# Import Tools
from ...tools import check_if_dirty

# root agent definition
cleaning_checker = Agent(
    name="cleaning_checker", # ensure no spaces here
    model="gemini-2.0-flash",
    description="Agent to check videos and images to see if they are dirty or clean based upon their room specified, then send the response back to the root agent and then transfer to the roborock agent",
    instruction="""You are an agent that helps determine if a room's floor is dirty based on media files.
When asked to check a room (e.g., "Is the kitchen dirty?", "Check the living room floor"):
1. Identify the room name from the request.
2. Use the 'check_if_dirty' tool, passing the room name to it.
3. The 'check_if_dirty' tool will analyze the media and provide a detailed report including:
    - Name/Path to Video File
    - Floor Type
    - Description of items on the floor
    - A Summary (e.g., dirty, relatively clean, clean)
    - A Final Decision (e.g., "The [room_name] is dirty, please clean it." or "The [room_name] is clean, please just get the Roborock status.")
Your task is to call the tool and present this report to the user.
    """,
    tools=[
       check_if_dirty,
    ],
)