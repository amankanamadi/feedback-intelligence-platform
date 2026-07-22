"""Accuracy evaluation harness, run manually against the real OpenAI API:

    python scripts/evaluate_accuracy.py

Measures classify_feedback() against a small hand-labeled dataset and
compares the results to the targets in the architecture doc:
  Category Accuracy 95%+, Sentiment Accuracy 97%+, Theme Accuracy 93%+,
  Average Confidence 95%, Processing Time <2s.

Not a pytest test: it costs money per run and is meant to be run
occasionally (e.g. after a prompt change), not on every commit.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.classification import classify_feedback  # noqa: E402
from app.database.models import MainCategory, Sentiment, SubCategory  # noqa: E402


@dataclass
class LabeledExample:
    text: str
    main_category: MainCategory
    sub_category: SubCategory
    sentiment: Sentiment
    theme_keywords: list = field(default_factory=list)


DATASET = [
    LabeledExample(
        "The app crashes every single time I try to open the settings page.",
        MainCategory.INCIDENT,
        SubCategory.APPLICATION_CRASH,
        Sentiment.NEGATIVE,
        ["crash", "settings"],
    ),
    LabeledExample(
        "My payment failed three times today even though my card is valid.",
        MainCategory.INCIDENT,
        SubCategory.PAYMENT_FAILURE,
        Sentiment.NEGATIVE,
        ["payment"],
    ),
    LabeledExample(
        "I've been unable to log into my account since yesterday, it just times out.",
        MainCategory.INCIDENT,
        SubCategory.LOGIN_ISSUE,
        Sentiment.NEGATIVE,
        ["login"],
    ),
    LabeledExample(
        "The dashboard takes over a minute to load every time, it used to be instant.",
        MainCategory.INCIDENT,
        SubCategory.PERFORMANCE_ISSUE,
        Sentiment.NEGATIVE,
        ["slow", "performance", "dashboard", "load"],
    ),
    LabeledExample(
        "I noticed my account briefly showed someone else's billing information.",
        MainCategory.INCIDENT,
        SubCategory.SECURITY_ISSUE,
        Sentiment.NEGATIVE,
        ["security", "data"],
    ),
    LabeledExample(
        "I lost three days of work when the editor failed to save my document.",
        MainCategory.INCIDENT,
        SubCategory.DATA_LOSS,
        Sentiment.NEGATIVE,
        ["data", "loss", "save"],
    ),
    LabeledExample(
        "Could you add a dark mode option to the app?",
        MainCategory.SERVICE_REQUEST,
        SubCategory.FEATURE_REQUEST,
        Sentiment.NEUTRAL,
        ["dark mode"],
    ),
    LabeledExample(
        "The checkout button is really hard to find, the layout could be clearer.",
        MainCategory.SERVICE_REQUEST,
        SubCategory.UI_UX_IMPROVEMENT,
        Sentiment.NEUTRAL,
        ["checkout", "ui", "layout"],
    ),
    LabeledExample(
        "Please add documentation for the webhook API, it's currently undocumented.",
        MainCategory.SERVICE_REQUEST,
        SubCategory.DOCUMENTATION_REQUEST,
        Sentiment.NEUTRAL,
        ["documentation", "webhook", "api"],
    ),
    LabeledExample(
        "Can you add a bulk export endpoint to the API?",
        MainCategory.SERVICE_REQUEST,
        SubCategory.API_ENHANCEMENT,
        Sentiment.NEUTRAL,
        ["api", "export"],
    ),
    LabeledExample(
        "It would help if screen readers worked better with your forms.",
        MainCategory.SERVICE_REQUEST,
        SubCategory.ACCESSIBILITY_IMPROVEMENT,
        Sentiment.NEUTRAL,
        ["accessibility", "screen reader"],
    ),
    LabeledExample(
        "Thank you so much, your team fixed my issue within the hour!",
        MainCategory.GENERAL_FEEDBACK,
        SubCategory.APPRECIATION,
        Sentiment.POSITIVE,
        ["thank", "support", "appreciat"],
    ),
    LabeledExample(
        "Your pricing is way too expensive compared to competitors.",
        MainCategory.GENERAL_FEEDBACK,
        SubCategory.PRICING_FEEDBACK,
        Sentiment.NEGATIVE,
        ["pricing", "expensive", "price"],
    ),
    LabeledExample(
        "The support agent I spoke to yesterday was incredibly rude.",
        MainCategory.GENERAL_FEEDBACK,
        SubCategory.CUSTOMER_SUPPORT,
        Sentiment.NEGATIVE,
        ["support", "rude"],
    ),
    LabeledExample(
        "How do I change my billing email address?",
        MainCategory.GENERAL_FEEDBACK,
        SubCategory.QUESTION,
        Sentiment.NEUTRAL,
        ["billing", "email"],
    ),
]

TARGETS = {
    "category_accuracy_pct": 95.0,
    "sentiment_accuracy_pct": 97.0,
    "theme_accuracy_pct_f1": 93.0,
    "average_confidence": 95.0,
    "average_processing_time_s": 2.0,
}


def theme_precision_recall(predicted_themes, expected_keywords):
    if not expected_keywords:
        return (1.0, 1.0)

    predicted_lower = [t.lower() for t in predicted_themes]
    matched_predicted = [p for p in predicted_lower if any(k in p for k in expected_keywords)]
    matched_keywords = [k for k in expected_keywords if any(k in p for p in predicted_lower)]

    precision = len(matched_predicted) / len(predicted_lower) if predicted_lower else 0.0
    recall = len(matched_keywords) / len(expected_keywords)
    return precision, recall


def run_evaluation():
    results = []
    for example in DATASET:
        start = time.perf_counter()
        prediction = classify_feedback(example.text)
        elapsed = time.perf_counter() - start

        precision, recall = theme_precision_recall(prediction.themes, example.theme_keywords)

        results.append(
            {
                "text": example.text,
                "expected_main_category": example.main_category.value,
                "predicted_main_category": prediction.main_category.value,
                "expected_sub_category": example.sub_category.value,
                "predicted_sub_category": prediction.sub_category.value,
                "expected_sentiment": example.sentiment.value,
                "predicted_sentiment": prediction.sentiment.value,
                "predicted_themes": prediction.themes,
                "confidence": prediction.confidence,
                "theme_precision": precision,
                "theme_recall": recall,
                "processing_time_s": elapsed,
                "category_exact_match": (
                    prediction.main_category == example.main_category
                    and prediction.sub_category == example.sub_category
                ),
                "sentiment_match": prediction.sentiment == example.sentiment,
            }
        )
    return results


def summarize(results):
    n = len(results)
    category_accuracy = sum(r["category_exact_match"] for r in results) / n * 100
    sentiment_accuracy = sum(r["sentiment_match"] for r in results) / n * 100
    avg_theme_precision = sum(r["theme_precision"] for r in results) / n * 100
    avg_theme_recall = sum(r["theme_recall"] for r in results) / n * 100
    theme_f1 = (
        2 * avg_theme_precision * avg_theme_recall / (avg_theme_precision + avg_theme_recall)
        if (avg_theme_precision + avg_theme_recall) > 0
        else 0.0
    )
    avg_confidence = sum(r["confidence"] for r in results) / n
    avg_processing_time = sum(r["processing_time_s"] for r in results) / n

    return {
        "sample_size": n,
        "category_accuracy_pct": round(category_accuracy, 1),
        "sentiment_accuracy_pct": round(sentiment_accuracy, 1),
        "theme_precision_pct": round(avg_theme_precision, 1),
        "theme_recall_pct": round(avg_theme_recall, 1),
        "theme_accuracy_pct_f1": round(theme_f1, 1),
        "average_confidence": round(avg_confidence, 1),
        "average_processing_time_s": round(avg_processing_time, 2),
    }


def print_report(summary):
    print("\n=== Accuracy Evaluation Report ===")
    print(f"Sample size: {summary['sample_size']}\n")
    for key, target in TARGETS.items():
        value = summary[key]
        lower_is_better = key == "average_processing_time_s"
        passed = value <= target if lower_is_better else value >= target
        comparator = "<=" if lower_is_better else ">="
        status = "PASS" if passed else "FAIL"
        print(f"{key:28s} {value:>7} {comparator} {target:<7} [{status}]")
    print()


def main():
    results = run_evaluation()
    summary = summarize(results)
    print_report(summary)

    output_path = Path(__file__).resolve().parent / "eval_results.json"
    output_path.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(f"Full results written to {output_path}")


if __name__ == "__main__":
    main()
