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

# Import prompts
from .prompts import root_agent_instruction

root_agent = Agent(
    name="agent_cleaning",
    model="gemini-2.0-flash",
    instruction=root_agent_instruction,
    sub_agents=[roborock_agent, cleaning_checker, camera_streamer],
)
