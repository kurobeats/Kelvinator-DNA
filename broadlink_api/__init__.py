"""
Broadlink NetworkAPI Python Reimplementation
=============================================
Reverse-engineered from libNetworkAPI.so (Broadlink DNA SDK v2.0.49-6566c07)

This library provides a Python-native implementation of the Broadlink DNA SDK
network API, originally implemented as a JNI shared library for Android.

The original library acts as a bridge between Java application code and the
Broadlink cloud API, with network I/O delegated to Java-side callbacks.
This reimplementation replaces JNI with direct Python HTTP/socket calls.
"""

from .network_api import NetworkAPI
from .device import BroadlinkDevice
from .crypto import AESCipher, broadlink_encrypt, broadlink_decrypt
from .protocol import (
    build_device_command,
    parse_device_response,
    build_discovery_packet,
    parse_discovery_response,
)

__version__ = "2.0.49"
__all__ = [
    "NetworkAPI",
    "BroadlinkDevice",
    "AESCipher",
    "broadlink_encrypt",
    "broadlink_decrypt",
    "build_device_command",
    "parse_device_response",
    "build_discovery_packet",
    "parse_discovery_response",
]
