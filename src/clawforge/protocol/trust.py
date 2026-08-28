"""Module 0.1: HTTPS Trust Boundary - Enforce secure external connections."""

import time
from urllib.parse import urlparse

import httpx
import structlog

logger = structlog.get_logger(__name__)

ALLOWED_HOST = "aiagentstore.ai"
ALLOWED_PREFIX = f"https://{ALLOWED_HOST}"


class TrustBoundaryError(Exception):
    """Raised when trust boundary is violated."""


class TrustBoundary:
    """Enforces HTTPS-only connections to trusted Claw hosts."""

    def __init__(self) -> None:
        """Initialize trust boundary."""
        self._approval_queue: list[dict] = []

    def validate_url(self, url: str) -> bool:
        """Validate URL against trust boundary rules.

        Rules:
        1. Must be HTTPS
        2. Must be from aiagentstore.ai

        Args:
            url: URL to validate.

        Returns:
            True if URL is trusted.

        Raises:
            TrustBoundaryError: If URL violates trust boundary.
        """
        parsed = urlparse(url)

        # Must be HTTPS
        if parsed.scheme != "https":
            logger.critical(
                "Non-HTTPS URL rejected",
                url=url,
                scheme=parsed.scheme,
            )
            raise TrustBoundaryError(f"Non-HTTPS URL rejected: {url}")

        # Must be from allowed host (exact match or subdomain of allowed host)
        hostname = parsed.hostname or ""
        if hostname != ALLOWED_HOST and not hostname.endswith(f".{ALLOWED_HOST}"):
            logger.critical(
                "Untrusted host rejected",
                url=url,
                host=hostname,
            )
            self._request_human_approval(url, "untrusted_host")
            raise TrustBoundaryError(f"Untrusted host rejected: {hostname}")

        logger.debug("URL validated", url=url)
        return True

    async def check_redirects(self, url: str) -> str:
        """Follow redirects and validate final host.

        Args:
            url: Initial URL to check.

        Returns:
            Final URL after redirects.

        Raises:
            TrustBoundaryError: If redirect leads to untrusted host.
        """
        self.validate_url(url)

        async with httpx.AsyncClient(
            follow_redirects=True,
            verify=True,
            timeout=30.0,
        ) as client:
            # Use HEAD request to check redirects without downloading content
            response = await client.head(url)

            final_url = str(response.url)
            final_parsed = urlparse(final_url)

            # Validate final host (exact match or subdomain)
            final_host = final_parsed.hostname or ""
            if final_host != ALLOWED_HOST and not final_host.endswith(f".{ALLOWED_HOST}"):
                logger.critical(
                    "Redirect to untrusted host blocked",
                    original=url,
                    final=final_url,
                )
                self._request_human_approval(final_url, "redirect_violation")
                raise TrustBoundaryError(
                    f"Redirect to untrusted host: {final_url}"
                )

            logger.info(
                "Redirect chain validated",
                original=url,
                final=final_url,
                redirects=len(response.history),
            )

            return final_url

    def _request_human_approval(self, url: str, reason: str) -> None:
        """Request human approval for trust boundary violation.

        Args:
            url: Violating URL.
            reason: Reason for violation.
        """
        approval_request = {
            "url": url,
            "reason": reason,
            "timestamp": time.time(),
            "status": "pending",
        }
        self._approval_queue.append(approval_request)

        logger.critical(
            "TRUST BOUNDARY VIOLATION - Human approval required",
            url=url,
            reason=reason,
            queue_length=len(self._approval_queue),
        )

    def get_pending_approvals(self) -> list[dict]:
        """Get list of pending approval requests.

        Returns:
            List of pending approval requests.
        """
        return [a for a in self._approval_queue if a["status"] == "pending"]

    def approve_request(self, index: int) -> bool:
        """Approve a pending request.

        Args:
            index: Index of request to approve.

        Returns:
            True if approved.
        """
        if 0 <= index < len(self._approval_queue):
            if self._approval_queue[index]["status"] == "pending":
                self._approval_queue[index]["status"] = "approved"
                logger.info("Trust boundary violation approved", index=index)
                return True
        return False

    def reject_request(self, index: int) -> bool:
        """Reject a pending request.

        Args:
            index: Index of request to reject.

        Returns:
            True if rejected.
        """
        if 0 <= index < len(self._approval_queue):
            if self._approval_queue[index]["status"] == "pending":
                self._approval_queue[index]["status"] = "rejected"
                logger.info("Trust boundary violation rejected", index=index)
                return True
        return False


# Global trust boundary instance
trust_boundary = TrustBoundary()
