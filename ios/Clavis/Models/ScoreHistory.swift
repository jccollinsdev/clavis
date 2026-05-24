import Foundation

struct ScoreHistoryPoint: Codable, Identifiable {
    let date: String
    let composite: Double
    let grade: String?
    let financialHealth: Double?
    let newsSentiment: Double?
    let macroExposure: Double?
    let sectorExposure: Double?
    let volatility: Double?
    let methodologyVersion: String?

    var id: String { date }

    enum CodingKeys: String, CodingKey {
        case date
        case composite
        case grade
        case financialHealth = "financial_health"
        case newsSentiment = "news_sentiment"
        case macroExposure = "macro_exposure"
        case sectorExposure = "sector_exposure"
        case volatility
        case methodologyVersion = "methodology_version"
    }
}

struct ScoreHistoryResponse: Codable {
    let ticker: String
    let points: [ScoreHistoryPoint]
    let historyCount: Int
    let daysRequested: Int

    enum CodingKeys: String, CodingKey {
        case ticker
        case points
        case historyCount = "history_count"
        case daysRequested = "days_requested"
    }
}

/// Bridges the wire format (`ScoreHistoryPoint` with string date) to the
/// chart's domain model (`ScoreSnapshot` with `Date`). Drops points whose
/// date string can't be parsed rather than silently mis-aligning the chart.
enum ScoreHistoryConversion {
    private static let isoFormatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withFullDate]
        return f
    }()

    static func snapshots(from points: [ScoreHistoryPoint]) -> [ScoreSnapshot] {
        points.compactMap { point in
            guard let date = isoFormatter.date(from: point.date) else { return nil }
            return ScoreSnapshot(
                id: point.date,
                date: date,
                composite: point.composite,
                financialHealth: point.financialHealth,
                newsSentiment: point.newsSentiment,
                macroExposure: point.macroExposure,
                sectorExposure: point.sectorExposure,
                volatility: point.volatility
            )
        }
    }
}

/// Minimal Today envelope decode. Fields not strictly needed by the UI today
/// can be added later as the iOS views consume them.
struct TodayResponse: Codable {
    struct Portfolio: Codable {
        let value: Double?
        let dayChangeAmount: Double?
        let dayChangePct: Double?
        let compositeScore: Double?
        let grade: String?
        let positionCount: Int?
        let generatedAt: String?

        enum CodingKeys: String, CodingKey {
            case value
            case dayChangeAmount = "day_change_amount"
            case dayChangePct = "day_change_pct"
            case compositeScore = "composite_score"
            case grade
            case positionCount = "position_count"
            case generatedAt = "generated_at"
        }
    }

    struct Dimension: Codable, Identifiable {
        let code: String
        let name: String
        let score: Double?
        let coverage: Int

        var id: String { code }
    }

    struct SectorCard: Codable, Identifiable {
        let sector: String
        let etf: String?
        let portfolioWeightPct: Double
        let etfDayChangePct: Double?

        var id: String { sector }

        enum CodingKeys: String, CodingKey {
            case sector
            case etf
            case portfolioWeightPct = "portfolio_weight_pct"
            case etfDayChangePct = "etf_day_change_pct"
        }
    }

    struct AttentionAlert: Codable, Identifiable {
        let id: String
        let category: String?
        let severity: String?
        let ticker: String?
        let title: String?
        let createdAt: String?

        enum CodingKeys: String, CodingKey {
            case id, category, severity, ticker, title
            case createdAt = "created_at"
        }
    }

    struct Attention: Codable {
        let unreadCount: Int
        let totalCount: Int
        let alerts: [AttentionAlert]

        enum CodingKeys: String, CodingKey {
            case unreadCount = "unread_count"
            case totalCount = "total_count"
            case alerts
        }
    }

    struct Report: Codable {
        let digestId: String?
        let preview: String?
        let status: String

        enum CodingKeys: String, CodingKey {
            case digestId = "digest_id"
            case preview
            case status
        }
    }

    let portfolio: Portfolio
    let dimensions: [Dimension]
    let sectorExposure: [SectorCard]
    let attention: Attention
    let report: Report

    enum CodingKeys: String, CodingKey {
        case portfolio
        case dimensions
        case sectorExposure = "sector_exposure"
        case attention
        case report
    }
}
