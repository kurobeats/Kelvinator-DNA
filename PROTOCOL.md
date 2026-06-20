# Broadlink DNA Protocol Reference

Reverse-engineered from `libNetworkAPI.so` v2.0.49-6566c07.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Android Application                              │
│  cn.com.broadlink.networkapi.NetworkAPI                                 │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ JNI
┌────────────────────────────▼────────────────────────────────────────────┐
│  libNetworkAPI.so  (this document)                                      │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ JNI Wrappers │  │ Internal API │  │  Network I/O  │                  │
│  │ (JavaString  │──│ (networkapi_ │──│  (delegated   │                  │
│  │  ↔ char*)    │  │  *_functions)│  │   to Java)    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                            │                            │
│  ┌──────────────┐  ┌──────────────┐       │                            │
│  │  BLJSON      │  │  Crypto      │       │                            │
│  │  (cJSON fork)│  │  (AES-128)   │       │                            │
│  └──────────────┘  └──────────────┘       │                            │
└───────────────────────────────────────────│────────────────────────────┘
                                            │ callbacks
┌───────────────────────────────────────────▼────────────────────────────┐
│  Java-side Network Transport                                            │
│  (OkHttp / HttpURLConnection → Broadlink Cloud API)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Insight

The library contains **zero socket code** for cloud communication. All network I/O is done via Java callbacks (`setNetworkCallback`). The library only handles:

- JSON parsing/construction (via BLJSON, a cJSON fork)
- AES-128-CBC encryption/decryption
- Device discovery protocol (UDP broadcast on port 80)
- Device pairing handshake
- PID-based product profile loading
- EasyConfig SmartConfig WiFi provisioning
- Sunrise/sunset calculation

---

## 2. JNI Entry Points

### 2.1 Function Calling Convention

Every JNI entry point follows the same pattern:

```
Java_cn_com_broadlink_networkapi_NetworkAPI_<Method>
  → GetStringUTFChars on each jstring argument
  → Call internal networkapi_* function
  → NewStringUTF on the return value
  → ReleaseStringUTFChars on each argument
```

### 2.2 Complete Export List

| Address | Symbol | Internal Call |
|---------|--------|---------------|
| `0x0011bf80` | `Java_..._SDKInit` | `networkapi_init` |
| `0x0011c130` | `Java_..._bl_1sdk_1auth` | `networkapi_sdk_auth` (13 params) |
| `0x0011cd10` | `Java_..._deviceBindWithServer` | `networkapi_device_bind` |
| `0x0011ce70` | `Java_..._deviceStatusOnServer` | `networkapi_device_devicestatus` |
| `0x0011cfd0` | `Java_..._bl_1easyconfig` | `networkapi_device_easyconfig` |
| `0x0011d0c0` | `Java_..._LicenseInfo` | `networkapi_license_info` |
| `0x0011d1b0` | `Java_..._SDKInit` | `networkapi_init` |
| `0x0011d2a0` | `Java_..._deviceEasyConfigCancel` | `networkapi_device_easyconfig_cancel` |
| `0x0011d330` | `Java_..._deviceGetAPList` | `networkapi_device_get_aplist` |
| `0x0011d420` | `Java_..._deviceAPConfig` | `networkapi_device_apconfig` |
| `0x0011d510` | `Java_..._deviceRedCodeInfomation` | `networkapi_red_code_information` |
| `0x0011d600` | `Java_..._deviceRedCodeData` | `networkapi_red_code_data` |
| `0x0011d6f0` | `Java_..._deviceProbe` | `networkapi_device_probe` |
| `0x0011d7e0` | `Java_..._deviceGetResourcesToken` | `networkapi_device_resources_token` |
| `0x0011d940` | `Java_..._devicePair` | `networkapi_device_pair` |
| `0x0011daa0` | `Java_..._deviceProfile` | `networkapi_device_profile` |
| `0x0011dc60` | `Java_..._deviceProfile2` | `networkapi_pid_profile` |
| `0x0011ddc0` | `Java_..._dnaControl` | `networkapi_dna_control` |
| `0x0011dff0` | `Java_..._deviceSubControlTranslate` | `networkapi_gateway_translate` |
| `0x0011e1b0` | `Java_..._calculateSunriseSunset` | `networkapi_sunrise_sunset` |
| `0x0011e2a0` | `Java_..._setNetworkCallback` | Stores Java callback ref |
| `0x0011e540` | `Java_..._setIRCodeCallback` | Stores Java callback ref |
| `0x0011e7e0` | `Java_..._setDeviceControlCallback` | Stores Java callback ref |

