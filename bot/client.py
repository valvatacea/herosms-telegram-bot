"""Klien HeroSMS API — semua endpoint dari OpenAPI spec (api-en.json)."""

from __future__ import annotations

import requests
import time
from typing import Any, Dict, List, Optional


class HeroSMSError(Exception):
    pass


class HeroSMS:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.legacy_base = self.base_url.replace("/api/v1", "")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"ApiKey {api_key}"})

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        return self._request_with_retry("GET", path, params=params)

    def _post(self, path: str, json: Optional[Dict] = None, data: Optional[Dict] = None) -> Any:
        return self._request_with_retry("POST", path, json=json, data=data)

    def _delete(self, path: str) -> Any:
        return self._request_with_retry("DELETE", path)

    def _request_with_retry(
        self, method: str, path: str, max_retries: int = 3, backoff: float = 1.5, **kwargs
    ) -> Any:
        """Kirim request dengan retry otomatis pada 429/5xx (exponential backoff)."""
        attempt = 0
        while True:
            try:
                if method == "GET":
                    r = self.session.get(f"{self.base_url}{path}", timeout=30, **kwargs)
                elif method == "POST":
                    r = self.session.post(f"{self.base_url}{path}", timeout=30, **kwargs)
                else:
                    r = self.session.delete(f"{self.base_url}{path}", timeout=30, **kwargs)
            except requests.RequestException:
                if attempt >= max_retries:
                    raise
                attempt += 1
                time.sleep(backoff ** attempt)
                continue
            # Retry hanya pada rate limit (429) atau server error (5xx)
            if r.status_code in (429, 500, 502, 503, 504):
                if attempt >= max_retries:
                    return self._handle(r)
                attempt += 1
                time.sleep(backoff ** attempt)
                continue
            return self._handle(r)

    @staticmethod
    def _handle(r: requests.Response) -> Any:
        try:
            body = r.json()
        except ValueError:
            body = {"text": r.text}
        if r.status_code >= 400:
            msg = body.get("message") or body.get("error") or str(body)
            raise HeroSMSError(f"HTTP {r.status_code}: {msg}")
        return body

    # ── Activations ──────────────────────────────────────────────

    def activation_history(
        self,
        from_: Optional[str] = None,
        to: Optional[str] = None,
        services: Optional[List[str]] = None,
        countries: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        size: int = 20,
        page: int = 1,
        sort: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict:
        params: Dict[str, Any] = {"size": size, "page": page}
        if from_: params["from"] = from_
        if to: params["to"] = to
        if services: params["services"] = services
        if countries: params["countries"] = countries
        if statuses: params["statuses"] = statuses
        if sort: params["sort"] = sort
        if search: params["search"] = search
        return self._get("/activations/history", params)

    def active_activations(
        self,
        size: int = 20,
        page: int = 1,
        sort: Optional[str] = None,
        search: Optional[str] = None,
        verification_type: Optional[str] = None,
        from_: Optional[str] = None,
        to: Optional[str] = None,
        countries: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
    ) -> Dict:
        params: Dict[str, Any] = {"size": size, "page": page}
        if sort: params["sort"] = sort
        if search: params["search"] = search
        if verification_type: params["verificationType"] = verification_type
        if from_: params["from"] = from_
        if to: params["to"] = to
        if countries: params["countries"] = countries
        if services: params["services"] = services
        return self._get("/activations", params)

    def buy_activation(
        self,
        service: str,
        country: Optional[str] = None,
        operator: Optional[str] = None,
        verification_type: Optional[str] = None,
    ) -> Dict:
        json_body: Dict[str, Any] = {"service": service}
        if country: json_body["country"] = country
        if operator: json_body["operator"] = operator
        if verification_type: json_body["verificationType"] = verification_type
        return self._post("/activations", json=json_body)

    def cancel_activation(self, activation_id: str) -> Dict:
        return self._delete(f"/activations/{activation_id}")

    def finish_activation(self, activation_id: str) -> Dict:
        return self._post(f"/activations/{activation_id}/finish")

    def replace_activation(self, activation_id: str) -> Dict:
        return self._post(f"/activations/{activation_id}/replace")

    def reactivate_activation(self, activation_id: str) -> Dict:
        return self._post(f"/activations/{activation_id}/reactivate")

    def reactivate_options(self, activation_id: str) -> Dict:
        return self._get(f"/activations/{activation_id}/reactivate/options")

    def prolong_activation(self, activation_id: str, duration: Optional[str] = None) -> Dict:
        json_body: Dict[str, Any] = {}
        if duration: json_body["duration"] = duration
        return self._post(f"/activations/{activation_id}/prolong", json=json_body)

    def prolong_options(self, activation_id: str) -> Dict:
        return self._get(f"/activations/{activation_id}/prolong/options")

    def prolong_history(self, activation_id: str) -> Dict:
        return self._get(f"/activations/{activation_id}/prolong/history")

    def resend_sms(self, activation_id: str) -> Dict:
        """Minta pengiriman ulang SMS (status 3 = request resending of SMS)."""
        return self.legacy("setStatus", {"id": activation_id, "status": 3})

    def lookup_price(self, country: str, service: str) -> tuple[str, str]:
        """Coba ambil harga dari legacy getPrices. Kembalikan (price, currency).

        Coba beberapa bentuk respons yang mungkin sebelum gagarkan '-'.
        """
        try:
            data = self.legacy("getPrices")
            if not isinstance(data, dict):
                return "-", ""

            country_l = country.lower()
            service_l = service.lower()

            # Format 1: {data: [{service, country, price, currency}, ...]}
            if isinstance(data.get("data"), list):
                for item in data["data"]:
                    if not isinstance(item, dict):
                        continue
                    if (str(item.get("service", "")).lower() == service_l
                            and str(item.get("country", "")).lower() == country_l):
                        return str(item.get("price", "-")), str(item.get("currency", ""))

            def _extract_price(val):
                if isinstance(val, dict):
                    return str(val.get("price", "-")), str(val.get("currency", ""))
                return str(val), ""

            # Format 2: {service: {country: price}} / {country: {service: price}}
            for k, v in data.items():
                if not isinstance(v, dict):
                    continue
                if str(k).lower() == service_l:
                    for ck, cv in v.items():
                        if str(ck).lower() == country_l:
                            return _extract_price(cv)
                if str(k).lower() == country_l:
                    for sk, sv in v.items():
                        if str(sk).lower() == service_l:
                            return _extract_price(sv)

            # Format 3: flat {service_country: price}
            for k, v in data.items():
                if f"{service}_{country}".lower() == str(k).lower():
                    return str(v), ""
        except Exception:  # noqa: BLE001
            pass
        return "-", ""

    def otp_last(self, activation_id: str) -> Dict:
        return self._get(f"/activations/{activation_id}/otp/last")

    def otp_list(
        self,
        activation_id: str,
        size: int = 20,
        page: int = 1,
        sort: Optional[str] = None,
        verification_type: Optional[str] = None,
        from_: Optional[str] = None,
        to: Optional[str] = None,
    ) -> Dict:
        params: Dict[str, Any] = {"size": size, "page": page}
        if sort: params["sort"] = sort
        if verification_type: params["verificationType"] = verification_type
        if from_: params["from"] = from_
        if to: params["to"] = to
        return self._get(f"/activations/{activation_id}/otp", params)

    # ── Classifiers ──────────────────────────────────────────────

    def custom_durations(self) -> Dict:
        return self._get("/classifiers/activations/custom-durations")

    # ── Stats ────────────────────────────────────────────────────

    def user_stats(self) -> Dict:
        return self._get("/activations/stats")

    def deliverability_stats(self) -> Dict:
        return self._get("/stats/deliverability")

    def offers(self, verification_type: str) -> Dict:
        return self._get(f"/activations/offers/{verification_type}")

    # ── Emails ───────────────────────────────────────────────────

    def email_list(
        self,
        size: int = 20,
        page: int = 1,
        sort: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict:
        params: Dict[str, Any] = {"size": size, "page": page}
        if sort: params["sort"] = sort
        if search: params["search"] = search
        return self._get("/emails", params)

    def buy_email_activation(
        self,
        domain: str,
        service: str,
        verification_type: Optional[str] = None,
    ) -> Dict:
        json_body: Dict[str, Any] = {"domain": domain, "service": service}
        if verification_type: json_body["verificationType"] = verification_type
        return self._post("/emails", json=json_body)

    def email_detail(self, email_id: str) -> Dict:
        return self._get(f"/emails/{email_id}")

    def cancel_email(self, email_id: str) -> Dict:
        return self._delete(f"/emails/{email_id}")

    def reorder_email(self, email_id: str) -> Dict:
        return self._post(f"/emails/{email_id}/reorder")

    def email_domains(self, site: Optional[str] = None) -> Dict:
        params: Dict[str, Any] = {}
        if site: params["site"] = site
        return self._get("/emails/domains", params)

    def email_offers(self, site: Optional[str] = None) -> Dict:
        params: Dict[str, Any] = {}
        if site: params["site"] = site
        return self._get("/emails/offers", params)

    # ── SMS-Activate compatible (query action) ───────────────────

    def legacy(self, action: str, params: Optional[Dict] = None) -> Dict:
        p = dict(params or {})
        p["action"] = action
        # legacy endpoint uses api_key as query param
        p["api_key"] = self.api_key
        r = self.session.get(f"{self.legacy_base}/stubs/handler_api.php", params=p, timeout=30)
        return self._handle(r)
