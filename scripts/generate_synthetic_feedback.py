"""Generate realistic synthetic feedback text to seed the RAG store, run
manually against the real OpenAI API:

    python scripts/generate_synthetic_feedback.py
    python scripts/generate_synthetic_feedback.py --output scripts/synthetic_dataset_batch2.json --per-topic 5

Generates raw text only - no category, sentiment, priority, or theme
labels are produced or stored anywhere. The taxonomy below is used purely
as a generation-time variety hint (so the output isn't all about the same
two topics); it is discarded after generation.

This is deliberate: seeding the RAG store with text manufactured to match
a label wouldn't be grounding in real precedent, it would be the model
referencing its own fabrications. Instead, the generated text here gets
POSTed through the real /feedback pipeline by scripts/seed_synthetic_feedback.py,
so whatever classification ends up stored is the model's own genuine
judgment on that text - the same as any real request, not an externally
injected answer. scripts/evaluate_accuracy.py's hand-written dataset is
untouched by this and stays the trustworthy evaluation set.

Output: scripts/synthetic_dataset.json, a flat JSON array of strings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel  # noqa: E402

from app.ai.prompt_builder import build_messages  # noqa: E402
from app.ai.structured_output import get_structured_completion  # noqa: E402
from app.database.models import MainCategory, SubCategory  # noqa: E402

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "synthetic_dataset.json"
DEFAULT_TEXTS_PER_TOPIC = 3

SYSTEM_PROMPT = """You are helping generate realistic synthetic customer
feedback for a SaaS product, to seed test data for a feedback intelligence
platform.

You will be given a topic area as inspiration only. Write ONE piece of
feedback text a real customer would plausibly write that's loosely
inspired by that topic - do not mention the topic label itself, do not
sound like you are filling out a category. Vary length, tone, and
specificity across calls: some one-liners, some multi-sentence, some
vague, some highly specific, a realistic mix of positive/neutral/negative
in tone depending on what naturally fits the topic. Do not repeat
scenarios or phrasing you have likely used before. Output only the
feedback text itself, nothing else.
"""

# Purely a generation-time variety hint - never persisted as a label.
TOPIC_HINTS = [
    (MainCategory.INCIDENT, SubCategory.PRODUCT_BUG),
    (MainCategory.INCIDENT, SubCategory.APPLICATION_CRASH),
    (MainCategory.INCIDENT, SubCategory.LOGIN_ISSUE),
    (MainCategory.INCIDENT, SubCategory.PAYMENT_FAILURE),
    (MainCategory.INCIDENT, SubCategory.PERFORMANCE_ISSUE),
    (MainCategory.INCIDENT, SubCategory.SECURITY_ISSUE),
    (MainCategory.INCIDENT, SubCategory.DATA_LOSS),
    (MainCategory.INCIDENT, SubCategory.INTEGRATION_FAILURE),
    (MainCategory.SERVICE_REQUEST, SubCategory.FEATURE_REQUEST),
    (MainCategory.SERVICE_REQUEST, SubCategory.UI_UX_IMPROVEMENT),
    (MainCategory.SERVICE_REQUEST, SubCategory.DOCUMENTATION_REQUEST),
    (MainCategory.SERVICE_REQUEST, SubCategory.API_ENHANCEMENT),
    (MainCategory.SERVICE_REQUEST, SubCategory.ACCESSIBILITY_IMPROVEMENT),
    (MainCategory.SERVICE_REQUEST, SubCategory.NEW_INTEGRATION),
    (MainCategory.GENERAL_FEEDBACK, SubCategory.APPRECIATION),
    (MainCategory.GENERAL_FEEDBACK, SubCategory.COMPLAINT),
    (MainCategory.GENERAL_FEEDBACK, SubCategory.PRICING_FEEDBACK),
    (MainCategory.GENERAL_FEEDBACK, SubCategory.CUSTOMER_SUPPORT),
    (MainCategory.GENERAL_FEEDBACK, SubCategory.QUESTION),
    (MainCategory.GENERAL_FEEDBACK, SubCategory.SUGGESTION),
]


class SyntheticText(BaseModel):
    raw_text: str


def generate_texts(texts_per_topic: int) -> list[str]:
    texts: list[str] = []
    total = len(TOPIC_HINTS) * texts_per_topic
    done = 0
    for main_category, sub_category in TOPIC_HINTS:
        topic_hint = f"{main_category.value} / {sub_category.value}"
        for _ in range(texts_per_topic):
            messages = build_messages(SYSTEM_PROMPT, f"Topic area (inspiration only): {topic_hint}")
            generated = get_structured_completion(messages, SyntheticText)
            texts.append(generated.raw_text)
            done += 1
            print(f"[{done}/{total}] ({topic_hint}): {generated.raw_text[:70]}")
    return texts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--per-topic", type=int, default=DEFAULT_TEXTS_PER_TOPIC)
    args = parser.parse_args()

    texts = generate_texts(args.per_topic)
    args.output.write_text(json.dumps(texts, indent=2))
    print(f"\nWrote {len(texts)} raw feedback strings to {args.output}")


if __name__ == "__main__":
    main()
