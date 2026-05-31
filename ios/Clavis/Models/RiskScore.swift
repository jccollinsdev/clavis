import Foundation

struct RiskScore: Identifiable, Codable {
    let id: String
    let positionId: String

    let financialHealth: Double?
    let newsSentiment: Double?
    let macroExposure: Double?
    let sectorExposure: Double?
    let volatility: Double?

    let positionSizing: Double?
    let volatilityTrend: Double?
    let totalScore: Double?
    let grade: String?
    let gradeDirection: String?
    let scoreDelta: Int?

    let safetyScore: Double?
    let confidence: Double?
    let structuralBaseScore: Double?
    let macroAdjustment: Double?
    let eventAdjustment: Double?
    let factorBreakdown: FactorBreakdown?
    let sourceCount: Int?
    let majorEventCount: Int?
    let minorEventCount: Int?
    let coverageState: String?
    let coverageNote: String?
    let isProvisional: Bool?
    let evidenceStrength: EvidenceStrength?

    let scoreSource: String?
    let scoreAsOf: Date?
    let scoreVersion: String?

    let reasoning: String?
    let calculatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case positionId = "position_id"
        case financialHealth = "financial_health"
        case newsSentiment = "news_sentiment"
        case macroExposure = "macro_exposure"
        case sectorExposure = "sector_exposure"
        case volatility = "volatility"
        case positionSizing = "position_sizing"
        case volatilityTrend = "volatility_trend"
        case totalScore = "total_score"
        case grade
        case gradeDirection = "grade_direction"
        case scoreDelta = "score_delta"
        case safetyScore = "safety_score"
        case confidence
        case structuralBaseScore = "structural_base_score"
        case macroAdjustment = "macro_adjustment"
        case eventAdjustment = "event_adjustment"
        case factorBreakdown = "factor_breakdown"
        case sourceCount = "source_count"
        case majorEventCount = "major_event_count"
        case minorEventCount = "minor_event_count"
        case coverageState = "coverage_state"
        case coverageNote = "coverage_note"
        case isProvisional = "is_provisional"
        case evidenceStrength = "evidence_strength"
        case scoreSource = "score_source"
        case scoreAsOf = "score_as_of"
        case scoreVersion = "score_version"
        case reasoning
        case calculatedAt = "calculated_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        // API returns "id": null for shared/virtual scores — fall back to positionId-based synthetic id
        let rawPositionId = (try? container.decodeIfPresent(String.self, forKey: .positionId)) ?? ""
        positionId = rawPositionId
        id = (try? container.decodeIfPresent(String.self, forKey: .id)) ?? "score:\(rawPositionId)"
        financialHealth = try? container.decodeFlexibleDoubleIfPresent(forKey: .financialHealth)
        newsSentiment = try? container.decodeFlexibleDoubleIfPresent(forKey: .newsSentiment)
        macroExposure = try? container.decodeFlexibleDoubleIfPresent(forKey: .macroExposure)
        sectorExposure = try? container.decodeFlexibleDoubleIfPresent(forKey: .sectorExposure)
        volatility = try? container.decodeFlexibleDoubleIfPresent(forKey: .volatility)
        positionSizing = try? container.decodeFlexibleDoubleIfPresent(forKey: .positionSizing)
        volatilityTrend = try? container.decodeFlexibleDoubleIfPresent(forKey: .volatilityTrend)
        totalScore = try? container.decodeFlexibleDoubleIfPresent(forKey: .totalScore)
        grade = try? container.decodeIfPresent(String.self, forKey: .grade)
        gradeDirection = try? container.decodeIfPresent(String.self, forKey: .gradeDirection)
        scoreDelta = try? container.decodeIfPresent(Int.self, forKey: .scoreDelta)
        safetyScore = try? container.decodeFlexibleDoubleIfPresent(forKey: .safetyScore)
        confidence = try? container.decodeFlexibleDoubleIfPresent(forKey: .confidence)
        structuralBaseScore = try? container.decodeFlexibleDoubleIfPresent(forKey: .structuralBaseScore)
        macroAdjustment = try? container.decodeFlexibleDoubleIfPresent(forKey: .macroAdjustment)
        eventAdjustment = try? container.decodeFlexibleDoubleIfPresent(forKey: .eventAdjustment)
        factorBreakdown = try? container.decode(FactorBreakdown.self, forKey: .factorBreakdown)
        sourceCount = try? container.decodeFlexibleIntIfPresent(forKey: .sourceCount)
        majorEventCount = try? container.decodeFlexibleIntIfPresent(forKey: .majorEventCount)
        minorEventCount = try? container.decodeFlexibleIntIfPresent(forKey: .minorEventCount)
        coverageState = try? container.decodeIfPresent(String.self, forKey: .coverageState)
        coverageNote = try? container.decodeIfPresent(String.self, forKey: .coverageNote)
        isProvisional = try? container.decodeIfPresent(Bool.self, forKey: .isProvisional)
        evidenceStrength = try? container.decodeIfPresent(EvidenceStrength.self, forKey: .evidenceStrength)
        scoreSource = try? container.decodeIfPresent(String.self, forKey: .scoreSource)
        scoreAsOf = try? container.decodeIfPresent(Date.self, forKey: .scoreAsOf)
        scoreVersion = try? container.decodeIfPresent(String.self, forKey: .scoreVersion)
        reasoning = try? container.decodeIfPresent(String.self, forKey: .reasoning)
        calculatedAt = (try? container.decodeIfPresent(Date.self, forKey: .calculatedAt)) ?? Date()
    }

    var displayScore: Double {
        totalScore ?? 0
    }

    var displayGrade: String {
        grade ?? "\u{2014}"
    }

    var confidenceLevel: ConfidenceLevel {
        guard let conf = confidence, isProvisional != true else { return .low }
        if conf >= 0.90 { return .high }
        if conf >= 0.70 { return .medium }
        return .low
    }
}

