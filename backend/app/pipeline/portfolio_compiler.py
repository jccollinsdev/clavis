from ..services.minimax import chatcompletion_text
from .analysis_utils import extract_json_object


SYSTEM_PROMPT = """You write the Clavynx morning portfolio digest for a self-directed investor.

This is not a research note and not a market essay.
It should feel like a sharp morning briefing that replaces the user's manual check-in.

Core rules:
- Focus on what changed, what matters, and what to do today.
- Only discuss the user's actual holdings.
- Lead with the single most important portfolio takeaway.
- Be concrete and decisive. Avoid analyst fluff, vague finance jargon, and generic macro commentary.
- If only one position truly matters today, say that plainly.
- For positions with no meaningful update, say "no material change" or "nothing urgent".
- Make the advice proportional. Do not overdramatize stable names.

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
    "major_events": ["..."],
    "watch_list": ["..."],
    "portfolio_advice": ["..."]
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
- Then a section titled: **Per Position**
- Then a section titled: **Bottom Line**
- Keep the whole digest compact enough to scan in under a minute.
- Under **Per Position**, cover each holding in descending order of urgency.
- Each position entry should be 1-3 short sentences.
- **Overnight Macro** should be brief if no significant macro happened; don't pad
- **What Matters Today** should be specific: earnings, data releases, Fed speakers, etc.

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


def _short_watch_item(position: dict) -> str:
    top_risks = position.get("top_risks") or []
    if not top_risks:
        return "No urgent watch item."
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
        brief = sector.get("brief") or "No sector brief available."
        headlines = sector.get("headlines") or []
        headline_text = ", ".join(headlines[:3]) if headlines else "none"
        lines.append(f"- {name}: {brief}")
        lines.append(f"  Headlines: {headline_text}")
    return "\n".join(lines)


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


def _fallback_portfolio_digest(position_data: list[dict], overall_grade: str) -> dict:
    ranked_positions = sorted(position_data, key=_position_urgency, reverse=True)
    lead = ranked_positions[0] if ranked_positions else None

    opening = (
        f"Your portfolio opens the day at grade {overall_grade}. "
        f"{lead['ticker']} is the only holding that clearly needs attention right now."
        if lead
        else f"Your portfolio opens the day at grade {overall_grade}."
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

    weakest = (
        ranked_positions[0]["ticker"] if ranked_positions else "your riskiest holding"
    )
    stable = [position["ticker"] for position in ranked_positions[1:3]]

    content = "\n\n".join(
        [
            "**Morning Portfolio Digest**",
            f"**Overall Portfolio Grade: {overall_grade}**",
            opening,
            "**What Matters Today**\n"
            + (
                f"- {weakest} is the main source of portfolio risk today.\n"
                + (
                    f"- {', '.join(stable)} do not show a material change this cycle."
                    if stable
                    else "- No other holding requires urgent attention."
                )
            ),
            "**Per Position**\n"
            + "\n\n".join(f"- {line}" for line in per_position_lines),
            "**Portfolio Impact**\n- Focus on the highest-urgency holding first.\n- Treat the rest as monitor names unless their headlines change materially.",
            f"**Bottom Line**\nKeep your focus on {weakest} today. The rest of the portfolio is a monitor, not an action item.",
        ]
    )

    return {
        "content": content,
        "overall_summary": opening,
        "sections": {
            "overnight_macro": {
                "headlines": [],
                "themes": [],
                "brief": "No overnight macro developments.",
            },
            "sector_overview": [],
            "position_impacts": [],
            "portfolio_impact": [
                "Focus on the highest-urgency holding first.",
                "Treat the rest as monitor names unless their headlines change materially.",
            ],
            "what_matters_today": [],
            "major_events": [
                f"{position['ticker']}: {_grade_change_text(position)}"
                for position in ranked_positions[:3]
            ],
            "watch_list": [
                f"{position['ticker']}: {_short_watch_item(position)}"
                for position in ranked_positions[:3]
            ],
            "portfolio_advice": [
                f"Focus your attention on {weakest} first.",
                "Treat unchanged positions as monitoring names, not mandatory action items.",
            ],
        },
    }


async def compile_portfolio_digest(
    position_data: list[dict],
    overall_grade: str,
    portfolio_risk: dict | None = None,
    macro_context: dict | None = None,
    sector_context: dict | None = None,
) -> dict:
    ranked_positions = sorted(position_data, key=_position_urgency, reverse=True)

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

    sector_info = _sector_overview_text(sector_context)

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
                    f"  Top risks: {', '.join(position.get('top_risks', [])[:3]) or 'none'}",
                    f"  Thesis verifier: {position.get('thesis_verifier', [])}",
                ]
            )
            for position in ranked_positions
        ]
    )

    macro_info = ""
    if macro_context and macro_context.get("overnight_macro"):
        om = macro_context["overnight_macro"]
        macro_info = f"""
