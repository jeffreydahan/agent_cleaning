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

"""Cleaning checker to automatically clean rooms by first calling
an agent to check media files for a room and then calling Roborock vacuum
if the room requires cleaning."""

from google.adk.agents import SequentialAgent

from .sub_agents.roborock_agent import roborock_agent
from .sub_agents.cleaning_checker import cleaning_checker


agent_cleaning = SequentialAgent(
    name='agent_cleaning',
    description=(
        """Cleaning checker to automatically clean rooms by first calling
        an agent to check media files for a room and then calling Roborock vacuum
        if the room requires cleaning.

        DIRECTIONS
        It can be possible to send commands directly to the sub_agent roborock_agent if the context is:
        - checking a status
        - sending a direct command like clean the kitchen
        - any command that is not asking about the cleanliness of a room

        Otherwise, do the following:
        First, always determine if a room is dirty by using the sub_agent cleaning_checker
        If the room is clean, do nothing and simply say that the room is clean and no action is required
        If the room is dirty, call the subagent roborock_agent and pass it the response from cleaning_checker
        """
    ),  
    sub_agents=[roborock_agent, cleaning_checker],
)

root_agent = agent_cleaning