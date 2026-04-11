import Foundation

struct Position: Identifiable, Codable, Hashable {
    let id: String
    let userId: String
    let ticker: String
    let shares: Double
    let purchasePrice: Double
    let archetype: Archetype
    let createdAt: Date
    let updatedAt: Date
    var currentPrice: Double?
    var riskGrade: String?
    var totalScore: Double?
    var previousGrade: String?
    var inferredLabels: [String]?
    var summary: String?
    var lastAnalyzedAt: Date?

    var riskState: RiskState? {
        guard let score = totalScore else { return nil }
        return RiskState.from(score: score)
    }

    var riskTrend: RiskTrend? {
        guard let current = riskGrade,
              let previous = previousGrade else { return .stable }
        if gradeValue(current) > gradeValue(previous) {
            return .improving
        } else if gradeValue(current) < gradeValue(previous) {
            return .increasing
        }
        return .stable
    }

    var actionPressure: ActionPressure? {
        guard let score = totalScore else { return nil }
        let trend = riskTrend ?? .stable
        return ActionPressure.from(score: score, trend: trend)
    }

    var currentValue: Double? {
        guard let price = currentPrice else { return nil }
        return shares * price
    }

    var unrealizedPL: Double? {
        guard let current = currentPrice else { return nil }
        return (current - purchasePrice) * shares
    }

    var unrealizedPLPercent: Double? {
        guard let current = currentPrice, purchasePrice > 0 else { return nil }
        return ((current - purchasePrice) / purchasePrice) * 100
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

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case ticker
        case shares
        case purchasePrice = "purchase_price"
        case archetype
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case currentPrice = "current_price"
        case riskGrade = "risk_grade"
        case totalScore = "total_score"
        case previousGrade = "previous_grade"
        case inferredLabels = "inferred_labels"
        case summary
        case lastAnalyzedAt = "last_analyzed_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        userId = try container.decode(String.self, forKey: .userId)
        ticker = try container.decode(String.self, forKey: .ticker)
        shares = try container.decodeFlexibleDouble(forKey: .shares)
        purchasePrice = try container.decodeFlexibleDouble(forKey: .purchasePrice)
        archetype = try container.decode(Archetype.self, forKey: .archetype)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        updatedAt = try container.decode(Date.self, forKey: .updatedAt)
        currentPrice = try container.decodeFlexibleDoubleIfPresent(forKey: .currentPrice)
        riskGrade = try container.decodeIfPresent(String.self, forKey: .riskGrade)
        totalScore = try container.decodeFlexibleDoubleIfPresent(forKey: .totalScore)
        previousGrade = try container.decodeIfPresent(String.self, forKey: .previousGrade)
        inferredLabels = try container.decodeIfPresent([String].self, forKey: .inferredLabels)
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        lastAnalyzedAt = try container.decodeIfPresent(Date.self, forKey: .lastAnalyzedAt)
    }
}

enum Archetype: String, Codable, CaseIterable {
    case growth
    case value
    case cyclical
    case defensive
    case smallCap = "small_cap"

    var displayName: String {
        switch self {
        case .growth: return "Growth"
        case .value: return "Value"
        case .cyclical: return "Cyclical"
        case .defensive: return "Defensive"
        case .smallCap: return "Small Cap"
        }
    }
}