Overnight Macro:
- Brief: {om.get("brief", "No significant overnight macro.")}
- Themes: {", ".join(om.get("themes", []) or ["none"])}
- Headlines: {", ".join(om.get("headlines", [])[:3] or ["none"])}
"""

    portfolio_impact_text = ""
    if portfolio_risk:
        portfolio_impact_text = f"""
Portfolio Impact:
- Allocation risk: {portfolio_risk.get("portfolio_allocation_risk_score", 0)}/100
- Concentration risk: {portfolio_risk.get("concentration_risk", 0)}/100
- Cluster risk: {portfolio_risk.get("cluster_risk", 0)}/100
"""

    prompt = f"""Portfolio overall grade: {overall_grade}
Average portfolio safety score: {avg_safety:.1f}/100{portfolio_risk_info}{macro_info}
{sector_info}
{portfolio_impact_text}

Important instruction:
- Lead with portfolio safety and what changed.
- Decide which one or two holdings truly matter today.
- If a holding is unchanged or low urgency, keep it brief.
- Make the digest feel like a morning briefing for an investor who wants to know where to focus.
- Prefer concrete language over polished market commentary.
- If nothing changed in a name, say so in the simplest possible way.
- Flag any concentration or cluster risks.
- Use the overnight macro section to set context before diving into positions
- Use the sector overview to show which groups are driving the tape for this portfolio
- Use "what_matters_today" for forward-looking items (earnings, data releases, Fed speakers)

Positions:
{position_summary}
"""

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.15,
        max_tokens=1400,
    )
    parsed = extract_json_object(result, {})
    fallback = _fallback_portfolio_digest(ranked_positions, overall_grade)
    sections = parsed.get("sections") or {}
    return {
        "content": parsed.get("content")
        or parsed.get("overall_summary")
        or fallback["content"],
        "overall_summary": parsed.get("overall_summary")
        or parsed.get("content")
        or fallback["overall_summary"],
        "sections": {
            "overnight_macro": sections.get("overnight_macro")
            or fallback["sections"].get("overnight_macro")
            or {
                "headlines": [],
                "themes": [],
                "brief": "No overnight macro developments.",
            },
            "sector_overview": sections.get("sector_overview")
            or fallback["sections"].get("sector_overview")
            or [],
            "position_impacts": sections.get("position_impacts")
            or fallback["sections"].get("position_impacts")
            or [],
            "portfolio_impact": sections.get("portfolio_impact")
            or fallback["sections"].get("portfolio_impact")
            or [],
            "what_matters_today": sections.get("what_matters_today")
            or fallback["sections"].get("what_matters_today")
            or [],
            "major_events": sections.get("major_events")
            or fallback["sections"]["major_events"],
            "watch_list": sections.get("watch_list")
            or fallback["sections"]["watch_list"],
            "portfolio_advice": sections.get("portfolio_advice")
            or fallback["sections"]["portfolio_advice"],
        },
    }
