"""Centralized HTTP client for the OpenStack API.

Authentication is performed via **Keystone v3** — the client obtains an
``X-Subject-Token`` and discovers service endpoints from the token's
catalogue.

Token caching
-------------
After the first authentication the token, catalog and expiry are written to
``~/.orca/token_cache.yaml`` (mode 0600).  Subsequent CLI invocations load
the cached token directly — no Keystone round-trip — unless:

* the cache key changes (different profile / auth_url / project / region);
* the token is expired or expires within ``TOKEN_EXPIRY_BUFFER`` seconds;
* Keystone returns 401 (the cache is cleared and a fresh token is fetched).
"""

from __future__ import annotations

import hashlib
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import yaml

from orca_cli.core.exceptions import APIError, AuthenticationError

# Seconds before actual expiry to treat the token as expired (5 min buffer)
TOKEN_EXPIRY_BUFFER = 300

TOKEN_CACHE_PATH = Path.home() / ".orca" / "token_cache.yaml"


class OrcaClient:
    """Authenticates against Keystone v3 and exposes helpers for Nova /
    Neutron / other OpenStack services."""

    def __init__(self, config: dict) -> None:
        self._auth_url = config["auth_url"].rstrip("/")
        self._username = config["username"]
        self._password = config["password"]

        # User domain — name or ID
        self._user_domain_name = config.get("user_domain_name")
        self._user_domain_id = config.get("user_domain_id")

        # Project domain — name or ID (falls back to user domain)
        self._project_domain_name = config.get("project_domain_name") or self._user_domain_name
        self._project_domain_id = config.get("project_domain_id") or self._user_domain_id

        # Project — name or ID
        self._project_name = config.get("project_name")
        self._project_id = config.get("project_id")

        # Interface preference (public / internal / admin)
        self._interface = config.get("interface", "public")

        # Region filter (optional)
        self._region_name = config.get("region_name")

        self._token: str | None = None
        self._catalog: list[dict] = []
        self._token_data: dict = {}  # full token body from Keystone
        self._token_from_cache: bool = False  # True when loaded from disk cache

        insecure = str(config.get("insecure", "false")).lower() in ("true", "1", "yes")
        verify: bool | str = not insecure
        if not insecure and config.get("cacert"):
            verify = config["cacert"]
        self._http = httpx.Client(timeout=httpx.Timeout(30.0, read=600.0, write=600.0), verify=verify)

        # Build a stable cache key from the identity of this "cluster"
        self._cache_key = self._build_cache_key()

        # Try cache first, fall back to live authentication
        if not self._load_token_cache():
            self._authenticate()

    # ── Cache key ─────────────────────────────────────────────────────────────

    def _build_cache_key(self) -> str:
        """SHA-256 of the fields that uniquely identify a cluster+user+project."""
        parts = "|".join([
            self._auth_url,
            self._username,
            self._user_domain_name or self._user_domain_id or "",
            self._project_name or self._project_id or "",
            self._region_name or "",
        ])
        return hashlib.sha256(parts.encode()).hexdigest()

    # ── Token cache (disk) ────────────────────────────────────────────────────

    def _load_token_cache(self) -> bool:
        """Load a previously cached token if it is still valid.

        Returns True when a usable cached token was loaded, False otherwise.
        """
        if not TOKEN_CACHE_PATH.exists():
            return False
        try:
            data = yaml.safe_load(TOKEN_CACHE_PATH.read_text())
        except Exception:
            return False

        if not isinstance(data, dict):
            return False

        # Verify the cache belongs to this cluster/user/project/region
        if data.get("cache_key") != self._cache_key:
            return False

        # Verify expiry
        expires_at_str = data.get("expires_at", "")
        if not expires_at_str:
            return False
        try:
            expires_at = datetime.fromisoformat(
                expires_at_str.replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            remaining = (expires_at - now).total_seconds()
            if remaining < TOKEN_EXPIRY_BUFFER:
                return False
        except Exception:
            return False

        # Cache is valid — restore state
        self._token = data.get("token")
        self._catalog = data.get("catalog", [])
        self._token_data = data.get("token_data", {})
        self._token_from_cache = True
        return bool(self._token)

    def _save_token_cache(self) -> None:
        """Persist the current token to disk."""
        expires_at = self._token_data.get("expires_at", "")
        data = {
            "cache_key": self._cache_key,
            "token": self._token,
            "expires_at": expires_at,
            "catalog": self._catalog,
            "token_data": self._token_data,
        }
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_PATH.write_text(yaml.dump(data, default_flow_style=False))
        TOKEN_CACHE_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600

    def _clear_token_cache(self) -> None:
        """Delete the on-disk token cache (called on 401)."""
        try:
            TOKEN_CACHE_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    # ── Keystone v3 authentication ────────────────────────────────────────────

    @staticmethod
    def _domain_ref(name: str | None, id_: str | None) -> dict:
        """Build a Keystone domain reference (``{name: …}`` or ``{id: …}``)."""
        if id_:
            return {"id": id_}
        return {"name": name or "Default"}

    def _authenticate(self) -> None:
        """POST to Keystone ``/v3/auth/tokens`` and store the token +
        service catalogue.  Saves the result to the disk cache."""
        url = f"{self._auth_url}/v3/auth/tokens"

        user_domain = self._domain_ref(self._user_domain_name, self._user_domain_id)
        project_domain = self._domain_ref(self._project_domain_name, self._project_domain_id)

        # Project scope — by name or by ID
        if self._project_id:
            project_scope: dict = {"id": self._project_id}
        else:
            project_scope = {"name": self._project_name, "domain": project_domain}

        payload = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self._username,
                            "domain": user_domain,
                            "password": self._password,
                        }
                    },
                },
                "scope": {"project": project_scope},
            }
        }
        resp = self._http.post(url, json=payload)
        if resp.status_code in (401, 403):
            raise AuthenticationError(
                "Keystone authentication failed — verify your credentials "
                "('orca setup')."
            )
        if not resp.is_success:
            raise APIError(resp.status_code, resp.text[:300])

        self._token = resp.headers.get("X-Subject-Token", resp.headers.get("x-subject-token"))
        if not self._token:
            raise AuthenticationError("No X-Subject-Token returned by Keystone.")

        body = resp.json()
        self._token_data = body.get("token", {})
        self._catalog = self._token_data.get("catalog", [])
        self._token_from_cache = False

        # Persist to disk so the next CLI invocation can reuse it
        self._save_token_cache()

    # ── Service catalogue helpers ─────────────────────────────────────────────

    def _endpoint_for(self, service_type: str, interface: str | None = None) -> str:
        """Resolve an endpoint URL from the Keystone catalogue."""
        iface = interface or self._interface or "public"
        for svc in self._catalog:
            if svc.get("type") == service_type:
                for ep in svc.get("endpoints", []):
                    if ep.get("interface") != iface:
                        continue
                    if self._region_name and ep.get("region_id") != self._region_name:
                        continue
                    return ep["url"].rstrip("/")
        raise APIError(
            0,
            f"Service '{service_type}' ({iface}) not found in the catalogue. "
            "Check your OpenStack project configuration.",
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

    @property
    def backup_url(self) -> str:
        """Freezer (backup) public endpoint."""
        return self._endpoint_for("backup")

    @property
    def object_store_url(self) -> str:
        """Swift (object-store) public endpoint."""
        return self._endpoint_for("object-store")

    @property
    def orchestration_url(self) -> str:
        """Heat (orchestration) public endpoint."""
        return self._endpoint_for("orchestration")

    @property
    def dns_url(self) -> str:
        """Designate (dns) public endpoint."""
        return self._endpoint_for("dns")

    @property
    def placement_url(self) -> str:
        """Placement public endpoint."""
        return self._endpoint_for("placement")

    @property
    def alarming_url(self) -> str:
        """Aodh (alarming) public endpoint."""
        return self._endpoint_for("alarming")

    # ── Generic HTTP helpers ──────────────────────────────────────────────────

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {
            "X-Auth-Token": self._token or "",
            "Accept": "application/json",
            "X-OpenStack-Nova-API-Version": "2.79",
        }
        if extra:
            h.update(extra)
        return h

    @staticmethod
    def _extract_error_message(body: dict) -> str:
        """Extract a human-readable message from OpenStack error responses."""
        if isinstance(body.get("message"), str):
            return body["message"]
        if isinstance(body.get("error"), str):
            return body["error"]
        if isinstance(body.get("error"), dict):
            return body["error"].get("message", str(body["error"]))
        for value in body.values():
            if isinstance(value, dict) and "message" in value:
                return value["message"]
        return str(body)

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code in (401, 403):
            raise AuthenticationError()
        if not response.is_success:
            detail = ""
            try:
                body = response.json()
                detail = self._extract_error_message(body)
            except Exception:
                detail = response.text[:300]
            raise APIError(response.status_code, detail)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def _request(self, method: str, url: str,
                 extra_headers: Optional[Dict[str, str]] = None,
                 **kwargs: Any) -> Any:
        """Execute an HTTP request, transparently re-authenticating once on 401.

        When a cached token is rejected by the server the cache is cleared,
        a fresh token is obtained, and the request is retried exactly once.
        """
        resp = getattr(self._http, method)(url, headers=self._headers(extra_headers), **kwargs)

        if resp.status_code == 401 and self._token_from_cache:
            # The cached token was rejected — clear cache, re-auth, retry
            self._clear_token_cache()
            self._authenticate()
            resp = getattr(self._http, method)(url, headers=self._headers(extra_headers), **kwargs)

        return self._handle_response(resp)

    # ── Public HTTP methods ───────────────────────────────────────────────────

    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None) -> Any:
        return self._request("get", url, extra_headers=headers, params=params)

    def post(self, url: str, json: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None) -> Any:
        return self._request("post", url, extra_headers=headers, json=json)

    def put(self, url: str, json: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None) -> Any:
        return self._request("put", url, extra_headers=headers, json=json)

    def patch(self, url: str, json: Optional[Dict[str, Any]] = None,
              content: Optional[bytes] = None,
              content_type: Optional[str] = None) -> Any:
        extra: Dict[str, str] = {}
        if content_type:
            extra["Content-Type"] = content_type
        if content is not None:
            return self._request("patch", url, extra_headers=extra or None, content=content)
        return self._request("patch", url, extra_headers=extra or None, json=json)

    def delete(self, url: str, params: Optional[Dict[str, Any]] = None,
               headers: Optional[Dict[str, str]] = None) -> Any:
        return self._request("delete", url, extra_headers=headers, params=params)

    def put_stream(self, url: str, stream, content_type: str = "application/octet-stream") -> Any:
        """PUT with a file-like stream body (for large uploads)."""
        extra = {"Content-Type": content_type}
        return self._request("put", url, extra_headers=extra, content=stream)

    def get_stream(self, url: str):
        """GET that returns a streaming response context manager."""
        return self._http.stream("GET", url, headers=self._headers())

    def close(self) -> None:
        self._http.close()
