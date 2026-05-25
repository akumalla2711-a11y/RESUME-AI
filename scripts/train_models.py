"""
Train category prediction models for ResumeAI.

Outputs:
- models/category_vectorizer.joblib
- models/category_classifier.joblib
- models/category_centroids.joblib (legacy fallback support)
- models/category_training_report.json
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import RandomOverSampler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split


# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.taxonomy import get_taxonomy_categories, resolve_category  # noqa: E402


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATASET = PROJECT_ROOT / "Resume.csv"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models"
DEFAULT_CORRECTIONS_PATH = PROJECT_ROOT / "data" / "user_corrections.csv"


@dataclass
class TrainConfig:
    test_size: float = 0.2
    random_state: int = 42
    max_features: int = 10000
    macro_f1_floor: float = 0.40
    minority_recall_floor: float = 0.25
    use_random_oversampling: bool = False
    include_user_corrections: bool = True


def simple_clean(text: str) -> str:
    """Lightweight text cleaner for training data."""
    if not isinstance(text, str):
        return ""
    value = text.lower()
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"http\S+", " ", value)
    value = re.sub(r"\S+@\S+", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def canonicalize_category(label: str) -> str | None:
    """Map raw label into taxonomy canonical label."""
    if not isinstance(label, str):
        return None
    stripped = label.strip()
    if not stripped:
        return None
    resolved = resolve_category(stripped)
    if resolved:
        return resolved
    uppercase = stripped.upper()
    return resolve_category(uppercase)


def load_base_dataset(data_path: Path) -> pd.DataFrame:
    """Load the primary Resume.csv dataset and canonicalize categories."""
    if not data_path.exists():
        raise FileNotFoundError(f"Resume.csv not found at: {data_path}")

    logger.info(f"Loading base dataset: {data_path}")
    df = pd.read_csv(data_path)
    if "Category" not in df.columns:
        raise ValueError("Resume.csv must contain a 'Category' column.")
    if "Resume_str" not in df.columns and "Cleaned_Resume" not in df.columns:
        raise ValueError("Resume.csv must contain either 'Resume_str' or 'Cleaned_Resume'.")

    text_col = "Cleaned_Resume" if "Cleaned_Resume" in df.columns else "Resume_str"
    df = df[[text_col, "Category"]].copy()
    df.columns = ["text", "category"]
    df["text"] = df["text"].fillna("").astype(str)
    df["text"] = df["text"].apply(simple_clean)
    df["category"] = df["category"].apply(canonicalize_category)

    before = len(df)
    df = df[(df["text"].str.len() >= 20) & df["category"].notna()].copy()
    logger.info(f"Base rows kept after cleaning: {len(df)} / {before}")
    return df


def load_user_corrections(corrections_path: Path) -> pd.DataFrame:
    """Load optional user feedback corrections."""
    if not corrections_path.exists():
        logger.info("No user corrections file found, continuing without it.")
        return pd.DataFrame(columns=["text", "category"])

    logger.info(f"Loading user corrections: {corrections_path}")
    df = pd.read_csv(corrections_path)
    required_cols = {"cleaned_resume_text", "confirmed_category"}
    if not required_cols.issubset(df.columns):
        logger.warning("Corrections file missing required columns, skipping corrections.")
        return pd.DataFrame(columns=["text", "category"])

    corr = df[["cleaned_resume_text", "confirmed_category"]].copy()
    corr.columns = ["text", "category"]
    corr["text"] = corr["text"].fillna("").astype(str).apply(simple_clean)
    corr["category"] = corr["category"].apply(canonicalize_category)
    corr = corr[(corr["text"].str.len() >= 20) & corr["category"].notna()].copy()
    logger.info(f"Valid corrections loaded: {len(corr)}")
    return corr


def enforce_taxonomy_parity(categories: List[str]) -> None:
    """Fail fast if model labels and taxonomy labels diverge."""
    dataset_labels = set(categories)
    taxonomy_labels = set(get_taxonomy_categories())

    if dataset_labels != taxonomy_labels:
        missing_in_taxonomy = sorted(dataset_labels - taxonomy_labels)
        missing_in_dataset = sorted(taxonomy_labels - dataset_labels)
        raise RuntimeError(
            "Taxonomy/data mismatch detected. "
            f"missing_in_taxonomy={missing_in_taxonomy}, "
            f"missing_in_dataset={missing_in_dataset}"
        )


def build_centroids(features, labels: np.ndarray, names: List[str]) -> np.ndarray:
    """Compute per-category TF-IDF centroids for backward-compatible fallback."""
    centroids = np.zeros((len(names), features.shape[1]), dtype=np.float64)
    for idx, category in enumerate(names):
        mask = labels == category
        if mask.sum() > 0:
            centroids[idx] = features[mask].mean(axis=0).A1
    return centroids


def summarize_confusion(labels: List[str], conf_mx: np.ndarray, limit: int = 20) -> List[Dict]:
    """Create compact, report-friendly confusion matrix summary."""
    rows = []
    for row_idx, true_label in enumerate(labels):
        row = conf_mx[row_idx]
        total = int(row.sum())
        if total == 0:
            continue
        correct = int(row[row_idx])
        mistakes = total - correct
        if mistakes <= 0:
            continue

        row_wo_diag = row.copy()
        row_wo_diag[row_idx] = 0
        confused_idx = int(np.argmax(row_wo_diag))
        rows.append(
            {
                "label": true_label,
                "support": total,
                "correct": correct,
                "mistakes": mistakes,
                "most_confused_with": labels[confused_idx],
                "confused_count": int(row_wo_diag[confused_idx]),
            }
        )

    rows.sort(key=lambda item: item["mistakes"], reverse=True)
    return rows[:limit]


def compute_minority_classes(labels: np.ndarray) -> List[str]:
    """Identify minority classes using bottom quartile support."""
    counts = pd.Series(labels).value_counts()
    cutoff = float(counts.quantile(0.25))
    return sorted(counts[counts <= cutoff].index.tolist())


def train_models(df: pd.DataFrame, model_dir: Path, cfg: TrainConfig) -> Dict:
    """Train vectorizer + classifier and produce evaluation metrics."""
    categories = sorted(df["category"].unique().tolist())
    enforce_taxonomy_parity(categories)

    texts = df["text"].astype(str).values
    labels = df["category"].values
    logger.info(f"Training rows: {len(texts)}, categories: {len(categories)}")

    vectorizer = TfidfVectorizer(
        max_features=cfg.max_features,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=2,
        max_df=0.95,
    )
    x_all = vectorizer.fit_transform(texts)

    x_train, x_test, y_train, y_test = train_test_split(
        x_all,
        labels,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=labels,
    )

    if cfg.use_random_oversampling:
        logger.info("Applying RandomOverSampler to training split.")
        oversampler = RandomOverSampler(random_state=cfg.random_state)
        x_train, y_train = oversampler.fit_resample(x_train, y_train)

    classifier = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        solver="lbfgs",
        random_state=cfg.random_state,
    )
    classifier.fit(x_train, y_train)

    y_pred = classifier.predict(x_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))

    per_class_recall: Dict[str, float] = {}
    for label in categories:
        mask = y_test == label
        if int(mask.sum()) == 0:
            per_class_recall[label] = 0.0
            continue
        recall = float((y_pred[mask] == label).mean())
        per_class_recall[label] = round(recall, 4)

    minority_classes = compute_minority_classes(y_train)
    minority_recalls = [per_class_recall.get(label, 0.0) for label in minority_classes]
    minority_recall_min = min(minority_recalls) if minority_recalls else 0.0

    conf_mx = confusion_matrix(y_test, y_pred, labels=categories)
    confusion_summary = summarize_confusion(categories, conf_mx, limit=20)

    metrics = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows_total": int(len(df)),
        "rows_train": int(len(y_train)),
        "rows_test": int(len(y_test)),
        "num_categories": int(len(categories)),
        "categories": categories,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class_recall": per_class_recall,
        "minority_classes": minority_classes,
        "minority_recall_min": round(float(minority_recall_min), 4),
        "quality_gates": {
            "macro_f1_floor": cfg.macro_f1_floor,
            "minority_recall_floor": cfg.minority_recall_floor,
            "macro_f1_passed": macro_f1 >= cfg.macro_f1_floor,
            "minority_recall_passed": float(minority_recall_min) >= cfg.minority_recall_floor,
        },
        "confusion_matrix_summary": confusion_summary,
    }

    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, model_dir / "category_vectorizer.joblib")
    joblib.dump(
        {"classifier": classifier, "names": categories, "metrics": metrics},
        model_dir / "category_classifier.joblib",
    )

    centroids = build_centroids(x_all, labels, categories)
    joblib.dump(
        {"centroids": centroids, "names": categories},
        model_dir / "category_centroids.joblib",
    )

    report_path = model_dir / "category_training_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Training report saved to {report_path}")

    if macro_f1 < cfg.macro_f1_floor:
        raise RuntimeError(
            f"Quality gate failed: macro_f1={macro_f1:.4f} < floor={cfg.macro_f1_floor:.4f}"
        )
    if float(minority_recall_min) < cfg.minority_recall_floor:
        raise RuntimeError(
            "Quality gate failed: "
            f"minority_recall_min={minority_recall_min:.4f} < floor={cfg.minority_recall_floor:.4f}"
        )

    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train ResumeAI category models.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATASET, help="Path to Resume.csv")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR, help="Model output directory")
    parser.add_argument(
        "--corrections",
        type=Path,
        default=DEFAULT_CORRECTIONS_PATH,
        help="Path to user corrections CSV",
    )
    parser.add_argument("--test-size", type=float, default=0.2, help="Validation split size")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed")
    parser.add_argument("--macro-f1-floor", type=float, default=0.40, help="Minimum allowed macro-F1")
    parser.add_argument(
        "--minority-recall-floor",
        type=float,
        default=0.25,
        help="Minimum allowed recall among minority classes",
    )
    parser.add_argument(
        "--use-random-oversampling",
        action="store_true",
        help="Apply RandomOverSampler on training split before fitting classifier",
    )
    parser.add_argument(
        "--no-user-corrections",
        action="store_true",
        help="Disable loading data/user_corrections.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_cfg = TrainConfig(
        test_size=args.test_size,
        random_state=args.random_state,
        macro_f1_floor=args.macro_f1_floor,
        minority_recall_floor=args.minority_recall_floor,
        use_random_oversampling=args.use_random_oversampling,
        include_user_corrections=not args.no_user_corrections,
    )

    base_df = load_base_dataset(args.data)
    frames = [base_df]
    if train_cfg.include_user_corrections:
        corrections_df = load_user_corrections(args.corrections)
        if not corrections_df.empty:
            frames.append(corrections_df)

    training_df = pd.concat(frames, ignore_index=True)
    if training_df.empty:
        raise RuntimeError("Training dataset is empty after preprocessing.")

    logger.info("Category distribution snapshot:")
    distribution = training_df["category"].value_counts().sort_index()
    for label, count in distribution.items():
        logger.info(f"  {label}: {count}")

    metrics = train_models(training_df, args.model_dir, train_cfg)

    logger.info("=" * 60)
    logger.info("Training completed successfully")
    logger.info(f"Accuracy: {metrics['accuracy']:.4f}")
    logger.info(f"Macro-F1: {metrics['macro_f1']:.4f}")
    logger.info(f"Minority Recall Min: {metrics['minority_recall_min']:.4f}")
    logger.info(f"Artifacts written to: {args.model_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
