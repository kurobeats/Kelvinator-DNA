# Broadlink NetworkAPI Python SDK

Python reimplementation of `libNetworkAPI.so` — the Broadlink DNA SDK native library
(Android JNI shared object). Reverse-engineered via Ghidra MCP from the ARMv7 binary.

**Binary version:** `2.0.49-6566c07` &nbsp;|&nbsp; **Python:** 3.8+ &nbsp;|&nbsp; **Tests:** 39 passing

---

## Overview

This library provides a drop-in Python equivalent of the `cn.com.broadlink.networkapi.NetworkAPI`
Java class, which previously required Android/JNI. It enables control of Broadlink smart home
devices (SP plugs, RM IR controllers, MP1 power strips, sensors, thermostats) from any
Python application on any platform.

### What Was Reverse-Engineered

The `libNetworkAPI.so` binary (3088 functions) was analyzed through the Ghidra MCP server.
Every JNI entry point was decompiled and traced to its internal implementation. The full
protocol, encryption scheme, device discovery mechanism, and callback architecture were
reconstructed. See **[`PROTOCOL.md`](PROTOCOL.md)** for the complete wire-level reference.

### Architecture Mapping

```
Original (Android)                              This Library (Python)
──────────────────                              ─────────────────────
Java → JNI → libNetworkAPI.so                   Python → broadlink_api
       │                                                 │
       ├── BLJSON (cJSON fork)                  →  stdlib json
       ├── AES-128-CBC encryption               →  cryptography library
       ├── UDP device discovery                 →  socket
       ├── EasyConfig/SmartConfig               →  socket broadcast
       ├── Java→cloud callback chain            →  Python callbacks
       └── Sunrise/sunset calculator            →  math
```

---

## Quick Start

### Installation

```bash
pip install -e /path/to/khome
```

Or copy the `broadlink_api/` directory into your project.

### Usage

```python
from broadlink_api import NetworkAPI

# 1. Initialize
api = NetworkAPI()
api.sdk_init({"loglevel": 3, "localctrl": True})

# 2. Discover devices on LAN
result = api.device_probe({"timeout": 5.0})
for device in result["list"]:
    print(f"Found {device['mac']} at {device['ip']}")

# 3. Pair (authenticate)
result = api.device_pair({
    "ip": "192.168.1.100",
    "mac": "b4:43:0d:12:34:56",
    "type": "0x2712",         # RM2 IR Controller
})

# 4. Control
result = api.dna_control(
    device_info={"ip": "...", "mac": "...", "type": "0x2712", "did": "...", "key": "..."},
    data={"pwr": 1},
)
```

### Lower-Level Device API

```python
from broadlink_api import BroadlinkDevice

devices = BroadlinkDevice.discover(timeout=5.0)
dev = devices[0]
dev.auth()
dev.set_power(True)
status = dev.get_status()
```

---

## Complete API Reference

| JNI Entry Point (original) | Python Method | Purpose |
|---|---|---|
| `SDKInit` | `sdk_init(config)` | Initialize SDK, set log level, filepath, local control mode |
| `bl_sdk_auth` (13 args) | `bl_sdk_auth(license_id, ...)` | Cloud authentication with Broadlink license |
| `deviceProbe` | `device_probe(options)` | UDP broadcast discovery of LAN devices |
| `devicePair` | `device_pair(pair_info)` | Authenticate and pair with a discovered device |
| `dnaControl` | `dna_control(device, sub, data, cmd)` | Send control command (local UDP or cloud) |
| `deviceProfile` | `device_profile(dev, sub, pid)` | Load product UI profile/script |
| `deviceProfile2` | `device_profile2(dev, sub)` | Load PID-based profile |
| `deviceStatusOnServer` | `device_status_on_server(params)` | Query device status from cloud |
| `deviceBindWithServer` | `device_bind_with_server(params)` | Bind device to cloud account |
| `bl_easyconfig` | `bl_easyconfig(config)` | SmartConfig WiFi provisioning |
| `deviceEasyConfigCancel` | `device_easyconfig_cancel()` | Cancel running EasyConfig |
| `deviceGetAPList` | `device_get_aplist(params)` | Get visible WiFi AP list |
| `deviceAPConfig` | `device_apconfig(config)` | Configure WiFi AP |
| `deviceRedCodeInfomation` | `device_red_code_information(p)` | Get IR code metadata (brands, categories) |
| `deviceRedCodeData` | `device_red_code_data(p)` | Get specific IR code data |
| `deviceGetResourcesToken` | `device_get_resources_token(d,p)` | Get cloud API resources token |
| `deviceSubControlTranslate` | `device_sub_control_translate(...)` | Gateway sub-device command translation |
| `calculateSunriseSunset` | `calculate_sunrise_sunset(params)` | Solar position calculator |
| `LicenseInfo` | `license_info(params)` | SDK version/license info |
| `setNetworkCallback` | `set_network_callback(cb)` | Register cloud HTTP handler |
| `setIRCodeCallback` | `set_ir_code_callback(cb)` | Register IR data handler |
| `setDeviceControlCallback` | `set_device_control_callback(cb)` | Register remote control handler |

