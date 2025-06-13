from google.adk.agents import Agent

# Import Tools
from ...tools import check_if_dirty

# root agent definition
cleaning_checker = Agent(
    name="cleaning_checker", # ensure no spaces here
    model="gemini-2.0-flash",
    description="Agent to check videos and images to see if they are dirty or clean based upon their room specified, and then send its 'Final Decision' back to the root agent.",
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
Your task is to:
1. Call the 'check_if_dirty' tool.
2. Present the full report (including Name/Path, Floor Type, Description, Summary, and Final Decision) to the user.

    ***Important***
    After presenting the full report, your very last step is to transfer back to the root_agent.
    To do this, your final output message MUST BE *ONLY* the 'Final Decision' string that the tool provided.
    For example, if the tool's report includes "Final Decision: The demobooth is dirty, please clean it.", your final output message to the root_agent should be exactly:
    "The demobooth is dirty, please clean it."
    Do not add any other text or explanation around this final message. This ensures the root_agent receives the precise instruction it needs for the roborock_agent.
    """,
    tools=[
       check_if_dirty,
    ],
)