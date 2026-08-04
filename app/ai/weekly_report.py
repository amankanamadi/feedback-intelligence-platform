from __future__ import annotations

from app.ai.prompt_builder import PROMPT_INJECTION_GUARD, build_messages
from app.ai.schemas import WeeklyNarrative
from app.ai.structured_output import get_structured_completion
from app.analytics.schemas import AnalyticsSummary
from app.database.models import Feedback, Role

# Shared across all 5 role framings below - only the final paragraph
# (ROLE_FRAMING) changes what gets emphasized; the required output shape
# and "ground truth, don't invent numbers" discipline stay identical.
_SHARED_INSTRUCTIONS = """You are an operations analyst producing a concise weekly operational
summary of guest and host feedback for an Airbnb-style short-term rental platform.

You will be given, for the reporting period:
- Aggregate metrics that have already been computed correctly - treat these as
  ground truth. Do not recompute them, do not restate exact figures repeatedly,
  and do not invent any numbers that are not given to you.
- A small sample of top-priority concerns (e.g. safety alerts, maintenance
  issues, refund escalations) and positive highlights (e.g. glowing guest
  reviews, host communication praise) from that period.

Produce:
- executive_summary: 2-4 sentences giving the big picture (volume, sentiment
  trend, most pressing category - e.g. a spike in cleanliness complaints in a
  particular city, or a safety issue trend), in plain business language.
- key_wins: 1-3 short bullet points on what is going well, grounded in the
  provided positive highlights.
- key_concerns: 1-3 short bullet points on the most pressing issues, grounded in
  the provided top concerns.
- recommended_actions: 1-3 short, concrete, actionable next steps to take this
  week.
- emerging_risks: 1-3 short bullet points on risks visible in the trend data
  that haven't yet become a key_concern (e.g. a category climbing week over
  week, a city trending more negative) - leave empty if nothing is emerging.
- forecast: one sentence projecting where the trend is headed next period if
  left unaddressed.

Synthesize and prioritize; do not simply restate the raw data back verbatim.
"""

# One short paragraph per staff role, appended to _SHARED_INSTRUCTIONS -
# this is what makes each role's report a distinct framing over the same
# underlying metrics, per the roadmap's "5 role-specific weekly reports."
ROLE_FRAMING: dict[Role, str] = {
    Role.OPS_MANAGER: (
        "Frame this for an Operations Manager: emphasize escalation backlog, "
        "SLA-breach queue health, and routing/staffing bottlenecks above all else."
    ),
    Role.SUPPORT_MANAGER: (
        "Frame this for a Support Manager: emphasize ticket volume, resolution "
        "time, and support-specific complaint patterns (booking, payments, "
        "refunds, app issues) above all else."
    ),
    Role.TRUST_SAFETY: (
        "Frame this for Trust & Safety: emphasize safety incidents and "
        "critical-priority cases above all else - other categories are "
        "secondary context, not the focus."
    ),
    Role.PRODUCT_MANAGER: (
        "Frame this for a Product Manager: emphasize feature requests, app "
        "issues, and product-shaped feedback above all else."
    ),
    Role.EXEC: (
        "Frame this for an executive audience: emphasize overall business "
        "health and guest satisfaction at a high level, and avoid operational "
        "minutiae that isn't decision-relevant at the leadership level."
    ),
}

ROLE_SYSTEM_PROMPTS: dict[Role, str] = {
    role: _SHARED_INSTRUCTIONS + framing + PROMPT_INJECTION_GUARD for role, framing in ROLE_FRAMING.items()
}


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
    emerging_risks=[
        "Cleanliness complaints have now appeared in back-to-back weeks - watch for a broader trend.",
    ],
    forecast=(
        "If the housekeeping issue isn't addressed, expect cleanliness complaints to continue "
        "next week at a similar or higher rate."
    ),
).model_dump_json()

# One shared example, not one per role: it demonstrates format and tone
# (synthesize, don't restate raw numbers, ground claims in the given
# excerpts) - role-agnostic concerns that the system prompt's framing
# paragraph above already steers toward the right emphasis.
FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [(_EXAMPLE_CONTEXT, _EXAMPLE_OUTPUT)]


def generate_weekly_narrative(
    metrics: AnalyticsSummary,
    top_concerns: list[Feedback],
    positive_highlights: list[Feedback],
    role: Role,
) -> WeeklyNarrative:
    context = build_report_context(metrics, top_concerns, positive_highlights)
    messages = build_messages(ROLE_SYSTEM_PROMPTS[role], context, FEW_SHOT_EXAMPLES)
    return get_structured_completion(messages, WeeklyNarrative)