enum ConfidenceLevel: String {
    case high = "High"
    case medium = "Medium"
    case low = "Low"

    var color: String {
        switch self {
        case .high: return "green"
        case .medium: return "yellow"
        case .low: return "red"
        }
    }
}

struct FactorBreakdown: Codable {
    let marketCapBucket: String?
    let marketCapContribution: Double?
    let assetClassContribution: Double?
    let liquidityScore: Double?
    let volatilityScore: Double?
    let leverageScore: Double?
    let profitabilityScore: Double?
    let macroAdjustment: Double?
    let eventAdjustment: Double?
    let eventCount: Int?
    let aiDimensions: AIDimensions?

    enum CodingKeys: String, CodingKey {
        case marketCapBucket = "market_cap_bucket"
        case marketCapContribution = "market_cap_contribution"
        case assetClassContribution = "asset_class_contribution"
        case liquidityScore = "liquidity_score"
        case volatilityScore = "volatility_score"
        case leverageScore = "leverage_score"
        case profitabilityScore = "profitability_score"
        case macroAdjustment = "macro_adjustment"
        case eventAdjustment = "event_adjustment"
        case eventCount = "event_count"
        case aiDimensions = "ai_dimensions"
    }
}

struct AIDimensions: Codable {
    let financialHealth: Double?
    let newsSentiment: Double?
    let macroExposure: Double?
    let sectorExposure: Double?
    let volatility: Double?
    let positionSizing: Double?
    let volatilityTrend: Double?

    enum CodingKeys: String, CodingKey {
        case financialHealth = "financial_health"
        case newsSentiment = "news_sentiment"
        case macroExposure = "macro_exposure"
        case sectorExposure = "sector_exposure"
        case volatility = "volatility"
        case positionSizing = "position_sizing"
        case volatilityTrend = "volatility_trend"
    }
}
