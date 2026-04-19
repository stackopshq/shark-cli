"""Tests for orca_cli.core.validators."""

from __future__ import annotations

import click
import pytest

from orca_cli.core.validators import validate_id, validate_ip


class TestValidateId:

    def test_accepts_uuid(self):
        uid = "12345678-1234-1234-1234-123456789abc"
        assert validate_id(None, None, uid) == uid

    def test_accepts_uppercase_uuid(self):
        uid = "12345678-ABCD-1234-1234-123456789ABC"
        assert validate_id(None, None, uid) == uid

    def test_accepts_numeric(self):
        assert validate_id(None, None, "42") == "42"

    def test_rejects_arbitrary_string(self):
        with pytest.raises(click.BadParameter, match="not a valid resource ID"):
            validate_id(None, None, "not-a-uuid")

    def test_rejects_empty(self):
        with pytest.raises(click.BadParameter):
            validate_id(None, None, "")

    def test_rejects_partial_uuid(self):
        with pytest.raises(click.BadParameter):
            validate_id(None, None, "1234-5678")


class TestValidateIp:

    def test_accepts_valid_ipv4(self):
        assert validate_ip(None, None, "192.168.1.1") == "192.168.1.1"

    def test_accepts_all_zeros(self):
        assert validate_ip(None, None, "0.0.0.0") == "0.0.0.0"

    def test_accepts_broadcast(self):
        assert validate_ip(None, None, "255.255.255.255") == "255.255.255.255"

    def test_rejects_three_octets(self):
        with pytest.raises(click.BadParameter, match="not a valid IPv4"):
            validate_ip(None, None, "192.168.1")

    def test_rejects_five_octets(self):
        with pytest.raises(click.BadParameter):
            validate_ip(None, None, "192.168.1.1.1")

    def test_rejects_non_numeric(self):
        with pytest.raises(click.BadParameter):
            validate_ip(None, None, "abc.def.ghi.jkl")

    def test_rejects_out_of_range(self):
        with pytest.raises(click.BadParameter):
            validate_ip(None, None, "256.1.1.1")

    def test_rejects_negative(self):
        with pytest.raises(click.BadParameter):
            validate_ip(None, None, "-1.2.3.4")

    def test_rejects_empty(self):
        with pytest.raises(click.BadParameter):
            validate_ip(None, None, "")
