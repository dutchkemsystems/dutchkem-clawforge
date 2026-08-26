import json
import hashlib
import time
from pathlib import Path

from ..models import AuditEntry


class HashChainLogger:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self._log_file = self.path / "audit.jsonl"
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self._log_file.exists():
            return "genesis"
        last_line = ""
        with open(self._log_file, "r") as f:
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

    def log(self, action: str, task_id: str = "", details: dict = None) -> AuditEntry:
        entry = AuditEntry(
            timestamp=time.time(),
            action=action,
            task_id=task_id,
            details=details or {},
            prev_hash=self._last_hash,
        )
        entry.hash = self._compute_hash(self._last_hash, entry.model_dump(exclude={"hash"}))
        self._last_hash = entry.hash

        # Atomic write: read existing, append new, write all to temp, then replace
        existing = ""
        if self._log_file.exists():
            existing = self._log_file.read_text()

        temp = self._log_file.with_suffix(".tmp")
        with open(temp, "w") as f:
            f.write(existing)
            f.write(entry.model_dump_json() + "\n")
        temp.replace(self._log_file)

        return entry

    def verify_chain(self) -> bool:
        """Verify hash chain integrity by recomputing hashes."""
        prev_hash = "genesis"
        if not self._log_file.exists():
            return True
        with open(self._log_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = AuditEntry.model_validate_json(line.strip())
                # Check prev_hash linkage
                if entry.prev_hash != prev_hash:
                    return False
                # Recompute hash and verify it matches stored hash
                expected_hash = self._compute_hash(
                    prev_hash, entry.model_dump(exclude={"hash"})
                )
                if entry.hash != expected_hash:
                    return False
                prev_hash = entry.hash
        return True

    def get_entries(self, task_id: str = "", since: float = 0) -> list[AuditEntry]:
        entries = []
        if not self._log_file.exists():
            return entries
        with open(self._log_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = AuditEntry.model_validate_json(line.strip())
                if task_id and entry.task_id != task_id:
                    continue
                if since and entry.timestamp < since:
                    continue
                entries.append(entry)
        return entries
