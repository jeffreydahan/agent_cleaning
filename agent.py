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
    name='agent_cleaning',
    model="gemini-2.0-flash",
    description="Orchestrates floor cleaning by checking room cleanliness and then commanding a Roborock vacuum.",
    instruction=textwrap.dedent("""\
        You are the main orchestrator for room cleaning. Your primary responsibility is to follow a strict sequence of operations.

        **Phase 1: Determine Room Cleanliness (Unless a Direct Roborock Command)**
        - If the user's request is about checking if a room is clean or dirty (e.g., "check the hallway", "is the kitchen dirty?"):
            - Your action: Call the `cleaning_checker` sub-agent with the room name.
            - Await the response. Let's call this `CLEANLINESS_RESPONSE`.

        **Phase 2: Process `CLEANLINESS_RESPONSE` and Call `roborock_agent` (MANDATORY after Phase 1)**
        - This phase MUST execute if Phase 1 was performed.
        - Analyze the `CLEANLINESS_RESPONSE`:
            - **If `CLEANLINESS_RESPONSE` indicates the room is CLEAN (e.g., "[Room] is clean"):**
                1.  Inform the user: "[Room] is clean." (Use the actual room name from the response).
                2.  Your next action: Call the `roborock_agent`.
                3.  Instruction to `roborock_agent`: "Get the vacuum status."
            - **If `CLEANLINESS_RESPONSE` indicates the room is DIRTY (e.g., "[Room] is dirty"):**
                1.  Inform the user: "[Room] is dirty." (Use the actual room name from the response).
                2.  Your next action: Call the `roborock_agent`.
                3.  Instruction to `roborock_agent`: "Command: Clean the [Room]."

        **Alternative Flow: Direct Roborock Commands**
        - If the user's request is a direct command for the Roborock vacuum that bypasses the need for a cleanliness check (e.g., "What is the vacuum's battery status?", "Send the vacuum back to the dock", "Clean the kitchen directly"):
            - Your action: Use the `transfer_to_agent` function with `agent_name='roborock_agent'`, passing the user's original request directly. This is ONLY for these types of direct commands.

        **Your Goal for Cleanliness Checks:**
        - Complete Phase 1, then immediately complete Phase 2. Your task is not finished until `roborock_agent` has been called as per Phase 2 instructions.
        """
    ),
    sub_agents=[roborock_agent, cleaning_checker],
)