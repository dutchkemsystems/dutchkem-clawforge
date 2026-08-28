
from ..economy.reputation import ReputationTracker
from ..models import Task


class SmartBidder:
    def __init__(self, reputation: ReputationTracker):
        self.reputation = reputation

    def calculate_bid(self, task: Task) -> float:
        base_cost = task.value_usdc * 0.8  # 80% of task value as bid
        stake_pct = self.reputation.get_stake_percentage()
        adjusted = base_cost * (1 - stake_pct * 0.5)
        return round(max(adjusted, task.value_usdc * 0.5), 6)

    def value_to_stake_ratio(self, task: Task) -> float:
        stake_pct = self.reputation.get_stake_percentage()
        stake = task.value_usdc * stake_pct
        if stake <= 0:
            return float("inf")
        return task.value_usdc / stake

    def rank_tasks(self, tasks: list[Task]) -> list[Task]:
        return sorted(tasks, key=self.value_to_stake_ratio, reverse=True)
