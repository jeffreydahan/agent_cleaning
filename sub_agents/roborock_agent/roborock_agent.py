# Import ADK Agent and other libraries
from google.adk.agents import Agent
import os  # Import the os module for environment variables
from dotenv import load_dotenv

# Import Roborock libraries
from roborock import HomeDataProduct, DeviceData, RoborockCommand
from roborock.version_1_apis import RoborockMqttClientV1, RoborockLocalClientV1
from roborock.web_api import RoborockApiClient


load_dotenv()  # Load environment variables from .env file

# Global variables to hold the MQTT client and device
mqtt_client = None
device = None

# Helper function to get environment variables
def get_env_var(key):
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Environment variable '{key}' not found.")
    return value

# Login to Roborock (will only run if mqtt_client is None)
async def ensure_login():
    global mqtt_client
    global device
    if mqtt_client is None:
        try:
            web_api = RoborockApiClient(username=get_env_var('ROBOROCK_USERNAME'))
            user_data = await web_api.pass_login(password=get_env_var('ROBOROCK_PASSWORD'))
            home_data = await web_api.get_home_data_v2(user_data)
            device_data = home_data.devices[0]
            product_info: dict[str, HomeDataProduct] = {
                product.id: product for product in home_data.products
            }
            device = DeviceData(device_data, product_info[device_data.product_id].model)
            mqtt_client = RoborockMqttClientV1(user_data, device)
            await mqtt_client.async_connect()
            print("Roborock login successful.")
            return True
        except Exception as e:
            print(f"Roborock login failed: {e}")
            mqtt_client = None
            device = None
            return False
    return True

# Resets Roborock login and session
async def reset_connection():
    global mqtt_client
    global device
    if mqtt_client:
        try:
            await mqtt_client.async_disconnect()
            print("MQTT client disconnected.")
        except Exception as e:
            print(f"Error disconnecting MQTT client: {e}")
        finally:
            mqtt_client = None
            device = None
            print("Roborock connection reset.")

# Get Roborock status
async def get_status():
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    try:
        status = await mqtt_client.get_status()
        print("Current Status:")
        print(status)
        return {
            "state": status.state_name,
            "battery": status.battery,
            "clean_time": status.clean_time,
            "clean_area": status.square_meter_clean_area,
            "error": status.error_code_name,
            "fan_speed": status.fan_power_name,
            "mop_mode": status.mop_mode_name,
            "docked": status.state_name == "charging"
        }
    except Exception as e:
        print(f"Error getting status: {e}")
        await reset_connection()
        return {"error": f"Error getting status: {e}. Connection reset."}

# Send basic Roborock commands that don't have parameters
async def send_basic_command(command: str) -> str:
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    try:
        await mqtt_client.send_command(command)
        print(f"Command sent: {command}")
        return {"result": f"Command {command} sent successfully."}
    except Exception as e:
        print(f"Error sending {command}: {e}")
        await reset_connection()
        return {"error": f"Error sending {command}: {e}. Connection reset."}

# cleans a specific room also known as segment. To Do is to make this dynamic based upon desired segment from instructions mapping in the Agent definition below. 
async def app_segment_clean(segment_number: dict) -> str:
    if not await ensure_login():
        return {"error": "Not logged in to Roborock."}
    command = "app_segment_clean"
    try:
        segment = await mqtt_client.send_command(command, [{"segments": segment_number, "repeat": 1}])
        print(f"Command sent: {command}")
        return segment
    except Exception as e:
        print(f"Error sending {command}: {e}")
        await reset_connection()
        return {"error": f"Error sending {command}: {e}. Connection reset."}

# root agent definition
roborock_agent = Agent(
    name="roborock_agent",
    model="gemini-2.0-flash",
    description="Agent to control and get status of your Roborock vacuum",
    instruction="""You are an agent that controls and gets the status of a Roborock vacuum.

        **How to respond to instructions:**

        1.  **Get Status:**
            - If you are asked for the vacuum's status (e.g., "provide the vacuum status", "what is the battery level?", or if you are told "The Hallway is clean, please provide the vacuum status"), you MUST call the `get_status` function.

        2.  **Clean a Specific Room (after being told it's dirty):**
            - If you are instructed to clean a specific room because it has been identified as dirty (e.g., "The Living Room is dirty. Please clean the Living Room."), you must:
                a. Identify the room name from the instruction (e.g., "Living Room").
                b. Find the corresponding segment number for that room from the `Segment mapping` below.
                c. Call the `app_segment_clean` function, passing the segment number as a list of integers. For example, to clean 'Living Room' (segment 26), call `app_segment_clean([26])`. If instructed to clean multiple specific rooms, include all their segment numbers, e.g., `app_segment_clean([21, 22])`.

        3.  **Direct Basic Commands:**
            - For the following direct commands, use the `send_basic_command` function with the command name as a string argument (e.g., `send_basic_command("app_charge")`):
                - `app_charge` (sends the Roborock back to the dock)
                - `app_start_wash` (starts the washing of the mop while docked)
                - `app_stop_wash` (stops the washing of the mop while docked)
                - `app_start` (starts a general vacuuming and mopping job)
                - `app_stop` (stops the current vacuuming and mopping job)
                - `app_pause` (pauses the current vacuuming and mopping job)
                - `app_start_collect_dust` (starts emptying the dust bin)
                - `app_stop_collect_dust` (stops emptying the dust bin)
                - `get_room_mapping` (gets a list of the rooms in a map)

        4.  **Direct Room Cleaning Command (User directly asks you to clean):**
            - If the user directly commands you to clean a specific room without a prior cleanliness check (e.g., "Clean the Kitchen"), identify the room, find its segment number from the mapping, and call `app_segment_clean` with the segment number(s).

        **Segment mapping:**
        16 = Bedroom4
        17 = Balcony
        18 = Bedroom3
        19 = Bathroom
        20 = Hallway
        21 = Kitchen
        22 = Dining Room
        23 = Entryway
        24 = Bedroom1
        25 = Bedroom2
        26 = Living Room

        **Important:** If you are passed a simple statement like "Kitchen is dirty" without an explicit instruction to clean, clarify if cleaning is required or ask for a more specific command. However, if the `root_agent` tells you "[Room] is dirty. Please clean the [Room].", proceed with cleaning.
        """,
    tools=[
        get_status,
        send_basic_command,
        app_segment_clean,
    ],
)
