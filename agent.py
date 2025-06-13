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

from .sub_agents.roborock_agent import roborock_agent
from .sub_agents.cleaning_checker import cleaning_checker
from .sub_agents.ip_camera_agent import camera_streamer



root_agent = Agent(
    name="agent_cleaning",
    model="gemini-2.0-flash",
    instruction="""
        - always transfer back to the root agent after all commands!  Then transfer to the roborock agent for the final command.  Let the user know you did this
        - if you get roborock commands directly (like get status of the vacuum or clean [room(s)]),
        transfer to the roborock agent and execute
        - If you are asked if a room is clean or not (e.g., "Is the demobooth dirty?" or "check the hallway"):
            1. First, transfer to the `camera_streamer` subagent to capture the video of that room. Your instruction to `camera_streamer` should be simple, like "capture video for [ROOM_NAME]".
            2. The `camera_streamer` subagent will complete its task and then transfer back to you (the root_agent). Its final message to you will be in the format: "Check the [ROOM_NAME] to see if it is clean or dirty".
            3. When you receive this exact message from `camera_streamer`, you MUST use this entire string verbatim as the instruction when you immediately transfer to the `cleaning_checker` subagent. For example, if `camera_streamer` sends you "Check the demobooth to see if it is clean or dirty", you will then transfer to `cleaning_checker` with the instruction "Check the demobooth to see if it is clean or dirty".
            Do not add any other text or try to rephrase this instruction.
        - The Roborock agent should always be the final sub_agent
        that executes any activity.
        - ALWAYS transfer to the roborock agent as the final step.  if for some reason
        the roborock agent is not getting called as the final step, force it via taking the 
        response (if a room is dirty) and sending it along, or if the room is clean, get the status
        - Never ask or wait for confirmation for any roborock commands.  You can proceed to clean
        or get status automatically when instructed to do so.
        - Provide a summary of the description of the room/floor that the cleaning_checker_agent returned 
        and always continue to the next step of using the roborock_agent subagent.
        
        ***Important***
        When the cleaning_checker subagent returns its 'Final Decision' (e.g., "The Kitchen is dirty, please clean it." or "The Living Room is clean, please just get the roborock status."):
        1. You MUST take this 'Final Decision' string verbatim.
        2. You MUST use this exact string as the instruction when you transfer to the roborock_agent subagent.
        This ensures the roborock_agent receives the command in the format it expects. For example, if cleaning_checker returns "The Office is dirty, please clean it.", you will transfer to roborock_agent with the message "The Office is dirty, please clean it.".
        """,
    sub_agents=[roborock_agent, cleaning_checker, camera_streamer],
)
