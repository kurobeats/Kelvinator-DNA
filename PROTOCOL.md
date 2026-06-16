# Kelvinator DNA Protocol Specification

> Reverse-engineered from the Kelvinator Home Comfort app (APK),
> libNetworkAPI.so (Ghidra analysis), and MITM traffic captures.

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Kelvinator Mobile App                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Java/Kotlin UI Layer                                     │ │
│  │  cn.com.broadlink.networkapi.NetworkAPI                   │ │
│  │    └─ public native dnaControl(String, String, String,   │ │
│  │         String, String) : String                          │ │
│  └───────────────────────┬──────────────────────────────────┘ │
│                          │ JNI                                │
│  ┌───────────────────────▼──────────────────────────────────┐ │
│  │  libNetworkAPI.so (ARM64/ARM native)                      │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  Entry points (JNI exports):                        │ │ │
│  │  │  • SDKInit     — Initialize library, load config    │ │ │
│  │  │  • dnaControl  — Main AC control function           │ │ │
│  │  │  • deviceProbe — Discover devices on LAN            │ │ │
│  │  │  • devicePair  — Pair with new device               │ │ │
│  │  │  • deviceProfile — Get device capabilities          │ │ │
│  │  │  • deviceStatusOnServer — Cloud status query        │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  Internal functions:                                 │ │ │
│  │  │  • networkapi_dna_control  — DNA protocol impl      │ │ │
│  │  │  • bl_data_pack           — Build DNA packets       │ │ │
│  │  │  • bl_data_tfb_encrypt    — TFB + AES encrypt       │ │ │
│  │  │  • bl_data_tfb_decrypt    — TFB + AES decrypt       │ │ │
│  │  │  • bl_tfb_checksum        — Compute packet checksum │ │ │
│  │  │  • bl_sdk_tfb_encode      — TFB serialization       │ │ │
│  │  │  • bl_sdk_tfb_decode      — TFB deserialization     │ │ │
│  │  │  • bl_checksum            — Simple byte sum         │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  Embedded mbedTLS fork (all functions prefixed      │ │ │
│  │  │  "broadlink_"):                                      │ │ │
│  │  │  • AES-128-ECB  (broadlink_cipher_*)                 │ │ │
│  │  │  • MD5          (broadlink_md5)                      │ │ │
│  │  │  • SHA1         (broadlink_sha1)                     │ │ │
│  │  │  • ECDH         (broadlink_ecdh_*)                   │ │ │
│  │  │  • ECDSA        (broadlink_ecdsa_*)                  │ │ │
│  │  │  • CTR_DRBG     (broadlink_ctr_drbg_*)              │ │ │
│  │  │  • X.509        (broadlink_x509_*)                  │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  Embedded Lua VM (broadlink_bvm_*):                  │ │ │
│  │  │  • Script file execution for device profiles         │ │ │
│  │  │  • cJSON integration (BLJSON_*)                      │ │ │
│  │  │  • API bridge (broadlink_api_lib)                    │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
     │                          │
     │ HTTPS (Cloud API)        │ UDP (Local Network)
     ▼                          ▼
┌──────────────┐     ┌──────────────────┐
│ BroadLink     │     │  Kelvinator AC   │
│ Cloud Server  │     │  (a0:43:b0:xx)  │
│ ibroadlink.com│     │  Port 80/UDP    │
└──────────────┘     └──────────────────┘
```

---

## 2. Layer 1: Cloud API (HTTPS)

### 2.1 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/ec4/v1/common/api` | Get API key (initial handshake) |
| POST | `/ec4/v1/user/getfamilyid` | Get family/home ID |
| POST | `/ec4/v1/family/getallinfo` | Get all devices with AES keys |
| POST | `/data/v1/appdata/upload?source=app&datatype=app_user_v1` | Upload analytics |

### 2.2 Authentication Flow

```
1. GET /ec4/v1/common/api
   Headers: system, appPlatform, language, timestamp
   Response: {"error":0, "key":"<32-char hex API key>", "timestamp":"..."}

2. POST /ec4/v1/user/getfamilyid
   Headers: Content-type: application/x-java-serialized-object
            loginsession, lid (license ID), userid, token, timestamp
   Body: Java ObjectOutputStream (encrypted parameters)
   Response: {"error":0, "familyinfo": [{"id":"<family ID>", "familyname":"...", ...}]}

3. POST /ec4/v1/family/getallinfo
   Headers: Same as above
   Body: Java ObjectOutputStream (encrypted parameters)
   Response: {"error":0, "familyallinfo": [{...rooms, devices, AES keys...}]}
```

