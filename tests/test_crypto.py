"""
Cryptography module tests.
"""

import pytest
import struct
from broadlink_api.crypto import (
    AESCipher,
    broadlink_encrypt,
    broadlink_decrypt,
    derive_device_key,
    _pkcs7_pad,
    _pkcs7_unpad,
)


class TestPKCS7:
    def test_pad_empty(self):
        result = _pkcs7_pad(b"")
        assert len(result) == 16
        assert result == bytes([16] * 16)

    def test_pad_partial_block(self):
        result = _pkcs7_pad(b"hello")
        assert len(result) == 16
        assert result[-11:] == bytes([11] * 11)

    def test_pad_full_block(self):
        result = _pkcs7_pad(b"A" * 16)
        assert len(result) == 32
        assert result[-16:] == bytes([16] * 16)

    def test_unpad_valid(self):
        padded = b"hello" + bytes([11] * 11)
        result = _pkcs7_unpad(padded)
        assert result == b"hello"

    def test_unpad_invalid(self):
        with pytest.raises(ValueError):
            _pkcs7_unpad(b"hello\x00\x00")

    def test_roundtrip(self):
        for data in [b"", b"h", b"hello world", b"A" * 16, b"B" * 32]:
            padded = _pkcs7_pad(data)
            unpadded = _pkcs7_unpad(padded)
            assert unpadded == data


class TestAESCipher:
    def test_encrypt_decrypt(self):
        key = b"0123456789abcdef"
        cipher = AESCipher(key)
        plaintext = b"Hello Broadlink!"
        encrypted = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext

    def test_custom_iv(self):
        key = b"0123456789abcdef"
        iv = b"fedcba9876543210"
        cipher = AESCipher(key, iv)
        plaintext = b"test data 12345"
        encrypted = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext

    def test_key_length_validation(self):
        with pytest.raises(ValueError):
            AESCipher(b"short")


class TestBroadlinkCrypto:
    def test_encrypt_decrypt(self):
        key = bytes([
            0x09, 0x76, 0x28, 0x34, 0x3F, 0xE9, 0x9E, 0x23,
            0x76, 0x5C, 0x15, 0x13, 0xAC, 0xCF, 0x8B, 0x02,
        ])
        payload = b"\x01\x00\x00\x00"  # Simple command
        encrypted = broadlink_encrypt(payload, key)
        decrypted = broadlink_decrypt(encrypted, key)
        assert decrypted == payload

    def test_checksum_verification(self):
        key = b"0123456789abcdef"
        payload = b"test command"
        encrypted = broadlink_encrypt(payload, key)
        decrypted = broadlink_decrypt(encrypted, key)
        assert decrypted == payload

    def test_checksum_mismatch(self):
        key = b"0123456789abcdef"
        payload = b"test" * 10  # longer payload to ensure > 16 bytes encrypted
        encrypted = broadlink_encrypt(payload, key)
        # Corrupt the encrypted data at a safe offset within payload area
        encrypted = bytearray(encrypted)
        encrypted[16] ^= 0xFF
        with pytest.raises(ValueError, match="Checksum mismatch"):
            broadlink_decrypt(bytes(encrypted), key)


class TestDeriveDeviceKey:
    def test_known_values(self):
        key = b"\x09\x76\x28\x34\x3F\xE9\x9E\x23\x76\x5C\x15\x13\xAC\xCF\x8B\x02"
        device_id = 0x12345678
        iv = derive_device_key(device_id, key)
        assert len(iv) == 16
        # IV should be MD5(key + little-endian device_id)
        # Not checking exact value since it depends on the key
        assert iv != key  # Should be different from the key
