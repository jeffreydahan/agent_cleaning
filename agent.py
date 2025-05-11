# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from google.adk.agents import Agent
import textwrap

from .sub_agents.roborock_agent import roborock_agent
from .sub_agents.cleaning_checker import cleaning_checker

root_agent = Agent(
    name="agent_cleaning",
    model="gemini-2.0-flash",
    description="Orchestrates floor cleaning by checking room cleanliness and then commanding a Roborock vacuum.",
    instruction=textwrap.dedent("""\
        - always transfer back to the root agent after all commands!  Then transfer to the roborock agent for the final command.  Let the user know you did this
        - if you get roborock commands directly (like get status of the vacuum or clean [room(s)]),
        transfer to the roborock agent and execute
        - if you are asked about if a room is clean or not, transfer to the cleaning checker.
        then take that output and transfer to the root agent and take the command and 
        transfer to the roborock agent.  The Roborock agent should always be the final sub_agent
        that executes any activity.
        - ALWAYS transfer to the roborock agent as the final step.  if for some reason
        the roborock agent is not getting called as the final step, force it via taking the 
        response (if a room is dirty) and sending it along, or if the room is clean, get the status
        """
    ),
    sub_agents=[roborock_agent, cleaning_checker],
)
