import Foundation

struct Digest: Identifiable, Codable {
    let id: String
    let userId: String
    let content: String
    let gradeSummary: [String: String]?
    let overallGrade: String?
    let overallScore: Double?
    let scoreSource: String?
    let scoreAsOf: Date?
    let scoreVersion: String?
    let structuredSections: DigestSections?
    let summary: String?
    let generatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case content
        case gradeSummary = "grade_summary"
        case overallGrade = "overall_grade"
        case overallScore = "overall_score"
        case scoreSource = "score_source"
        case scoreAsOf = "score_as_of"
        case scoreVersion = "score_version"
        case structuredSections = "structured_sections"
        case summary
        case generatedAt = "generated_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decodeIfPresent(String.self, forKey: .id) ?? UUID().uuidString
        userId = try container.decodeIfPresent(String.self, forKey: .userId) ?? ""
        content = try container.decodeIfPresent(String.self, forKey: .content) ?? ""
        gradeSummary = try? container.decodeIfPresent([String: String].self, forKey: .gradeSummary)
        overallGrade = try container.decodeIfPresent(String.self, forKey: .overallGrade)
        overallScore = try container.decodeFlexibleDoubleIfPresent(forKey: .overallScore)
        scoreSource = try container.decodeIfPresent(String.self, forKey: .scoreSource)
        scoreAsOf = try container.decodeIfPresent(Date.self, forKey: .scoreAsOf)
        scoreVersion = try container.decodeIfPresent(String.self, forKey: .scoreVersion)
        structuredSections = try? container.decodeIfPresent(DigestSections.self, forKey: .structuredSections)
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        generatedAt = try container.decodeIfPresent(Date.self, forKey: .generatedAt) ?? Date()
    }
}

struct DigestResponse: Decodable {
    let digest: Digest?
    let savedDigest: Digest?
    let generatedDigest: Digest?
    let analysisRun: AnalysisRun?
    let overallGrade: String?
    let overallScore: Double?
    let scoreSource: String?
    let scoreAsOf: Date?
    let scoreVersion: String?
    let structuredSections: DigestSections?
    let generatedAt: Date?
    let gradeSummary: [String: String]?
    let message: String

    enum CodingKeys: String, CodingKey {
        case digest
        case savedDigest = "saved_digest"
        case generatedDigest = "generated_digest"
        case analysisRun = "analysis_run"
        case overallGrade = "overall_grade"
        case overallScore = "overall_score"
        case scoreSource = "score_source"
        case scoreAsOf = "score_as_of"
        case scoreVersion = "score_version"
        case structuredSections = "structured_sections"
        case generatedAt = "generated_at"
        case gradeSummary = "grade_summary"
        case message
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        digest = try? container.decodeIfPresent(Digest.self, forKey: .digest)
        savedDigest = try? container.decodeIfPresent(Digest.self, forKey: .savedDigest)
        generatedDigest = try? container.decodeIfPresent(Digest.self, forKey: .generatedDigest)
        analysisRun = try? container.decodeIfPresent(AnalysisRun.self, forKey: .analysisRun)
        overallGrade = try container.decodeIfPresent(String.self, forKey: .overallGrade)
        overallScore = try container.decodeFlexibleDoubleIfPresent(forKey: .overallScore)
        scoreSource = try container.decodeIfPresent(String.self, forKey: .scoreSource)
        scoreAsOf = try container.decodeIfPresent(Date.self, forKey: .scoreAsOf)
        scoreVersion = try container.decodeIfPresent(String.self, forKey: .scoreVersion)
        structuredSections = try? container.decodeIfPresent(DigestSections.self, forKey: .structuredSections)
        generatedAt = try container.decodeIfPresent(Date.self, forKey: .generatedAt)
        gradeSummary = try? container.decodeIfPresent([String: String].self, forKey: .gradeSummary)
        message = try container.decodeIfPresent(String.self, forKey: .message) ?? "ok"
    }
}

struct DigestHistoryResponse: Codable {
    let digest: Digest?
    let message: String?
}

