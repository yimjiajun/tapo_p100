'''AMI Plug Conntroller'''
import sys
import subprocess

PACKAGES = ["tapo", "ttkthemes", "colorama"]
for module in PACKAGES:
    try:
        __import__(module)
    except ImportError:
        print(f"{module} is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module])
        print(f"{module} has been installed.")

import threading
import os
import json
import argparse
import asyncio
from getpass import getpass
from tapo import ApiClient
from colorama import Fore, Style, init
from tkinter import ttk, PhotoImage
from ttkthemes import ThemedTk

SUBJECT="AMI EC Plug Control Panel"
SETUP_FILE = os.path.join(os.path.expanduser('~'), '.ami_ec_remote_plug')
ICON_FILE = 'ami.png'
global p100
global info
p100 = {}
tapo_info = { "username": None, "password": None, "ip": [] }
tkinter_button_event = []

def tkinter_insert_button_event(device: dict):
    """
    Insert the button event to the tkinter_button_event list

    Parameters:
    - device: The device object (p100)

    Returns:
    - None
    """
    device["tkinter"]["button"].config(text="Processing", state="disabled", cursor="watch")
    tkinter_button_event.append(device)

async def tkinter_button_handler():
    """
    Handle the button event
    Process the button event in the tkinter_button_event list
    """
    try:
        while True:
            events = tkinter_button_event.copy()

            for event in events:
                await toggle(event)
                power_button_display = "Turn Off" if event["power"] else "Turn On"
                style_button_display = 'On.TButton' if event["power"] else "Off.TButton"
                event["tkinter"]["button"].config(text=power_button_display, state="enabled", cursor="", style=style_button_display)
                tkinter_button_event.remove(event)

            if check_only_active_main_threads():
                break

            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass

class TkinterDevice:
    """
    TkinterDevice class
    """
    def __init__(self):
        """
        Initialize the TkinterDevice class
        """
        pass

    def setup_window_at_center(self, window, width, height):
        """
        Setup the window at the center of the screen

        Parameters:
        - window: The window object
        - width: The width of the window
        - height: The height of the window

        Returns:
        - None
        """
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        window_widthInc = (screen_width // 2) - (width // 2)
        window_heightInc = (screen_height // 2) - (height // 2)
        window.geometry('{}x{}+{}+{}'.format(width, height, window_widthInc, window_heightInc))

    def initialize(self):
        """
        Initialize the TkinterDevice class and setup the window
        running the main loop
        """
        col = 5
        root = ThemedTk(theme='black')
        root.title(SUBJECT)
        root.protocol("WM_DELETE_WINDOW", root.quit)
        root.resizable(False, False)

        try:
            path = os.path.dirname(__file__)
        except Exception as _:
            path = os.curdir

        for path_root, dirs, files in os.walk(path):
            if ICON_FILE in files:
                icon_file_path = os.path.join(path_root, ICON_FILE)
                icon = PhotoImage(file=icon_file_path)
                root.iconphoto(True, icon, icon)
                break

        frame = ttk.Frame(root)
        # Set background color for the button
        style = ttk.Style(root)
        style.configure('On.TButton', background='yellow', foreground='black')
        style.map('On.TButton', background=[('active', '#FFCC00')])
        style.configure('Off.TButton', foreground='yellow')
        style.map('Off.TButton', background=[('active', 'grey')])
        style.configure('Invalid.TButton', foreground='black')
        style.map('Invalid.TButton', background=[('disabled', 'grey')])

        for index, key in enumerate(p100):
            p100[key]["tkinter"] = {}
            row_dev_title_align = int(int(index / col + 1) * 2)
            row_dev_button_align = row_dev_title_align + 1
            col_dev_align = int(index % col)
            frame.grid_rowconfigure(row_dev_title_align, weight=1) # Title of device name
            frame.grid_rowconfigure(row_dev_button_align, weight=1) # Button of device
            frame.grid_columnconfigure(col_dev_align, weight=1) # column of device position
            # Setup title of device name
            label = ttk.Label(frame, text=p100[key]["name"], font=("Helvetica", 12))
            label.grid(row = row_dev_title_align, column = col_dev_align, sticky = "ns")
            label.config(anchor="center")
            p100[key]["tkinter"]["label"] = label
            # power behavior
            if p100[key]["power"] is not None:
                power_status = "On" if p100[key]["power"] else "Off"
                # Indicate next step of behavior when press button
                power_button_display = "Turn Off" if power_status == "On" else "Turn On"
                style_button_display = 'On.TButton' if power_status == "On" else "Off.TButton"
                button = ttk.Button(frame, text=power_button_display, width=10)
                button.config(command=lambda i=p100[key]: tkinter_insert_button_event(i), style=style_button_display)
            else:
                power_button_display = 'Invalid'
                style_button_display = 'Invalid.TButton'
                button = ttk.Button(frame, text=power_button_display, width=10)
                button.config(command=None, style=style_button_display)
            button.grid(row = row_dev_button_align, column = col_dev_align, sticky = "ns")
            p100[key]["tkinter"]["button"] = button

        if len(p100) == 0:
            frame.grid_rowconfigure(0, weight=1) # Title of device name
            frame.grid_columnconfigure(0, weight=1) # column of device position
            label = ttk.Label(frame, text="NO Available Device", font=("Helvetica", 12))
            label.grid(row = 0, column = 0, sticky = "ns")
            label.config(anchor="center")

        frame.pack(expand=True, fill="both")
        min_size = 200
        max_size = 800
        width = min_size * len(p100)
        height = min_size * int(len(p100) / col)
        self.setup_window_at_center(root,
                               max(min_size, min(width, max_size)),
                               max(min_size, min(height, max_size)))
        root.mainloop()

def output_message(msg: str, color: str = Fore.RESET, end: str = "\n"):
    """
    output_message the message with color

    Parameters:
    - msg: The message to be output_messageed
    - color: The color of the message

    Returns:
    - None
    """
    try:
        print(color + msg + Style.RESET_ALL, end=end)
    except Exception as _:
        print(msg, end=end)

async def user_input_handler():
    """
    Handle user input

    Returns:
    - None
    """
    invalid_message = None
    user_input = None
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            output_message(f'{"=" * 50}')
            output_message(f"{SUBJECT:^50}", Fore.CYAN)
            output_message(f'{"=" * 50}')
            output_message(f"{'Index':<6} {'Device Name':<20} {'Power Status'}")
            output_message(f'{"-" * 50}')
            for index, (key, value) in enumerate(p100.items(), start=1):
                if value["object"] is None:
                    output_message(f"{index:^6} {value['name']:<20} {'N/A':<3}", Fore.RED)
                    continue
                power_status = "On" if value["power"] else "Off"
                output_message(f"{index:^6} {value['name']:<20} {power_status:<3}", Fore.LIGHTYELLOW_EX if value["power"] else Fore.RESET)
            output_message(f'{"-" * 50}')

            output_message(f"Enter 0 ~ {len(p100)} to select device toggle power. Enter 'refresh'/'r' to refresh the device list. Enter 'exit' to exit.", end="")

            if invalid_message is not None:
                output_message(f" {invalid_message}", Fore.RED, end="")
            user_input = input("\n")
            invalid_message = None

            if user_input.lower() in ["exit", "quit", "q"]:
                break

            if user_input.lower() in ["refresh", "r"]:
                await register_p10x(tapo_info)
                continue

            if "," in user_input:
                couple_index = user_input.split(",")

                if not all([i.isdigit() for i in couple_index]):
                    invalid_message = f"Invalid input ({user_input})"
                    output_message(f"{invalid_message}", Fore.RED)
                    continue

                couple_index = [int(i) for i in couple_index]

                for i in couple_index:
                    if i <= 0 or i > len(p100):
                        invalid_message = f"Skip invalid index {i}" if invalid_message is None else f"{invalid_message}, {i}"
                        output_message(f"{invalid_message}", Fore.RED)
                        continue

                    _, value = list(p100.items())[i - 1]
                    await toggle(value)

                continue

            if "-" in user_input:
                start, end = user_input.split("-")
                if not start.isdigit() or not end.isdigit():
                    invalid_message = f"Invalid input ({user_input})"
                    output_message(f"{invalid_message}", Fore.RED)
                    continue

                start, end = int(start), int(end)
            elif not user_input.isdigit():
                invalid_message = f"Invalid input ({user_input})"
                output_message(f"{invalid_message}", Fore.RED)
                continue
            else:
                start = end = int(user_input)

            if start == 0 or end == 0:
                invalid_message = f"Invalid Index ({start})"
                output_message(f"{invalid_message}", Fore.RED)
                continue

            if start > end or start < 0 or end > len(p100):
                if start == end:
                    invalid_message = f"Invalid Index ({start})"
                else:
                    invalid_message = f"Invalid Range ({start} - {end})"

                output_message(f"{invalid_message}", Fore.RED)
                continue

            for i in range(start, end + 1):
                _, value = list(p100.items())[i - 1]
                await toggle(value)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass

async def register_p10x(info: dict):
    """
    Register P10x plug object

    Parameters:
    - info: The information of the plug
        - username: The username of the Tapo account
        - password: The password of the Tapo account
        - ip: The IP(s) address of the plug

    Returns:
    - None
    """
    for ip in info["ip"]:
        if any([ip == key for key in p100.keys()]):
            continue

        try:
            client = ApiClient(info["username"], info["password"], timeout_s = 2)
            output_message(f"Connecting to {ip} ... ", end="")
            device = await client.p100(ip)
            device_info = await device.get_device_info()
            device_name = device_info.to_dict().get("nickname", "Unknown")

            p100[ip] = {
                "name": device_name,
                "object": device,
                "action": {
                        "on": device.on,
                        "off": device.off,
                        "info": device.get_device_info,
                        "usage": device.get_device_usage
                    },
                "power": device_info.to_dict().get("device_on", False)
            }
            output_message(f"Success => {device_name}", Fore.GREEN)
        except Exception as e:
            p100[ip] = {
                "name": ip,
                "object": None,
                "action": None,
                "power": None,
            }
            output_message("Failure", Fore.RED)

async def power_on(device: dict):
    """
    Turn on the plug

    Parameters:
    - device: The device object of Tapo

    Returns:
    - The power status of the plug
        - True: The plug is on
        - False: Failed to turn on the plug
    """
    if device["object"] is None:
        return False

    await device["action"]["on"]()
    device_info = await device["action"]["info"]()
    device["power"] = device_info.to_dict().get("device_on", False)

    return device["power"] is True

async def power_off(device: dict):
    """
    Turn off the plug

    Parameters:
    - device: The device object of Tapo

    Returns:
    - The power status of the plug
        - True: The plug is off
        - False: Failed to turn off the plug
    """
    if device["object"] is None:
        return False

    await device["action"]["off"]()
    device_info = await device["action"]["info"]()
    device["power"] = device_info.to_dict().get("device_on", True)

    return device["power"] is False

async def toggle(device: dict):
    """
    Toggle the power of the plug

    Parameters:
    - device: The device object of Tapo

    Returns:
    - The power status of the plug
        - True: The plug is on
        - False: The plug is off
    """
    if device["object"] is None:
        return False

    device_info = await device["action"]["info"]()
    device["power"] = device_info.to_dict().get("device_on", True)

    toggle_power = "off" if device["power"] else "on"
    await device["action"][toggle_power]()

    device_info = await device["action"]["info"]()
    device["power"] = device_info.to_dict().get("device_on", False)

    return device["power"]

async def direct_power_control(device: dict, power_switch: bool = False, toggle_power_switch: bool = False, power_interval: int = 0):
    """
    Directly control the power of the plug

    Parameters:
    - device: The device object of Tapo
    - power_on: The power status of the plug
        - True: Turn on the plug
        - False: Turn off the plug
    - power_interval: The interval time (sec) to toggle/power the power of the plug

    Returns:
    - None
    """
    try:
        while True:
            if toggle_power_switch:
                await toggle(device)
            else:
                if power_switch:
                    await power_on(device)
                else:
                    await power_off(device)

            output_message(f"{device['name']} is {'On' if device['power'] else 'Off'}")

            if power_interval == 0:
                break

            await asyncio.sleep(power_interval)

    except KeyboardInterrupt as _:
        pass

def check_only_active_main_threads():
    """
    Check only active main threads is running

    Parameters:
    - None

    Returns:
    - True: Only active main threads is running
    - False: More than one active threads is running
    """
    active_threads = threading.enumerate()

    if threading.active_count() == 1 and active_threads[0].name == "MainThread":
        return True

    return False

async def main():
    parser = argparse.ArgumentParser(description="AMI EC plug controller")
    parser.add_argument("--username", "-u", type=str, help="Username / Email of Tapo account")
    parser.add_argument("--password", "-P", type=str, help="Password of Tapo account")
    parser.add_argument("--ip", "-I", type=str, help="IP address of the plug")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--power_on", "-1", action="store_true", help="Turn on the plug")
    parser.add_argument("--power_off", "-0", action="store_true", help="Turn off the plug")
    parser.add_argument("--toggle", "-T", action="store_true", help="Toggle the power of the plug")
    parser.add_argument("--power_interval", "-t", type=int, help="The interval time (sec) to toggle/power the power of the plug", default=0)
    args = parser.parse_args()

    try:
        with open(SETUP_FILE, "r") as f:
            data = json.load(f)

        tapo_info["username"] = data.get("username", None)
        tapo_info["password"] = data.get("password", None)
        tapo_info["ip"] = data.get("ip", [])
    except Exception as _:
        output_message(f"skip loading setup file {SETUP_FILE}", Fore.YELLOW)

    tapo_info["username"] = args.username if args.username else tapo_info["username"]
    tapo_info["password"] = args.password if args.password else tapo_info["password"]
    for ip in args.ip.split() if args.ip else []:
        tapo_info["ip"].append(ip)

    if len(tapo_info["ip"]) == 0:
        output_message("No plug IP address found", Fore.RED)
        sys.exit(1)

    if not tapo_info["username"]:
        tapo_info["username"] = input("Enter Tapo account username: ")

    if not tapo_info["password"]:
        tapo_info["password"] = getpass(f'Enter Tapo account "{tapo_info["username"]}" password: ')

    if not tapo_info["username"] or not tapo_info["password"]:
        output_message("No Tapo account username or password found", Fore.RED)
        sys.exit(1)

    await register_p10x(tapo_info)

    task_power_handlers = []
    if (args.power_on or args.power_off or args.toggle) and args.ip:
        for key, value in p100.items():
            if value["object"] is None:
                output_message(f"Invalid IP address {key}", Fore.RED)
                continue

            t = asyncio.create_task(direct_power_control(value, args.power_on, args.toggle, args.power_interval))
            task_power_handlers.append(t)
    elif args.interactive:
        t = asyncio.create_task(user_input_handler())
        task_power_handlers.append(t)
    else:
        t = asyncio.create_task(tkinter_button_handler())
        task_power_handlers.append(t)
        tkinter_dev = TkinterDevice()
        thread_tkinter = threading.Thread(target=tkinter_dev.initialize)
        thread_tkinter.start()

    await asyncio.gather(*task_power_handlers)

if __name__ == "__main__":
    init(autoreset=True)
    asyncio.run(main())
