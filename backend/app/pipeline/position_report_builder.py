from ..services.minimax import chatcompletion_text
from .analysis_utils import (
    extract_json_list,
    extract_json_object,
    sanitize_public_analysis_text,
)


SYSTEM_PROMPT = """You are an equity risk analyst writing a research note for a self-directed investor. Your job is to synthesize what the evidence means, not catalog what articles exist.

Return strict JSON with this shape:
{{
  "summary": "2-3 sentence thesis-first summary: state the dominant risk force, acknowledge counter-evidence briefly, and identify what would change the thesis",
  "long_report": "4-8 sentence detailed report that develops the thesis with specific evidence, resolves contradictions rather than listing them, and closes with what could materially shift the read",
  "methodology": "brief explanation of the evidence used",
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

Writing rules:
1. Lead with the dominant narrative — what is the most important force acting on this position? Do not start by describing what articles exist or what the coverage says.
2. If positive and negative evidence compete, resolve the tension: explain which force matters more and why. Do not just list both sides and leave it to the reader.
3. If strong headlines coexist with structural risk (e.g., earnings beat but valuation is stretched, revenue growth but macro headwinds), explain why the structural factor can outweigh the headline.
4. Close with what would change the thesis — a specific catalyst, resolution, or development, not a generic "watch for developments."
5. Write like concise equity research — direct, specific, grounded. Not a news summary, not a process description.

Forbidden: internal evidence labels (full_body, title_only, headline_summary), scoring methodology references, "the model", "recent event flow is [stance]", "N relevant items in this cycle", implementation jargon.

CRITICAL - Macro as Risk Context:
- For thesis_verifier, assess whether any macro context confirms, challenges, or is neutral to this position's risk profile
- If the position has no clear setup, use "neutral" for thesis_impact
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

    stance = "mixed — no single force clearly dominates"
    if worsening_count > improving_count:
        stance = "downside pressure is the primary concern"
    elif improving_count > worsening_count:
        stance = "constructive but still subject to reversal"

    summary = (
        f"{ticker}'s current risk profile leans {labels_text}. "
        f"The dominant read is {stance}, based on {len(event_analyses)} tracked developments."
    )
    long_report = (
        f"{ticker} is classified as {labels_text}. "
        f"The most relevant developments were {', '.join(event_titles)}. "
        f"{worsening_count} item(s) flagged downside pressure and {improving_count} pointed to improvement. "
        f"This assessment is provisional — a single new filing, earnings surprise, or regulatory update could shift the read materially."
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
        "methodology": "Summary assembled from event-level analysis. LLM synthesis was unavailable for this position.",
        "top_risks": top_risks
        or ["A single new article or filing could materially change the risk read."],
        "watch_items": watch_items
        or [
            "Watch for new company-specific news, guidance, or filings that change the setup."
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
        return sanitize_public_analysis_text(
            {
                "summary": f"There is not enough recent news to form a confident risk thesis for {ticker}. The current read relies on existing position context and structural factors.",
                "long_report": f"Event coverage for {ticker} is thin in this cycle, so the dominant risk thesis defaults to structural and macro factors rather than company-specific catalysts. This is a low-confidence read — any new company-specific development (earnings, guidance, regulatory action) could shift the picture meaningfully. Treat this as provisional until fuller coverage arrives.",
                "methodology": "Low-confidence assessment based on position metadata and structural context. No usable event coverage for this cycle.",
                "top_risks": [
                    "No confirmed company-specific catalyst in this cycle."
                ],
                "watch_items": [
                    "Recheck for resolved company or sector coverage before treating the current read as settled."
                ],
            }
        )

    event_summary = "\n".join(
        f"- [{event.get('significance', 'minor')}] {event.get('title', '')}: {event.get('long_analysis', '')[:400]}"
        for event in event_analyses[:8]
    )
    is_backfill_mode = (
        str(position.get("analysis_mode") or "").strip().lower() == "sp500_backfill"
    )
    prompt = f"""Position:
    - Ticker: {position.get("ticker", "")}
    - Sector: {position.get("sector", "unknown")}
    - Inferred labels: {", ".join(inferred_labels) if inferred_labels else "unknown"}
    """

    if is_backfill_mode:
        prompt += """
Backfill context:
- This is a synthetic ticker-level backfill snapshot, not a live user position.
- Do not infer conviction, entry timing, position sizing, or portfolio intent from placeholder shares or purchase price fields.
"""
    else:
        prompt += f"""
- Shares: {position.get("shares", 0)}
- Purchase price: {position.get("purchase_price", 0)}
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

    try:
        result = chatcompletion_text(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1400,
        )
    except Exception:
        fallback = _fallback_position_report(position, inferred_labels, event_analyses)
        return sanitize_public_analysis_text(
            {
                "summary": fallback["summary"],
                "long_report": fallback["long_report"],
                "methodology": fallback["methodology"],
                "top_risks": fallback["top_risks"],
                "watch_items": fallback["watch_items"],
                "thesis_verifier": [],
            }
        )

    parsed = extract_json_object(result, {})
    fallback = _fallback_position_report(position, inferred_labels, event_analyses)
    return sanitize_public_analysis_text(
        {
            "summary": parsed.get("summary") or fallback["summary"],
            "long_report": parsed.get("long_report")
            or parsed.get("summary")
            or fallback["long_report"],
            "methodology": parsed.get("methodology") or fallback["methodology"],
            "top_risks": parsed.get("top_risks") or fallback["top_risks"],
            "watch_items": parsed.get("watch_items") or fallback["watch_items"],
            "thesis_verifier": parsed.get("thesis_verifier") or [],
        }
    )


BATCH_REPORT_PROMPT = """You write concise equity risk research notes for multiple stock positions.

Write like an analyst briefing a portfolio manager — direct, specific, thesis-driven. Do not catalog articles; synthesize what they mean.

Return a JSON array with one object per position in order.
Each object has:
- "summary": "2-3 sentence thesis-first summary: dominant risk force, counter-evidence acknowledged, what changes the thesis"
- "long_report": "4-8 sentence detailed report that develops the thesis, resolves contradictions with evidence, and closes with what could shift the read"
- "methodology": "brief explanation of the evidence used"
- "top_risks": ["risk 1", "risk 2", "risk 3"]
- "watch_items": ["watch item 1", "watch item 2"]
- "thesis_verifier": [{{"macro_event": "...", "thesis_impact": "confirms|challenges|neutral", "reasoning": "..."}}]

Writing rules:
1. Lead with the dominant narrative, not with what coverage exists.
2. If positive and negative evidence compete, resolve which matters more and why. Do not list both sides.
3. Close with what would change the thesis — specific, not generic.

Forbidden: internal evidence labels (full_body, title_only, headline_summary), scoring methodology references, "recent event flow is [stance]", "N relevant items", implementation jargon.

CRITICAL - Macro as Risk Context:
- For thesis_verifier, assess whether any macro context confirms, challenges, or is neutral to each position's risk profile
- If a position has no clear setup, use "neutral" for thesis_impact
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
                sanitize_public_analysis_text(
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
