from dataclasses import asdict, dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ModelMetadata:
    model_name: str
    version: str
    training_dataset: str
    training_date: str
    framework: str
    metrics: dict[str, float]
    parameters: dict[str, str]
    status: str


class ModelRegistry:
    """Central model metadata source; inference never hard-codes model paths."""

    def __init__(self, registry_path: Path) -> None:
        self._registry_path = registry_path
        self._models = self._load()

    def _load(self) -> dict[str, ModelMetadata]:
        if not self._registry_path.exists():
            return {}
        raw = yaml.safe_load(self._registry_path.read_text(encoding="utf-8")) or {}
        records = raw.get("models", [])
        return {item["model_name"]: ModelMetadata(
            model_name=item["model_name"], version=item["version"],
            training_dataset=item["training_dataset"], training_date=item["training_date"],
            framework=item["framework"], metrics=item.get("metrics", {}),
            parameters=item.get("parameters", {}), status=item["status"],
        ) for item in records}

    def list(self) -> list[dict[str, object]]:
        return [asdict(model) for model in self._models.values()]

    def is_ready(self) -> bool:
        return any(model.status == "production" for model in self._models.values())
