from .portfolio_compiler import compile_portfolio_digest


async def compile_digest(
    position_data: list[dict],
    portfolio_risk: dict | None = None,
    macro_context: dict | None = None,
    sector_context: dict | None = None,
) -> str:
    digest = await compile_portfolio_digest(
        position_data,
        "N/A",
        portfolio_risk=portfolio_risk,
        macro_context=macro_context,
        sector_context=sector_context,
    )
    return digest["content"]
