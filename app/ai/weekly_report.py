from __future__ import annotations

from app.ai.prompt_builder import PROMPT_INJECTION_GUARD, build_messages
from app.ai.schemas import WeeklyNarrative
from app.ai.structured_output import get_structured_completion
from app.analytics.schemas import AnalyticsSummary
from app.database.models import Feedback

SYSTEM_PROMPT = """You are an operations analyst producing a concise weekly operational
summary of guest and host feedback for an Airbnb-style short-term rental platform's
leadership team.

You will be given, for the reporting period:
- Aggregate metrics that have already been computed correctly - treat these as
  ground truth. Do not recompute them, do not restate exact figures repeatedly,
  and do not invent any numbers that are not given to you.
- A small sample of top-priority concerns (e.g. safety alerts, maintenance
  issues, refund escalations) and positive highlights (e.g. glowing guest
  reviews, host communication praise) from that period.

Produce:
- executive_summary: 2-4 sentences giving leadership the big picture (volume,
  sentiment trend, most pressing category - e.g. a spike in cleanliness
  complaints in a particular city, or a safety issue trend), in plain
  business language.
- key_wins: 1-3 short bullet points on what is going well, grounded in the
  provided positive highlights.
- key_concerns: 1-3 short bullet points on the most pressing issues, grounded in
  the provided top concerns.
- recommended_actions: 1-3 short, concrete, actionable next steps an ops or
  product leader could take this week.

Synthesize and prioritize; do not simply restate the raw data back verbatim.
""" + PROMPT_INJECTION_GUARD


def _format_metrics(metrics: AnalyticsSummary) -> str:
    lines = [
        f"Total feedback: {metrics.total_feedback} ({metrics.classified_feedback} classified)",
        f"Sentiment: {metrics.positive_pct}% Positive, {metrics.neutral_pct}% Neutral, "
        f"{metrics.negative_pct}% Negative",
        f"Categories: {metrics.guest_reviews} Guest Reviews, {metrics.host_complaints} Host "
        f"Complaints, {metrics.support_tickets} Support Tickets",
    ]
    if metrics.average_confidence is not None:
        lines.append(f"Average classification confidence: {metrics.average_confidence}%")
    return "\n".join(lines)


def _format_excerpts(label: str, items: list[Feedback]) -> str:
    if not items:
        return f"{label}: none this period."

    lines = [f"{label}:"]
    for item in items:
        tags = " / ".join(
            value.value
            for value in (item.main_category, item.sub_category, item.sentiment, item.priority)
            if value is not None
        )
        lines.append(f'- [{tags}] "{item.raw_text}"')
    return "\n".join(lines)


def build_report_context(
    metrics: AnalyticsSummary, top_concerns: list[Feedback], positive_highlights: list[Feedback]
) -> str:
    return "\n\n".join(
        [
            _format_metrics(metrics),
            _format_excerpts("Top concerns (high/critical priority)", top_concerns),
            _format_excerpts("Positive highlights", positive_highlights),
        ]
    )


_EXAMPLE_CONTEXT = (
    "Total feedback: 20 (19 classified)\n"
    "Sentiment: 40.0% Positive, 25.0% Neutral, 35.0% Negative\n"
    "Categories: 9 Guest Reviews, 6 Host Complaints, 5 Support Tickets\n"
    "Average classification confidence: 90.0%\n\n"
    "Top concerns (high/critical priority):\n"
    '- [Host Complaint / Safety / Negative / Critical] "The front door lock has been broken for two days."\n'
    '- [Guest Review / Cleanliness / Negative / High] "The apartment was filthy when we arrived."\n\n'
    "Positive highlights:\n"
    '- [Guest Review / Host Communication / Positive] "Our host fixed the check-in issue within minutes."'
)

_EXAMPLE_OUTPUT = WeeklyNarrative(
    executive_summary=(
        "Feedback volume held steady this week with a mild negative tilt, driven mainly by "
        "a recurring cleanliness complaint and a critical safety report at one property. "
        "Guests continue to praise host responsiveness."
    ),
    key_wins=["Host communication and responsiveness continue to earn praise from guests."],
    key_concerns=[
        "A broken door lock left a property unsecured and was flagged as a critical safety issue.",
        "Cleanliness complaints recurred at more than one listing this week.",
    ],
    recommended_actions=[
        "Dispatch a locksmith to the affected property today and confirm the fix with Trust & Safety.",
        "Follow up with the housekeeping vendors tied to this week's cleanliness complaints.",
    ],
).model_dump_json()

FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [(_EXAMPLE_CONTEXT, _EXAMPLE_OUTPUT)]


def generate_weekly_narrative(
    metrics: AnalyticsSummary, top_concerns: list[Feedback], positive_highlights: list[Feedback]
) -> WeeklyNarrative:
    context = build_report_context(metrics, top_concerns, positive_highlights)
    messages = build_messages(SYSTEM_PROMPT, context, FEW_SHOT_EXAMPLES)
    return get_structured_completion(messages, WeeklyNarrative)
