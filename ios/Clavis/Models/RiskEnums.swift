import Foundation

enum RiskState: String, Codable, CaseIterable {
    case safe
    case stable
    case elevated
    case risky
    case critical

    var displayName: String {
        switch self {
        case .safe: return "Safe"
        case .stable: return "Stable"
        case .elevated: return "Elevated"
        case .risky: return "Risky"
        case .critical: return "Critical"
        }
    }

    static func from(score: Double) -> RiskState {
        if score >= 80 { return .safe }
        if score >= 65 { return .stable }
        if score >= 50 { return .elevated }
        if score >= 35 { return .risky }
        return .critical
    }
}

enum RiskTrend: String, Codable, CaseIterable {
    case worsening
    case stable
    case improving

    var displayName: String {
        switch self {
        case .worsening:  return "Worsening"
        case .stable:     return "Stable"
        case .improving:  return "Improving"
        }
    }

    var arrow: String {
        switch self {
        case .worsening:  return "\u{2193}"
        case .stable:     return "\u{2192}"
        case .improving:  return "\u{2191}"
        }
    }

    var iconName: String {
        switch self {
        case .worsening:  return "arrow.down.right"
        case .stable:     return "minus"
        case .improving:  return "arrow.up.right"
        }
    }
}

enum EvidenceStrength: String, Codable, CaseIterable {
    case thin
    case moderate
    case strong

    var dotCount: Int {
        switch self {
        case .thin:     return 1
        case .moderate: return 2
        case .strong:   return 3
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
        case .medium: return "Review closely \u{2014} check for change"
        case .high: return "Consider reducing exposure / reassessing now"
        }
    }

    static func from(score: Double, trend: RiskTrend) -> ActionPressure {
        if trend == .worsening && score < 65 {
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
    case aaa = "AAA"
    case aa  = "AA"
    case a   = "A"
    case bbb = "BBB"
    case bb  = "BB"
    case b   = "B"
    case ccc = "CCC"
    case cc  = "CC"
    case c   = "C"
    case f   = "F"

    var displayName: String { rawValue }

    var ordinalValue: Int {
        switch self {
        case .aaa: return 10
        case .aa:  return 9
        case .a:   return 8
        case .bbb: return 7
        case .bb:  return 6
        case .b:   return 5
        case .ccc: return 4
        case .cc:  return 3
        case .c:   return 2
        case .f:   return 1
        }
    }

    static func ordinalValue(for grade: String) -> Int {
        Grade(rawValue: grade)?.ordinalValue ?? 0
    }

    var riskState: RiskState {
        RiskState.from(score: midpointScore)
    }

    var midpointScore: Double {
        switch self {
        case .aaa: return 95
        case .aa:  return 85
        case .a:   return 75
        case .bbb: return 65
        case .bb:  return 55
        case .b:   return 45
        case .ccc: return 35
        case .cc:  return 25
        case .c:   return 15
        case .f:   return 5
        }
    }
}

struct RiskDrivers: Codable {
    let financialHealth: Double
    let newsSentiment: Double
    let macroExposure: Double
    let sectorExposure: Double
    let volatility: Double

    var strongestPositive: String {
        let scores: [(String, Double)] = [
            ("Financial Health", financialHealth),
            ("News Sentiment", newsSentiment),
            ("Macro Exposure", macroExposure),
            ("Sector Exposure", sectorExposure),
            ("Volatility", volatility)
        ]
        return scores.max(by: { $0.1 < $1.1 })?.0 ?? "Financial Health"
    }

    var strongestNegative: String {
        let scores: [(String, Double)] = [
            ("Financial Health", financialHealth),
            ("News Sentiment", newsSentiment),
            ("Macro Exposure", macroExposure),
            ("Sector Exposure", sectorExposure),
            ("Volatility", volatility)
        ]
        return scores.min(by: { $0.1 < $1.1 })?.0 ?? "Financial Health"
    }

    enum CodingKeys: String, CodingKey {
        case financialHealth = "financial_health"
        case newsSentiment = "news_sentiment"
        case macroExposure = "macro_exposure"
        case sectorExposure = "sector_exposure"
        case volatility = "volatility"
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
    case critical = "Critical"
    case risky = "Risky"
    case elevated = "Elevated"
    case improving = "Improving"
    case majorEvent = "Major Event"

    func matches(position: Position) -> Bool {
        switch self {
        case .all:
            return true
        case .critical:
            let g = position.resolvedRiskGrade ?? ""
            return g == "F" || g == "C" || g == "CC"
        case .risky:
            let g = position.resolvedRiskGrade ?? ""
            return g == "CCC" || g == "B"
        case .elevated:
            let g = position.resolvedRiskGrade ?? ""
            return g == "BB" || g == "BBB"
        case .improving:
            return gradeImproved(position)
        case .majorEvent:
            return false
        }
    }

    private func gradeImproved(_ position: Position) -> Bool {
        guard let current = position.resolvedRiskGrade,
              let previous = position.previousGrade else { return false }
        return Grade.ordinalValue(for: current) > Grade.ordinalValue(for: previous)
    }
}

enum HoldingSort: String, CaseIterable {
    case grade = "Grade"
    case ticker = "Ticker"
    case value = "Value"

    func sort(_ positions: [Position]) -> [Position] {
        switch self {
        case .grade:
            return positions.sorted { ($0.resolvedTotalScore ?? 50) < ($1.resolvedTotalScore ?? 50) }
        case .ticker:
            return positions.sorted { $0.ticker < $1.ticker }
        case .value:
            return positions.sorted { positionValue($0) > positionValue($1) }
        }
    }

    private func positionValue(_ position: Position) -> Double {
        let price = position.resolvedCurrentPrice ?? position.purchasePrice
        return position.shares * price
    }
}
