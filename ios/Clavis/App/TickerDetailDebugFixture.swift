#if DEBUG
import Foundation
import SwiftUI

struct TickerDetailDebugFixture {
    let detail: TickerDetailResponse
    let methodology: MethodologyResponse
    let priceHistory: [PricePoint]
    let scoreHistory: [ScoreHistoryPoint]

    static let hifiCycle3: TickerDetailDebugFixture = {
        let summary: [String: Any] = [
            "ticker": "NVDA",
            "company_name": "NVIDIA Corporation",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Semiconductors",
            "current_score": 64,
            "current_grade": "BBB",
            "grade_direction": "down",
            "score_delta": -3,
            "grade_rationale": "Downgraded A to BBB overnight. News signal is the primary driver while balance sheet strength remains intact.",
            "source_count": 14,
            "major_event_count": 2,
            "minor_event_count": 5,
            "analysis_run_id": "debug-run-nvda",
            "methodology_version": "v2",
            "analysis_source": "debug_fixture",
            "freshness": [
                "status": "fresh",
                "coverage_state": "full",
                "score_as_of": "2026-05-26T09:10:00Z",
                "analysis_as_of": "2026-05-26T09:10:00Z",
                "price_as_of": "2026-05-26T09:10:00Z",
                "news_as_of": "2026-05-26T08:55:00Z",
                "last_news_refresh_at": "2026-05-26T08:55:00Z",
                "methodology_version": "v2"
            ],
            "latest_price": 478.22,
            "previous_close": 482.76,
            "day_change_amount": -4.54,
            "day_change_pct": -0.94,
            "risk_dimensions": [
                "financial_health": 82,
                "news_sentiment": 38,
                "macro_exposure": 64,
                "sector_exposure": 58,
                "volatility": 76
            ],
            "is_supported": true,
            "outside_universe": false
        ]

        let detailObject: [String: Any] = [
            "ticker": "NVDA",
            "profile": [
                "ticker": "NVDA",
                "company_name": "NVIDIA Corporation",
                "exchange": "NASDAQ",
                "sector": "Technology",
                "industry": "Semiconductors",
                "pe_ratio": 58.4,
                "week_52_high": 505.72,
                "week_52_low": 317.11,
                "market_cap": 1170000000000.0
            ],
            "position": [
                "id": "debug-position-nvda",
                "user_id": "debug-user",
                "ticker": "NVDA",
                "shares": 420,
                "purchase_price": 312.16,
                "archetype": "growth",
                "created_at": "2026-01-15T12:00:00Z",
                "updated_at": "2026-05-26T09:10:00Z",
                "current_price": 478.22,
                "risk_grade": "BBB",
                "total_score": 64,
                "previous_grade": "A",
                "grade_direction": "down",
                "score_delta": -3,
                "summary": "News signal is the primary driver of the downgrade.",
                "analysis_state": "ready",
                "score_source": "ticker_risk_snapshots",
                "score_as_of": "2026-05-26T09:10:00Z",
                "price_as_of": "2026-05-26T09:10:00Z",
                "company_name": "NVIDIA Corporation",
                "shared_analysis": summary
            ],
            "latest_price": [
                "price": 478.22,
                "price_as_of": "2026-05-26T09:10:00Z",
                "previous_close": 482.76,
                "open_price": 481.04,
                "day_high": 484.11,
                "day_low": 475.32,
                "week_52_high": 505.72,
                "week_52_low": 317.11,
                "avg_volume": 47800000,
                "source": "polygon"
            ],
            "source": "debug_fixture",
            "current_score": [
                "id": "debug-risk-score-nvda",
                "position_id": "debug-position-nvda",
                "financial_health": 82,
                "news_sentiment": 38,
                "macro_exposure": 64,
                "sector_exposure": 58,
                "volatility": 76,
                "total_score": 64,
                "grade": "BBB",
                "grade_direction": "down",
                "score_delta": -3,
                "safety_score": 64,
                "confidence": 0.92,
                "score_source": "ticker_risk_snapshots",
                "score_as_of": "2026-05-26T09:10:00Z",
                "score_version": "v2",
                "reasoning": "News pressure outweighs otherwise strong fundamentals.",
                "calculated_at": "2026-05-26T09:10:00Z"
            ],
            "current_analysis": [
                "id": "debug-analysis-nvda",
                "analysis_run_id": "debug-run-nvda",
                "position_id": "debug-position-nvda",
                "ticker": "NVDA",
                "summary": "Export controls and higher sector beta are offsetting best-in-class cash flow.",
                "driver_cards_state": "ready",
                "driver_cards_source": "debug_fixture",
                "driver_cards": [
                    [
                        "id": "driver-1",
                        "rank": 1,
                        "title": "Chip-export curbs widened",
                        "summary": "Reuters · 4h ago. Second-tier Chinese AI labs were added to the entity list. Estimated 3-4% revenue at risk in a severe case.",
                        "strength": "strong",
                        "direction": "negative",
                        "theme": "regulatory_risk",
                        "source_chips": ["News Signal", "Reuters"],
                        "supporting_event_ids": [],
                        "supporting_news_ids": ["news-1"],
                        "supporting_evidence": []
                    ],
                    [
                        "id": "driver-2",
                        "rank": 2,
                        "title": "Sector beta to XLK is rising",
                        "summary": "Rolling 90-day beta climbed from 1.18 to 1.34 since March, raising the sector regime sensitivity.",
                        "strength": "moderate",
                        "direction": "negative",
                        "theme": "macro_risk",
                        "source_chips": ["Sector Exposure"],
                        "supporting_event_ids": [],
                        "supporting_news_ids": [],
                        "supporting_evidence": []
                    ],
                    [
                        "id": "driver-3",
                        "rank": 3,
                        "title": "Cash flow remains best in class",
                        "summary": "TTM free-cash-flow margin is 47% and debt-to-equity remains low, keeping financial health resilient.",
                        "strength": "strong",
                        "direction": "positive",
                        "theme": "liquidity_risk",
                        "source_chips": ["Financial Health"],
                        "supporting_event_ids": [],
                        "supporting_news_ids": [],
                        "supporting_evidence": []
                    ]
                ],
                "major_event_count": 2,
                "minor_event_count": 5,
                "source_count": 14,
                "updated_at": "2026-05-26T09:10:00Z"
            ],
            "recent_news": [
                [
                    "id": "news-1",
                    "title": "US widens AI chip restrictions for additional Chinese labs",
                    "source": "Reuters",
                    "published_at": "2026-05-26T05:00:00Z",
                    "source_tier": 1,
                    "recency_weight": 1.0,
                    "sentiment_score": 28,
                    "impact_tag": "Headwind",
                    "tldr": "Expanded export restrictions could pressure a small but material revenue slice.",
                    "what_it_means": "The rating remains investable, but policy risk is rising.",
                    "key_implications": ["China revenue guidance matters", "Policy risk remains elevated"],
                    "source_url": "https://example.com/reuters-nvda"
                ],
                [
                    "id": "news-2",
                    "title": "Hyperscaler capex plans remain steady ahead of earnings",
                    "source": "Bloomberg",
                    "published_at": "2026-05-25T18:30:00Z",
                    "source_tier": 1,
                    "recency_weight": 0.9,
                    "sentiment_score": 64,
                    "impact_tag": "Tailwind",
                    "tldr": "Cloud buyers are still signaling strong AI infrastructure demand.",
                    "what_it_means": "Demand remains supportive even as policy headlines worsen.",
                    "key_implications": ["Capex remains healthy"],
                    "source_url": "https://example.com/bloomberg-nvda"
                ],
                [
                    "id": "news-3",
                    "title": "Sector volatility ticks higher as semiconductor beta climbs",
                    "source": "CNBC",
                    "published_at": "2026-05-25T11:20:00Z",
                    "source_tier": 2,
                    "recency_weight": 0.8,
                    "sentiment_score": 42,
                    "impact_tag": "Pressure",
                    "tldr": "Short-term sector positioning is amplifying day-to-day moves.",
                    "what_it_means": "Volatility is manageable but no longer benign.",
                    "key_implications": ["Watch implied vol", "Track sector breadth"],
                    "source_url": "https://example.com/cnbc-nvda"
                ]
            ],
            "recent_alerts": [],
            "freshness": [
                "price_as_of": "2026-05-26T09:10:00Z",
                "analysis_as_of": "2026-05-26T09:10:00Z",
                "last_news_refresh_at": "2026-05-26T08:55:00Z",
                "news_refresh_status": "fresh",
                "news_as_of": "2026-05-26T08:55:00Z"
            ],
            "user_context": [
                "is_held": true,
                "holding_ids": ["debug-position-nvda"],
                "is_in_watchlist": true
            ],
            "shared_analysis": [
                "summary": summary,
                "latest_price": 478.22,
                "previous_close": 482.76,
                "open_price": 481.04,
                "day_high": 484.11,
                "day_low": 475.32,
                "week_52_high": 505.72,
                "week_52_low": 317.11,
                "avg_volume": 47800000,
                "pe_ratio": 58.4,
                "market_cap": 1170000000000.0,
                "risk_dimensions": [
                    "financial_health": 82,
                    "news_sentiment": 38,
                    "macro_exposure": 64,
                    "sector_exposure": 58,
                    "volatility": 76
                ],
                "executive_summary": "The downgrade is being driven by news and sector sensitivity rather than by core balance-sheet weakness.",
                "executive_summary_breakdown": [
                    "bull_case": "FCF margin remains near 47%. CoWoS supply is easing and hyperscaler capex stays firm.",
                    "risk_case": "Export-control expansion and a fresh inference benchmark miss could drag News and Sector scores lower.",
                    "what_to_watch": "Q3 earnings on May 22. Focus on China revenue guidance, inference-tier ASPs, and whether the News score posts a second straight decline."
                ],
                "risk_drivers_state": "ready",
                "risk_drivers": [],
                "events": [],
                "key_implications": [],
                "follow_up_notes": [],
                "source_links": []
            ],
            "portfolio_overlay": [
                "position_id": "debug-position-nvda",
                "holding_ids": ["debug-position-nvda"],
                "is_held": true,
                "is_in_watchlist": true,
                "shares": 420,
                "cost_basis": 131107.2,
                "current_price": 478.22,
                "market_value": 200852.4,
                "portfolio_weight": 0.156,
                "risk_contribution_score": 0.171,
                "recent_alert_count": 2,
                "overlay_as_of": "2026-05-26T09:10:00Z"
            ]
        ]

        let methodologyObject: [String: Any] = [
            "ticker": "NVDA",
            "dimensions": [
                "financial_health": [
                    "score": 82,
                    "debt_to_equity": 0.21,
                    "fcf_margin": 0.47,
                    "interest_coverage": 18.2,
                    "current_ratio": 3.4,
                    "revenue_growth_trend": "positive",
                    "profitability_trend": "improving",
                    "as_of_date": "2026-05-25",
                    "data_source": "finnhub",
                    "peer_comparisons": [],
                    "sector_median_comparison": [:]
                ],
                "news_sentiment": [
                    "score": 38,
                    "article_count_7d": 14,
                    "volume_signal": true,
                    "weighted_score": 38,
                    "articles": detailObject["recent_news"] as? [[String: Any]] ?? [],
                    "article_histogram_14d": [
                        ["date": "2026-05-20", "count": 2],
                        ["date": "2026-05-21", "count": 3],
                        ["date": "2026-05-22", "count": 1],
                        ["date": "2026-05-23", "count": 2],
                        ["date": "2026-05-24", "count": 2],
                        ["date": "2026-05-25", "count": 2],
                        ["date": "2026-05-26", "count": 2]
                    ],
                    "sentiment_distribution": [
                        ["bucket": "negative", "count": 6],
                        ["bucket": "neutral", "count": 4],
                        ["bucket": "positive", "count": 4]
                    ]
                ],
                "macro_exposure": [
                    "score": 64,
                    "r_squared": 0.61,
                    "trading_days_used": 252,
                    "limited_data": false,
                    "as_of_date": "2026-05-25",
                    "coefficients": [
                        "spy": 1.12,
                        "vix": -0.41,
                        "dxy": -0.13
                    ],
                    "current_factor_levels": [
                        "spy": 745.64,
                        "vix": 25.43,
                        "dxy": 27.77
                    ],
                    "factor_levels": [
                        "spy": 745.64,
                        "vix": 25.43,
                        "dxy": 27.77
                    ],
                    "narrative": "Macro sensitivity is moderate and primarily routes through broad equity risk appetite."
                ],
                "sector_exposure": [
                    "score": 58,
                    "sector": "Technology",
                    "sector_etf": "XLK",
                    "sector_beta": 1.34,
                    "sector_momentum_30d": 0.072,
                    "sector_breadth": 0.58,
                    "narrative": "Semiconductor leadership remains intact but the group is trading with higher beta.",
                    "peer_comparisons": [],
                    "sector_median_comparison": [:]
                ],
                "volatility": [
                    "score": 76,
                    "realized_vol_30d": 0.29,
                    "realized_vol_90d": 0.24,
                    "vol_ratio": 1.21,
                    "max_drawdown_252d": 0.18,
                    "beta_to_spy": 1.31,
                    "iv_rank": 0.63,
                    "implied_volatility": 0.34,
                    "iv_source": "polygon",
                    "factor_levels": [
                        "realized_vol_30d": 0.29,
                        "realized_vol_90d": 0.24,
                        "implied_vol_30d": 0.34,
                        "iv_rank": 0.63
                    ],
                    "as_of_date": "2026-05-25"
                ]
            ],
            "composite": [
                "score": 64,
                "grade": "BBB",
                "methodology_version": "v2"
            ]
        ]

        let priceHistoryObjects = Self.makePriceHistory()
        let scoreHistoryObjects = Self.makeScoreHistory()

        return TickerDetailDebugFixture(
            detail: Self.decode(TickerDetailResponse.self, from: detailObject),
            methodology: Self.decode(MethodologyResponse.self, from: methodologyObject),
            priceHistory: Self.decode([PricePoint].self, from: priceHistoryObjects),
            scoreHistory: Self.decode([ScoreHistoryPoint].self, from: scoreHistoryObjects)
        )
    }()

