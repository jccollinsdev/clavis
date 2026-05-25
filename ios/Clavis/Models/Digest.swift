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

enum MorningReportState {
    case placeholder
    case generating(startedAt: Date?)
    case ready(Digest)
}

struct DigestStatusResponse: Decodable {
    let state: String
    let startedAt: Date?
    let digest: Digest?

    enum CodingKeys: String, CodingKey {
        case state
        case startedAt = "started_at"
        case digest
    }
}

struct DigestHistoryResponse: Codable {
    let digest: Digest?
    let message: String?
}

struct DigestHeader: Codable, Hashable {
    let date: String
    let portfolioGrade: String
    let summaryLine: String

    enum CodingKeys: String, CodingKey {
        case date
        case portfolioGrade = "portfolio_grade"
        case summaryLine = "summary_line"
    }
}

struct DigestSections: Codable {
    let header: DigestHeader?
    let overnightMacro: DigestMacroSection?
    let sectorHeat: [DigestSectorOverviewItem]
    let positions: [DigestPositionImpact]
    let watchlistUpdates: DigestWatchlistUpdates?
    let whatToWatchToday: DigestWhatToWatch?

    enum CodingKeys: String, CodingKey {
        case header
        case overnightMacro = "overnight_macro"
        case sectorHeat = "sector_heat"
        case positions
        case watchlistUpdates = "watchlist_updates"
        case whatToWatchToday = "what_to_watch_today"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        header = try? container.decodeIfPresent(DigestHeader.self, forKey: .header)
        overnightMacro = try? container.decodeIfPresent(DigestMacroSection.self, forKey: .overnightMacro)
        sectorHeat = (try? container.decode([DigestSectorOverviewItem].self, forKey: .sectorHeat)) ?? []
        positions = (try? container.decode([DigestPositionImpact].self, forKey: .positions)) ?? []
        watchlistUpdates = try? container.decodeIfPresent(DigestWatchlistUpdates.self, forKey: .watchlistUpdates)
        whatToWatchToday = try? container.decodeIfPresent(DigestWhatToWatch.self, forKey: .whatToWatchToday)
    }
}

struct DigestWatchlistUpdates: Codable, Hashable {
    let alerts: [String]
    let watchList: [String]

    enum CodingKeys: String, CodingKey {
        case alerts
        case watchList = "watch_list"
    }
}

struct DigestWhatToWatch: Codable, Hashable {
    let catalysts: [DigestWhatMattersItem]
    let monitoring: [String]

    enum CodingKeys: String, CodingKey {
        case catalysts
        case monitoring
    }
}

struct DigestMacroSection: Codable, Hashable {
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
    let dimensionBreakdown: DimensionBreakdown?
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
        dimensionBreakdown = try? container.decodeIfPresent(DimensionBreakdown.self, forKey: .dimensionBreakdown)
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