### 2.3 Credential Identifiers

| Field | Format | Example | Purpose |
|-------|--------|---------|---------|
| License ID (lid) | 32 hex chars | `bddb4af53f74edaa03b1aa439b75e7a6` | OEM installation ID |
| User ID | 32 hex chars | `0086942d0b76d306304d4a456f31fb89` | User account ID |
| Login Session | 32 hex chars | `9cd307d65e7d7b09307dd2d5ee37da92` | Session token |
| Token | 32 hex chars | `b5a5a37681b1d119f0b1fdeb4e76aecd` | Per-request auth token |
| API Key | 32 hex chars | `f67c1f5d283e774825a625e893ad9314` | Returned from handshake |
| Family ID | 32 hex chars | `011652d007852ee4a8bb9e5288bbeaee` | Home/family identifier |
| Device ID (DID) | 34 hex chars | `00000000000000000000a043b036bff4` | Device unique ID |
| AES Key | 32 hex chars | `99293543659c5b0caf659134ead8817f` | Per-device AES-128 key |
| Password | 32-bit integer | `754770058` | Device auth password |

### 2.4 Device Information (from getallinfo)

```json
{
  "familyallinfo": [{
    "devinfo": [{
      "did": "00000000000000000000a043b036bff4",
      "mac": "a0:43:b0:36:bf:f4",
      "password": 754770058,
      "devtype": 20379,
      "pid": "0000000000000000000000009b4f0000",
      "name": "master bedroom aircon",
      "aeskey": "99293543659c5b0caf659134ead8817f",
      "terminalid": 1,
      "subdevicenum": 0
    }]
  }]
}
```

---

## 3. Layer 2: DNA Protocol (UDP)

### 3.1 Transport

- **Protocol**: UDP (connectionless)
- **Device Port**: 80 (UDP)
- **Direction**: Bidirectional (client ↔ device)
- **MTU**: ~1024 bytes (DNA_MAX_PAYLOAD)
- **Timeout**: 5 seconds recommended
- **Retries**: 3 recommended

### 3.2 Packet Format

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Magic     |     Magic     |          Payload Len           |
|    0x5a      |    0xa5      |         (little-endian)         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Command Hi  |   Command Lo  |                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               |
|                                                               |
|                    Payload (variable length)                  |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Checksum            |
|         (big-endian)          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **Magic**: `0x5A 0xA5` (2 bytes) — packet start marker
- **Payload Length**: Little-endian uint16 (2 bytes) — length of payload + checksum
- **Command**: Big-endian uint16 (2 bytes) — command identifier
- **Payload**: Variable length bytes (encrypted or plain)
- **Checksum**: Big-endian uint16 (2 bytes) — sum of all payload bytes mod 65536

### 3.3 Command IDs

| Command | Value | Description |
|---------|-------|-------------|
| HEARTBEAT | `0x0000` | Keep-alive / no-op |
| DEVICE_DISCOVER | `0x0001` | LAN device discovery probe |
| DEVICE_INFO | `0x0002` | Query device information |
| DEVICE_PAIR | `0x0003` | Pair with new device |
| DEVICE_BIND | `0x0004` | Bind device to account |
| FIRMWARE_UPDATE | `0x000E` | OTA firmware update |
| AUTH_REQUEST | `0x0065` | Authentication request |
| AUTH_RESPONSE | `0x0066` | Authentication response |
| DEVICE_CONTROL | `0x006A` | Send control command |
| DEVICE_STATUS | `0x006B` | Query device status |
| DEVICE_SUB_CONTROL | `0x006C` | Sub-device control |

---

## 4. Layer 3: AES-128-ECB Encryption

### 4.1 Algorithm

- **Cipher**: AES-128
- **Mode**: ECB (Electronic Codebook)
- **Padding**: PKCS#7
- **Key**: 16-byte per-device AES key (from cloud API)

### 4.2 Pre-encryption XOR

Before AES encryption, the first 16 bytes of the plaintext are XOR'd with
a key derived from the device password:

