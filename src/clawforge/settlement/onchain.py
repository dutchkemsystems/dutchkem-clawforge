"""On-chain settlement module for Base chain USDC transactions."""

import json
import time
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class OnChainSettlement(BaseModel):
    """Settlement record for on-chain USDC transfer."""

    task_id: str
    from_address: str
    to_address: str
    amount_usdc: float
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    status: str = "pending"
    created_at: float = Field(default_factory=time.time)
    settled_at: Optional[float] = None
    gas_used: Optional[float] = None


class SettlementQueue:
    """File-based settlement queue with retry logic."""

    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self._queue_file = self.path / "settlement_queue.jsonl"

    def enqueue(self, settlement: OnChainSettlement) -> None:
        """Add a settlement to the queue."""
        existing = ""
        if self._queue_file.exists():
            existing = self._queue_file.read_text()
        entry = settlement.model_dump_json()
        temp = self._queue_file.with_suffix(".tmp")
        temp.write_text(existing + entry + "\n")
        temp.replace(self._queue_file)

    def get_pending(self) -> list[OnChainSettlement]:
        """Get all pending settlements."""
        if not self._queue_file.exists():
            return []
        settlements = []
        for line in self._queue_file.read_text().strip().split("\n"):
            if line.strip():
                s = OnChainSettlement.model_validate_json(line.strip())
                if s.status == "pending":
                    settlements.append(s)
        return settlements

    def mark_completed(self, task_id: str, tx_hash: str, block_number: int, gas_used: float) -> bool:
        """Mark a settlement as completed."""
        if not self._queue_file.exists():
            return False
        lines = self._queue_file.read_text().strip().split("\n")
        updated = False
        new_lines = []
        for line in lines:
            if not line.strip():
                continue
            s = OnChainSettlement.model_validate_json(line.strip())
            if s.task_id == task_id and s.status == "pending":
                s.status = "completed"
                s.tx_hash = tx_hash
                s.block_number = block_number
                s.gas_used = gas_used
                s.settled_at = time.time()
                updated = True
            new_lines.append(s.model_dump_json())
        if updated:
            temp = self._queue_file.with_suffix(".tmp")
            temp.write_text("\n".join(new_lines) + "\n")
            temp.replace(self._queue_file)
        return updated

    def mark_failed(self, task_id: str, error: str) -> bool:
        """Mark a settlement as failed."""
        if not self._queue_file.exists():
            return False
        lines = self._queue_file.read_text().strip().split("\n")
        updated = False
        new_lines = []
        for line in lines:
            if not line.strip():
                continue
            s = OnChainSettlement.model_validate_json(line.strip())
            if s.task_id == task_id and s.status == "pending":
                s.status = "failed"
                updated = True
            new_lines.append(s.model_dump_json())
        if updated:
            temp = self._queue_file.with_suffix(".tmp")
            temp.write_text("\n".join(new_lines) + "\n")
            temp.replace(self._queue_file)
        return updated


class OnChainSettler:
    """Handles on-chain USDC settlement on Base chain.

    Web3 imports are lazy to avoid slow startup on Python 3.14.
    """

    BASE_USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    BASE_CHAIN_ID = 8453
    USDC_DECIMALS = 6

    def __init__(self, private_key: str, rpc_url: str = "https://mainnet.base.org"):
        self.private_key = private_key
        self.rpc_url = rpc_url
        self._w3: Any = None

    def _get_web3(self) -> Any:
        """Lazy-load Web3."""
        if self._w3 is None:
            from web3 import Web3
            self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        return self._w3

    def get_wallet_address(self) -> str:
        """Derive wallet address from private key."""
        from eth_account import Account
        account = Account.from_key(self.private_key)
        return account.address

    def get_usdc_balance(self, address: str) -> float:
        """Get USDC balance for an address."""
        try:
            from web3 import Web3
            w3 = self._get_web3()
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                },
            ]
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(self.BASE_USDC_ADDRESS),
                abi=erc20_abi,
            )
            raw_balance = contract.functions.balanceOf(
                Web3.to_checksum_address(address)
            ).call()
            return raw_balance / (10 ** self.USDC_DECIMALS)
        except Exception:
            return 0.0

    def create_settlement(self, task_id: str, to_address: str, amount_usdc: float) -> OnChainSettlement:
        """Create a settlement record (does not broadcast yet)."""
        from_address = self.get_wallet_address()
        return OnChainSettlement(
            task_id=task_id,
            from_address=from_address,
            to_address=to_address,
            amount_usdc=amount_usdc,
        )


def create_settler() -> OnChainSettler:
    """Create an OnChainSettler from current settings."""
    settings = get_settings()
    return OnChainSettler(
        private_key=settings.CLAW_EARN_PRIVATE_KEY,
        rpc_url="https://mainnet.base.org",
    )
