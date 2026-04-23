from datetime import datetime, timezone

from ..services.minimax import chatcompletion_text
from .analysis_utils import extract_json_object


SYSTEM_PROMPT = """You write the Clavis morning portfolio digest for a self-directed investor.

This is not a research note and not a market essay.
It should feel like a sharp morning briefing that summarizes current portfolio conditions.

Core rules:
- Focus on what changed, what matters, and what is being observed today.
- Only discuss the user's actual holdings.
- Lead with the single most important portfolio takeaway.
- Be concrete and decisive. Avoid analyst fluff, vague finance jargon, and generic macro commentary.
- If only one position truly matters today, say that plainly.
- For positions with no meaningful update, say "no material change" or "nothing urgent".
- Keep the language proportional. Do not overdramatize stable names.
- Start with macro, then the sectors the user actually owns, then position impact, then monitoring notes.

Return strict JSON with this shape:
{
  "content": "markdown digest",
  "overall_summary": "one paragraph, 2-3 sentences max",
  "sections": {
    "overnight_macro": {
      "headlines": ["..."],
      "themes": ["rate_policy", "growth_recession"],
      "brief": "2-3 sentence synthesis"
    },
    "sector_overview": [
      {"sector": "technology", "brief": "...", "headlines": ["..."]}
    ],
    "position_impacts": [
      {"ticker": "...", "macro_relevance": "confirms|challenges|neutral", "impact_summary": "..."}
    ],
    "portfolio_impact": [
      "1-3 bullets on the portfolio-wide takeaway"
    ],
    "what_matters_today": [
      {"catalyst": "...", "impacted_positions": ["..."], "urgency": "high|medium|low"}
    ],
    "watchlist_alerts": [
      "WATCHLIST ticker — major news or risk change"
    ],
    "major_events": ["..."],
    "watch_list": ["..."],
    "monitoring_notes": ["..."]
  }
}

Digest structure for content field:
- Use markdown.
- Start with the heading: **Morning Portfolio Digest**
- Then one line: **Overall Portfolio Grade: X**
- Then a short opening paragraph.
- Then a section titled: **Overnight Macro** (summarize what happened globally)
- Then a section titled: **Sector Overview** (highlight which sectors matter today)
- Then a section titled: **Position Impacts** (how macro affects your holdings)
- Then a section titled: **Portfolio Impact**
- Then a section titled: **What Matters Today** (forward-looking catalysts)
- Then a section titled: **Watchlist Alerts** (only if a watchlist name has real news or risk changes)
- Then a section titled: **Per Position**
- Then a section titled: **Monitoring Notes**
- Keep the whole digest compact enough to scan in under a minute.
- Under **Per Position**, cover each holding in descending order of urgency.
- Each position entry should be 1-3 short sentences.
- **Overnight Macro** should be brief if no significant macro happened; don't pad
- **What Matters Today** should be specific: earnings, data releases, Fed speakers, etc.
- **Watchlist Alerts** should only include watchlist names with real new information, and each line should be plain English.
- **Monitoring Notes** should be a short checklist with ticker-specific observations, not generic portfolio filler.
- If a holding is fine, say "no material change" in plain English and name the ticker.

Voice:
- Plain English
- Specific
- Calm, direct, useful
- More operator than analyst

Avoid phrases like:
- "middle of the road"
- "risk-adjusted profile"
- "defensible but not compelling"
- "autopilot"
- "structurally"
"""


def _grade_change_text(position: dict) -> str:
    previous_grade = position.get("previous_grade")
    current_grade = position.get("grade")
    if not current_grade:
        return "No current grade available"
    if previous_grade and previous_grade != current_grade:
        return f"Grade changed from {previous_grade} to {current_grade}"
    return f"Grade remains {current_grade}"


def _first_sentence(text: str | None) -> str:
    if not text:
        return ""
    sentence = text.strip().split(". ")[0].strip()
    if sentence and not sentence.endswith("."):
        sentence += "."
    return sentence


def _normalize_ticker(value: str | None) -> str:
    return str(value or "").strip().upper()


def _digest_now() -> datetime:
    return datetime.now(timezone.utc)