```
xor_key = repeat(password_bytes, 16)  # password is big-endian uint32
for i in range(min(len(plaintext), 16)):
    plaintext[i] ^= xor_key[i]
```

### 4.3 Encryption Flow

```
plaintext (TFB encoded)
    │
    ├─→ XOR first 16 bytes with password-derived key
    │
    ├─→ PKCS#7 pad to 16-byte boundary
    │
    ├─→ AES-128-ECB encrypt
    │
    ▼
ciphertext (for DNA packet payload)
```

### 4.4 Decryption Flow

```
ciphertext (from DNA packet payload)
    │
    ├─→ AES-128-ECB decrypt
    │
    ├─→ Remove PKCS#7 padding
    │
    ├─→ XOR first 16 bytes with password-derived key
    │
    ▼
plaintext (TFB encoded)
```

---

## 5. Layer 4: TFB (Type-Field-Body) Serialization

### 5.1 Overview

TFB is a binary serialization format used within BroadLink's protocol.
It is similar to a simplified BSON or MessagePack. Each TFB element
consists of:

```
[Type: 1 byte] [Length: 1-2 bytes] [Value: variable]
```

### 5.2 Type Codes

| Type | Code | Description |
|------|------|-------------|
| STRING | `0x00` | UTF-8 string, length-prefixed (2 bytes) |
| INT | `0x01` | 32-bit integer, little-endian |
| BOOL | `0x02` | Boolean (1 byte: 0x00 or 0x01) |
| BYTES | `0x03` | Raw bytes, length-prefixed (2 bytes) |
| ARRAY | `0x04` | Array, count-prefixed (2 bytes) |
| MAP | `0x05` | Key-value map |
| FLOAT | `0x06` | Float value |

---

## 6. Device Control Command Format

### 6.1 JNI Function Signature

```java
// cn/com/broadlink/networkapi/NetworkAPI.smali
public native String dnaControl(
    String did,       // Device ID (34 hex chars)
    String mac,       // MAC address (colon-separated)
    String aesKey,    // AES-128 key (32 hex chars)
    String password,  // Device password (decimal string) or sub-command
    String command    // JSON command parameters
);
```

### 6.2 Control Payload Structure

The control payload is a TFB-encoded binary structure:

```
Byte Offset  Size    Field
──────────────────────────────────────
0            17      Device ID (DID) — 17 bytes binary
17           2       Sub-device ID (0x0000 for main device)
19           1       Command Type byte:
                       0x01 = Set control
                       0x02 = Query status
                       0x03 = Query capabilities
20+          var     Parameter blocks (see below)
```

### 6.3 Parameter Blocks

Each parameter is a TLV (Type-Length-Value) block:

```
[Param ID: 1 byte] [Length: 1 byte] [Value: variable]
```

| Param ID | Name | Length | Value |
|----------|------|--------|-------|
| `0x01` | Power | 1 | 0=OFF, 1=ON |
| `0x02` | Mode | 1 | 0=COOL, 1=HEAT, 2=AUTO, 3=FAN, 4=DRY |
| `0x03` | Temperature | 1 | 16-30 (Celsius) |
| `0x04` | Fan Speed | 1 | 0=AUTO, 1=LOW, 2=MED, 3=HIGH |
| `0x05` | Swing | 1 | 0=OFF, 1=VERT, 2=HORIZ, 3=BOTH |
| `0x06` | Sleep | 1 | 0=OFF, 1=ON |
| `0x07` | Turbo | 1 | 0=OFF, 1=ON |
| `0x08` | Temp Unit | 1 | 0=Celsius, 1=Fahrenheit |
| `0x09` | Room Temp | 1 | Room temperature (read-only) |
| `0x0A` | Error Code | 1 | Error status |

### 6.4 Status Response Structure

Response uses the same parameter block encoding:

```python
{
    'power': True/False,
    'mode': 0-4,
    'temp': 16-30,
    'fan': 0-3,
    'swing': 0-3,
    'sleep': True/False,
    'turbo': True/False,
    'room_temp': 0-50,     # Current room temperature
    'error_code': 0,       # 0 = no error
}
```

### 6.5 Example: Set Cooling to 22°C

