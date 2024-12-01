'''AMI Plug Conntroller'''
import sys
import subprocess

PACKAGES = ["tapo"]
for module in PACKAGES:
    try:
        __import__(module)
    except ImportError:
        print(f"{module} is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module])
        print(f"{module} has been installed.")

import os
import json
import argparse
import asyncio
from getpass import getpass
from tapo import ApiClient
from colorama import Fore, Style, init

SUBJECT="AMI EC Plug Control Panel"
SETUP_FILE = os.path.join(os.path.expanduser('~'), '.ami_ec_remote_plug')
global p100
global info
p100 = {}
tapo_info = {
    "username": "",
    "password": "",
    "ip": []
}

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
    while True:
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            output_message(f'{"=" * 50}')
            output_message(f"{SUBJECT:^50}", Fore.CYAN)
            output_message(f'{"=" * 50}')
            output_message(f"{'Index':<6} {'Device Name':<20} {'Power Status'}")
            output_message(f'{"-" * 50}')
            for index, (key, value) in enumerate(p100.items(), start=1):
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

        except KeyboardInterrupt:
            break

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
        client = ApiClient(info["username"], info["password"])
        output_message(f"Connecting to {ip} ...")
        device = await client.p100(ip)
        device_info = await device.get_device_info()
        device_name = device_info.to_dict().get("nickname", "Unknown")

        if ip in p100:
            ip = f"{ip}_1"

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
            await asyncio.sleep(power_interval)

    except KeyboardInterrupt as _:
        pass

async def main():
    parser = argparse.ArgumentParser(description="AMI EC plug controller")
    parser.add_argument("--username", "-u", type=str, help="Username / Email of Tapo account")
    parser.add_argument("--password", "-P", type=str, help="Password of Tapo account")
    parser.add_argument("--ip", "-i", type=str, help="IP address of the plug")
    parser.add_argument("--power_on", "-1", action="store_true", help="Turn on the plug")
    parser.add_argument("--power_off", "-0", action="store_true", help="Turn off the plug")
    parser.add_argument("--toggle", "-T", action="store_true", help="Toggle the power of the plug")
    parser.add_argument("--power_interval", "-t", type=int, help="The interval time (sec) to toggle/power the power of the plug")
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
        tapo_info["username"] = input("Enter Tapo account username: ", Fore.GREEN)

    if not tapo_info["password"]:
        tapo_info["password"] = getpass("Enter Tapo account password: ", Fore.GREEN)

    if not tapo_info["username"] or not tapo_info["password"]:
        output_message("No Tapo account username or password found", Fore.RED)
        sys.exit(1)

    await register_p10x(tapo_info)

    if (args.power_on or args.power_off or args.toggle) and args.ip:
        task_power_handler = asyncio.create_task(direct_power_control(p100[args.ip], args.power_on, args.toggle, args.power_interval))
    else:
        task_power_handler = asyncio.create_task(user_input_handler())

    await asyncio.gather(task_power_handler)

if __name__ == "__main__":
    init(autoreset=True)
    asyncio.run(main())
