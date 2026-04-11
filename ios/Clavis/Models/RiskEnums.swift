import Foundation

enum RiskState: String, Codable, CaseIterable {
    case safe
    case stable
    case watch
    case elevated
    case highRisk = "high_risk"

    var displayName: String {
        switch self {
        case .safe: return "Safe"
        case .stable: return "Stable"
        case .watch: return "Watch"
        case .elevated: return "Elevated"
        case .highRisk: return "High Risk"
        }
    }

    static func from(score: Double) -> RiskState {
        switch score {
        case 75...100: return .safe
        case 55..<75:  return .stable
        case 35..<55:  return .watch
        case 15..<35:  return .elevated
        default:       return .highRisk
        }
    }
}

enum RiskTrend: String, Codable, CaseIterable {
    case increasing
    case stable
    case improving

    var displayName: String {
        switch self {
        case .increasing: return "Increasing"
        case .stable: return "Stable"
        case .improving: return "Improving"
        }
    }

    var iconName: String {
        switch self {
        case .increasing: return "arrow.up.right"
        case .stable: return "minus"
        case .improving: return "arrow.down.right"
        }
    }
}

enum ActionPressure: String, Codable, CaseIterable {
    case low
    case medium
    case high

    var displayName: String {
        switch self {
        case .low: return "Low"
        case .medium: return "Medium"
        case .high: return "High"
        }
    }

    var description: String {
        switch self {
        case .low: return "No action needed"
        case .medium: return "Review closely / monitor for change"
        case .high: return "Consider reducing exposure / reassessing now"
        }
    }

    static func from(score: Double, trend: RiskTrend) -> ActionPressure {
        if trend == .increasing && score < 65 {
            return .high
        }
        switch score {
        case 65...100: return .low
        case 35..<65: return .medium
        default: return .high
        }
    }
}

enum Grade: String, Codable, CaseIterable {
    case a = "A"
    case b = "B"
    case c = "C"
    case d = "D"
    case f = "F"

    var displayName: String { rawValue }

    static func from(score: Double) -> Grade {
        switch score {
        case 75...100: return .a
        case 55..<75:  return .b
        case 35..<55:  return .c
        case 15..<35:  return .d
        default:       return .f
        }
    }

    var riskState: RiskState {
        RiskState.from(score: gradeToScore)
    }

    private var gradeToScore: Double {
        switch self {
        case .a: return 90
        case .b: return 72.5
        case .c: return 57.5
        case .d: return 42.5
        case .f: return 17
        }
    }
}

struct RiskDrivers: Codable {
    let newsSentiment: Double
    let macroExposure: Double
    let positionSizing: Double
    let volatilityTrend: Double
    let marketIntegrity: Double

    var strongestPositive: String {
        let scores: [(String, Double)] = [
            ("News Sentiment", newsSentiment),
            ("Macro Exposure", macroExposure),
            ("Position Sizing", positionSizing),
            ("Volatility Trend", volatilityTrend),
            ("Market Integrity", marketIntegrity)
        ]
        return scores.max(by: { $0.1 < $1.1 })?.0 ?? "News Sentiment"
    }

    var strongestNegative: String {
        let scores: [(String, Double)] = [
            ("News Sentiment", newsSentiment),
            ("Macro Exposure", macroExposure),
            ("Position Sizing", positionSizing),
            ("Volatility Trend", volatilityTrend),
            ("Market Integrity", marketIntegrity)
        ]
        return scores.min(by: { $0.1 < $1.1 })?.0 ?? "Market Integrity"
    }

    enum CodingKeys: String, CodingKey {
        case newsSentiment = "news_sentiment"
        case macroExposure = "macro_exposure"
        case positionSizing = "position_sizing"
        case volatilityTrend = "volatility_trend"
        case marketIntegrity = "market_integrity"
    }
}

struct RecentDevelopment: Codable, Identifiable {
    let id: String
    let title: String
    let severity: String
    let impact: String
    let timestamp: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case severity
        case impact
        case timestamp
    }
}

enum HoldingFilter: String, CaseIterable {
    case all = "All"
    case highRisk = "High Risk"
    case elevated = "Elevated"
    case watch = "Watch"
    case improving = "Improving"
    case majorEvent = "Major Event"

    func matches(position: Position) -> Bool {
        switch self {
        case .all:
            return true
        case .highRisk:
            return position.riskGrade == "D" || position.riskGrade == "F"
        case .elevated:
            return position.riskGrade == "D"
        case .watch:
            return position.riskGrade == "C"
        case .improving:
            return gradeImproved(position)
        case .majorEvent:
            return false
        }
    }

    private func gradeImproved(_ position: Position) -> Bool {
        guard let current = position.riskGrade,
              let previous = position.previousGrade else { return false }
        return gradeValue(current) > gradeValue(previous)
    }

    private func gradeValue(_ grade: String) -> Int {
        switch grade {
        case "A": return 5
        case "B": return 4
        case "C": return 3
        case "D": return 2
        case "F": return 1
        default: return 0
        }
    }
}

enum HoldingSort: String, CaseIterable {
    case grade = "Grade"
    case ticker = "Ticker"
    case value = "Value"

    func sort(_ positions: [Position]) -> [Position] {
        switch self {
        case .grade:
            return positions.sorted { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
        case .ticker:
            return positions.sorted { $0.ticker < $1.ticker }
        case .value:
            return positions.sorted { positionValue($0) > positionValue($1) }
        }
    }

    private func positionValue(_ position: Position) -> Double {
        let price = position.currentPrice ?? position.purchasePrice
        return position.shares * price
    }
}