### 2.3 Callback Mechanism

The library uses a global singleton structure at `0x00228698` (the "DNA SDK context"):

```
Offset  Type    Description
------  ----    -----------
0x00    8*N     pthread_rwlock_t (rwlock)
0x40    8*N     network_callback JNI global ref
0x48    8*N     ir_code_callback JNI global ref
0x50    8*N     device_control_callback JNI global ref
0x58    8       cookie_string_ptr
0x60    8       cookie_string_ptr
...
0xB0    1       local_ctrl_override (bool)
0xB2    1       sdk_init_called (bool)
0xB3    1       log_level (0-3)
...
0x2F0   386     filepath buffer (script directory)
```

Callback functions acquire the lock via `pthread_rwlock_rdlock`, call the Java method with `CallObjectMethod`, and release.

### 2.4 Global Data Tables

The library stores server URLs and endpoint paths in data tables at runtime:

| Address | Content |
|---------|---------|
| `0x00232c88` | `device_config` endpoint ref |
| `0x00232c90` | `server_config` ref |
| `0x00232c98` | `write_config` endpoint ref |
| `0x00232ca0` | `ac_ircode` endpoint ref |
| `0x00232ca8` | `server_config_2` ref |
| `0x00232cb0` | `ircode` endpoint ref |
| `0x00232cb8` | `remote_control` endpoint ref |
| `0x00232cc0` | `server_config_3` ref |
| `0x00232cc8` | JVM pointer (obtained from `GetJavaVM`) |
| `0x00232cd0` | JNI lock flag |

---

## 3. Device Discovery Protocol (UDP)

### 3.1 Discovery Packet (Probe)

Sent to `255.255.255.255:80` (UDP broadcast):

```
Offset  Size  Value / Description
──────  ────  ───────────────────
0x00    4     System timestamp (u32, little-endian)
0x04    4     Local IP address (u32, little-endian) — e.g. 192.168.1.100 = 0x6401A8C0
0x08    2     Local UDP source port
0x0A    38    Zero padding
──────────────────────────────────
Total: 48 bytes
```

### 3.2 Discovery Response

Received from device (unicast UDP):

```
Offset  Size  Description
──────  ────  ───────────────────
0x00    2     Payload length (little-endian u16)
0x02    2     Reserved
0x04    4     Device type (u32 LE):
                0x0000 = SP1
                0x2711 = SP2
                0x947A = SP3
                0x9479 = SP3S
                0x2222 = SP4L
                0x2712 = RM2
                0x51DA = RM4
                0x2737 = RM Mini
                0x2714 = A1
                0x4EB5 = MP1
                0x4EAD = SC1
                0x4EAF = Hysen
0x08    2     Command (0x6A = 106)
0x0A    2     Packet count
0x0C    4     Device ID (u32 LE)
0x10    6     MAC address (raw bytes)
0x16    2     Padding
0x18    4     Device ID copy
0x1C    4     IP address (network byte order / raw bytes)
0x20    16    Additional data / padding
──────────────────────────────────
Total: 48 bytes (0x30)
```

---

## 4. Device Command Protocol (UDP)

### 4.1 Packet Structure

Sent to/received from `<device_ip>:80` (unicast UDP):

```
Offset  Size  Description
──────  ────  ───────────────────
0x00    2     Encrypted payload length (u16 LE, including 2-byte checksum prefix)
0x02    2     Reserved (0x0000)
0x04    4     Device type (u32 LE)
0x08    2     Command type:
                0x65 = Auth
                0x03 = Login
                0x06 = Device Info
                0x6A = Device Control
                0x6B = Device Status
0x0A    2     Packet sequence count (monotonically increasing)
0x0C    4     Device ID (u32 LE)
0x10    6     MAC address (raw bytes, zero-padded to 8)
0x18    4     Device ID copy
0x1C    4     Timestamp (u32 LE, Unix epoch)
0x20    4     Reserved / flags
0x24    4     Reserved
0x28    4     Reserved
0x2C    4     Reserved
──────────────────────────────────
Header: 0x38 bytes (56 bytes)
0x30    N     Encrypted payload (AES-128-CBC)
```

### 4.2 Command Types

