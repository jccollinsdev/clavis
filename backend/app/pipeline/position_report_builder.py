from ..services.minimax import chatcompletion_text
from .analysis_utils import extract_json_list, extract_json_object


SYSTEM_PROMPT = """You write a long-form investment risk report for one stock position.

Return strict JSON with this shape:
{{
  "summary": "2-3 sentence executive summary",
  "long_report": "4-8 sentence detailed report",
  "methodology": "brief explanation of the evidence and framework used",
  "top_risks": ["risk 1", "risk 2", "risk 3"],
  "watch_items": ["watch item 1", "watch item 2"],
  "thesis_verifier": [
    {{
      "macro_event": "description of macro development",
      "thesis_impact": "confirms|challenges|neutral",
      "reasoning": "one sentence explaining why"
    }}
  ]
}}

Anchor the report in the supplied event evidence. Mention both near-term and longer-term implications when relevant.

CRITICAL - Macro as Thesis Verifier:
- For thesis_verifier, assess whether any macro context confirms, challenges, or is neutral to this position's investment thesis
- If the position has no clear thesis, use "neutral" for thesis_impact
- Macro should VERIFY the thesis, not drive it. If macro is neutral to the thesis, say so simply.
- Only include thesis_verifier entries for macro events that actually relate to this position's sector/theme
- If no relevant macro context exists, omit thesis_verifier array entirely (do not include empty array)
"""


def _fallback_position_report(
    position: dict,
    inferred_labels: list[str],
    event_analyses: list[dict],
) -> dict:
    ticker = position.get("ticker", "This holding")
    major_events = [
        event for event in event_analyses if event.get("significance") == "major"
    ]
    worsening_count = len(
        [
            event
            for event in event_analyses
            if event.get("risk_direction") == "worsening"
        ]
    )
    improving_count = len(
        [
            event
            for event in event_analyses
            if event.get("risk_direction") == "improving"
        ]
    )
    labels_text = ", ".join(inferred_labels[:3]) if inferred_labels else "core"
    event_titles = [
        event.get("title", "recent coverage") for event in event_analyses[:3]
    ]

    stance = "mixed but monitorable"
    if worsening_count > improving_count:
        stance = "skewing negative"
    elif improving_count > worsening_count:
        stance = "constructive but still worth monitoring"

    summary = (
        f"{ticker} is currently framed as {labels_text}. "
        f"Recent event flow is {stance}, with {len(event_analyses)} relevant items in this cycle."
    )
    long_report = (
        f"{summary} The most relevant developments were {', '.join(event_titles)}. "
        f"{ticker} logged {len(major_events)} major events and {len(event_analyses) - len(major_events)} minor events in this run. "
        f"The current assessment is derived from event-level analysis text, scenario summaries, and direction-of-risk tags across the news set."
    )
    top_risks = [
        event.get("scenario_summary") or event.get("title", "Recent catalyst risk")
        for event in event_analyses[:3]
    ]
    watch_items = [
        followup
        for event in event_analyses[:3]
        for followup in (event.get("recommended_followups") or [])[:1]
    ]

    return {
        "summary": summary,
        "long_report": long_report,
        "methodology": "Fallback synthesis from structured event analyses, inferred labels, and direction-of-risk signals.",
        "top_risks": top_risks
        or ["Watch for changes in thesis integrity and follow-on reporting."],
        "watch_items": watch_items
        or [
            "Watch for additional company-specific or macro updates that change event significance."
        ],
    }


async def build_position_report(
    position: dict,
    inferred_labels: list[str],
    event_analyses: list[dict],
    macro_context: dict | None = None,
) -> dict:
    if not event_analyses:
        ticker = position.get("ticker", "This holding")
        return {
            "summary": f"No material new risk events were identified for {ticker} in this cycle.",
            "long_report": f"{ticker} did not have any relevant events that cleared the portfolio relevance threshold during this run. The current view is therefore based on existing position context and the absence of new negative catalysts.",
            "methodology": "Position review based on position metadata and an empty relevant-event set for this analysis cycle.",
            "top_risks": ["No new material risk catalysts identified."],
            "watch_items": ["Watch for new company-specific or macro catalysts."],
        }

    event_summary = "\n".join(
        f"- [{event.get('significance', 'minor')}] {event.get('title', '')}: {event.get('long_analysis', '')[:400]}"
        for event in event_analyses[:8]
    )
    prompt = f"""Position:
    - Ticker: {position.get("ticker", "")}
    - Sector: {position.get("sector", "unknown")}
    - Shares: {position.get("shares", 0)}
    - Purchase price: {position.get("purchase_price", 0)}
    - Inferred labels: {", ".join(inferred_labels) if inferred_labels else "unknown"}
    """

    if macro_context and macro_context.get("overnight_macro"):
        macro_brief = macro_context["overnight_macro"].get("brief", "")
        macro_themes = macro_context["overnight_macro"].get("themes", [])
        prompt += f"""
Macro Context (overnight developments):
- Brief: {macro_brief}
- Themes: {", ".join(macro_themes) if macro_themes else "none detected"}
"""

        position_impacts = macro_context.get("position_impacts", [])
        ticker_impact = next(
            (
                imp
                for imp in position_impacts
                if imp.get("ticker", "").upper() == position.get("ticker", "").upper()
            ),
            None,
        )
        if ticker_impact:
            prompt += f"- Macro impact on {position.get('ticker')}: {ticker_impact.get('impact_summary', '')}\n"

    prompt += f"""
Event analyses:
{event_summary}
"""

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1400,
    )

    parsed = extract_json_object(result, {})
    fallback = _fallback_position_report(position, inferred_labels, event_analyses)
    return {
        "summary": parsed.get("summary") or fallback["summary"],
        "long_report": parsed.get("long_report")
        or parsed.get("summary")
        or fallback["long_report"],
        "methodology": parsed.get("methodology") or fallback["methodology"],
        "top_risks": parsed.get("top_risks") or fallback["top_risks"],
        "watch_items": parsed.get("watch_items") or fallback["watch_items"],
        "thesis_verifier": parsed.get("thesis_verifier") or [],
    }


