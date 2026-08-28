import json
import time
from pathlib import Path

from .ledger import USDCLedger
from ..models import StakeRecord
from ..utils.filelock import file_lock, locked_file


class AutoStaker:
    def __init__(self, ledger: USDCLedger, stake_percentage: float = 0.10):
        self.ledger = ledger
        self.stake_pct = stake_percentage
        self._stakes: dict[str, StakeRecord] = {}
        self._stake_file = ledger.path / "stakes.json"
        self._load()

    def _load(self):
        if self._stake_file.exists():
            with locked_file(self._stake_file, "r") as f:
                data = json.load(f)
                for tid, rec in data.items():
                    self._stakes[tid] = StakeRecord(**rec)

    def _save(self):
        with file_lock(self._stake_file):
            temp = self._stake_file.with_suffix(".tmp")
            temp.write_text(json.dumps({k: v.model_dump() for k, v in self._stakes.items()}, indent=2))
            temp.replace(self._stake_file)

    def stake_for_task(self, task_id: str, task_value: float) -> float:
        stake_amount = round(task_value * self.stake_pct, 6)
        if stake_amount <= 0:
            return 0.0
        self.ledger.append(task_id, -stake_amount, "stake", f"Auto-stake {self.stake_pct * 100:.0f}%")
        self._stakes[task_id] = StakeRecord(
            task_id=task_id,
            amount=stake_amount,
            staked_at=time.time(),
            status="staked",
        )
        self._save()
        return stake_amount

    def reclaim_stake(self, task_id: str) -> float:
        if task_id not in self._stakes:
            return 0.0
        stake = self._stakes[task_id]
        if stake.status != "staked":
            return 0.0
        stake.status = "reclaimed"
        stake.reclaimed_at = time.time()
        self.ledger.append(task_id, stake.amount, "stake_reclaim", "Stake reclaimed after rating")
        self._save()
        return stake.amount

    def execute_rate_and_claim(self, task_id: str) -> float:
        """Execute agentRateAndClaimStake when nextAction=rate_and_claim_stake."""
        return self.reclaim_stake(task_id)

    def get_staked_amount(self) -> float:
        return sum(s.amount for s in self._stakes.values() if s.status == "staked")
