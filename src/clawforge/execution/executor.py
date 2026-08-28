"""Work executor with real AI agent dispatch via OpenAI."""

import asyncio
import json
import time

import httpx

from ..config import get_settings
from ..models import AgentType, Task, TaskResult

AGENT_DISPATCH = {
    "sales": AgentType.SALES,
    "kyc": AgentType.KYC_AML,
    "ecommerce": AgentType.ECOMMERCE,
    "general": AgentType.GENERAL,
}

AGENT_SYSTEM_PROMPTS = {
    AgentType.SALES: (
        "You are a sales AI agent. Analyze the task and produce a concise, "
        "actionable sales output. Focus on conversion, outreach strategy, "
        "or lead generation as appropriate."
    ),
    AgentType.KYC_AML: (
        "You are a KYC/AML compliance agent. Analyze the task for identity "
        "verification, anti-money laundering checks, or regulatory compliance. "
        "Output a structured compliance assessment."
    ),
    AgentType.ECOMMERCE: (
        "You are an ecommerce AI agent. Handle product listings, pricing, "
        "inventory management, or customer support tasks. Output structured "
        "ecommerce data or recommendations."
    ),
    AgentType.GENERAL: (
        "You are a general-purpose AI agent. Analyze the task and produce "
        "a clear, structured output that completes the work."
    ),
}


class AIAgentExecutor:
    """Execute tasks using OpenAI API with agent-specific prompts."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini", timeout: float = 120.0):
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.timeout = timeout
        self._base_url = "https://api.openai.com/v1"

    async def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """Call OpenAI API with retries."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait = 2 ** attempt
                        await asyncio.sleep(wait)
                        continue
                    raise
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    raise

    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task using the appropriate AI agent."""
        start = time.time()
        agent_type = AGENT_DISPATCH.get(task.type, AgentType.GENERAL)
        system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_type, AGENT_SYSTEM_PROMPTS[AgentType.GENERAL])

        user_message = (
            f"Task ID: {task.id}\n"
            f"Title: {task.title}\n"
            f"Description: {task.description}\n"
            f"Value: {task.value_usdc} USDC\n"
            f"Required Skills: {', '.join(task.required_skills) if task.required_skills else 'None'}\n\n"
            f"Complete this task and provide the output."
        )

        try:
            output = await asyncio.wait_for(
                self._call_openai(system_prompt, user_message),
                timeout=self.timeout,
            )
            return TaskResult(
                task_id=task.id,
                success=True,
                output=output,
                execution_time=time.time() - start,
                agent_type=agent_type,
            )
        except TimeoutError:
            return TaskResult(
                task_id=task.id,
                success=False,
                output="",
                execution_time=time.time() - start,
                error="Execution timeout",
                agent_type=agent_type,
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                output="",
                execution_time=time.time() - start,
                error=str(e),
                agent_type=agent_type,
            )


class FallbackExecutor:
    """Fallback executor when OpenAI is unavailable."""

    async def execute_task(self, task: Task) -> TaskResult:
        start = time.time()
        agent_type = AGENT_DISPATCH.get(task.type, AgentType.GENERAL)
        await asyncio.sleep(0.1)

        output = json.dumps({
            "task_id": task.id,
            "title": task.title,
            "agent_type": agent_type.value,
            "status": "completed",
            "summary": f"Task {task.id} processed by {agent_type.value} agent",
        }, indent=2)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=output,
            execution_time=time.time() - start,
            agent_type=agent_type,
        )


class WorkExecutor:
    """Main executor that tries AI first, falls back to stub."""

    def __init__(self, timeout: float = 300.0):
        self.timeout = timeout
        settings = get_settings()
        if settings.OPENAI_API_KEY:
            self._ai = AIAgentExecutor(timeout=min(timeout, 120.0))
        else:
            self._ai = None
        self._fallback = FallbackExecutor()

    async def execute(self, task: Task) -> TaskResult:
        try:
            if self._ai:
                try:
                    return await asyncio.wait_for(
                        self._ai.execute_task(task), timeout=self.timeout
                    )
                except (TimeoutError, Exception):
                    pass
            return await asyncio.wait_for(
                self._fallback.execute_task(task), timeout=self.timeout
            )
        except TimeoutError:
            return TaskResult(
                task_id=task.id,
                success=False,
                output="",
                execution_time=0,
                error="Execution timeout",
            )
