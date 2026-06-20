"""
NetworkAPI class tests.
"""

import json
import pytest
from broadlink_api import NetworkAPI


class TestSDKInit:
    def test_basic_init(self):
        api = NetworkAPI()
        result = api.sdk_init({"loglevel": 2})
        assert result["status"] == 0
        assert "init success" in result["msg"]
        assert "version" in result

    def test_init_with_localctrl(self):
        api = NetworkAPI()
        result = api.sdk_init({"loglevel": 1, "localctrl": True})
        assert result["status"] == 0
        assert ".local" in result["version"]

    def test_init_invalid_json(self):
        api = NetworkAPI()
        result = api.sdk_init("not a dict")  # type: ignore
        assert result["status"] == -4000

    def test_init_invalid_loglevel(self):
        api = NetworkAPI()
        result = api.sdk_init({"loglevel": "not_a_number"})
        assert result["status"] == -4001

    def test_init_invalid_localctrl(self):
        api = NetworkAPI()
        result = api.sdk_init({"localctrl": "yes"})
        assert result["status"] == -4001

    def test_init_filepath_too_long(self):
        api = NetworkAPI()
        result = api.sdk_init({"filepath": "x" * 400})
        assert result["status"] == -4008

    def test_init_returns_version(self):
        api = NetworkAPI()
        result = api.sdk_init({})
        assert result["status"] == 0
        assert "2.0.49" in result["version"]


class TestLicenseInfo:
    def test_license_info(self):
        api = NetworkAPI()
        result = api.license_info({})
        assert result["status"] == 0
        assert result["version"] == "2.0.49-6566c07"


class TestSunriseSunset:
    def test_basic_calculation(self):
        api = NetworkAPI()
        result = api.calculate_sunrise_sunset({
            "longitude": 121.47,
            "latitude": 31.23,
            "timezone": 8,
            "year": 2024,
            "month": 6,
            "day": 20,
        })
        assert result["status"] == 0
        assert "sunrise" in result
        assert "sunset" in result
        # Verify format HH:MM
        assert len(result["sunrise"]) == 5
        assert len(result["sunset"]) == 5

    def test_polar_region(self):
        api = NetworkAPI()
        result = api.calculate_sunrise_sunset({
            "longitude": 0,
            "latitude": 89.9,  # Near north pole in summer
            "timezone": 0,
            "year": 2024,
            "month": 6,
            "day": 20,
        })
        # May return error for polar day/night
        assert "status" in result


class TestDevicePair:
    def test_missing_ip(self):
        api = NetworkAPI()
        result = api.device_pair({"mac": "b4:43:0d:12:34:56"})
        assert result["status"] == -4000

    def test_invalid_input(self):
        api = NetworkAPI()
        result = api.device_pair("not_a_dict")  # type: ignore
        assert result["status"] == -4000


class TestEasyConfig:
    def test_missing_ssid(self):
        api = NetworkAPI()
        result = api.bl_easyconfig({})
        assert result["status"] == -4000

    def test_easyconfig_cancel(self):
        api = NetworkAPI()
        result = api.device_easyconfig_cancel()
        assert result["status"] == 0


class TestDeviceProfile:
    def test_missing_pid(self):
        api = NetworkAPI()
        result = api.device_profile({})
        assert result["status"] == -4000


class TestCallbacks:
    def test_network_callback(self):
        api = NetworkAPI()
        api.sdk_init({})

        def cb(op, params):
            return '{"status": 0, "userid": "test123"}'

        api.set_network_callback(cb)
        result = api.bl_sdk_auth(license_id="test")
        assert result["status"] == 0
        assert result["userid"] == "test123"

    def test_network_callback_device_bind(self):
        api = NetworkAPI()
        api.sdk_init({})

        def cb(op, params):
            return '{"status": 0, "msg": "bound"}'

        api.set_network_callback(cb)
        result = api.device_bind_with_server({"did": "test"})
        assert result["status"] == 0

    def test_device_control_callback(self):
        api = NetworkAPI()
        api.sdk_init({"localctrl": False})

        def cb(device_info, sub_device, data, command):
            return '{"status": 0, "msg": "ok"}'

        api.set_device_control_callback(cb)
        result = api.dna_control(
            device_info={"did": "test"},
            data={"pwr": 1},
        )
        assert result["status"] == 0

    def test_no_callback_no_local(self):
        api = NetworkAPI()
        api.sdk_init({"localctrl": False})
        result = api.dna_control(
            device_info={"did": "test"},
            data={"pwr": 1},
        )
        assert result["status"] == -4002


class TestDeviceProbe:
    def test_probe_returns_structure(self):
        api = NetworkAPI()
        # Discovery on a network without devices should still return valid JSON
        result = api.device_probe({"timeout": 1.0})
        assert "status" in result
        assert "list" in result
        assert isinstance(result["list"], list)