def _digest_date_context(now: datetime | None = None) -> dict[str, str | bool]:
    current = now or _digest_now()
    day = current.strftime("%A")
    date_text = current.strftime("%B %-d, %Y")
    is_weekend = current.weekday() >= 5
    trading_note = (
        "Weekend digest: markets are closed, so frame observations for the next trading session."
        if is_weekend
        else "Trading day digest: keep observations focused on today."
    )
    return {
        "day": day,
        "date_text": date_text,
        "is_weekend": is_weekend,
        "trading_note": trading_note,
    }


def _is_valid_sector_name(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(normalized and normalized not in {"unknown", "none", "null", "n/a"})


def _clean_text_list(values: list[object] | None) -> list[str]:
    cleaned = []
    for value in values or []:
        text = str(value or "").strip().replace("_", " ")
        if text:
            cleaned.append(" ".join(text.split()))
    return cleaned


def _sanitize_dimension_breakdown(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}

    cleaned: dict[str, str] = {}
    for key, raw_value in value.items():
        text = str(raw_value or "").strip().replace("_", " ")
        if text:
            cleaned[str(key)] = " ".join(text.split())
    return cleaned


def _sanitize_sector_overview(items: list[dict] | None) -> list[dict]:
    sanitized = []
    seen = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        sector = str(item.get("sector") or "").strip().lower()
        if not _is_valid_sector_name(sector) or sector in seen:
            continue
        seen.add(sector)
        sanitized.append(
            {
                "sector": sector,
                "brief": str(
                    item.get("brief") or "No material overnight update."
                ).strip(),
                "headlines": item.get("headlines")
                if isinstance(item.get("headlines"), list)
                else [],
            }
        )
    return sanitized


def _fallback_sector_overview(
    position_data: list[dict], macro_context: dict | None = None
) -> list[dict]:
    sector_map: dict[str, dict] = {}

    for position in position_data:
        sector = str(position.get("sector") or "unknown").strip().lower()
        if not _is_valid_sector_name(sector):
            sector = "other"

        sector_entry = sector_map.setdefault(
            sector,
            {"sector": sector, "brief": "", "headlines": []},
        )

        ticker = _normalize_ticker(position.get("ticker")) or "Unknown"
        summary = _first_sentence(position.get("summary")) or _short_watch_item(
            position
        )
        if summary and len(sector_entry["headlines"]) < 3:
            sector_entry["headlines"].append(f"{ticker}: {summary}")

    if not sector_map and macro_context and macro_context.get("overnight_macro"):
        overnight_macro = macro_context["overnight_macro"]
        return [
            {
                "sector": "portfolio",
                "brief": str(
                    overnight_macro.get("brief")
                    or "No sector-specific overnight update."
                ).strip(),
                "headlines": _clean_text_list(overnight_macro.get("headlines")),
            }
        ]

    fallback_sections: list[dict] = []
    for sector, entry in sorted(sector_map.items()):
        lead_text = (
            entry["headlines"][0].split(": ", 1)[-1]
            if entry["headlines"]
            else "No material overnight change."
        )
        entry["brief"] = (
            f"{len(entry['headlines']) or 1} holding(s) tied to this sector. {lead_text}"
        )
        fallback_sections.append(entry)

    return fallback_sections


def _normalize_position_impacts(
    impacts: list[dict] | None,
    position_data: list[dict],
    macro_context: dict | None = None,
) -> list[dict]:
    impact_map: dict[str, dict] = {}

    for source in (impacts or [], (macro_context or {}).get("position_impacts") or []):
        for item in source:
            if not isinstance(item, dict):
                continue
            ticker = _normalize_ticker(item.get("ticker"))
            if not ticker or ticker in impact_map:
                continue
            impact_map[ticker] = {
                "ticker": ticker,
                "macro_relevance": str(item.get("macro_relevance") or "neutral")
                .strip()
                .lower()
                or "neutral",
                "impact_summary": str(item.get("impact_summary") or "").strip(),
                "watch_items": _clean_text_list(item.get("watch_items")),
                "top_risks": _clean_text_list(item.get("top_risks")),
                "dimension_breakdown": _sanitize_dimension_breakdown(
                    item.get("dimension_breakdown")
                ),
                "urgency": str(item.get("urgency") or "medium").strip().lower()
                or "medium",
            }

    normalized = []
    for position in position_data:
        ticker = _normalize_ticker(position.get("ticker"))
        if not ticker:
            continue
        impact = impact_map.get(ticker)
        if impact and impact.get("impact_summary"):
            impact["watch_items"] = impact.get("watch_items") or _clean_text_list(
                position.get("watch_items")
            )
            impact["top_risks"] = impact.get("top_risks") or _clean_text_list(
                position.get("top_risks")
            )
            impact["dimension_breakdown"] = impact.get(
                "dimension_breakdown"
            ) or _sanitize_dimension_breakdown(position.get("dimension_breakdown"))
            impact["urgency"] = (
                impact.get("urgency")
                or str(position.get("urgency") or "medium").strip().lower()
            )
            normalized.append(impact)
            continue
        normalized.append(
            {
                "ticker": ticker,
                "macro_relevance": "neutral",
                "impact_summary": "No clear overnight macro change for this holding; keep the focus on company-specific developments and any follow-through in its sector.",
                "watch_items": _clean_text_list(position.get("watch_items")),
                "top_risks": _clean_text_list(position.get("top_risks")),
                "dimension_breakdown": _sanitize_dimension_breakdown(
                    position.get("dimension_breakdown")
                ),
                "urgency": str(position.get("urgency") or "medium").strip().lower()
                or "medium",
            }
        )
    return normalized


def _build_portfolio_advice(
    ranked_positions: list[dict],
    position_impacts: list[dict],
) -> list[str]:
    impact_map = {
        _normalize_ticker(item.get("ticker")): item
        for item in position_impacts
        if item.get("ticker")
    }
    advice = []
    for position in ranked_positions:
        ticker = _normalize_ticker(position.get("ticker"))
        if not ticker:
            continue
        impact = impact_map.get(ticker, {})
        summary = str(impact.get("impact_summary") or "").strip()
        relevance = str(impact.get("macro_relevance") or "neutral").strip().lower()

        if relevance in {"confirms", "challenges"} and summary:
            advice.append(f"{ticker}: {summary}")
            continue

        grade = str(position.get("grade") or "").strip().upper()
        previous_grade = str(position.get("previous_grade") or "").strip().upper()
        score = float(position.get("total_score") or 0)

        if (
            grade in {"D", "F"}
            or score < 45
            or (previous_grade and previous_grade != grade)
        ):
            if ticker == "HIMS":
                advice.append(
                    f"{ticker}: risk read remains elevated relative to the rest of the book."
                )
            elif ticker == "GDX":
                advice.append(f"{ticker}: macro sensitivity remains elevated.")
            elif ticker == "AAPL":
                advice.append(
                    f"{ticker}: tech follow-through remains a relevant backdrop."
                )
            elif ticker == "SMCI":
                advice.append(f"{ticker}: volatility remains a major part of the read.")
            elif ticker == "HOOD":
                advice.append(f"{ticker}: rates and risk appetite remain key context.")
            else:
                advice.append(f"{ticker}: risk remains elevated or changed materially.")

    return advice[:5]


def _sanitize_portfolio_advice(items: list[str] | None) -> list[str]:
    cleaned = []
    for item in items or []:
        text = str(item or "").strip()
        if not text:
            continue
        if ":" not in text:
            continue
        prefix, body = text.split(":", 1)
        if not prefix.strip().isupper():
            continue
        body_lower = body.lower()
        if any(
            phrase in body_lower
            for phrase in [
                "no immediate change",
                "no action",
                "focus on",
                "treat the rest",
            ]
        ):
            continue
        cleaned.append(text)
    return cleaned


def _short_watch_item(position: dict) -> str:
    watch_items = position.get("watch_items") or []
    if watch_items:
        item = str(watch_items[0]).strip().replace("_", " ")
        if item:
            return item[:140].rstrip(".")
    top_risks = position.get("top_risks") or []
    if not top_risks:
        return "No urgent change."
    item = str(top_risks[0]).strip()
    if len(item) > 140:
        item = item[:137].rstrip() + "..."
    return item


def _sector_overview_text(sector_context: dict | None) -> str:
    if not sector_context:
        return ""

    sector_overview = sector_context.get("sector_overview") or []
    if not sector_overview:
        return ""

    lines = ["Sector Overview:"]
    for sector in sector_overview[:8]:
        name = sector.get("sector", "unknown")
        brief = str(sector.get("brief") or "No sector brief available.").replace(
            "_", " "
        )
        lines.append(f"- {name}: {brief}")
    return "\n".join(lines)


def _macro_overview_text(macro_context: dict | None) -> str:
    if not macro_context or not macro_context.get("overnight_macro"):
        return ""

    overnight_macro = macro_context["overnight_macro"]
    headlines = overnight_macro.get("headlines") or []
    themes = overnight_macro.get("themes") or []
    lines = ["Overnight Macro:"]
    lines.append(
        f"- Brief: {overnight_macro.get('brief', 'No significant overnight macro.')}"
    )
    lines.append(
        f"- Themes: {', '.join(theme.replace('_', ' ') for theme in themes) if themes else 'none'}"
    )
    lines.append(f"- Headlines: {', '.join(headlines[:3]) if headlines else 'none'}")
    return "\n".join(lines)


def _position_impacts_text(macro_context: dict | None) -> str:
    if not macro_context:
        return ""

    impacts = macro_context.get("position_impacts") or []
    if not impacts:
        return ""

    lines = ["Position Impacts:"]
    for item in impacts[:8]:
        ticker = item.get("ticker", "unknown")
        relevance = item.get("macro_relevance", "neutral")
        summary = item.get("impact_summary") or "No material change."
        lines.append(f"- {ticker} ({relevance}): {summary}")
    return "\n".join(lines)


def _what_matters_text(macro_context: dict | None) -> str:
    if not macro_context:
        return ""

    matters = macro_context.get("what_matters_today") or []
    if not matters:
        return ""

    lines = ["What Matters Today:"]
    for item in matters[:6]:
        catalyst = item.get("catalyst", "")
        impacted_positions = item.get("impacted_positions") or []
        urgency = item.get("urgency", "medium")
        impacted_text = ", ".join(impacted_positions) if impacted_positions else "none"
        lines.append(f"- {catalyst} | impacted: {impacted_text} | urgency: {urgency}")
    return "\n".join(lines)


def _watchlist_alerts_text(watchlist_alerts: list[str] | None) -> str:
    if not watchlist_alerts:
        return ""

    lines = ["Watchlist Alerts:"]
    for item in watchlist_alerts[:6]:
        text = str(item or "").strip().replace("_", " ")
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines) if len(lines) > 1 else ""


