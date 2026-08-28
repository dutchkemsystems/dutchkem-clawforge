import asyncio
import time
from collections.abc import Awaitable, Callable

from ..models import Subtask


class A2AQueue:
    def __init__(self):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._handlers: dict[str, Callable[[Subtask], Awaitable[str]]] = {}

    def register_handler(self, task_type: str, handler: Callable[[Subtask], Awaitable[str]]):
        self._handlers[task_type] = handler

    async def post_bounty(self, description: str, task_type: str, value: float) -> Subtask:
        subtask = Subtask(
            id=f"a2a-{int(time.time())}",
            description=description,
            type=task_type,
            value_usdc=value,
            created_at=time.time(),
        )
        await self._queue.put(subtask)
        return subtask

    async def process_next(self) -> tuple[Subtask, str] | None:
        try:
            subtask = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

        handler = self._handlers.get(subtask.type)
        if not handler:
            return subtask, "No handler registered"

        result = await handler(subtask)
        return subtask, result
