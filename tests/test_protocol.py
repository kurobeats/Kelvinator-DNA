"""
Protocol module tests.
"""

import struct
import pytest
from broadlink_api.protocol import (
    build_device_command,
    parse_device_response,
    build_discovery_packet,
    parse_discovery_response,
    HEADER_SIZE,
)


class TestBuildDeviceCommand:
    def test_basic_packet(self):
        key = b"0123456789abcdef"
        mac = bytes([0xB4, 0x43, 0x0D, 0x12, 0x34, 0x56])
        payload = b"\x01\x00\x00\x00"

        pkt = build_device_command(
            device_id=0x12345678,
            device_type=0x2712,
            device_mac=mac,
            device_key=key,
            command=0x6A,
            payload=payload,
            count=1,
        )

        # Should have header + encrypted payload
        assert len(pkt) > HEADER_SIZE
        header = pkt[:HEADER_SIZE]

        pkt_len = struct.unpack_from("<H", header, 0x00)[0]
        assert pkt_len == len(pkt) - HEADER_SIZE

        dev_type = struct.unpack_from("<I", header, 0x04)[0]
        assert dev_type == 0x2712

        cmd = struct.unpack_from("<H", header, 0x08)[0]
        assert cmd == 0x6A

        dev_id = struct.unpack_from("<I", header, 0x0C)[0]
        assert dev_id == 0x12345678

        # MAC should be in bytes 0x10-0x15
        assert header[0x10:0x16] == mac.ljust(6, b'\x00')


class TestParseDeviceResponse:
    def test_roundtrip(self):
        key = b"0123456789abcdef"
        mac = b"\xB4\x43\x0D\x12\x34\x56"
        payload = b"response data here"

        pkt = build_device_command(
            device_id=0x12345678,
            device_type=0x2712,
            device_mac=mac,
            device_key=key,
            command=0x6A,
            payload=payload,
            count=5,
        )

        result = parse_device_response(pkt, key, 0x12345678)
        assert result["device_id"] == 0x12345678
        assert result["device_type"] == 0x2712
        assert result["command"] == 0x6A
        assert result["count"] == 5
        assert result["payload"] == payload


class TestDiscovery:
    def test_build_discovery_packet(self):
        pkt = build_discovery_packet(local_ip="192.168.1.100", source_port=12345)
        assert len(pkt) == 48

        source_port = struct.unpack_from("<H", pkt, 0x08)[0]
        assert source_port == 12345

    def test_parse_discovery_response(self):
        # Build a mock discovery response
        data = bytearray(0x30)
        struct.pack_into("<H", data, 0x00, 0x30)          # packet length
        struct.pack_into("<I", data, 0x04, 0x2712)         # device type RM2
        struct.pack_into("<H", data, 0x08, 0x6A)           # command
        struct.pack_into("<I", data, 0x0C, 0x12345678)     # device ID
        data[0x10:0x16] = b"\xB4\x43\x0D\x12\x34\x56"     # MAC
        struct.pack_into("<I", data, 0x18, 0x12345678)     # Dev ID copy
        # IP bytes in network byte order (big-endian) at offset 0x1C: 192.168.1.100
        data[0x1C:0x20] = bytes([192, 168, 1, 100])
        data = bytes(data)

        result = parse_discovery_response(data)
        assert result["device_type"] == 0x2712
        assert result["device_id"] == 0x12345678
        assert result["ip"] == "192.168.1.100"
        assert "b4:43:0d:12:34:56" in result["mac_str"]


class TestEdgeCases:
    def test_empty_payload(self):
        key = b"0123456789abcdef"
        mac = b"\x00\x00\x00\x00\x00\x00"

        pkt = build_device_command(
            device_id=0, device_type=0, device_mac=mac,
            device_key=key, command=0, payload=b"", count=0,
        )
        assert len(pkt) > HEADER_SIZE

        result = parse_device_response(pkt, key, 0)
        assert result["payload"] == b""

    def test_max_device_id(self):
        key = b"0123456789abcdef"
        mac = b"\xFF\xFF\xFF\xFF\xFF\xFF"

        pkt = build_device_command(
            device_id=0xFFFFFFFF, device_type=0xFFFF, device_mac=mac,
            device_key=key, command=0xFFFF, payload=b"\x00", count=0xFFFF,
        )
        result = parse_device_response(pkt, key, 0xFFFFFFFF)
        assert result["device_id"] == 0xFFFFFFFF
        assert result["device_type"] == 0xFFFF
