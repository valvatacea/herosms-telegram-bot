"""Tes sederhana tanpa memanggil API nyata (menggunakan unittest.mock)."""
from __future__ import annotations

import json
from unittest.mock import patch

from bot.client import HeroSMS, HeroSMSError
from bot.messages import esc, bold, code, active_list_msg, purchase_success, buy_confirm_msg


def _mock_session(payload, status=200):
    class _Resp:
        status_code = status
        text = json.dumps(payload)

        def json(self):
            return payload

    class _Session:
        def __init__(self):
            self.headers = {}

        def update(self, d):
            self.headers.update(d)

        def get(self, *a, **k):
            return _Resp()

        def post(self, *a, **k):
            return _Resp()

        def delete(self, *a, **k):
            return _Resp()

    return _Session()


def test_buy_activation():
    api = HeroSMS("k", "https://hero-sms.com/api/v1")
    api.session = _mock_session({"id": 1, "phone": "+628****6789", "status": "pending"})
    act = api.buy_activation(service="wa", country="id")
    assert act["id"] == 1
    assert act["phone"] == "+628****6789"
    print("OK test_buy_activation")


def test_otp_last():
    api = HeroSMS("k", "https://hero-sms.com/api/v1")
    api.session = _mock_session({"code": "123456", "date": "2025-03-18 10:40:37"})
    data = api.otp_last("1")
    assert data["code"] == "123456"
    print("OK test_otp_last")


def test_cancel_activation():
    api = HeroSMS("k", "https://hero-sms.com/api/v1")
    api.session = _mock_session({"success": True})
    res = api.cancel_activation("1")
    assert res["success"] is True
    print("OK test_cancel_activation")


def test_error_raised():
    api = HeroSMS("k", "https://hero-sms.com/api/v1")
    api.session = _mock_session({"message": "not found"}, status=404)
    try:
        api.otp_last("999")
        assert False, "seharusnya melempar HeroSMSError"
    except HeroSMSError as exc:
        assert "404" in str(exc)
    print("OK test_error_raised")


def test_esc_bold_code():
    assert esc("a_b[c]") == r"a\_b\[c\]"
    assert bold("hai") == "*hai*"
    assert code("x") == "`x`"
    print("OK test_esc_bold_code")


def test_active_list_msg_empty():
    out = active_list_msg({"data": []})
    assert "Belum ada aktivasi aktif" in out
    print("OK test_active_list_msg_empty")


def test_purchase_success():
    out = purchase_success({"id": 7, "phone": "+6281", "cost": "0.5", "currency": "IDR"})
    assert "Nomor Dibeli" in out
    assert "+6281" in out
    print("OK test_purchase_success")


def test_buy_confirm_msg():
    out = buy_confirm_msg("id", "wa", "5000", "IDR")
    assert "Konfirmasi Pembelian" in out
    assert "id" in out
    assert "wa" in out
    assert "5000" in out
    assert "IDR" in out
    print("OK test_buy_confirm_msg")


def test_lookup_price_list_format():
    from bot.client import HeroSMS
    from unittest.mock import MagicMock
    api = HeroSMS.__new__(HeroSMS)
    api.legacy = MagicMock(return_value={
        "data": [{"service": "wa", "country": "id", "price": "0.5", "currency": "IDR"}]
    })
    price, cur = api.lookup_price("id", "wa")
    assert price == "0.5"
    assert cur == "IDR"
    print("OK test_lookup_price_list_format")


def test_lookup_price_nested_format():
    from bot.client import HeroSMS
    from unittest.mock import MagicMock
    api = HeroSMS.__new__(HeroSMS)
    api.legacy = MagicMock(return_value={"wa": {"id": {"price": "0.7", "currency": "IDR"}}})
    price, cur = api.lookup_price("id", "wa")
    assert price == "0.7"
    assert cur == "IDR"
    print("OK test_lookup_price_nested_format")


def test_lookup_price_flat_format():
    from bot.client import HeroSMS
    from unittest.mock import MagicMock
    api = HeroSMS.__new__(HeroSMS)
    api.legacy = MagicMock(return_value={"wa_id": "0.9"})
    price, cur = api.lookup_price("id", "wa")
    assert price == "0.9"
    assert cur == ""
    print("OK test_lookup_price_flat_format")


def test_lookup_price_not_found():
    from bot.client import HeroSMS
    from unittest.mock import MagicMock
    api = HeroSMS.__new__(HeroSMS)
    api.legacy = MagicMock(return_value={"data": [{"service": "wa", "country": "us", "price": "1.0", "currency": "USD"}]})
    price, cur = api.lookup_price("id", "wa")
    assert price == "-"
    assert cur == ""
    print("OK test_lookup_price_not_found")


if __name__ == "__main__":
    test_buy_activation()
    test_otp_last()
    test_cancel_activation()
    test_error_raised()
    test_esc_bold_code()
    test_active_list_msg_empty()
    test_purchase_success()
    test_buy_confirm_msg()
    test_lookup_price_list_format()
    test_lookup_price_nested_format()
    test_lookup_price_flat_format()
    test_lookup_price_not_found()
    print("\nSemua tes lolos.")
