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

import email.utils
import hashlib
import logging
import os
import random
import re
import stat
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

import httpx
import yaml

from orca_cli.core.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    PermissionDeniedError,
)


def with_version(url: str, version: str) -> str:
    """Append ``/{version}`` to ``url`` if not already present (idempotent).

    OpenStack catalogues are inconsistent: the same service may be advertised
    versionless (e.g. ``http://host/identity``) or already versioned
    (``http://host/identity/v3``). Services that need a specific API version
    use this helper so callers don't have to special-case every cloud.

    The match is anchored on the exact version segment to avoid false
    positives across versions:

    >>> with_version("http://host/identity", "v3")
    'http://host/identity/v3'
    >>> with_version("http://host/identity/v3", "v3")
    'http://host/identity/v3'
    >>> with_version("http://host/heat-api/v1/uuid", "v1")
    'http://host/heat-api/v1/uuid'
    """
    stripped = url.rstrip("/")
    pattern = rf"/{re.escape(version)}(?:/|$)"
    if re.search(pattern, stripped):
        return stripped
    return f"{stripped}/{version}"

# Module logger — silent by default (no handlers attached). The root CLI
# wires handlers when --debug is passed. Auth payloads are never logged,
# and HTTP headers are filtered to strip `X-Auth-Token` before emission.
logger = logging.getLogger(__name__)

# Header names (lowercased) whose values must never appear in debug logs.
_REDACTED_HEADERS = frozenset({"x-auth-token", "x-subject-token", "authorization"})