| Value | Name | Description |
|-------|------|-------------|
| `0x65` | Auth | Device authentication handshake |
| `0x03` | Login | Cloud login (not used for local) |
| `0x06` | Info | Get device information |
| `0x6A` | Control | Send control command |
| `0x6B` | Status | Query device status |

### 4.3 Authentication Handshake

```
Client                                          Device
  │                                                │
  │ ─── CMD_AUTH (0x65) + 80 zero bytes ──────→   │
  │                                                │
  │ ←── Encrypted response with device ID ──────   │
  │     (device ID extracted from header 0x0C)     │
  │                                                │
  │     IV = MD5(key + device_id_as_u32_le)        │
  │                                                │
  │ ─── Subsequent commands with derived IV ───→   │
  │                                                │
```

---

## 5. Encryption Scheme

### 5.1 Parameters

- **Algorithm**: AES-128-CBC
- **Key**: 16-byte device key (default: `097628343fe99e23765c1513accf8b02`)
- **IV derivation**: `MD5(key || pack("<I", device_id))`
- **Padding**: PKCS7

### 5.2 Encryption Process

```
1. Compute checksum: u16_le = sum(payload_bytes) & 0xFFFF
2. Prepend: full_payload = pack("<H", checksum) + payload
3. Pad: padded = PKCS7_pad(full_payload, 16)
4. Encrypt: ciphertext = AES_CBC_ENCRYPT(key, iv, padded)
```

### 5.3 Decryption Process

```
1. Decrypt: padded = AES_CBC_DECRYPT(key, iv, ciphertext)
2. Unpad: full_payload = PKCS7_unpad(padded)
3. Extract: checksum = unpack("<H", full_payload[:2])
4. Verify: assert checksum == sum(full_payload[2:]) & 0xFFFF
5. Return: full_payload[2:]
```

### 5.4 Pseudocode

```python
def broadlink_encrypt(payload, key, iv):
    checksum = sum(payload) & 0xFFFF
    plain = struct.pack("<H", checksum) + payload
    padded = pkcs7_pad(plain, 16)
    return aes_cbc_encrypt(key, iv, padded)

def broadlink_decrypt(ciphertext, key, iv):
    padded = aes_cbc_decrypt(key, iv, ciphertext)
    plain = pkcs7_unpad(padded)
    checksum_recv = struct.unpack("<H", plain[:2])[0]
    payload = plain[2:]
    assert checksum_recv == sum(payload) & 0xFFFF
    return payload
```

---

## 6. Network I/O Pattern (Callback-Based)

All cloud/remote operations in the binary follow this identical pattern:

```
1. Acquire JNI read lock: FUN_0011ea10() → pthread_rwlock_rdlock
2. Look up global callback ref from DATA table
3. Convert C string param → JNI NewStringUTF
4. Call Java callback: (*env)->CallObjectMethod(env, callback, method_id, ...)
5. Get result: (*env)->GetStringUTFChars(env, result)
6. Copy result to output buffer
7. Release JNI read lock: FUN_0011eaf0() → pthread_rwlock_unlock
```

This pattern is used by `network_read_private_data`, `network_write_private_data`,
`network_ac_ircode_operation`, `network_ircode_operation`, and `network_device_remote_control`.

### 6.1 Java Callback Interface

The callback flows are:

```
deviceProbe → network_device_probe → network_read_private_data → Java callback
dnaControl  → networkapi_dna_control → (local UDP) or network_device_remote_control → Java callback
bl_easyconfig → networkapi_device_easyconfig → SDK thread + UDP broadcast
```

---

## 7. EasyConfig / SmartConfig Protocol

### 7.1 Overview

EasyConfig is Broadlink's proprietary WiFi provisioning protocol. The original
binary sends UDP broadcast packets to port 49999 in a loop for a configurable
timeout (default 75 seconds, max 150 seconds).

### 7.2 Credential Payload

```
Offset  Size  Description
──────  ────  ───────────────────
0x00    5     Magic: "BLINK"
0x05    1     SSID length
0x06    32    SSID (null-padded)
0x26    1     Password length
0x27    64    Password (null-padded)
0x67    1     Security type:
                0 = Open
                1 = WEP
                2 = WPA
                3 = WPA2
                4 = WPA3
0x68    1     Checksum (additive sum of bytes 0x00-0x67)
──────────────────────────────────
Total: 105 bytes
```

### 7.3 Timing

