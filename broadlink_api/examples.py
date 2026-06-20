"""
Example usage of the Broadlink NetworkAPI Python reimplementation.

This demonstrates the full API surface matching the original
libNetworkAPI.so JNI library.
"""

import json
import logging
from broadlink_api import NetworkAPI, BroadlinkDevice

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("broadlink_api")


def example_sdk_init():
    """Initialize the SDK."""
    api = NetworkAPI()

    result = api.sdk_init({
        "loglevel": 3,       # Debug
        "localctrl": True,   # Enable local LAN control
    })
    print("SDKInit result:", json.dumps(result, indent=2))
    return api


def example_device_discovery(api):
    """Discover devices on the local network."""
    print("\n--- Device Discovery ---")

    result = api.device_probe({
        "timeout": 5.0,
    })
    print("deviceProbe result:", json.dumps(result, indent=2))

    if result.get("status") == 0:
        for dev in result.get("list", []):
            print(f"  Found: {dev}")
    return result


def example_device_pair(api):
    """Pair with a discovered device."""
    print("\n--- Device Pairing ---")

    # Replace with actual discovered device info
    pair_info = {
        "ip": "192.168.1.100",
        "mac": "b4:43:0d:12:34:56",
        "type": "0x2712",         # RM2 IR Controller
        "did": "0x12345678",
        # "key": "097628343fe99e23765c1513accf8b02",  # Optional
    }

    result = api.device_pair(pair_info)
    print("devicePair result:", json.dumps(result, indent=2))
    return result


def example_device_control(api):
    """Control a device."""
    print("\n--- Device Control ---")

    device_info = {
        "ip": "192.168.1.100",
        "mac": "b4:43:0d:12:34:56",
        "type": "0x2712",
        "did": "0x12345678",
        "key": "097628343fe99e23765c1513accf8b02",
    }

    # Turn on (for SP plug) or send IR (for RM)
    result = api.dna_control(
        device_info=device_info,
        data={"pwr": 1},
    )
    print("dnaControl result:", json.dumps(result, indent=2))

    # Get device status
    result = api.dna_control(
        device_info=device_info,
        data={"cmd": "status"},
    )
    print("dnaControl (status) result:", json.dumps(result, indent=2))


def example_cloud_auth(api):
    """Authenticate with the Broadlink cloud."""
    print("\n--- Cloud Authentication ---")

    result = api.bl_sdk_auth(
        license_id="your_license_id",
        license_key="your_license_key",
        company_id="your_company_id",
        app_id="com.example.app",
        app_version="1.0.0",
        phone_id="android_12345",
        phone_os="Android",
        country="CN",
    )
    print("bl_sdk_auth result:", json.dumps(result, indent=2))
    return result


def example_easyconfig(api):
    """Provision a device with WiFi credentials."""
    print("\n--- EasyConfig WiFi Provisioning ---")

    result = api.bl_easyconfig({
        "ssid": "MyHomeWiFi",
        "password": "my_wifi_password",
        "security": "wpa2",
        "timeout": 75,
    })
    print("bl_easyconfig result:", json.dumps(result, indent=2))


def example_sunrise_sunset(api):
    """Calculate sunrise and sunset times."""
    print("\n--- Sunrise/Sunset Calculator ---")

    result = api.calculate_sunrise_sunset({
        "longitude": 121.47,
        "latitude": 31.23,
        "timezone": 8,
        "year": 2024,
        "month": 6,
        "day": 20,
    })
    print("calculateSunriseSunset result:", json.dumps(result, indent=2))


def example_device_profile(api):
    """Get device profile."""
    print("\n--- Device Profile ---")

    result = api.device_profile({
        "pid": "rm2_home_control",
    })
    print("deviceProfile result:", json.dumps(result, indent=2))


def example_ir_control(api):
    """IR code operations (for RM series controllers)."""
    print("\n--- IR Code Operations ---")

    # Get IR code information for a TV brand
    result = api.device_red_code_information({
        "category": "TV",
        "brand": "Samsung",
    })
    print("deviceRedCodeInfomation result:", json.dumps(result, indent=2))

    # Get specific IR code data
    result = api.device_red_code_data({
        "code_id": "tv_samsung_power",
    })
    print("deviceRedCodeData result:", json.dumps(result, indent=2))


def example_license_info(api):
    """Get license information."""
    print("\n--- License Info ---")

    result = api.license_info({})
    print("LicenseInfo result:", json.dumps(result, indent=2))


def example_using_broadlink_device_directly():
    """Use the BroadlinkDevice class directly (lower-level API)."""
    print("\n--- Direct Device API ---")

    # Discover devices
    devices = BroadlinkDevice.discover(timeout=5.0)
    print(f"Discovered {len(devices)} device(s):")
    for dev in devices:
        print(f"  {dev}")

    if devices:
        dev = devices[0]
        # Authenticate
        ok = dev.auth()
        print(f"Auth: {ok}, device_id=0x{dev.device_id:08X}")

        if ok:
            # Get device info
            info = dev.get_device_info()
            print(f"Device info: {info}")

            # Get status
            status = dev.get_status()
            print(f"Status: {status}")


def example_with_callbacks():
    """Demonstrate using callbacks for cloud API integration."""
    print("\n--- Callback-based Cloud Integration ---")

    api = NetworkAPI()
    api.sdk_init({"loglevel": 2, "localctrl": False})

    # Register a network callback that forwards to your HTTP client
    def my_network_callback(operation: str, params_json: str) -> str:
        """Called whenever the SDK needs to make a cloud API call."""
        print(f"  Cloud API call: {operation}")
        print(f"  Params: {params_json}")

        # In a real app, you'd make the actual HTTP request here
        # and return the JSON response

        # Simulated response
        responses = {
            "sdk_auth": '{"status":0,"userid":"user123","access_token":"tok_xxx"}',
            "device_bind": '{"status":0,"msg":"bound"}',
            "device_status": '{"status":0,"data":{"pwr":1}}',
        }
        return responses.get(operation, '{"status":0}')

    api.set_network_callback(my_network_callback)

    # Now cloud operations will use your callback
    result = api.bl_sdk_auth(license_id="test")
    print(f"  Auth result: {result}")

    result = api.device_bind_with_server({"did": "0x12345678"})
    print(f"  Bind result: {result}")


if __name__ == "__main__":
    print("=" * 60)
    print("Broadlink NetworkAPI Python SDK - Examples")
    print("=" * 60)

    api = example_sdk_init()

    # LAN operations
    example_device_discovery(api)
    # example_device_pair(api)      # Uncomment with real device
    # example_device_control(api)   # Uncomment with real device

    # WiFi provisioning
    # example_easyconfig(api)       # Uncomment to test

    # Utility
    example_sunrise_sunset(api)
    example_license_info(api)

    # IR operations (requires callback or cloud access)
    # example_ir_control(api)

    # Device profiles
    # example_device_profile(api)

    # Cloud operations (requires callbacks)
    example_with_callbacks()

    # Direct device API
    # example_using_broadlink_device_directly()