    private static func decode<T: Decodable>(_ type: T.Type, from jsonObject: Any) -> T {
        do {
            let data = try JSONSerialization.data(withJSONObject: jsonObject, options: [])
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .custom { decoder in
                let container = try decoder.singleValueContainer()
                let value = try container.decode(String.self)
                if let date = FlexibleDateDecoder.decode(value) {
                    return date
                }
                throw DecodingError.dataCorruptedError(in: container, debugDescription: "Invalid fixture date: \\(value)")
            }
            return try decoder.decode(T.self, from: data)
        } catch {
            fatalError("Failed to decode ticker debug fixture: \\(error)")
        }
    }

    private static func makePriceHistory() -> [[String: Any]] {
        let calendar = Calendar(identifier: .gregorian)
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]

        return (0..<365).compactMap { index in
            guard let date = calendar.date(byAdding: .day, value: -(364 - index), to: Date()) else {
                return nil
            }
            let trend = Double(index) / 364.0
            let seasonal = sin(Double(index) / 18.0) * 7.5
            let step = sin(Double(index) / 6.0) * 2.2
            let price = 392.0 + (trend * 86.22) + seasonal + step
            return [
                "id": "price-\\(index)",
                "ticker": "NVDA",
                "price": (price * 100).rounded() / 100,
                "recorded_at": formatter.string(from: date)
            ]
        }
    }

    private static func makeScoreHistory() -> [[String: Any]] {
        let calendar = Calendar(identifier: .gregorian)
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"

        return (0..<120).compactMap { index in
            guard let date = calendar.date(byAdding: .day, value: -(119 - index), to: Date()) else {
                return nil
            }
            let trend = Double(index) / 119.0
            let news = 52 - (trend * 14) + sin(Double(index) / 7.0) * 4
            let macro = 62 + sin(Double(index) / 10.0) * 3
            let sector = 58 + cos(Double(index) / 11.0) * 2
            let volatility = 72 + sin(Double(index) / 8.5) * 3
            let composite = 68 - (trend * 4) + sin(Double(index) / 14.0) * 2
            return [
                "date": formatter.string(from: date),
                "composite": (composite * 10).rounded() / 10,
                "grade": index > 95 ? "BBB" : "A",
                "financial_health": 82,
                "news_sentiment": (news * 10).rounded() / 10,
                "macro_exposure": (macro * 10).rounded() / 10,
                "sector_exposure": (sector * 10).rounded() / 10,
                "volatility": (volatility * 10).rounded() / 10,
                "methodology_version": "v2"
            ]
        }
    }
}

struct TickerDetailDebugHarness: View {
    let scrollTarget: String?

    var body: some View {
        NavigationStack {
            TickerDetailView(
                ticker: "NVDA",
                debugFixture: .hifiCycle3,
                debugScrollTarget: scrollTarget
            )
        }
    }
}
#endif
