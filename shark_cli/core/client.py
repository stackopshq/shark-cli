"""Centralized HTTP client for the Sharktech Cloud (OpenStack) API.

Authentication is performed via **Keystone v3** — the client obtains an
``X-Subject-Token`` and discovers service endpoints from the token's
catalogue.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from shark_cli.core.exceptions import APIError, AuthenticationError


class SharkClient:
    """Authenticates against Keystone v3 and exposes helpers for Nova /
    Neutron / other OpenStack services."""

    def __init__(
        self,
        auth_url: str,
        username: str,
        password: str,
        domain_id: str,
        project_id: str,
        insecure: bool = False,
    ) -> None:
        self._auth_url = auth_url.rstrip("/")
        self._username = username
        self._password = password
        self._domain_id = domain_id
        self._project_id = project_id

        self._token: str | None = None
        self._catalog: list[dict] = []

        self._http = httpx.Client(timeout=httpx.Timeout(30.0, read=600.0, write=600.0), verify=not insecure)

        # Authenticate immediately so errors surface early
        self._authenticate()

    # ── Keystone v3 authentication ────────────────────────────────────

    def _authenticate(self) -> None:
        """POST to Keystone ``/v3/auth/tokens`` and store the token +
        service catalogue."""
        url = f"{self._auth_url}/v3/auth/tokens"
        payload = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self._username,
                            "domain": {"name": self._domain_id},
                            "password": self._password,
                        }
                    },
                },
                "scope": {
                    "project": {
                        "name": self._project_id,
                        "domain": {"name": self._domain_id},
                    }
                },
            }
        }
        resp = self._http.post(url, json=payload)
        if resp.status_code in (401, 403):
            raise AuthenticationError(
                "Keystone authentication failed — verify your credentials "
                "('shark setup')."
            )
        if not resp.is_success:
            raise APIError(resp.status_code, resp.text[:300])

        self._token = resp.headers.get("X-Subject-Token", resp.headers.get("x-subject-token"))
        if not self._token:
            raise AuthenticationError("No X-Subject-Token returned by Keystone.")

        body = resp.json()
        self._catalog = body.get("token", {}).get("catalog", [])

    # ── Service catalogue helpers ─────────────────────────────────────

    def _endpoint_for(self, service_type: str, interface: str = "public") -> str:
        """Resolve a public endpoint URL from the Keystone catalogue."""
        for svc in self._catalog:
            if svc.get("type") == service_type:
                for ep in svc.get("endpoints", []):
                    if ep.get("interface") == interface:
                        return ep["url"].rstrip("/")
        raise APIError(
            0,
            f"Service '{service_type}' ({interface}) not found in the catalogue. "
            "Check your Sharktech project configuration.",
        )

    @property
    def compute_url(self) -> str:
        """Nova (compute) public endpoint."""
        return self._endpoint_for("compute")

    @property
    def network_url(self) -> str:
        """Neutron (network) public endpoint."""
        return self._endpoint_for("network")

    @property
    def identity_url(self) -> str:
        """Keystone (identity) public endpoint."""
        return self._endpoint_for("identity")

    @property
    def image_url(self) -> str:
        """Glance (image) public endpoint."""
        return self._endpoint_for("image")

    @property
    def volume_url(self) -> str:
        """Cinder (volume) public endpoint."""
        return self._endpoint_for("volumev3")

    @property
    def container_infra_url(self) -> str:
        """Magnum (container-infra) public endpoint."""
        return self._endpoint_for("container-infra")

    @property
    def metric_url(self) -> str:
        """Gnocchi (metric) public endpoint."""
        return self._endpoint_for("metric")

    @property
    def key_manager_url(self) -> str:
        """Barbican (key-manager) public endpoint."""
        return self._endpoint_for("key-manager")

    @property
    def load_balancer_url(self) -> str:
        """Octavia (load-balancer) public endpoint."""
        return self._endpoint_for("load-balancer")

    # ── Generic HTTP helpers ──────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Auth-Token": self._token or "",
            "Accept": "application/json",
            "X-OpenStack-Nova-API-Version": "2.79",
        }

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code in (401, 403):
            raise AuthenticationError()
        if not response.is_success:
            detail = ""
            try:
                body = response.json()
                detail = body.get("message") or body.get("error") or str(body)
            except Exception:
                detail = response.text[:300]
            raise APIError(response.status_code, detail)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = self._http.get(url, headers=self._headers(), params=params)
        return self._handle_response(resp)

    def post(self, url: str, json: Optional[Dict[str, Any]] = None) -> Any:
        resp = self._http.post(url, headers=self._headers(), json=json)
        return self._handle_response(resp)

    def put(self, url: str, json: Optional[Dict[str, Any]] = None) -> Any:
        resp = self._http.put(url, headers=self._headers(), json=json)
        return self._handle_response(resp)

    def patch(self, url: str, json: Optional[Dict[str, Any]] = None,
              content: Optional[bytes] = None,
              content_type: Optional[str] = None) -> Any:
        headers = self._headers()
        if content_type:
            headers["Content-Type"] = content_type
        if content is not None:
            resp = self._http.patch(url, headers=headers, content=content)
        else:
            resp = self._http.patch(url, headers=headers, json=json)
        return self._handle_response(resp)

    def delete(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = self._http.delete(url, headers=self._headers(), params=params)
        return self._handle_response(resp)

    def put_stream(self, url: str, stream, content_type: str = "application/octet-stream") -> Any:
        """PUT with a file-like stream body (for large uploads)."""
        headers = self._headers()
        headers["Content-Type"] = content_type
        resp = self._http.put(url, headers=headers, content=stream)
        return self._handle_response(resp)

    def get_stream(self, url: str):
        """GET that returns a streaming response context manager."""
        return self._http.stream("GET", url, headers=self._headers())

    def close(self) -> None:
        self._http.close()