def _sanitize_watch_list(items: list[str] | None) -> list[str]:
    cleaned = []
    for item in items or []:
        text = str(item or "").strip().replace("_", " ")
        if not text:
            continue
        cleaned.append(" ".join(text.split()))
    return cleaned


def _sanitize_watchlist_alerts(items: list[str] | None) -> list[str]:
    cleaned = []
    for item in items or []:
        text = str(item or "").strip().replace("_", " ")
        if not text:
            continue
        cleaned.append(" ".join(text.split()))
    return cleaned


def _position_urgency(position: dict) -> tuple[int, float]:
    grade = position.get("grade") or "C"
    priority = {"F": 5, "D": 4, "C": 3, "B": 2, "A": 1}.get(grade, 3)
    changed = (
        1
        if position.get("previous_grade") and position.get("previous_grade") != grade
        else 0
    )
    score = float(position.get("total_score") or 0)
    return (priority + changed, -score)


def _fallback_portfolio_digest(
    position_data: list[dict],
    overall_grade: str,
    watchlist_alerts: list[str] | None = None,
) -> dict:
    ranked_positions = sorted(position_data, key=_position_urgency, reverse=True)
    lead = ranked_positions[0] if ranked_positions else None
    date_context = _digest_date_context()
    fallback_impacts = [
        {
            "ticker": position.get("ticker", "Unknown"),
            "macro_relevance": "neutral",
            "impact_summary": f"No material macro change. {_short_watch_item(position)}",
            "watch_items": _clean_text_list(position.get("watch_items")),
            "top_risks": _clean_text_list(position.get("top_risks")),
            "dimension_breakdown": _sanitize_dimension_breakdown(
                position.get("dimension_breakdown")
            ),
            "urgency": "high"
            if position.get("previous_grade")
            and position.get("previous_grade") != position.get("grade")
            else "medium",
        }
        for position in ranked_positions
    ]
    fallback_advice = _build_portfolio_advice(ranked_positions, fallback_impacts)

    opening = (
        f"Today is {date_context['day']}, {date_context['date_text']}. {date_context['trading_note']} Your portfolio opens the day at grade {overall_grade}."
        if lead
        else f"Today is {date_context['day']}, {date_context['date_text']}. {date_context['trading_note']} Your portfolio opens the day at grade {overall_grade}."
    )

    per_position_lines = []
    for position in ranked_positions:
        ticker = position.get("ticker", "Unknown")
        change_text = _grade_change_text(position)
        summary = (
            _first_sentence(position.get("summary"))
            or "No material new catalyst identified."
        )
        risk_hint = _short_watch_item(position)
        per_position_lines.append(
            f"**{ticker}** — {change_text}. {summary} Primary thing to watch: {risk_hint}"
        )

    monitoring_notes_block = ""
    if fallback_advice:
        monitoring_notes_block = "**Monitoring Notes**\n" + "\n".join(
            f"- {item}" for item in fallback_advice
        )

    watchlist_alerts_block = ""
    fallback_watchlist_alerts = _sanitize_watchlist_alerts(watchlist_alerts)
    if fallback_watchlist_alerts:
        watchlist_alerts_block = "**Watchlist Alerts**\n" + "\n".join(
            f"- {item}" for item in fallback_watchlist_alerts[:4]
        )
    elif ranked_positions:
        alert_lines = []
        for position in ranked_positions[:4]:
            watch_item = _short_watch_item(position)
            if watch_item:
                alert_lines.append(f"- {position['ticker']} — {watch_item}")
        if alert_lines:
            watchlist_alerts_block = "**Watchlist Alerts**\n" + "\n".join(alert_lines)

    sector_overview_lines = _fallback_sector_overview(position_data)
    if sector_overview_lines:
        sector_overview_block = "**Sector Overview**\n" + "\n".join(
            f"- {sector.get('sector', 'unknown')}: {sector.get('brief', '')}"
            for sector in sector_overview_lines
        )
    else:
        sector_overview_block = (
            "**Sector Overview**\n- No sector-specific headlines available."
        )

    position_impacts_block = (
        "**Position Impacts**\n"
        + "\n".join(
            f"- {impact['ticker']}: {impact['impact_summary']}"
            for impact in fallback_impacts
        )
        if fallback_impacts
        else "**Position Impacts**\n- No macro position impacts available."
    )

    content_parts = [
        "**Morning Portfolio Digest**",
        f"**Overall Portfolio Grade: {overall_grade}**",
        opening,
        "**Overnight Macro**\n- No overnight macro developments.",
        sector_overview_block,
        position_impacts_block,
        "**Portfolio Impact**\n- The highest-urgency holding is the main current change driver.",
    ]
    if watchlist_alerts_block:
        content_parts.append(watchlist_alerts_block)
    if monitoring_notes_block:
        content_parts.append(monitoring_notes_block)
    content_parts.extend(
        [
            "**Per Position**\n"
            + "\n\n".join(f"- {line}" for line in per_position_lines),
            f"**Bottom Line**\n{lead['ticker']} remains the highest-urgency holding today."
            if lead
            else "**Bottom Line**\nThe riskiest holding is the main current change driver.",
        ]
    )
    content = "\n\n".join(content_parts)

    return {
        "content": content,
        "overall_summary": opening,
        "sections": {
            "overnight_macro": {
                "headlines": [],
                "themes": [],
                "brief": "No overnight macro developments.",
            },
            "sector_overview": _fallback_sector_overview(position_data),
            "position_impacts": fallback_impacts,
            "portfolio_impact": ["Focus on the highest-urgency holding first."],
            "what_matters_today": [],
            "watchlist_alerts": fallback_watchlist_alerts,
            "major_events": [
                f"{position['ticker']}: {_grade_change_text(position)}"
                for position in ranked_positions[:3]
            ],
            "watch_list": [
                f"{position['ticker']}: {_short_watch_item(position)}"
                for position in ranked_positions[:3]
            ],
            "monitoring_notes": fallback_advice,
            "portfolio_advice": fallback_advice,
        },
    }


