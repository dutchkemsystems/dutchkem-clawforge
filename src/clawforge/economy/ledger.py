import hashlib
import json
import time
from pathlib import Path

from ..models import LedgerEntry
from ..utils.filelock import file_lock, locked_file


class USDCLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self._ledger_file = self.path / "ledger.jsonl"
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Load the hash of the last entry for chaining."""
        if not self._ledger_file.exists():
            return "genesis"
        last_line = ""
        with locked_file(self._ledger_file, "r") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
        if last_line:
            entry = json.loads(last_line)
            return entry.get("hash", "genesis")
        return "genesis"

    def _compute_hash(self, prev_hash: str, data: dict) -> str:
        content = f"{prev_hash}:{json.dumps(data, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def append(self, task_id: str, amount: float, tx_type: str, description: str = "") -> LedgerEntry:
        """Append a new ledger entry with hash chaining."""
        with file_lock(self._ledger_file):
            entry = LedgerEntry(
                timestamp=time.time(),
                task_id=task_id,
                amount=amount,
                type=tx_type,
                description=description,
                prev_hash=self._last_hash,
            )
            entry.hash = self._compute_hash(self._last_hash, {k: v for k, v in entry.model_dump().items() if k != "hash"})
            self._last_hash = entry.hash

            # Atomic write: read existing, write all to temp, then rename
            existing = ""
            if self._ledger_file.exists():
                existing = self._ledger_file.read_text()
            temp_file = self._ledger_file.with_suffix(".tmp")
            temp_file.write_text(existing + entry.model_dump_json() + "\n")
            temp_file.replace(self._ledger_file)

            return entry

    def get_entries(self, task_id: str | None = None, since: float | None = None) -> list[LedgerEntry]:
        entries = []
        if not self._ledger_file.exists():
            return entries
        with locked_file(self._ledger_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = LedgerEntry.model_validate_json(line.strip())
                if task_id and entry.task_id != task_id:
                    continue
                if since and entry.timestamp < since:
                    continue
                entries.append(entry)
        return entries

    def verify_chain(self) -> bool:
        """Verify hash chain integrity."""
        prev_hash = "genesis"
        if not self._ledger_file.exists():
            return True
        with locked_file(self._ledger_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = LedgerEntry.model_validate_json(line.strip())
                if entry.prev_hash != prev_hash:
                    return False
                expected = self._compute_hash(prev_hash, {k: v for k, v in entry.model_dump().items() if k != "hash"})
                if entry.hash != expected:
                    return False
                prev_hash = entry.hash
        return True

    def get_balance(self) -> float:
        entries = self.get_entries()
        return sum(e.amount for e in entries)