---

## Supported Devices

| Device | Type Code | Capabilities |
|--------|-----------|-------------|
| SP1 | `0x0000` | Smart Plug — power on/off |
| SP2 | `0x2711` | Smart Plug — power on/off, energy monitoring |
| SP3 | `0x947A` | Smart Plug — power on/off, energy monitoring |
| SP3S | `0x9479` | Smart Plug — power on/off |
| SP4L | `0x2222` | Smart Plug — power on/off |
| RM2 | `0x2712` | IR/RF Controller — 433/315MHz RF + IR |
| RM4 | `0x51DA` | IR/RF Controller — enhanced range |
| RM Mini | `0x2737` | IR Controller — compact IR-only |
| MP1 | `0x4EB5` | Power Strip — 4 independent outlets |
| A1 | `0x2714` | Environmental Sensor — temp, humidity, light, noise, air quality |
| SC1 | `0x4EAD` | Smart Switch — wall switch replacement |
| Hysen | `0x4EAF` | Thermostat — heating/cooling control |

---

## Cloud Integration

When `localctrl` is `False`, all network operations delegate to registered Python callbacks:

```python
def my_network_handler(operation: str, params_json: str) -> str:
    """Called for: sdk_auth, device_bind, device_status, device_profile, etc."""
    url = {
        "sdk_auth": "https://api.broadlink.com.cn/sdk/auth",
        "device_bind": "https://api.broadlink.com.cn/device/bind",
    }[operation]
    response = requests.post(url, json=json.loads(params_json))
    return response.text

api.set_network_callback(my_network_handler)
```

This mirrors the original JNI callback architecture where the Java side handled all HTTP
requests and the `.so` library only handled protocol formatting and encryption.

---

## Project Structure

```
khome/
├── broadlink_api/
│   ├── __init__.py         # Package exports
│   ├── network_api.py      # Main API class (20+ methods matching JNI)
│   ├── device.py           # Low-level BroadlinkDevice class
│   ├── crypto.py           # AES-128-CBC + Broadlink checksum scheme
│   ├── protocol.py         # Packet builder/parser (56-byte header protocol)
│   └── examples.py         # Usage examples
├── tests/
│   ├── __init__.py
│   ├── test_crypto.py      # 13 crypto tests
│   ├── test_protocol.py    # 9 protocol tests
│   └── test_network_api.py # 17 API tests
├── PROTOCOL.md             # Complete wire-level protocol reference
├── README.md               # This file
└── pyproject.toml          # Build config
```

---

## Protocol Documentation

See **[PROTOCOL.md](PROTOCOL.md)** for the complete reverse-engineered protocol reference
including:

- JNI entry point map (all 24 exports with addresses)
- UDP discovery packet format (48 bytes)
- Command packet format (56-byte header + encrypted payload)
- AES-128-CBC encryption scheme with PKCS7 padding and checksum verification
- Authentication handshake (key derivation: `MD5(key + device_id_le)`)
- EasyConfig/SmartConfig WiFi provisioning packet format
- Global context structure layout at `0x00228698`
- Internal function call graphs
- Thread safety model (`pthread_rwlock`)
- BLJSON (cJSON fork) API mapping
- Complete error code table

---

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

39 tests covering:
- **Crypto**: PKCS7 padding, AES encrypt/decrypt, Broadlink checksum, key derivation
- **Protocol**: Packet building, response parsing, discovery packets, edge cases
- **API**: SDK init, device pairing, EasyConfig, sunrise/sunset, callbacks, error paths

---

## License

Reverse-engineered for educational and interoperability purposes. The Broadlink DNA SDK
is copyright Hangzhou Broadlink Technology Co., Ltd. This Python reimplementation
provides a compatible interface without using any Broadlink proprietary code.