async def compile_portfolio_digest(
    position_data: list[dict],
    overall_grade: str,
    portfolio_risk: dict | None = None,
    macro_context: dict | None = None,
    sector_context: dict | None = None,
    watchlist_alerts: list[str] | None = None,
    summary_length: str = "standard",
) -> dict:
    ranked_positions = sorted(position_data, key=_position_urgency, reverse=True)
    date_context = _digest_date_context()

    safety_scores = [
        p.get("safety_score") or p.get("total_score", 50) for p in ranked_positions
    ]
    avg_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 50

    portfolio_risk_info = ""
    if portfolio_risk:
        risk_score = portfolio_risk.get("portfolio_allocation_risk_score", 0)
        concentration = portfolio_risk.get("concentration_risk", 0)
        cluster = portfolio_risk.get("cluster_risk", 0)
        top_drivers = portfolio_risk.get("top_risk_drivers", [])

        portfolio_risk_info = f"""
Portfolio Risk Analysis:
- Portfolio risk score: {risk_score}/100
- Concentration risk: {concentration}/100
- Cluster risk: {cluster}/100
- Top risk drivers: {", ".join([d.get("type", "unknown") for d in top_drivers[:3]]) or "none identified"}
"""

    macro_info = _macro_overview_text(macro_context)
    sector_info = _sector_overview_text(sector_context)
    position_impacts_info = _position_impacts_text(macro_context)
    what_matters_info = _what_matters_text(macro_context)
    watchlist_alerts_info = _watchlist_alerts_text(watchlist_alerts)

    position_summary = "\n".join(
        [
            "\n".join(
                [
                    f"- Ticker: {position['ticker']}",
                    f"  Sector: {position.get('sector', 'unknown')}",
                    f"  Grade: {position.get('grade', 'N/A')}",
                    f"  Safety score: {position.get('safety_score') or position.get('total_score', 'N/A')}",
                    f"  Confidence: {position.get('confidence', 'N/A')}",
                    f"  Structural base: {position.get('structural_base_score', 'N/A')}",
                    f"  Previous grade: {position.get('previous_grade') or 'no change'}",
                    f"  Shares: {position.get('shares', 0)}",
                    f"  Summary: {position.get('summary') or 'No summary available.'}",
                    f"  Watch items: {', '.join(str(item).replace('_', ' ') for item in position.get('watch_items', [])[:3]) or 'none'}",
                    f"  Top risks: {', '.join(position.get('top_risks', [])[:3]) or 'none'}",
                    f"  Dimension breakdown: {position.get('dimension_breakdown') or 'none'}",
                    f"  Risk verifier: {position.get('thesis_verifier', [])}",
                ]
            )
            for position in ranked_positions
        ]
    )

    portfolio_impact_text = ""
    if portfolio_risk:
        portfolio_impact_text = f"""
Portfolio Impact:
- Allocation risk: {portfolio_risk.get("portfolio_allocation_risk_score", 0)}/100
- Concentration risk: {portfolio_risk.get("concentration_risk", 0)}/100
- Cluster risk: {portfolio_risk.get("cluster_risk", 0)}/100
"""

    prompt = f"""Portfolio overall grade: {overall_grade}
Today is {date_context["day"]}, {date_context["date_text"]}.
{date_context["trading_note"]}
Average portfolio safety score: {avg_safety:.1f}/100{portfolio_risk_info}{macro_info}
{sector_info}
{position_impacts_info}
{portfolio_impact_text}
{what_matters_info}
{watchlist_alerts_info}

Important instruction:
- Lead with portfolio safety and what changed.
- Decide which one or two holdings truly matter today.
- If a holding is unchanged or low urgency, keep it brief.
- Make the digest feel like a morning briefing that states current conditions.
- Prefer concrete language over polished market commentary.
- If nothing changed in a name, say so in the simplest possible way.
- Flag any concentration or cluster risks.
- Use the overnight macro section to set context before diving into positions.
- Use the sector overview to show which groups are driving the tape for this portfolio.
- Use "what_matters_today" for forward-looking items (earnings, data releases, Fed speakers).
- Use "watchlist_alerts" only for watchlist names that have real news or risk changes.
- Base watchlist items on the article evidence already captured on each company, not generic market language.
- Preserve structured watch_items, top_risks, and dimension_breakdown data on each position when available.
- Build "watch_list" from each holding's own watch items or news-driven changes first, then fall back to risk notes only if needed.
- Keep watch list items concise and avoid repeating the same ticker or company name more than once.
- Emit the markdown content in this exact order: overall grade, overnight macro, sector overview, position impacts, portfolio impact, what matters today, watchlist alerts, per position, monitoring notes.
- Make "sector_overview" only cover the sectors the user actually owns.
- Make "position_impacts" concise, ticker-specific, and risk-oriented.
- Make "monitoring_notes" a short checklist of factual notes for the holdings that matter most today.
- Do not include holdings that do not have a meaningful change.
- If it is a weekend, frame the observations for the next trading session.
- Mention the day and date in the opening line.

Positions:
{position_summary}
"""

    token_map = {"brief": 800, "standard": 1400, "detailed": 2200}
    max_tokens = token_map.get(summary_length, 1400)

    try:
        result = chatcompletion_text(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
            max_tokens=max_tokens,
        )
        parsed = extract_json_object(result, {})
    except Exception:
        parsed = {}
    fallback = _fallback_portfolio_digest(
        ranked_positions, overall_grade, watchlist_alerts=watchlist_alerts
    )
    sections = parsed.get("sections") or {}
    normalized_sector_overview = _sanitize_sector_overview(
        sections.get("sector_overview")
        or (sector_context.get("sector_overview") if sector_context else None)
        or _fallback_sector_overview(ranked_positions, macro_context=macro_context)
        or fallback["sections"].get("sector_overview")
    )
    normalized_position_impacts = _normalize_position_impacts(
        sections.get("position_impacts"),
        ranked_positions,
        macro_context=macro_context,
    )
    normalized_watch_list = _sanitize_watch_list(
        sections.get("watch_list") or fallback["sections"]["watch_list"]
    )
    normalized_watchlist_alerts = _sanitize_watchlist_alerts(
        sections.get("watchlist_alerts") or watchlist_alerts or []
    )
    monitoring_notes = (
        sections.get("monitoring_notes")
        or sections.get("portfolio_advice")
        or fallback["sections"]["portfolio_advice"]
    )
    if not isinstance(monitoring_notes, list):
        monitoring_notes = fallback["sections"]["portfolio_advice"]
    monitoring_notes = _sanitize_portfolio_advice(monitoring_notes)
    return {
        "content": parsed.get("content")
        or parsed.get("overall_summary")
        or fallback["content"],
        "overall_summary": parsed.get("overall_summary")
        or parsed.get("content")
        or fallback["overall_summary"],
        "sections": {
            "overnight_macro": sections.get("overnight_macro")
            or (macro_context.get("overnight_macro") if macro_context else None)
            or fallback["sections"].get("overnight_macro")
            or {
                "headlines": [],
                "themes": [],
                "brief": "No overnight macro developments.",
            },
            "sector_overview": normalized_sector_overview,
            "position_impacts": normalized_position_impacts,
            "portfolio_impact": sections.get("portfolio_impact")
            or fallback["sections"].get("portfolio_impact")
            or [],
            "major_events": sections.get("major_events")
            or fallback["sections"]["major_events"],
            "what_matters_today": sections.get("what_matters_today")
            or fallback["sections"].get("what_matters_today")
            or [],
            "watchlist_alerts": normalized_watchlist_alerts,
            "watch_list": normalized_watch_list,
            "monitoring_notes": monitoring_notes,
            "portfolio_advice": monitoring_notes,
        },
    }
