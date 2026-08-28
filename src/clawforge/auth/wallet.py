"""Module 1: Wallet management and authentication."""


import structlog

from clawforge.config import get_settings
from clawforge.crypto.signer import Signer

logger = structlog.get_logger(__name__)


class WalletManager:
    """Manages wallet loading and authentication."""

    def __init__(self) -> None:
        """Initialize wallet manager."""
        self._settings = get_settings()
        self._signer: Signer | None = None

    def load_wallet(self) -> Signer:
        """Load wallet from environment variables.

        Returns:
            Configured signer instance.

        Raises:
            ValueError: If wallet configuration is invalid.
        """
        if self._signer is not None:
            return self._signer

        wallet_address = self._settings.CLAW_EARN_WALLET
        private_key = self._settings.CLAW_EARN_PRIVATE_KEY

        if not wallet_address or not private_key:
            raise ValueError("CLAW_EARN_WALLET and CLAW_EARN_PRIVATE_KEY are required")

        self._signer = Signer(private_key, wallet_address)

        logger.info(
            "Wallet loaded successfully",
            wallet=wallet_address,
        )

        return self._signer

    def get_signer(self) -> Signer:
        """Get the loaded signer instance.

        Returns:
            Signer instance.

        Raises:
            RuntimeError: If wallet not loaded.
        """
        if self._signer is None:
            raise RuntimeError("Wallet not loaded. Call load_wallet() first.")
        return self._signer

    def validate_wallet(self) -> bool:
        """Validate wallet configuration.

        Returns:
            True if wallet is valid.
        """
        try:
            signer = self.load_wallet()

            # Sign a test message to verify functionality
            test_message = "CLAW_FORGE_VALIDATION_TEST"
            signature = signer.sign_message(test_message)

            # Verify the signature
            is_valid = signer.verify_signature(test_message, signature)

            if is_valid:
                logger.info("Wallet validation successful")
            else:
                logger.error("Wallet validation failed - signature mismatch")

            return is_valid
        except Exception as e:
            logger.error("Wallet validation failed", error=str(e))
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if wallet is loaded."""
        return self._signer is not None

    @property
    def address(self) -> str | None:
        """Get wallet address if loaded."""
        if self._signer:
            return self._signer.address
        return None


# Global wallet manager instance
wallet_manager = WalletManager()
