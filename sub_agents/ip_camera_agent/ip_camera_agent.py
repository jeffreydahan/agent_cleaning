from google.adk.agents import Agent

# Import Tools
from ...tools import capture_camera_stream, copy_to_google_cloud_storage

# root agent definition
camera_streamer = Agent(
    name="camera_streamer", # ensure no spaces here
    model="gemini-2.0-flash",
    description="Agent to to capture a remote camera stream and copy it to a google cloud storage bucket and folder",
    instruction="""
        I am an agent that connects to a remote camera and captures a stream of video.  Then I upload the video to
        a folder in a google cloud storage bucket. I use tools for these activities.  
        
        First, I call capture_camera_stream with the room name as the argument.
        Example:  capture_camera_stream("demobooth")

        Finally, I send a status back to the root_agent per below: 

        When you provide the status back, tell the root_agent to call the cleaning_checker_agent to "Check the [ROOM] to see
        if it is clean or dirty".  Example for the 'demobooth': "Check the demobooth to see if it is clean or dirty"
        """,
    tools=[
       capture_camera_stream,
       copy_to_google_cloud_storage,
    ],
)