BATCH_REPORT_PROMPT = """You write long-form investment risk reports for multiple stock positions.

Return a JSON array with one object per position in order.
Each object has:
- "summary": "2-3 sentence executive summary"
- "long_report": "4-8 sentence detailed report"
- "methodology": "brief explanation of the evidence and framework used"
- "top_risks": ["risk 1", "risk 2", "risk 3"]
- "watch_items": ["watch item 1", "watch item 2"]
- "thesis_verifier": [{{"macro_event": "...", "thesis_impact": "confirms|challenges|neutral", "reasoning": "..."}}]

CRITICAL - Macro as Thesis Verifier:
- For thesis_verifier, assess whether any macro context confirms, challenges, or is neutral to each position's investment thesis
- If a position has no clear thesis, use "neutral" for thesis_impact
- Macro should VERIFY the thesis, not drive it. If macro is neutral to the thesis, say so simply.
- Only include thesis_verifier entries for macro events that actually relate to each position's sector/theme
- If no relevant macro context exists for a position, omit thesis_verifier array for that position

Positions:
{positions}

Return a JSON array with {count} objects, one per position in order."""


async def build_position_reports_batch(
    positions: list[dict],
    positions_inferred_labels: dict[str, list[str]],
    all_event_analyses: dict[str, list[dict]],
    macro_context: dict | None = None,
) -> list[dict]:
    if not positions:
        return []

    macro_brief = ""
    macro_themes = []
    if macro_context and macro_context.get("overnight_macro"):
        macro_brief = macro_context["overnight_macro"].get("brief", "")
        macro_themes = macro_context["overnight_macro"].get("themes", [])

    position_impacts = (
        macro_context.get("position_impacts", []) if macro_context else []
    )

    positions_text = []
    for i, position in enumerate(positions):
        ticker = position.get("ticker", "")
        inferred_labels = positions_inferred_labels.get(ticker, [])
        event_analyses = all_event_analyses.get(ticker, [])

        event_summary = "\n".join(
            f"- [{event.get('significance', 'minor')}] {event.get('title', '')}: {event.get('long_analysis', '')[:300]}"
            for event in event_analyses[:6]
        )

        pos_text = f"""[{i}] Ticker: {ticker}
- Sector: {position.get("sector", "unknown")}
- Shares: {position.get("shares", 0)}
- Purchase price: {position.get("purchase_price", 0)}
- Inferred labels: {", ".join(inferred_labels) if inferred_labels else "unknown"}"""

        if macro_brief:
            pos_text += f"""
- Macro Context: Brief: {macro_brief}, Themes: {", ".join(macro_themes) if macro_themes else "none"}"""

        ticker_impact = next(
            (
                imp
                for imp in position_impacts
                if imp.get("ticker", "").upper() == ticker.upper()
            ),
            None,
        )
        if ticker_impact:
            pos_text += f"\n- Macro impact: {ticker_impact.get('impact_summary', '')}"

        if event_summary:
            pos_text += f"\n- Event analyses:\n{event_summary}"
        else:
            pos_text += "\n- Event analyses: None"

        positions_text.append(pos_text)

    prompt = BATCH_REPORT_PROMPT.format(
        positions="\n\n".join(positions_text),
        count=len(positions),
    )

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=5000,
    )

    parsed = extract_json_list(result, None)

    results = []
    if isinstance(parsed, list) and len(parsed) == len(positions):
        for i, position in enumerate(positions):
            ticker = position.get("ticker", "")
            inferred_labels = positions_inferred_labels.get(ticker, [])
            event_analyses = all_event_analyses.get(ticker, [])
            fallback = _fallback_position_report(
                position, inferred_labels, event_analyses
            )
            p = parsed[i]
            results.append(
                {
                    "summary": p.get("summary") or fallback["summary"],
                    "long_report": p.get("long_report")
                    or p.get("summary")
                    or fallback["long_report"],
                    "methodology": p.get("methodology") or fallback["methodology"],
                    "top_risks": p.get("top_risks") or fallback["top_risks"],
                    "watch_items": p.get("watch_items") or fallback["watch_items"],
                    "thesis_verifier": p.get("thesis_verifier") or [],
                }
            )
    else:
        for position in positions:
            ticker = position.get("ticker", "")
            inferred_labels = positions_inferred_labels.get(ticker, [])
            event_analyses = all_event_analyses.get(ticker, [])
            results.append(
                _fallback_position_report(position, inferred_labels, event_analyses)
            )

    return results
