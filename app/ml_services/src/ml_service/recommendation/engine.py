from pathlib import Path
from typing import Any

import yaml

from ml_service.api.schemas import (
    ActionRecommendation,
    ActionType,
    BusinessCategory,
    ResolutionStatus,
    UrgencyLevel,
)


class RecommendationEngine:
    """Evaluates business rules in config/action_rules.yaml to recommend actions."""

    def __init__(self, rules_path: Path | str) -> None:
        self.rules_path = Path(rules_path)
        self.rules: list[dict[str, Any]] = []
        if self.rules_path.exists():
            with self.rules_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.rules = data.get("rules", [])
                # Sort rules by ascending priority number (lower = higher precedence)
                self.rules.sort(key=lambda r: int(r.get("priority", 999)))

    def recommend(
        self,
        category: BusinessCategory | str | None,
        urgency: UrgencyLevel | str | None = None,
        resolution: ResolutionStatus | str | None = None,
        security_risk: str | None = None,
    ) -> ActionRecommendation:
        cat_str = str(category.value if isinstance(category, BusinessCategory) else category or "")
        urg_str = str(urgency.value if isinstance(urgency, UrgencyLevel) else urgency or "")
        res_str = str(
            resolution.value if isinstance(resolution, ResolutionStatus) else resolution or ""
        )
        sec_str = str(security_risk or "").upper()

        for rule in self.rules:
            cond = rule.get("conditions", {})
            # Match security risk
            if "security_risk" in cond and sec_str not in cond["security_risk"]:
                continue
            # Match category
            if "category" in cond and cat_str not in cond["category"]:
                continue
            # Match urgency
            if "urgency" in cond and urg_str not in cond["urgency"]:
                continue
            # Match resolution
            if "resolution" in cond and res_str not in cond["resolution"]:
                continue

            # Matched rule!
            primary = ActionType(rule["primary_action"])
            secondaries = [ActionType(a) for a in rule.get("secondary_actions", [])]
            return ActionRecommendation(
                primary_action=primary,
                secondary_actions=secondaries,
                rationale=rule.get("rationale", "Rule matched based on ticket attributes."),
                matched_rule_id=rule.get("id", "UNKNOWN_RULE"),
            )

        # Fallback default
        return ActionRecommendation(
            primary_action=ActionType.STANDARD_SUPPORT_RESPONSE,
            secondary_actions=[ActionType.REQUEST_MORE_INFORMATION],
            rationale="Default fallback action applied.",
            matched_rule_id="RULE_DEFAULT_FALLBACK",
        )
