from google.adk.agents import Agent

# Import Tools
from ...tools import check_if_dirty

# Import prompts
from ...prompts import cleaning_checker_description, cleaning_checker_instruction

# root agent definition
cleaning_checker = Agent(
    name="cleaning_checker", # ensure no spaces here
    model="gemini-2.0-flash",
    description=cleaning_checker_description,
    instruction=cleaning_checker_instruction,
    tools=[
       check_if_dirty,
    ],
)