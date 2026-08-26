import time
from pathlib import Path

from ..memory.warm import WarmMemory


class SupplyDemandScanner:
    def __init__(self, warm_memory: WarmMemory, data_path: Path):
        self.warm = warm_memory
        self.data_path = data_path
        self._last_scan = 0.0
        self._scan_interval = 300  # 5 minutes

    def should_generate_study_tasks(self, available_tasks: int) -> bool:
        self._last_scan = time.time()
        return available_tasks < 5

    def generate_study_tasks(self, count: int = 3) -> list[dict]:
        entries = self.warm.get_frequent_entries(min_accesses=2, within_minutes=60)
        tasks = []
        for i, entry in enumerate(entries[:count]):
            tasks.append({
                "task_id": f"study-{int(time.time())}-{i}",
                "type": "study",
                "description": f"Practice: {entry.key}",
                "value_usdc": 0,
                "generated_at": time.time(),
            })
        return tasks
