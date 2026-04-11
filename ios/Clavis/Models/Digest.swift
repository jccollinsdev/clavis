import Foundation

struct Digest: Identifiable, Codable {
    let id: String
    let userId: String
    let content: String
    let gradeSummary: [String: String]?
    let overallGrade: String?
    let overallScore: Double?
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
        structuredSections = try? container.decodeIfPresent(DigestSections.self, forKey: .structuredSections)
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        generatedAt = try container.decodeIfPresent(Date.self, forKey: .generatedAt) ?? Date()
    }
}

struct DigestResponse: Codable {
    let digest: Digest?
    let analysisRun: AnalysisRun?
    let overallGrade: String?
    let structuredSections: DigestSections?
    let generatedAt: Date?
    let gradeSummary: [String: String]?
    let message: String

    enum CodingKeys: String, CodingKey {
        case digest
        case analysisRun = "analysis_run"
        case overallGrade = "overall_grade"
        case structuredSections = "structured_sections"
        case generatedAt = "generated_at"
        case gradeSummary = "grade_summary"
        case message
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        digest = try? container.decodeIfPresent(Digest.self, forKey: .digest)
        analysisRun = try? container.decodeIfPresent(AnalysisRun.self, forKey: .analysisRun)
        overallGrade = try container.decodeIfPresent(String.self, forKey: .overallGrade)
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
    let majorEvents: [String]
    let watchList: [String]
    let portfolioAdvice: [String]

    enum CodingKeys: String, CodingKey {
        case majorEvents = "major_events"
        case watchList = "watch_list"
        case portfolioAdvice = "portfolio_advice"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        majorEvents = (try? container.decode([String].self, forKey: .majorEvents)) ?? []
        watchList = (try? container.decode([String].self, forKey: .watchList)) ?? []
        portfolioAdvice = (try? container.decode([String].self, forKey: .portfolioAdvice)) ?? []
    }
}
