from pathlib import Path

from ..models import ReputationProfile


class ReputationTracker:
    TIERS = {
        "bronze": {"min_ratings": 0, "min_avg": 0.0, "stake_pct": 0.30},
        "silver": {"min_ratings": 6, "min_avg": 3.0, "stake_pct": 0.25},
        "gold": {"min_ratings": 6, "min_avg": 4.0, "stake_pct": 0.20},
        "platinum": {"min_ratings": 10, "min_avg": 4.2, "stake_pct": 0.15},
        "diamond": {"min_ratings": 12, "min_avg": 4.5, "stake_pct": 0.10},
    }

    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self._file = path / "reputation.json"
        self.profile = self._load()

    def _load(self) -> ReputationProfile:
        if self._file.exists():
            return ReputationProfile.model_validate_json(self._file.read_text())
        return ReputationProfile()

    def _save(self):
        temp = self._file.with_suffix(".tmp")
        temp.write_text(self.profile.model_dump_json(indent=2))
        temp.replace(self._file)

    def record_rating(self, rating: float) -> str:
        self.profile.total_ratings += 1
        self.profile.rating_sum += rating
        self.profile.average_rating = round(self.profile.rating_sum / self.profile.total_ratings, 2)
        self.profile.tier = self._compute_tier()
        self.profile.stake_percentage = self.TIERS[self.profile.tier]["stake_pct"]
        self._save()
        return self.profile.tier

    def _compute_tier(self) -> str:
        for tier_name in ["diamond", "platinum", "gold", "silver", "bronze"]:
            tier = self.TIERS[tier_name]
            if self.profile.total_ratings >= tier["min_ratings"] and self.profile.average_rating >= tier["min_avg"]:
                return tier_name
        return "bronze"

    def get_stake_percentage(self) -> float:
        return self.profile.stake_percentage
