from google.adk.agents import Agent

# Import Tools
from ...tools import check_if_dirty

# root agent definition
cleaning_checker = Agent(
    name="cleaning_checker", # ensure no spaces here
    model="gemini-2.0-flash",
    description="Agent to check videos and images to see if they are dirty or clean based upon their room specified, then send the response back to the root agent and then transfer to the roborock agent",
    instruction="""I am an agent that checks file and folder locations for media files
        to see if the floors shown require cleaning than I provide this information back to the root_agent which will then
        transfer to the root agent and then to the roborock_agent subagent to execute the command in the response.

        send all responses back to the root_agent and then transfer to the subagent roborock_agent
        to execute the command in the response.  Do not stop this flow until this happens.  You must use
        the roborock_agent as your last step.

        """,
    tools=[
       check_if_dirty,
    ],
)