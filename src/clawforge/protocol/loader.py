"""Module 0: Protocol Loader - Fetch and validate Claw Earn specifications."""

import json
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog

from clawforge.config import get_settings
from clawforge.crypto.hasher import sha256_hash

logger = structlog.get_logger(__name__)

PROTOCOL_CACHE_FILE = "claw-earn.json"
PROTOCOL_VERSION_FILE = "version.txt"
PROTOCOL_BACKUP_FILE = "claw-earn.json.bak"


class ProtocolLoader:
    """Fetches and validates Claw Earn protocol specifications."""

    def __init__(self) -> None:
        """Initialize protocol loader."""
        self._settings = get_settings()
        self._protocol_path = self._settings.get_protocol_path()
        self._protocol_path.mkdir(parents=True, exist_ok=True)
        self._cached_spec: Optional[dict[str, Any]] = None
        self._cached_version: Optional[str] = None

    async def fetch_protocol(self) -> dict[str, Any]:
        """Fetch protocol specification from remote URL.

        Returns:
            Parsed protocol specification.

        Raises:
            httpx.HTTPError: If fetch fails.
        """
        url = f"{self._settings.CLAW_EARN_BASE_URL}/claw-earn.json"

        logger.info("Fetching protocol specification", url=url)

        async with httpx.AsyncClient(verify=True) as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()

            spec = response.json()
            version = sha256_hash(json.dumps(spec, sort_keys=True))

            # Cache locally
            self._save_to_cache(spec, version)

            logger.info(
                "Protocol fetched successfully",
                version=version[:16],
            )

            self._cached_spec = spec
            self._cached_version = version

            return spec

    async def load_protocol(self) -> dict[str, Any]:
        """Load protocol specification, falling back to cache on failure.

        Returns:
            Protocol specification.
        """
        try:
            return await self.fetch_protocol()
        except Exception as e:
            logger.warning(
                "Failed to fetch protocol, using cache",
                error=str(e),
            )
            return self._load_from_cache()

    def _save_to_cache(self, spec: dict[str, Any], version: str) -> None:
        """Save protocol to local cache.

        Args:
            spec: Protocol specification.
            version: Version hash.
        """
        # Backup existing
        cache_path = self._protocol_path / PROTOCOL_CACHE_FILE
        if cache_path.exists():
            backup_path = self._protocol_path / PROTOCOL_BACKUP_FILE
            cache_path.replace(backup_path)

        # Write new
        temp_path = cache_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(spec, indent=2))
        temp_path.replace(cache_path)

        # Write version
        version_path = self._protocol_path / PROTOCOL_VERSION_FILE
        version_path.write_text(version)

        logger.debug("Protocol cached locally", version=version[:16])

    def _load_from_cache(self) -> dict[str, Any]:
        """Load protocol from local cache.

        Returns:
            Cached protocol specification.

        Raises:
            FileNotFoundError: If no cached protocol exists.
        """
        cache_path = self._protocol_path / PROTOCOL_CACHE_FILE

        if not cache_path.exists():
            raise FileNotFoundError("No cached protocol specification found")

        spec = json.loads(cache_path.read_text())

        # Load cached version
        version_path = self._protocol_path / PROTOCOL_VERSION_FILE
        if version_path.exists():
            self._cached_version = version_path.read_text().strip()

        self._cached_spec = spec

        logger.info("Protocol loaded from cache")
        return spec

    def get_version(self) -> Optional[str]:
        """Get current protocol version hash.

        Returns:
            Version hash or None.
        """
        if self._cached_version:
            return self._cached_version

        version_path = self._protocol_path / PROTOCOL_VERSION_FILE
        if version_path.exists():
            self._cached_version = version_path.read_text().strip()
            return self._cached_version

        return None

    def validate_spec(self, spec: dict[str, Any]) -> bool:
        """Validate protocol specification schema.

        Args:
            spec: Protocol specification to validate.

        Returns:
            True if valid.
        """
        required_fields = ["version", "endpoints", "schemas"]
        for field in required_fields:
            if field not in spec:
                logger.warning("Missing required field in protocol spec", field=field)
                return False

        # Validate endpoints
        endpoints = spec.get("endpoints", {})
        required_endpoints = ["tasks", "proof", "settlement"]
        for endpoint in required_endpoints:
            if endpoint not in endpoints:
                logger.warning("Missing required endpoint", endpoint=endpoint)
                return False

        logger.info("Protocol specification validated", version=spec.get("version"))
        return True

    def get_endpoint(self, name: str) -> Optional[str]:
        """Get API endpoint URL by name.

        Args:
            name: Endpoint name.

        Returns:
            Endpoint URL or None.
        """
        if not self._cached_spec:
            self._load_from_cache()

        if self._cached_spec:
            endpoints = self._cached_spec.get("endpoints", {})
            return endpoints.get(name)

        return None
