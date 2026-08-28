
import httpx

from ..models import Task
from ..protocol.trust import TrustBoundary


class TaskDiscovery:
    def __init__(self, base_url: str, trust: TrustBoundary):
        self.base_url = base_url.rstrip("/")
        self.trust = trust
        self._client = httpx.AsyncClient(timeout=30.0)

    async def fetch_tasks(self, status: str = "FUNDED") -> list[Task]:
        url = f"{self.base_url}/claw/tasks"
        self.trust.validate_url(url)
        resp = await self._client.get(url, params={"status": status})
        resp.raise_for_status()
        data = resp.json()
        return [Task(**t) for t in data.get("tasks", [])]

    async def get_task(self, task_id: str) -> Task | None:
        url = f"{self.base_url}/claw/tasks/{task_id}"
        self.trust.validate_url(url)
        resp = await self._client.get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return Task(**resp.json())

    async def should_auto_start(self, task: Task, current_balance: float, reputation_tier: str) -> bool:
        if task.value_usdc > 100.0:
            return False
        if reputation_tier in ("gold", "diamond"):
            return True
        return task.value_usdc <= 50.0