The broadcast runs at approximately 10 packets per second for the duration of the
timeout. Each packet is sent to `255.255.255.255:49999`.

### 7.4 Cancellation

`deviceEasyConfigCancel()` stops the broadcast by setting a flag checked by the
packet-sending loop.

---

## 8. Internal Helper Functions

### 8.1 `FUN_0011ea10` — Get JNI read lock

```c
// Acquires pthread_rwlock_rdlock, returns Java callback ref
// Returns NULL if lock acquisition fails
```

### 8.2 `FUN_0011eaf0` — Release JNI read lock

```c
// Releases pthread_rwlock if it was acquired
```

### 8.3 `FUN_001cbf90` — Log helper

```c
// Internal logging: formats "[filename]:[line] [tag]" and prints via __android_log_print
// Logs only if log_level ≥ configured level
```

### 8.4 `FUN_001d48f0` — Parse device info from JSON

```c
// Extracts MAC, IP, type, DID, key from a JSON object
// Used by devicePair and dna_control
```

### 8.5 `FUN_001d0880` — Copy device context

```c
// Copies device authentication context (key, IV, MAC, type, DID, IP)
// between internal structures
```

### 8.6 `FUN_001db970` — Parse sub-device info

```c
// Extracts sub-device information from JSON for multi-outlet devices (MP1)
```

---

## 9. DNA Control Command Flow

```
dnaControl(deviceInfo, subDeviceInfo, data, command) {
    1. Parse device_info JSON → MAC, IP, type, DID, key
    2. Parse sub_device_info JSON (optional)
    3. Parse data JSON → command type & parameters
    4. Parse command JSON → additional parameters

    IF localctrl == true AND IP present:
        5a. Build Broadlink packet header
        6a. Encrypt command payload with AES-128-CBC
        7a. Send via UDP to device:80
        8a. Receive response
        9a. Decrypt response payload
        10a. Format as JSON result

    ELSE IF device_control_callback registered:
        5b. Call Java callback with all 4 params
        6b. Return callback result

    ELSE:
        Return error -4002 (no control path)
}
```

---

## 10. Error Codes

| Code | Name | Description |
|------|------|-------------|
| `0` | Success | Operation completed successfully |
| `-1` | Generic Error | Catch-all for exceptions |
| `-4000` | Invalid JSON | Input string is not valid JSON |
| `-4001` | Invalid Type | Field has wrong type (e.g. string instead of number) |
| `-4002` | No Path | No local IP and no cloud callback available |
| `-4006` | Auth Failed | Device authentication handshake failed |
| `-4008` | Too Long | String exceeds maximum length (e.g. filepath > 384) |
| `-4018` | JSON Create Fail | Failed to allocate/construct JSON object (malloc failure) |

---

## 11. Version String

The library reports its version as:

```
"2.0.49-6566c07"
```

With optional `.local` suffix when `localctrl` is enabled:

```
"2.0.49-6566c07.local"
```

The hardcoded source paths in debug strings reveal the origin:
- `/Users/admin/Work/Broadlink/Gitlab/DNASDK/linux/src/networkapi_command.c`

---

## 12. BLJSON (cJSON Fork)

The library bundles a modified version of cJSON under the prefix `BLJSON`:

| Function | cJSON Equivalent |
|----------|-----------------|
| `BLJSON_Parse` | `cJSON_Parse` |
| `BLJSON_PrintUnformatted` | `cJSON_PrintUnformatted` |
| `BLJSON_CreateObject` | `cJSON_CreateObject` |
| `BLJSON_CreateArray` | `cJSON_CreateArray` |
| `BLJSON_CreateString` | `cJSON_CreateString` |
| `BLJSON_CreateNumber` | `cJSON_CreateNumber` |
| `BLJSON_AddItemToObject` | `cJSON_AddItemToObject` |
| `BLJSON_GetObjectItem` | `cJSON_GetObjectItem` |
| `BLJSON_Delete` | `cJSON_Delete` |
| `BLJSON_GetErrorPtr` | `cJSON_GetErrorPtr` |
| `BLJSON_InitHooks` | `cJSON_InitHooks` |

---

## 13. Thread Safety

The library uses a single `pthread_rwlock_t` stored at offset 0 of the global context
(`0x00228698`). All operations that access shared state (callbacks, config, device list)
acquire this lock.

- **Read lock**: Callback invocations, config reads
- **Write lock**: SDK initialization, callback registration
