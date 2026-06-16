#!/usr/bin/env python3
"""
Example: Control a Kelvinator/Electrolux AC unit.

This script demonstrates how to:
1. Load cached device credentials (from a JSON file)
2. Connect to an AC unit via UDP
3. Query status and set control parameters
4. Discover devices on the local network

Setup:
  1. Create a file called devices.json with your device credentials:
     {
       "devices": [{
         "did": "00000000000000000000a043b036bff4",
         "mac": "a0:43:b0:36:bf:f4",
         "name": "master bedroom aircon",
         "aes_key": "99293543659c5b0caf659134ead8817f",
         "password": 754770058,
         "devtype": 20379,
         "pid": "0000000000000000000000009b4f0000"
       }]
     }

  2. Run: python examples/control_ac.py --device devices.json --action status
"""

import argparse
import json
import logging
import sys
import os

# Add parent directory to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kelvinator_dna.device import KelvinatorDevice, discover_devices
from kelvinator_dna.cloud import load_cached_devices, save_cached_devices
from kelvinator_dna.commands import ACMode, FanSpeed, SwingMode, ACState


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )


def cmd_discover(args):
    """Discover devices on the local network."""
    print("Discovering devices on the local network...")
    devices = discover_devices(timeout=args.timeout)
    if not devices:
        print("No devices found.")
        return

    print(f"\nFound {len(devices)} device(s):")
    for d in devices:
        print(f"  IP: {d['ip']}")
        print(f"  MAC: {d['mac']}")
        print(f"  DID: {d['did']}")
        print(f"  Name: {d.get('name', 'Unknown')}")
        print()

    # Save for later use
    if args.output:
        save_cached_devices(devices, args.output)
        print(f"Saved to {args.output}")


def cmd_status(args):
    """Query device status."""
    devices = load_cached_devices(args.device_file)
    if not devices:
        print("No devices found in config file.")
        return

    dev_info = devices[0]  # Use first device
    if args.ip:
        dev_ip = args.ip
    else:
        print("Please specify device IP with --ip")
        return

    dev = KelvinatorDevice(
        ip=dev_ip,
        did=dev_info.did,
        mac=dev_info.mac,
        aes_key=dev_info.aes_key,
        password=dev_info.password,
    )

    with dev:
        dev.authenticate()
        status = dev.get_status()
        print(f"Device: {dev_info.name}")
        print(f"Status: {status}")


def cmd_control(args):
    """Send control command to device."""
    devices = load_cached_devices(args.device_file)
    if not devices:
        print("No devices found in config file.")
        return

    dev_info = devices[0]
    if not args.ip:
        print("Please specify device IP with --ip")
        return

    dev = KelvinatorDevice(
        ip=args.ip,
        did=dev_info.did,
        mac=dev_info.mac,
        aes_key=dev_info.aes_key,
        password=dev_info.password,
    )

    # Build state
    state = ACState()
    if args.power_on:
        state.power = True
    elif args.power_off:
        state.power = False
    if args.mode is not None:
        mode_map = {'cool': 0, 'heat': 1, 'auto': 2, 'fan': 3, 'dry': 4}
        state.mode = mode_map.get(args.mode, 0)
    if args.temp:
        state.temp = args.temp
    if args.fan:
        fan_map = {'auto': 0, 'low': 1, 'med': 2, 'high': 3}
        state.fan = fan_map.get(args.fan, 0)
    if args.swing:
        swing_map = {'off': 0, 'vert': 1, 'horiz': 2, 'both': 3}
        state.swing = swing_map.get(args.swing, 0)
    if args.sleep:
        state.sleep = True
    if args.turbo:
        state.turbo = True

    print(f"Sending: {state}")
    with dev:
        dev.authenticate()
        dev.set_state(state)
        print("Control command sent.")


def main():
    parser = argparse.ArgumentParser(
        description="Kelvinator/Electrolux AC Controller"
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Discover
    p_discover = subparsers.add_parser('discover', help='Discover devices on the network')
    p_discover.add_argument('-t', '--timeout', type=float, default=3.0, help='Discovery timeout')
    p_discover.add_argument('-o', '--output', default='discovered_devices.json', help='Output file')

    # Status
    p_status = subparsers.add_parser('status', help='Query device status')
    p_status.add_argument('-d', '--device-file', required=True, help='Device credentials JSON')
    p_status.add_argument('-i', '--ip', help='Device IP address')

    # Control
    p_control = subparsers.add_parser('control', help='Control the AC')
    p_control.add_argument('-d', '--device-file', required=True, help='Device credentials JSON')
    p_control.add_argument('-i', '--ip', help='Device IP address')
    p_control.add_argument('--power-on', action='store_true', help='Turn power on')
    p_control.add_argument('--power-off', action='store_true', help='Turn power off')
    p_control.add_argument('--mode', choices=['cool', 'heat', 'auto', 'fan', 'dry'], help='AC mode')
    p_control.add_argument('--temp', type=int, help='Target temperature (16-30°C)')
    p_control.add_argument('--fan', choices=['auto', 'low', 'med', 'high'], help='Fan speed')
    p_control.add_argument('--swing', choices=['off', 'vert', 'horiz', 'both'], help='Swing mode')
    p_control.add_argument('--sleep', action='store_true', help='Enable sleep mode')
    p_control.add_argument('--turbo', action='store_true', help='Enable turbo mode')

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == 'discover':
        cmd_discover(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'control':
        cmd_control(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
