import Foundation

private func parseEventDate(_ raw: String?) -> Date? {
    guard let raw else { return nil }
    let iso8601Fractional = ISO8601DateFormatter()
    iso8601Fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    if let date = iso8601Fractional.date(from: raw) {
        return date
    }

    let iso8601Basic = ISO8601DateFormatter()
    iso8601Basic.formatOptions = [.withInternetDateTime]
    if let date = iso8601Basic.date(from: raw) {
        return date
    }

    let postgresFractional = DateFormatter()
    postgresFractional.locale = Locale(identifier: "en_US_POSIX")
    postgresFractional.dateFormat = "yyyy-MM-dd HH:mm:ss.SSSSSSXXXXX"
    if let date = postgresFractional.date(from: raw) {
        return date
    }

    let postgresBasic = DateFormatter()
    postgresBasic.locale = Locale(identifier: "en_US_POSIX")
    postgresBasic.dateFormat = "yyyy-MM-dd HH:mm:ssXXXXX"
    return postgresBasic.date(from: raw)
}

struct PositionAnalysis: Codable {
    let id: String?
    let analysisRunId: String?
    let positionId: String?
    let ticker: String?
    let inferredLabels: [String]?
    let summary: String?
    let longReport: String?
    let methodology: String?
    let topRisks: [String]?
    let watchItems: [String]?
    let topNews: [String]?
    let majorEventCount: Int?
    let minorEventCount: Int?
    let status: String?
    let progressMessage: String?
    let sourceCount: Int?
    let updatedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case analysisRunId = "analysis_run_id"
        case positionId = "position_id"
        case ticker
        case inferredLabels = "inferred_labels"
        case summary
        case longReport = "long_report"
        case methodology
        case topRisks = "top_risks"
        case watchItems = "watch_items"
        case topNews = "top_news"
        case majorEventCount = "major_event_count"
        case minorEventCount = "minor_event_count"
        case status
        case progressMessage = "progress_message"
        case sourceCount = "source_count"
        case updatedAt = "updated_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decodeIfPresent(String.self, forKey: .id)
        analysisRunId = try container.decodeIfPresent(String.self, forKey: .analysisRunId)
        positionId = try container.decodeIfPresent(String.self, forKey: .positionId)
        ticker = try container.decodeIfPresent(String.self, forKey: .ticker)
        inferredLabels = try container.decodeIfPresent([String].self, forKey: .inferredLabels)
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        longReport = try container.decodeIfPresent(String.self, forKey: .longReport)
        methodology = try container.decodeIfPresent(String.self, forKey: .methodology)
        topRisks = try container.decodeIfPresent([String].self, forKey: .topRisks)
        watchItems = try container.decodeIfPresent([String].self, forKey: .watchItems)
        topNews = try container.decodeIfPresent([String].self, forKey: .topNews)
        majorEventCount = try container.decodeFlexibleIntIfPresent(forKey: .majorEventCount)
        minorEventCount = try container.decodeFlexibleIntIfPresent(forKey: .minorEventCount)
        status = try container.decodeIfPresent(String.self, forKey: .status)
        progressMessage = try container.decodeIfPresent(String.self, forKey: .progressMessage)
        sourceCount = try container.decodeFlexibleIntIfPresent(forKey: .sourceCount)
        updatedAt = try container.decodeIfPresent(Date.self, forKey: .updatedAt)
    }
}

struct EventAnalysis: Identifiable, Codable {
    let id: String
    let analysisRunId: String?
    let positionId: String?
    let eventHash: String?
    let title: String
    let summary: String?
    let source: String?
    let sourceURL: String?
    let publishedAt: Date?
    let eventType: String?
    let significance: String?
    let analysisSource: String?
    let longAnalysis: String?
    let confidence: Double?
    let impactHorizon: String?
    let riskDirection: String?
    let scenarioSummary: String?
    let keyImplications: [String]?
    let recommendedFollowups: [String]?

    enum CodingKeys: String, CodingKey {
        case id
        case analysisRunId = "analysis_run_id"
        case positionId = "position_id"
        case eventHash = "event_hash"
        case title
        case summary
        case source
        case sourceURL = "source_url"
        case publishedAt = "published_at"
        case eventType = "event_type"
        case significance
        case analysisSource = "analysis_source"
        case longAnalysis = "long_analysis"
        case confidence
        case impactHorizon = "impact_horizon"
        case riskDirection = "risk_direction"
        case scenarioSummary = "scenario_summary"
        case keyImplications = "key_implications"
        case recommendedFollowups = "recommended_followups"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        analysisRunId = try container.decodeIfPresent(String.self, forKey: .analysisRunId)
        positionId = try container.decodeIfPresent(String.self, forKey: .positionId)
        eventHash = try container.decodeIfPresent(String.self, forKey: .eventHash)
        title = try container.decodeIfPresent(String.self, forKey: .title) ?? ""
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        source = try container.decodeIfPresent(String.self, forKey: .source)
        sourceURL = try container.decodeIfPresent(String.self, forKey: .sourceURL)
        if let publishedAtString = try container.decodeIfPresent(String.self, forKey: .publishedAt) {
            publishedAt = parseEventDate(publishedAtString)
        } else {
            publishedAt = try container.decodeIfPresent(Date.self, forKey: .publishedAt)
        }
        eventType = try container.decodeIfPresent(String.self, forKey: .eventType)
        significance = try container.decodeIfPresent(String.self, forKey: .significance)
        analysisSource = try container.decodeIfPresent(String.self, forKey: .analysisSource)
        longAnalysis = try container.decodeIfPresent(String.self, forKey: .longAnalysis)
        confidence = try container.decodeFlexibleDoubleIfPresent(forKey: .confidence)
        impactHorizon = try container.decodeIfPresent(String.self, forKey: .impactHorizon)
        riskDirection = try container.decodeIfPresent(String.self, forKey: .riskDirection)
        scenarioSummary = try container.decodeIfPresent(String.self, forKey: .scenarioSummary)
        keyImplications = try container.decodeFlexibleStringArrayIfPresent(forKey: .keyImplications)
        recommendedFollowups = try container.decodeFlexibleStringArrayIfPresent(forKey: .recommendedFollowups)
    }
}