struct DigestSections: Codable {
    let digestVersion: Int?
    let overnightMacro: DigestMacroSection?
    let sectorOverview: [DigestSectorOverviewItem]
    let positionImpacts: [DigestPositionImpact]
    let portfolioImpact: [String]
    let whatMattersToday: [DigestWhatMattersItem]
    let watchlistAlerts: [String]
    let majorEvents: [String]
    let watchList: [String]
    let portfolioAdvice: [String]

    enum CodingKeys: String, CodingKey {
        case digestVersion = "digest_version"
        case overnightMacro = "overnight_macro"
        case sectorOverview = "sector_overview"
        case positionImpacts = "position_impacts"
        case portfolioImpact = "portfolio_impact"
        case whatMattersToday = "what_matters_today"
        case watchlistAlerts = "watchlist_alerts"
        case majorEvents = "major_events"
        case watchList = "watch_list"
        case portfolioAdvice = "portfolio_advice"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        digestVersion = try container.decodeIfPresent(Int.self, forKey: .digestVersion)
        overnightMacro = try? container.decodeIfPresent(DigestMacroSection.self, forKey: .overnightMacro)
        sectorOverview = (try? container.decode([DigestSectorOverviewItem].self, forKey: .sectorOverview)) ?? []
        positionImpacts = (try? container.decode([DigestPositionImpact].self, forKey: .positionImpacts)) ?? []
        portfolioImpact = (try? container.decode([String].self, forKey: .portfolioImpact)) ?? []
        whatMattersToday = (try? container.decode([DigestWhatMattersItem].self, forKey: .whatMattersToday)) ?? []
        watchlistAlerts = (try? container.decode([String].self, forKey: .watchlistAlerts)) ?? []
        majorEvents = (try? container.decode([String].self, forKey: .majorEvents)) ?? []
        watchList = (try? container.decode([String].self, forKey: .watchList)) ?? []
        portfolioAdvice = (try? container.decode([String].self, forKey: .portfolioAdvice)) ?? []
    }
}

struct DigestMacroSection: Codable {
    let headlines: [String]
    let themes: [String]
    let brief: String
}

struct DigestSectorOverviewItem: Codable, Hashable, Identifiable {
    let sector: String
    let brief: String
    let headlines: [String]

    var id: String { sector }
}

struct DigestPositionImpact: Codable, Hashable, Identifiable {
    let ticker: String
    let macroRelevance: String
    let impactSummary: String
    let watchItems: [String]
    let topRisks: [String]
    let dimensionBreakdown: [String: String]
    let urgency: String?

    var id: String { ticker }

    enum CodingKeys: String, CodingKey {
        case ticker
        case macroRelevance = "macro_relevance"
        case impactSummary = "impact_summary"
        case watchItems = "watch_items"
        case topRisks = "top_risks"
        case dimensionBreakdown = "dimension_breakdown"
        case urgency
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        ticker = try container.decode(String.self, forKey: .ticker)
        macroRelevance = try container.decodeIfPresent(String.self, forKey: .macroRelevance) ?? "neutral"
        impactSummary = try container.decodeIfPresent(String.self, forKey: .impactSummary) ?? ""
        watchItems = (try? container.decode([String].self, forKey: .watchItems)) ?? []
        topRisks = (try? container.decode([String].self, forKey: .topRisks)) ?? []
        dimensionBreakdown = (try? container.decode([String: String].self, forKey: .dimensionBreakdown)) ?? [:]
        urgency = try container.decodeIfPresent(String.self, forKey: .urgency)
    }
}

struct DigestWhatMattersItem: Codable, Hashable, Identifiable {
    let catalyst: String
    let impactedPositions: [String]
    let urgency: String

    var id: String { "\(catalyst)-\(impactedPositions.joined(separator: ","))-\(urgency)" }

    enum CodingKeys: String, CodingKey {
        case catalyst
        case impactedPositions = "impacted_positions"
        case urgency
    }
}
