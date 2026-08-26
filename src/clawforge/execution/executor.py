import time
import asyncio

from ..models import Task, TaskResult, AgentType


AGENT_DISPATCH = {
    "sales": AgentType.SALES,
    "kyc": AgentType.KYC_AML,
    "ecommerce": AgentType.ECOMMERCE,
    "general": AgentType.GENERAL,
}


class WorkExecutor:
    def __init__(self, timeout: float = 300.0):
        self.timeout = timeout

    async def execute(self, task: Task) -> TaskResult:
        start = time.time()
        agent_type = AGENT_DISPATCH.get(task.type, AgentType.GENERAL)

        try:
            output = await asyncio.wait_for(
                self._dispatch_work(agent_type, task),
                timeout=self.timeout,
            )
            return TaskResult(
                task_id=task.id,
                success=True,
                output=output,
                execution_time=time.time() - start,
                agent_type=agent_type,
            )
        except asyncio.TimeoutError:
            return TaskResult(
                task_id=task.id,
                success=False,
                output="",
                execution_time=time.time() - start,
                error="Execution timeout",
                agent_type=agent_type,
            )

    async def _dispatch_work(self, agent_type: AgentType, task: Task) -> str:
        # Placeholder for actual agent execution
        await asyncio.sleep(0.1)
        return f"Completed task {task.id} via {agent_type.value}"