```
Control Payload (hex):
  DID:      00000000000000000000a043b036bff4
  SubDevID: 0000
  CmdType:  01
  Power:    01 01 01     (param=0x01, len=1, value=ON)
  Mode:     02 01 00     (param=0x02, len=1, value=COOL)
  Temp:     03 01 16     (param=0x03, len=1, value=22°C)
  Fan:      04 01 00     (param=0x04, len=1, value=AUTO)
  Swing:    05 01 03     (param=0x05, len=1, value=BOTH)

Full payload: 00000000000000000000a043b036bff4000001010101020100030116040100050103
```

---

## 7. Device Discovery

### 7.1 Broadcast Probe

Send a UDP broadcast to port 80:

```
DNA Packet:
  Magic:   5a a5
  Length:  06 00  (6 bytes: 4 payload + 2 checksum)
  Command: 00 01  (DEVICE_DISCOVER)
  Payload: 00 00 00 00  (zero-filled probe)
  Checksum: 00 00
```

### 7.2 Discovery Response

```
Payload:
  [MAC: 6 bytes]
  [IP: 4 bytes]
  [DID: 17 bytes]
  [Name: UTF-8 string (variable)]
```

---

## 8. Known Device Types

| devtype | PID | Product |
|---------|-----|---------|
| 20379 (`0x4F9B`) | `...9b4f0000` | Kelvinator/Electrolux AC (Wi-Fi) |

The devtype `0x4F9B` corresponds to the product code `9b4f` (little-endian byte order).

---

## 9. Internal Library Architecture

### 9.1 Function Call Graph

```
Java: NetworkAPI.dnaControl(did, mac, aesKey, password, command)
  │
  ▼
JNI: Java_cn_com_broadlink_networkapi_NetworkAPI_dnaControl
  │
  ├─→ JSON parse (BLJSON_Parse)
  ├─→ networkapi_dna_control()
  │     │
  │     ├─→ Validate parameters
  │     ├─→ Build TFB payload
  │     │     └─→ bl_sdk_tfb_encode()
  │     ├─→ Encrypt payload
  │     │     └─→ bl_data_tfb_encrypt()
  │     │           ├─→ password XOR
  │     │           └─→ broadlink_cipher_crypt (AES-128-ECB)
  │     ├─→ Build DNA packet
  │     │     └─→ bl_data_pack()
  │     │           ├─→ Add header (magic, length, command)
  │     │           └─→ bl_tfb_checksum() / bl_checksum()
  │     ├─→ Send via UDP socket
  │     ├─→ Receive response
  │     ├─→ Parse DNA packet
  │     ├─→ Decrypt payload
  │     │     └─→ bl_data_tfb_decrypt()
  │     └─→ Decode TFB response
  │           └─→ bl_sdk_tfb_decode()
  │
  ▼
Returns: JSON response string (jstring)
```

### 9.2 Memory Map

Loadable segments from libNetworkAPI.so (Ghidra analysis):
- `.text`: `0x187b0 - 0x1b82f` (core code)
- `.text`: `0x1b830 - 0xff800` (main code, ~915KB)
- `.data`: various
- `.rodata`: `0x110198 - 0x120003`
- `.dynamic`: `0x128448 - 0x128697`
- `.bss`: `0x132c80 - 0x135081`

---

## 10. Security Considerations

1. **AES-ECB is weak**: ECB mode does not provide semantic security.
   Identical plaintext blocks produce identical ciphertext blocks.

2. **Static keys**: Each device has a static AES key retrieved from the
   cloud. If the cloud account is compromised, all device keys are exposed.

3. **Password XOR is deterministic**: The password-based XOR before
   encryption adds minimal security.

4. **No replay protection**: DNA packets lack timestamps or nonces,
   making them potentially vulnerable to replay attacks.

5. **UDP without integrity**: While the checksum provides basic integrity,
   there is no cryptographic MAC (Message Authentication Code).

---

## 11. References

- BroadLink DNA SDK (commercial, requires NDA)
- [python-broadlink](https://github.com/mjg59/python-broadlink) — Open-source
  BroadLink protocol implementation
- [Home Assistant BroadLink integration](https://www.home-assistant.io/integrations/broadlink/)
- Ghidra: `libNetworkAPI.so` analysis (this project)
- MITM proxy flows: `tools/flows` (this project)
