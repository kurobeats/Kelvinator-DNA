# Kelvinator-DNA

Reverse-engineered Python library for controlling **Kelvinator/Electrolux** air conditioner units that use the **BroadLink DNA protocol** (devtype 20379 / `0x4F9B`).

## Quick Start

```python
from kelvinator_dna.device import KelvinatorDevice
from kelvinator_dna.commands import ACMode, FanSpeed, SwingMode, ACState

# Connect to your AC (credentials from devices.json)
dev = KelvinatorDevice(
    ip="192.168.1.100",
    did="00000000000000000000a043b036bff4",
    mac="a0:43:b0:36:bf:f4",
    aes_key="99293543659c5b0caf659134ead8817f",
    password=754770058,
)

with dev:
    dev.authenticate()

    # Get current status
    status = dev.get_status()
    print(status)  # power=ON, mode=COOL, temp=22°C, fan=AUTO

    # Set cooling to 22°C with auto fan
    dev.set_power(True)
    dev.set_mode(ACMode.COOL)
    dev.set_temperature(22)
    dev.set_fan_speed(FanSpeed.AUTO)
    dev.send_control()
```

## Architecture

```
Kelvinator App → libNetworkAPI.so (JNI) → UDP Port 80 → AC Unit (a0:43:b0:xx)
                    ↓ AES-128-ECB
                  DNA Protocol Packets
```

The protocol stack:
1. **Cloud API** (HTTPS/REST) — Device discovery, credential retrieval
2. **DNA Protocol** (UDP) — Packet framing with magic bytes + checksum
3. **AES-128-ECB** — Payload encryption with per-device key
4. **TFB** — Type-Field-Body binary serialization format

## Files

```
kelvinator_dna/
├── __init__.py      # Package exports
├── protocol.py      # DNA packet, AES encryption, TFB serialization
├── device.py        # High-level AC device control interface
├── commands.py      # ACMode, FanSpeed, SwingMode, ACState enums
├── cloud.py         # BroadLink cloud API client
├── cli.py           # Command-line interface
└── so_bridge.py     # ctypes bridge to libNetworkAPI.so

examples/
└── control_ac.py    # Example script

PROTOCOL.md          # Full protocol specification
```

## Getting Device Credentials

You need the AES key and device password for your AC. These are retrieved from
the BroadLink cloud API after authentication.

**Option 1: MITM proxy** (easiest)
1. Set up a MITM proxy (mitmproxy, Burp Suite)
2. Install the proxy CA on your phone
3. Open the Kelvinator app — credentials appear in the `/ec4/v1/family/getallinfo` response

**Option 2: Cloud API**
```python
from kelvinator_dna.cloud import KelvinatorCloud

cloud = KelvinatorCloud(license_id="your-license-id")
cloud.authenticate()
devices = cloud.discover_devices()
for d in devices:
    print(f"{d.name}: AES key={d.aes_key}, password={d.password}")
```

## CLI Usage

```bash
# Install
pip install -e .

# Discover devices on the local network
kelvinator-cli discover

# Query status
kelvinator-cli status -d devices.json -i 192.168.1.100

# Control
kelvinator-cli control -d devices.json -i 192.168.1.100 \
    --power-on --mode cool --temp 22 --fan auto
```

## Requirements

- Python 3.8+
- `pycryptodome` (for AES-128-ECB)

## Protocol Documentation

See [PROTOCOL.md](PROTOCOL.md) for the complete protocol specification including:
- Packet format diagrams
- Command IDs and parameter mappings
- Encryption details
- Cloud API endpoints
- Internal library architecture

## License

MIT