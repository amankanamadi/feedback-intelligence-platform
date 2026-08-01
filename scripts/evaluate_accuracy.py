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
        "The apartment was filthy when we arrived - dust everywhere and the bathroom hadn't been cleaned.",
        MainCategory.GUEST_REVIEW,
        SubCategory.CLEANLINESS,
        Sentiment.NEGATIVE,
        ["dirty", "clean", "dust"],
    ),
    LabeledExample(
        "The WiFi signal barely reaches the bedroom, I couldn't get a stable video call all week.",
        MainCategory.GUEST_REVIEW,
        SubCategory.WIFI,
        Sentiment.NEGATIVE,
        ["wifi", "connection", "signal"],
    ),
    LabeledExample(
        "The keypad code didn't work when we arrived at midnight and we waited outside for 45 minutes.",
        MainCategory.GUEST_REVIEW,
        SubCategory.CHECK_IN,
        Sentiment.NEGATIVE,
        ["check-in", "code", "lock"],
    ),
    LabeledExample(
        "The kitchen was fully stocked and the pool was immaculate, we used it every single day!",
        MainCategory.GUEST_REVIEW,
        SubCategory.AMENITIES,
        Sentiment.POSITIVE,
        ["pool", "kitchen", "amenities"],
    ),
    LabeledExample(
        "Our host responded to every message within minutes and even recommended amazing restaurants nearby.",
        MainCategory.GUEST_REVIEW,
        SubCategory.HOST_COMMUNICATION,
        Sentiment.POSITIVE,
        ["host", "communication", "responsive"],
    ),
    LabeledExample(
        "The place was beautiful but the host never answered any of my messages the whole stay.",
        MainCategory.GUEST_REVIEW,
        SubCategory.HOST_COMMUNICATION,
        Sentiment.NEGATIVE,
        ["host", "communication", "unresponsive"],
    ),
    LabeledExample(
        "As the host, the smoke detector in the hallway has been beeping and dead for a week and I'm "
        "worried about guest safety.",
        MainCategory.HOST_COMPLAINT,
        SubCategory.SAFETY,
        Sentiment.NEGATIVE,
        ["safety", "smoke detector"],
    ),
    LabeledExample(
        "The guests who checked out yesterday left a cracked window and a stained mattress, I need this "
        "fixed before the next booking.",
        MainCategory.HOST_COMPLAINT,
        SubCategory.MAINTENANCE,
        Sentiment.NEGATIVE,
        ["damage", "maintenance", "broken"],
    ),
    LabeledExample(
        "My reservation was cancelled by the host two days before check-in with no explanation.",
        MainCategory.SUPPORT_TICKET,
        SubCategory.BOOKING_EXPERIENCE,
        Sentiment.NEGATIVE,
        ["booking", "cancel", "reservation"],
    ),
    LabeledExample(
        "Great, another host cancellation right before my trip. Third time this has happened with this app.",
        MainCategory.SUPPORT_TICKET,
        SubCategory.BOOKING_EXPERIENCE,
        Sentiment.NEGATIVE,
        ["cancel", "booking"],
    ),
    LabeledExample(
        "I was charged twice for the same reservation and neither charge has been refunded yet.",
        MainCategory.SUPPORT_TICKET,
        SubCategory.PAYMENTS,
        Sentiment.NEGATIVE,
        ["charge", "payment", "double"],
    ),
    LabeledExample(
        "It's been three weeks since my trip was cancelled and I still haven't received my refund.",
        MainCategory.SUPPORT_TICKET,
        SubCategory.REFUNDS,
        Sentiment.NEGATIVE,
        ["refund"],
    ),
    LabeledExample(
        "The app crashes every time I try to open the messages tab with my host.",
        MainCategory.SUPPORT_TICKET,
        SubCategory.APP_ISSUES,
        Sentiment.NEGATIVE,
        ["app", "crash"],
    ),
    LabeledExample(
        "It would be great if I could filter search results by listings that allow pets.",
        MainCategory.SUPPORT_TICKET,
        SubCategory.FEATURE_REQUESTS,
        Sentiment.NEUTRAL,
        ["filter", "pet", "feature"],
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
