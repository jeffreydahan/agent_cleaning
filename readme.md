# Background
This is a Google Agent Development Kit (ADK) Multi-Agent system which can check if a location is clean or dirty using an IP Camera, and then send a Roborock vacuum to clean the location. The following is the high level architecture and flow:
![image](https://github.com/user-attachments/assets/3fb51c71-2d2c-4257-bbc4-aa1f8ab6556b)


The following flow outlines how this Multi-Agent system operates:
- Cleaning Agent:  This agent handles the user request and agent/sub-agent responses.  It routes the agentic requests between the sub-agents as needed.
- Camera Agent:  This sub-agent handles the capture of an IP Camera video stream and copies it to a Google Cloud Storage Bucket.
- Cleaning Checker:  This sub-agent determines if a room's floor is clean or dirty based upon the video/image stored from the Camera sub-agent.  The folder structure needs to have a subfolder for each room.  For example, if you have a home with a kitchen and hallway that you want to check, build the following in Google Cloud Storage.
```
GCS Bucket
|--hallway
   |--movie.mov
|--kitchen
   |--movie.mov
```
- Roborock Agent:  This sub-agent handles all Roborock operations

ADK can be downloaded from here:
- https://github.com/google/adk-python

This is a personal development project and is not related to Google or Roborock professionally or at a partnership level.  

Gemini Code Assist was extremely valuable with this effort and saved many hours related to trying different structures and especially with debugging errors. 

This agent allows for natural language interaction with your Roborock device. The Agent translates your natural language chat inputs into valid commanda by making use of the functions (tools) defined in the agent files file

This agent makes use of the python-roborock library:
- https://github.com/Python-roborock/python-roborock

# Current Roborock Sub-Agent Features
The current features are also listed in the agent.py root_agent instructions
- get_status (this command gets the current status of the Roborock)
- app_charge (this command sends the Roborock back to the dock)
- app_start_wash (this command starts the washing of the mop while docked)
- app_stop_wash (this command stops the washing of the mop while docked)
- app_start (this command starts vacuuming and mopping job)
- app_stop (this command stops the vacuuming and mopping job)
- app_pause (this command pauses the vacuuming and mopping job)
- app_start_collect_dust (this command starts emptying the dust bin)
- app_stop_collect_dust (this command stops emptying the dust bin)
- get_room_mapping (gets a list of the rooms in a map)
- app_segment_clean (starts cleaning rooms or segments, single or multiple)

The commands are split into 3 function calls:
- get_status since it has a different command structure
- send_basic_command for commands with no extra arguments
- app_segment_clean for room cleaning commands since there are extra list arguments for the room index

Some of the above command separation was due to issues with passing optional parameters.  This needs some work.

# Installation Steps
Create a python virtual environment
```
python -m venv .venv
```

Install all pre-requisites using. I ran a pip freeze command which output all requirements. You will likely already have most of them satisfied. 
```
pip install -r requirements.txt
```

Following the installation, ensure you run
'''
pip freeze > requirements.txt
'''
in the same directory as your 'agent.py'.  This will ensure you have the latest
requirements set for later deployment below.

Then create a .env file at the root of the directory with the following information (you can rename the 'rename.env' file to serve as the basis for the '.env' file):

# Running locally
From the directory above agent_cleaning,
```
adk web
```
then browse to http://localhost:8000 to begin configuration and testing
# Agent Configuration
After the above installation, you will need to update the room mapping in your instructions.  You can do this using the output of the get_room_mappings function from the agent after you run locally below.  You can see from the output here, they are only returned as identifiers and not your actually room names.
![image](https://github.com/user-attachments/assets/440a02d4-66fd-446b-bd2b-8f71b83c8715)
And on the left side, you can see and scroll to get all of your room indexes (in this case starting at 16)
![image](https://github.com/user-attachments/assets/f55ee86d-9587-4520-93cf-c86018f88fbd)
Next, add your indexes to the instructions section of your root_agent
```
Segment mapping:
16 = Bedroom4
17 = Balcony
18 = Bedroom3
...
```
Next using the placeholders I have here, ask the agent to clean Bedroom 4.
![image](https://github.com/user-attachments/assets/76092257-9ed2-4010-8fcd-178f0248a5b6)
Now in the Roborock App, you can see which room actually will be cleaned.
![image](https://github.com/user-attachments/assets/851bfff1-1104-4f11-9093-bd83c2cca364)
Now update the instructions line for 16 with your actual room name. You can type stop immediately and keep iterating until complete without having to return to the dock.

You can also ask the agent to clean multiple rooms since it will pass the segment numbers as a python dictionary
# Limitations and Issues
You must add a mapping manually in the agent.py root_agent instruction sections to let the agent know which room name corresponds to which segment name.  See above for how to do this.

# Bonus - Deploy to Agent Engine
There are some additional options be deloy to Google Agent Engine
- https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview

Make sure you run the scripts below from the same folder as 'agent.py'

In order to deploy the agent to Agent Engine, run the following command:
```
python3 deploy_to_agent_engine.py
```
This will take 5 to 10 for the deployment to complete.  At this point, you can run some test queries using 'query_agent_engine.py'.  You can modify the 'message' variable towards the bottom of the file to adjust your query.  You will see the output in the console.  To run the query, run the following command:
```
python3 query_agent_engine.py
```
# Bonus #2 - Deploy the Agent to Google Agentspace
Google Agentspace is Google's Agentic AI and Enterprise search hub.  
- https://cloud.google.com/agentspace/docs/overview
You can deploy custom agents to this platform.  Run the following command:
```
deploy_to_agentspace.sh
```
Next you will see your custom agent in the 'Agents' section of Agentspace under 'Your Agents'.  Click the agent to interact. 
![image](https://github.com/user-attachments/assets/29aff263-8a1d-4ddf-8c20-f34b354a8611)