def _redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return a copy of ``headers`` with sensitive values replaced by ``***``."""
    return {k: ("***" if k.lower() in _REDACTED_HEADERS else v)
            for k, v in headers.items()}

# Seconds before actual expiry to treat the token as expired (5 min buffer)
TOKEN_EXPIRY_BUFFER = 300

TOKEN_CACHE_PATH = Path.home() / ".orca" / "token_cache.yaml"

# ── Transient-error retry policy ─────────────────────────────────────────────
# HTTP statuses that indicate a transient server/infra problem.
RETRY_STATUSES = frozenset({500, 502, 503, 504})
# HTTP statuses handled with a dedicated rate-limit wait (honours Retry-After)
# instead of the exponential-backoff path. Retried on any method — 429 means
# "try again later", not "the request was rejected", so it's safe even for
# POST/PATCH which would otherwise bypass the transient-retry loop.
RATE_LIMIT_STATUSES = frozenset({429})
# Idempotent methods — only these are retried on 5xx/network errors. POST/PATCH
# can create duplicates and are never retried in that path.
RETRY_METHODS = frozenset({"get", "delete", "put", "head", "options"})
# Total retries on transient failures (initial attempt + MAX_RETRIES retries).
MAX_RETRIES = 2
# Exponential backoff base: sleeps are RETRY_BACKOFF_BASE * 2**attempt
# → with MAX_RETRIES=2 and base=0.5: 0.5s, 1.0s between attempts.
RETRY_BACKOFF_BASE = 0.5
# Upper bound on a Retry-After hint we'll honour — a buggy server advertising
# "wait an hour" mustn't freeze the CLI. Beyond this we surface the 429 as an
# APIError so the user can decide.
MAX_RATE_LIMIT_WAIT = 60.0
# httpx transport exceptions that we treat as retryable network blips.
_TRANSIENT_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)


def _parse_retry_after(value: str) -> Optional[float]:
    """Interpret a ``Retry-After`` header per RFC 7231 §7.1.3.

    Accepts either delta-seconds (``"5"``) or an HTTP-date (``"Wed, 21 Oct 2015
    07:28:00 GMT"``). Returns seconds to wait, or ``None`` if the header is
    absent/unparseable — callers fall back to exponential backoff in that case.
    """
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    parsed = email.utils.parsedate_to_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    delta = (parsed - datetime.now(timezone.utc)).total_seconds()
    return max(0.0, delta)


def _backoff_with_jitter(attempt: int) -> float:
    """Exponential backoff with full jitter (AWS architecture blog pattern).

    Jitter matters even for a single client: a user who scripts ``orca`` in a
    CI runner across many parallel jobs will otherwise spike Keystone every
    ``RETRY_BACKOFF_BASE * 2**attempt`` seconds in lockstep.
    """
    ceiling = RETRY_BACKOFF_BASE * (2 ** attempt)
    return random.uniform(0.0, ceiling)


class OrcaClient:
    """Authenticates against Keystone v3 and exposes helpers for Nova /
    Neutron / other OpenStack services."""

    def __init__(self, config: dict) -> None:
        self._auth_url = config["auth_url"].rstrip("/")

        # ── Auth method (password or v3applicationcredential) ─────────────
        # Auto-detected from presence of application_credential_* fields
        # unless an explicit auth_type is provided.
        self._auth_type = self._detect_auth_type(config)

        # Password-flow credentials (also reused as the "user" reference when
        # an application credential is identified by name rather than by id).
        self._username = config.get("username", "")
        self._password = config.get("password", "")

        # Application-credential fields
        self._app_cred_id = config.get("application_credential_id")
        self._app_cred_secret = config.get("application_credential_secret")
        self._app_cred_name = config.get("application_credential_name")

        # User domain — name or ID
        self._user_domain_name = config.get("user_domain_name")
        self._user_domain_id = config.get("user_domain_id")

        # Project domain — name or ID (falls back to user domain)
        self._project_domain_name = config.get("project_domain_name") or self._user_domain_name
        self._project_domain_id = config.get("project_domain_id") or self._user_domain_id

        # Project — name or ID. Application credentials are pre-scoped at
        # creation time, so these fields are ignored for that auth method.
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

        verify = self._resolve_tls_verify(config)
        self._http = httpx.Client(timeout=httpx.Timeout(30.0, read=600.0, write=600.0), verify=verify)

        # Build a stable cache key from the identity of this "cluster"
        self._cache_key = self._build_cache_key()

        # Try cache first, fall back to live authentication
        if not self._load_token_cache():
            self._authenticate()

    # ── TLS verification ─────────────────────────────────────────────────────

    @staticmethod
    def _resolve_tls_verify(config: dict) -> bool | str:
        """Derive the ``httpx`` ``verify=`` argument from profile config.

        Returns ``False`` when ``insecure=true`` (and emits a visible warning
        so the user can't forget that MITM is undetectable on this connection),
        the ``cacert`` path when a custom CA is configured, or ``True`` for the
        default OS trust store. Raises ``ConfigurationError`` when ``cacert``
        points at a missing or non-readable file — failing fast beats a
        cryptic SSL handshake error later.
        """
        insecure = str(config.get("insecure", "false")).lower() in ("true", "1", "yes")
        cacert_path = config.get("cacert")

        if insecure:
            # Always to stderr — a TLS-off warning that only shows up with
            # --debug would defeat the point.
            sys.stderr.write(
                "WARNING: TLS certificate verification is disabled "
                "(insecure=true). MITM attacks on this connection are "
                "undetectable.\n"
            )
            return False

        if cacert_path:
            path = Path(cacert_path).expanduser()
            if not path.is_file():
                raise ConfigurationError(
                    f"cacert path is not a readable file: {cacert_path}"
                )
            return str(path)

        return True

    # ── Auth-type detection ──────────────────────────────────────────────────

    @staticmethod
    def _detect_auth_type(config: dict) -> str:
        """Return ``"application_credential"`` or ``"password"``.

        Honours an explicit ``auth_type`` setting (``v3applicationcredential``
        / ``application_credential`` / ``password``); otherwise auto-detects
        based on the presence of any ``application_credential_*`` field.
        """
        explicit = str(config.get("auth_type", "")).lower()
        if explicit in ("v3applicationcredential", "application_credential"):
            return "application_credential"
        if explicit == "password":
            return "password"
        if config.get("application_credential_id") or config.get("application_credential_secret"):
            return "application_credential"
        return "password"

    # ── Cache key ─────────────────────────────────────────────────────────────

    def _build_cache_key(self) -> str:
        """SHA-256 of the fields that uniquely identify this token's scope.

        Application credentials are pre-scoped at creation time, so the cache
        key keys on the credential identity (id, or name@user) rather than on
        username+project.
        """
        if self._auth_type == "application_credential":
            identity = self._app_cred_id or f"{self._app_cred_name}@{self._username}"
            parts = "|".join([
                self._auth_url,
                "appcred",
                identity,
                self._region_name or "",
            ])
        else:
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
        if self._token:
            logger.debug("Loaded token from cache, %.0fs remaining", remaining)
        return bool(self._token)

    def _save_token_cache(self) -> None:
        """Persist the current token to disk atomically.

        Writes to a sibling tempfile and ``os.replace`` into place so a
        concurrent ``orca`` invocation reading the cache never observes a
        truncated half-write. The tempfile inherits the 0600 mode *before*
        the rename — no window where the final path exists world-readable.
        """
        expires_at = self._token_data.get("expires_at", "")
        data = {
            "cache_key": self._cache_key,
            "token": self._token,
            "expires_at": expires_at,
            "catalog": self._catalog,
            "token_data": self._token_data,
        }
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".token_cache.", suffix=".tmp", dir=str(TOKEN_CACHE_PATH.parent)
        )
        try:
            os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600 before write
            with os.fdopen(tmp_fd, "w") as f:
                yaml.dump(data, f, default_flow_style=False)
            os.replace(tmp_path, TOKEN_CACHE_PATH)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

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

    def _build_auth_payload(self) -> dict:
        """Construct the Keystone v3 ``/auth/tokens`` request body for the
        configured auth type.

        Application credentials are pre-scoped at creation time, so no
        ``scope`` block is sent for that flow.
        """
        if self._auth_type == "application_credential":
            if not self._app_cred_secret:
                raise AuthenticationError(
                    "Application credential secret is missing. Set "
                    "'application_credential_secret' in your profile or "
                    "OS_APPLICATION_CREDENTIAL_SECRET in your environment."
                )
            if self._app_cred_id:
                ac: dict = {"id": self._app_cred_id, "secret": self._app_cred_secret}
            elif self._app_cred_name and self._username:
                ac = {
                    "name": self._app_cred_name,
                    "secret": self._app_cred_secret,
                    "user": {
                        "name": self._username,
                        "domain": self._domain_ref(self._user_domain_name, self._user_domain_id),
                    },
                }
            else:
                raise AuthenticationError(
                    "Application credential needs either "
                    "'application_credential_id' or "
                    "('application_credential_name' + 'username')."
                )
            return {
                "auth": {
                    "identity": {
                        "methods": ["application_credential"],
                        "application_credential": ac,
                    }
                }
            }

        # Password flow
        if not self._password:
            raise AuthenticationError(
                "Password is missing. Set 'password' in your profile or "
                "OS_PASSWORD in your environment."
            )
        user_domain = self._domain_ref(self._user_domain_name, self._user_domain_id)
        project_domain = self._domain_ref(self._project_domain_name, self._project_domain_id)
        if self._project_id:
            project_scope: dict = {"id": self._project_id}
        else:
            project_scope = {"name": self._project_name, "domain": project_domain}
        return {
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

    def _authenticate(self) -> None:
        """POST to Keystone ``/v3/auth/tokens`` and store the token +
        service catalogue.  Saves the result to the disk cache."""
        url = f"{self._auth_url}/v3/auth/tokens"
        # Log auth intent without the payload — it contains the password
        # or application-credential secret.
        logger.debug(
            "Authenticating to %s (auth_type=%s, user=%s, project=%s, region=%s)",
            url, self._auth_type,
            self._username or self._app_cred_name or self._app_cred_id or "?",
            self._project_name or self._project_id or "?",
            self._region_name or "any",
        )
        payload = self._build_auth_payload()
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
        logger.debug("Authentication successful, %d service(s) in catalogue",
                     len(self._catalog))

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
    def token(self) -> str:
        """The current Keystone X-Auth-Token (empty string before auth)."""
        return self._token or ""

    @property
    def token_data(self) -> dict:
        """The full ``token`` object returned by Keystone (user, project,
        roles, catalog, expires_at, ...). Empty before authentication.
        """
        return self._token_data or {}

    @property
    def catalog(self) -> list[dict]:
        """The service catalog returned in the active token (read-only view)."""
        return list(self._catalog)

    @property
    def auth_url(self) -> str:
        """The Keystone v3 base URL configured for this client."""
        return self._auth_url

    @property
    def region_name(self) -> Optional[str]:
        """The region used to filter the catalogue, or ``None``."""
        return self._region_name

    @property
    def interface(self) -> str:
        """The interface (``public`` / ``internal`` / ``admin``) used to
        select endpoints from the catalogue.
        """
        return self._interface

    @property
    def project_id(self) -> Optional[str]:
        """The project ID this client is scoped to, if any."""
        return self._project_id

    def authenticate(self) -> None:
        """Force a fresh Keystone ``/auth/tokens`` round-trip.

        The cached token (if any) is *not* cleared by this call — it is
        intentional that a successful authentication overwrites the cached
        token with a fresh one. ``setup`` uses this to verify credentials
        against the live cloud.
        """
        self._authenticate()

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
        """Cinder (block storage) public endpoint.

        The service type was renamed from ``volumev3`` to ``block-storage``
        in OpenStack Train (2019.2). New deployments (DevStack 2024+, recent
        public clouds) only advertise ``block-storage``; older ones still
        ship ``volumev3`` (or ``volumev2``). We try the modern type first
        and fall back so orca works against both eras of catalogue.
        """
        for service_type in ("block-storage", "volumev3", "volumev2"):
            try:
                return self._endpoint_for(service_type)
            except APIError:
                continue
        raise APIError(
            0,
            "Cinder/block-storage endpoint not found in catalogue. "
            "Check your OpenStack project configuration.",
        )

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

    @property
    def rating_url(self) -> str:
        """CloudKitty (rating) public endpoint."""
        return self._endpoint_for("rating")

    # ── Generic HTTP helpers ──────────────────────────────────────────────────

    def _headers(self, extra: Optional[Dict[str, str]] = None,
                 url: Optional[str] = None) -> Dict[str, str]:
        h: Dict[str, str] = {
            "X-Auth-Token": self._token or "",
            "Accept": "application/json",
        }
        if url and self._is_compute_url(url):
            h["X-OpenStack-Nova-API-Version"] = "2.79"
        if extra:
            h.update(extra)
        return h

    def _is_compute_url(self, url: str) -> bool:
        """True if the URL targets Nova — the only service that honours the microversion header."""
        try:
            return url.startswith(self.compute_url)
        except APIError:
            return False

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

    @staticmethod
    def _is_html_response(response: httpx.Response) -> bool:
        """True if the body is HTML — typically a load-balancer 404 page for
        an endpoint that is advertised in the catalogue but not actually
        exposed on this cloud."""
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" in content_type:
            return True
        # Some gateways don't set content-type correctly; sniff the first bytes.
        preview = response.text[:200].lstrip().lower()
        return preview.startswith("<!doctype html") or preview.startswith("<html")

    @staticmethod
    def _extract_request_id(response: httpx.Response) -> str:
        """Return the OpenStack request-id from response headers, if any.

        Services expose this under ``x-openstack-request-id`` (Keystone,
        Glance, Cinder, Neutron…) with Nova additionally echoing it as
        ``x-compute-request-id``. Case-insensitive by httpx conventions.
        """
        return (response.headers.get("x-openstack-request-id")
                or response.headers.get("x-compute-request-id")
                or "")

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code == 401:
            raise AuthenticationError()
        request_id = self._extract_request_id(response)
        if response.status_code == 403:
            detail = ""
            try:
                body = response.json()
                detail = self._extract_error_message(body)
            except Exception:
                pass
            msg = (
                "Permission denied (403). Your token is valid but lacks the required "
                "role for this action — typically an admin-only operation."
            )
            if detail:
                msg += f" — {detail}"
            if request_id:
                msg += f" [request-id: {request_id}]"
            raise PermissionDeniedError(msg)
        if not response.is_success:
            if self._is_html_response(response):
                raise APIError(
                    response.status_code,
                    "Service returned an HTML error page — the endpoint is advertised "
                    "in the catalogue but not actually exposed on this cloud.",
                    request_id=request_id,
                )
            detail = ""
            try:
                body = response.json()
                detail = self._extract_error_message(body)
            except Exception:
                detail = response.text[:300]
            raise APIError(response.status_code, detail, request_id=request_id)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def _send(self, method: str, url: str,
              extra_headers: Optional[Dict[str, str]] = None,
              **kwargs: Any) -> httpx.Response:
        """Single HTTP send with inline 401→re-auth retry (once, cached token only)."""
        started = time.monotonic()
        headers = self._headers(extra_headers, url=url)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("HTTP %s %s headers=%s params=%s",
                         method.upper(), url,
                         _redact_headers(headers), kwargs.get("params"))
        # httpx's per-method shortcuts (.delete, .get, ...) refuse a
        # `json=` body for methods that don't usually carry one. A handful
        # of OpenStack endpoints (Barbican container consumers) do, so we
        # route through ``request()`` whenever a JSON body is present.
        if "json" in kwargs and method.lower() in ("delete", "get", "head", "options"):
            resp = self._http.request(method.upper(), url,
                                       headers=headers, **kwargs)
        else:
            resp = getattr(self._http, method)(url, headers=headers, **kwargs)
        if resp.status_code == 401 and self._token_from_cache:
            # Cached token was rejected — clear cache, re-auth, retry once.
            logger.debug("HTTP %s %s → 401 with cached token, re-authenticating",
                         method.upper(), url)
            self._clear_token_cache()
            self._authenticate()
            headers = self._headers(extra_headers, url=url)
            if "json" in kwargs and method.lower() in ("delete", "get", "head", "options"):
                resp = self._http.request(method.upper(), url,
                                           headers=headers, **kwargs)
            else:
                resp = getattr(self._http, method)(url, headers=headers, **kwargs)
        logger.debug("HTTP %s %s → %d in %.2fs",
                     method.upper(), url, resp.status_code,
                     time.monotonic() - started)
        return resp

    def _request(self, method: str, url: str,
                 extra_headers: Optional[Dict[str, str]] = None,
                 **kwargs: Any) -> Any:
        """Execute an HTTP request with three independent recovery mechanisms:

        1. 401 with cached token → clear cache, re-authenticate, retry once.
        2. Transient failure (5xx or network error) on an idempotent method →
           jittered exponential-backoff retry up to MAX_RETRIES times.
           POST/PATCH are never retried here because they are not guaranteed
           idempotent.
        3. 429 rate-limited → honour the ``Retry-After`` header (capped at
           MAX_RATE_LIMIT_WAIT) or fall back to jittered backoff. Applied to
           any method: 429 means "request not processed, retry later", which
           is safe even for POST/PATCH.
        """
        is_idempotent = method.lower() in RETRY_METHODS

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self._send(method, url, extra_headers=extra_headers, **kwargs)
            except _TRANSIENT_EXCEPTIONS as exc:
                if is_idempotent and attempt < MAX_RETRIES:
                    wait = _backoff_with_jitter(attempt)
                    logger.debug("Transient %s on %s %s, retrying in %.2fs (attempt %d/%d)",
                                 type(exc).__name__, method.upper(), url,
                                 wait, attempt + 1, MAX_RETRIES)
                    time.sleep(wait)
                    continue
                raise APIError(0, f"Network error: {exc}") from exc

            if (resp.status_code in RATE_LIMIT_STATUSES
                    and attempt < MAX_RETRIES):
                hint = _parse_retry_after(resp.headers.get("Retry-After", ""))
                if hint is None:
                    wait = _backoff_with_jitter(attempt)
                elif hint > MAX_RATE_LIMIT_WAIT:
                    # Server asked us to wait too long — surface the 429 to the
                    # caller instead of hanging the CLI.
                    logger.debug("429 with Retry-After=%.0fs exceeds cap %.0fs, surfacing error",
                                 hint, MAX_RATE_LIMIT_WAIT)
                    return self._handle_response(resp)
                else:
                    # Add a small jitter on top of the hint so concurrent
                    # clients don't all retry at the same instant.
                    wait = hint + random.uniform(0.0, min(1.0, hint * 0.1))
                logger.debug("Rate-limited on %s %s, waiting %.2fs (hint=%s)",
                             method.upper(), url, wait,
                             "server" if hint is not None else "backoff")
                time.sleep(wait)
                continue

            if (resp.status_code in RETRY_STATUSES
                    and is_idempotent
                    and attempt < MAX_RETRIES):
                wait = _backoff_with_jitter(attempt)
                logger.debug("HTTP %d on %s %s, retrying in %.2fs (attempt %d/%d)",
                             resp.status_code, method.upper(), url,
                             wait, attempt + 1, MAX_RETRIES)
                time.sleep(wait)
                continue

            return self._handle_response(resp)

    # ── Public HTTP methods ───────────────────────────────────────────────────

    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None) -> Any:
        return self._request("get", url, extra_headers=headers, params=params)

    def post(self, url: str, json: Optional[Union[Dict[str, Any], list]] = None,
             headers: Optional[Dict[str, str]] = None) -> Any:
        return self._request("post", url, extra_headers=headers, json=json)

    def put(self, url: str, json: Optional[Union[Dict[str, Any], list]] = None,
            headers: Optional[Dict[str, str]] = None) -> Any:
        return self._request("put", url, extra_headers=headers, json=json)

    def patch(self, url: str, json: Optional[Union[Dict[str, Any], list]] = None,
              content: Optional[bytes] = None,
              content_type: Optional[str] = None) -> Any:
        extra: Dict[str, str] = {}
        if content_type:
            extra["Content-Type"] = content_type
        if content is not None:
            return self._request("patch", url, extra_headers=extra or None, content=content)
        return self._request("patch", url, extra_headers=extra or None, json=json)

    def delete(self, url: str, params: Optional[Dict[str, Any]] = None,
               headers: Optional[Dict[str, str]] = None,
               json: Optional[Union[Dict[str, Any], list]] = None) -> Any:
        # Some OpenStack APIs (e.g. Barbican container consumers) require a
        # JSON body on DELETE — uncommon for HTTP but valid per RFC 7231.
        # Only forward `json` when supplied so httpx's per-method shortcut
        # isn't tripped up by a None-but-present kwarg.
        kwargs: dict = {"params": params}
        if json is not None:
            kwargs["json"] = json
        return self._request("delete", url, extra_headers=headers, **kwargs)

    def paginate(self, url: str, key: str, *,
                 page_size: int = 1000,
                 params: Optional[Dict[str, Any]] = None,
                 max_items: Optional[int] = None) -> list:
        """Walk an OpenStack list endpoint using marker-based pagination.

        Many services (Nova, Cinder, Neutron with ``allow_pagination``) cap
        a single response at 1000 items; without a pagination loop, callers
        silently miss anything beyond the first page. This helper issues
        ``limit`` + ``marker`` requests until one returns fewer than
        ``page_size`` items, then concatenates the pages.

        On endpoints that don't honour ``marker`` the first page is returned
        as-is (the loop exits because ``len(batch) < page_size`` or because
        the same marker is echoed back — the ``id``-based advance detects
        the fixed point).

        Args:
            url: absolute URL of the list endpoint.
            key: body key under which items are returned (e.g. ``"servers"``).
            page_size: items per page (default 1000, the OpenStack cap).
            params: extra query parameters merged into every page request.
            max_items: stop once this many items have been collected.
        """
        collected: list = []
        marker: Optional[str] = None
        base_params: Dict[str, Any] = dict(params or {})
        while True:
            p = dict(base_params)
            p["limit"] = page_size
            if marker:
                p["marker"] = marker
            page = self.get(url, params=p) or {}
            batch = page.get(key, []) if isinstance(page, dict) else []
            if not batch:
                break
            collected.extend(batch)
            if max_items is not None and len(collected) >= max_items:
                return collected[:max_items]
            if len(batch) < page_size:
                break
            last_id = batch[-1].get("id") if isinstance(batch[-1], dict) else None
            if not last_id or last_id == marker:
                break
            marker = last_id
        return collected

    def put_stream(self, url: str, *, content: Any,
                   content_type: str = "application/octet-stream",
                   content_length: Optional[int] = None,
                   extra_headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """PUT a streaming body (file-like or iterable). Returns the raw httpx response.

        Streamed bodies cannot be replayed, so this path deliberately bypasses
        ``_request``'s retry loop: a 5xx mid-upload would re-consume the
        already-drained iterator. Callers must inspect ``resp.status_code`` and
        raise :class:`APIError` themselves (see ``_check_streaming_response``
        in services).
        """
        headers = self._headers(url=url)
        headers["Content-Type"] = content_type
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        if extra_headers:
            headers.update(extra_headers)
        return self._http.put(url, headers=headers, content=content)

    def post_stream(self, url: str, *, content: Any,
                    content_type: str = "application/octet-stream",
                    content_length: Optional[int] = None,
                    extra_headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """POST a streaming or raw body. Returns the raw httpx response.

        Like :meth:`put_stream`, this bypasses ``_request``'s retry loop so the
        body iterator is never re-consumed. Use when the server expects a body
        type other than JSON (Designate ``text/dns`` zone imports, custom raw
        protocols, etc.).
        """
        headers = self._headers(url=url)
        headers["Content-Type"] = content_type
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        if extra_headers:
            headers.update(extra_headers)
        return self._http.post(url, headers=headers, content=content)

    def post_no_body(self, url: str, *,
                     extra_headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """POST without a JSON body, returning the raw response.

        Used by Swift metadata updates (account/container/object), where the
        update is conveyed through ``X-*-Meta-*`` headers and the body must be
        empty.
        """
        headers = self._headers(url=url)
        if extra_headers:
            headers.update(extra_headers)
        return self._http.post(url, headers=headers)

    def head_request(self, url: str, *,
                     extra_headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """HEAD request with auth headers — returns the raw response so callers
        can read metadata from response headers (Swift account/container/object).
        """
        headers = self._headers(url=url)
        if extra_headers:
            headers.update(extra_headers)
        return self._http.head(url, headers=headers)

    def get_stream(self, url: str, *,
                   extra_headers: Optional[Dict[str, str]] = None):
        """GET that returns a streaming response context manager."""
        headers = self._headers(url=url)
        if extra_headers:
            headers.update(extra_headers)
        return self._http.stream("GET", url, headers=headers)

    def close(self) -> None:
        self._http.close()
