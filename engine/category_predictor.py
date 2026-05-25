"""Category predictor with probabilistic classifier + centroid fallback."""
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class CategoryPredictor:
    """
    Predicts the most likely career categories for a resume.
    Primary mode: probabilistic classifier (Logistic Regression).
    Fallback mode: TF-IDF + nearest centroid.
    """

    def __init__(self):
        self.vectorizer = None
        self.classifier = None
        self.category_centroids = None
        self.category_names = None
        self.mode = None
        self.is_ready = False

    def load(self, model_dir: Path):
        """Load model artifacts from disk."""
        vec_path = model_dir / "category_vectorizer.joblib"
        clf_path = model_dir / "category_classifier.joblib"
        centroids_path = model_dir / "category_centroids.joblib"

        if not vec_path.exists():
            logger.warning("Category vectorizer not found. Category predictor disabled.")
            self.is_ready = False
            return False

        self.vectorizer = joblib.load(vec_path)

        # Try classifier-first mode
        if clf_path.exists():
            try:
                clf_obj = joblib.load(clf_path)
                if isinstance(clf_obj, dict):
                    self.classifier = clf_obj.get("classifier")
                    names = clf_obj.get("names")
                    if names:
                        self.category_names = list(names)
                else:
                    self.classifier = clf_obj

                if self.classifier is not None and hasattr(self.classifier, "classes_"):
                    self.category_names = list(self.classifier.classes_)
                    self.mode = "classifier"
            except Exception as e:
                logger.warning(f"Failed to load classifier artifact, will try centroid fallback: {e}")

        # Centroid fallback
        if centroids_path.exists():
            try:
                data = joblib.load(centroids_path)
                self.category_centroids = data["centroids"]
                if not self.category_names:
                    self.category_names = list(data["names"])
                if self.mode is None:
                    self.mode = "centroid"
            except Exception as e:
                logger.warning(f"Failed to load centroid artifact: {e}")

        self.is_ready = self.mode in {"classifier", "centroid"} and bool(self.category_names)
        if self.is_ready:
            logger.info(f"Category predictor loaded in {self.mode} mode: {len(self.category_names)} categories")
        else:
            logger.warning("Category prediction artifacts unavailable. Will use fallback prediction.")
        return self.is_ready

    def predict(self, cleaned_text: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Predict top-N categories in backward-compatible tuple format.
        Returns list of (category, confidence).
        """
        details = self.predict_with_details(cleaned_text, top_n=top_n)
        return [(item["category"], item["confidence"]) for item in details]

    def predict_with_details(self, cleaned_text: str, top_n: int = 3) -> List[Dict]:
        """
        Predict top-N categories with rich metadata.
        Returns list of dicts: {category, confidence, raw_score, method}.
        """
        if not self.is_ready:
            return [{
                "category": "General",
                "confidence": 0.5,
                "raw_score": 0.5,
                "method": "fallback",
            }]

        try:
            if self.mode == "classifier" and self.classifier is not None:
                return self._predict_classifier_details(cleaned_text, top_n=top_n)
            return self._predict_centroid_details(cleaned_text, top_n=top_n)
        except Exception as e:
            logger.error(f"Category prediction failed: {e}")
            return [{
                "category": "General",
                "confidence": 0.5,
                "raw_score": 0.5,
                "method": "fallback",
            }]

    def _predict_classifier_details(self, cleaned_text: str, top_n: int = 3) -> List[Dict]:
        """Predict categories using classifier probabilities."""
        vec = self.vectorizer.transform([cleaned_text])
        probs = self.classifier.predict_proba(vec).flatten()
        class_names = list(self.classifier.classes_)

        top_indices = np.argsort(probs)[::-1][:top_n]
        results = []
        for idx in top_indices:
            p = float(probs[idx])
            results.append({
                "category": class_names[idx],
                "confidence": round(p, 3),
                "raw_score": round(p, 6),
                "method": "classifier",
            })
        return results

    def _predict_centroid_details(self, cleaned_text: str, top_n: int = 3) -> List[Dict]:
        """Predict categories using centroid cosine similarity."""
        vec = self.vectorizer.transform([cleaned_text])
        similarities = cosine_similarity(vec, self.category_centroids).flatten()

        max_sim = similarities.max()
        min_sim = similarities.min()
        if max_sim > min_sim:
            normalized = (similarities - min_sim) / (max_sim - min_sim)
        else:
            normalized = np.ones_like(similarities) / len(similarities)

        top_indices = np.argsort(similarities)[::-1][:top_n]
        results = []
        for idx in top_indices:
            results.append({
                "category": self.category_names[idx],
                "confidence": round(float(normalized[idx]), 3),
                "raw_score": round(float(similarities[idx]), 6),
                "method": "centroid",
            })
        return results
