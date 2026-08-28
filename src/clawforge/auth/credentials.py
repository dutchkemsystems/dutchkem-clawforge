"""Module 1.1: Least Privilege Credential Scopes."""

import json
import time
from datetime import UTC, datetime

import structlog

from clawforge.config import get_settings
from clawforge.crypto.signer import Signer
from clawforge.crypto.vault import Vault
from clawforge.models import SpendLimit

logger = structlog.get_logger(__name__)


class SpendLimitExceeded(Exception):
    """Raised when spend limit is exceeded."""


class ServerSigner:
    """Server signer with scoped credentials and spend limits."""

    def __init__(self, signer: Signer, vault: Vault | None = None) -> None:
        """Initialize server signer."""
        self._signer = signer
        self._vault = vault
        self._settings = get_settings()
        self._credentials_path = self._settings.get_credentials_path()
        self._credentials_path.mkdir(parents=True, exist_ok=True)

        # Load or initialize spend limits
        self._spend_limit = self._load_spend_limit()

        logger.info(
            "Server signer initialized",
            wallet=signer.address,
        )

    def _load_spend_limit(self) -> SpendLimit:
        """Load spend limits from file or create defaults."""
        limit_file = self._credentials_path / "spend_limits.json"

        if limit_file.exists():
            try:
                data = json.loads(limit_file.read_text())
                return SpendLimit(**data)
            except Exception as e:
                logger.warning("Failed to load spend limits", error=str(e))

        # Default limits
        return SpendLimit(
            max_gas_per_tx=float(self._settings.MAX_GAS_FEE_WEI),
            max_usdc_stake_per_day=float(self._settings.MAX_DAILY_STAKE_USDC),
            current_daily_stake=0.0,
            last_reset=time.time(),
        )

    def _save_spend_limit(self) -> None:
        """Save spend limits to file."""
        limit_file = self._credentials_path / "spend_limits.json"
        temp_path = limit_file.with_suffix(".tmp")

        data = self._spend_limit.model_dump(mode="json")
        temp_path.write_text(json.dumps(data, indent=2))
        temp_path.replace(limit_file)

        logger.debug("Spend limits saved")

    def check_gas_limit(self, gas_fee_wei: float) -> bool:
        """Check if gas fee exceeds per-transaction limit."""
        if gas_fee_wei > self._spend_limit.max_gas_per_tx:
            logger.critical(
                "Gas fee exceeds limit",
                gas_fee=gas_fee_wei,
                limit=self._spend_limit.max_gas_per_tx,
            )
            self._route_to_human_approval("gas_limit_exceeded", {
                "gas_fee": gas_fee_wei,
                "limit": self._spend_limit.max_gas_per_tx,
            })
            raise SpendLimitExceeded(
                f"Gas fee {gas_fee_wei} exceeds limit {self._spend_limit.max_gas_per_tx}"
            )
        return True

    def check_daily_stake(self, amount: float) -> bool:
        """Check if stake amount exceeds daily limit."""
        # Check if we need to reset daily counter
        if self._needs_daily_reset():
            self._reset_daily_stake()

        new_total = self._spend_limit.current_daily_stake + amount
        if new_total > self._spend_limit.max_usdc_stake_per_day:
            logger.critical(
                "Daily stake limit exceeded",
                amount=amount,
                current=self._spend_limit.current_daily_stake,
                limit=self._spend_limit.max_usdc_stake_per_day,
            )
            self._route_to_human_approval("daily_stake_exceeded", {
                "amount": amount,
                "current": self._spend_limit.current_daily_stake,
                "limit": self._spend_limit.max_usdc_stake_per_day,
            })
            raise SpendLimitExceeded(
                f"Daily stake {new_total} would exceed limit {self._spend_limit.max_usdc_stake_per_day}"
            )
        return True

    def record_stake(self, amount: float) -> None:
        """Record a stake amount."""
        self._spend_limit.current_daily_stake += amount
        self._save_spend_limit()

        logger.info(
            "Stake recorded",
            amount=amount,
            daily_total=self._spend_limit.current_daily_stake,
        )

    def _needs_daily_reset(self) -> bool:
        """Check if daily stake counter needs reset (UTC-based)."""
        now = datetime.now(UTC).date()
        last_reset = datetime.fromtimestamp(self._spend_limit.last_reset, tz=UTC).date()
        return now > last_reset

    def _reset_daily_stake(self) -> None:
        """Reset daily stake counter."""
        self._spend_limit.current_daily_stake = 0.0
        self._spend_limit.last_reset = time.time()
        self._save_spend_limit()

        logger.info("Daily stake counter reset")

    def _route_to_human_approval(self, action: str, details: dict) -> None:
        """Route transaction to human approval queue."""
        approval_file = self._credentials_path / "approval_queue.json"

        # Load existing queue
        queue = []
        if approval_file.exists():
            try:
                queue = json.loads(approval_file.read_text())
            except Exception:
                queue = []

        # Add new request
        request = {
            "action": action,
            "details": details,
            "timestamp": time.time(),
            "status": "pending",
        }
        queue.append(request)

        # Save queue atomically
        temp_path = approval_file.with_suffix(".tmp")
        temp_path.write_text(json.dumps(queue, indent=2))
        temp_path.replace(approval_file)

        logger.critical(
            "Transaction routed to human approval",
            action=action,
            queue_length=len(queue),
        )

    def sign_message(self, message: str) -> str:
        """Sign a message using the server signer."""
        return self._signer.sign_message(message)

    @property
    def address(self) -> str:
        """Get signer address."""
        return self._signer.address

    @property
    def spend_limit(self) -> SpendLimit:
        """Get current spend limits."""
        return self._spend_limit
