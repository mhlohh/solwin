from pathlib import Path
from typing import Any

import joblib
import numpy as np

from ml_service.api.schemas import BusinessCategory, ClassificationResult
from ml_service.preprocessing.cleaner import build_complaint_text


class ComplaintClassifier:
    """Production complaint classifier with calibrated probabilities and abstention logic."""

    def __init__(
        self,
        model_path: Path | str,
        model_name: str = "complaint-classifier-baseline",
        model_version: str = "1.0.0",
        confidence_threshold: float = 0.60,
        fine_grained_model_path: Path | str | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.model_name = model_name
        self.model_version = model_version
        self.confidence_threshold = confidence_threshold
        self.pipeline: Any = None
        self.fine_grained_pipeline: Any = None

        if self.model_path.exists():
            self.pipeline = joblib.load(self.model_path)

        if fine_grained_model_path and Path(fine_grained_model_path).exists():
            self.fine_grained_pipeline = joblib.load(fine_grained_model_path)

    @property
    def is_loaded(self) -> bool:
        return self.pipeline is not None

    def classify(
        self,
        message: str | None,
        subject: str | None = None,
        threshold: float | None = None,
    ) -> ClassificationResult:
        """Classify complaint into 11 business categories with calibrated probabilities."""
        if not self.is_loaded:
            raise RuntimeError("Classifier model artifact is not loaded.")

        effective_threshold = threshold if threshold is not None else self.confidence_threshold
        text = build_complaint_text(message, subject)

        if not text:
            # Fallback for empty text
            return ClassificationResult(
                category=BusinessCategory.OTHER,
                confidence=0.0,
                probabilities={cat.value: 0.0 for cat in BusinessCategory},
                needs_review=True,
                model_name=self.model_name,
                model_version=self.model_version,
            )

        # Vectorizer and calibrated classifier pipeline
        probabilities = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_

        prob_dict: dict[str, float] = {
            cls_name: round(float(prob), 4)
            for cls_name, prob in zip(classes, probabilities, strict=False)
        }

        # Find best class
        best_idx = int(np.argmax(probabilities))
        best_class = str(classes[best_idx])
        best_confidence = round(float(probabilities[best_idx]), 4)

        # Check confidence threshold for abstention
        needs_review = best_confidence < effective_threshold

        category_enum = BusinessCategory(best_class)

        fine_grained: str | None = None
        if self.fine_grained_pipeline:
            fg_pred = self.fine_grained_pipeline.predict([text])[0]
            fine_grained = str(fg_pred)

        return ClassificationResult(
            category=category_enum,
            confidence=best_confidence,
            probabilities=prob_dict,
            needs_review=needs_review,
            model_name=self.model_name,
            model_version=self.model_version,
            fine_grained_intent=fine_grained,
        )
