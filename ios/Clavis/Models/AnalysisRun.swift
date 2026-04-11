import Foundation

struct AnalysisRun: Codable, Identifiable {
    let id: String
    let userId: String
    let status: String
    let triggeredBy: String?
    let errorMessage: String?
    let progress: Int?
    let digestReady: Bool?
    let startedAt: Date?
    let completedAt: Date?
    let overallPortfolioGrade: String?
    let positionsProcessed: Int?
    let eventsProcessed: Int?
    let eventsAnalyzed: Int?
    let currentStage: String?
    let currentStageMessage: String?
    let digestId: String?
    let overallGrade: String?
    let generatedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case status
        case triggeredBy = "triggered_by"
        case errorMessage = "error_message"
        case progress
        case digestReady = "digest_ready"
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case overallPortfolioGrade = "overall_portfolio_grade"
        case positionsProcessed = "positions_processed"
        case eventsProcessed = "events_processed"
        case eventsAnalyzed = "events_analyzed"
        case currentStage = "current_stage"
        case currentStageMessage = "current_stage_message"
        case digestId = "digest_id"
        case overallGrade = "overall_grade"
        case generatedAt = "generated_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        userId = try container.decodeIfPresent(String.self, forKey: .userId) ?? ""
        status = try container.decode(String.self, forKey: .status)
        triggeredBy = try container.decodeIfPresent(String.self, forKey: .triggeredBy)
        errorMessage = try container.decodeIfPresent(String.self, forKey: .errorMessage)
        progress = try container.decodeFlexibleIntIfPresent(forKey: .progress)
        digestReady = try container.decodeIfPresent(Bool.self, forKey: .digestReady)
        startedAt = try container.decodeIfPresent(Date.self, forKey: .startedAt)
        completedAt = try container.decodeIfPresent(Date.self, forKey: .completedAt)
        overallPortfolioGrade = try container.decodeIfPresent(String.self, forKey: .overallPortfolioGrade)
        positionsProcessed = try container.decodeFlexibleIntIfPresent(forKey: .positionsProcessed)
        eventsProcessed = try container.decodeFlexibleIntIfPresent(forKey: .eventsProcessed)
        eventsAnalyzed = try container.decodeFlexibleIntIfPresent(forKey: .eventsAnalyzed)
        currentStage = try container.decodeIfPresent(String.self, forKey: .currentStage)
        currentStageMessage = try container.decodeIfPresent(String.self, forKey: .currentStageMessage)
        digestId = try container.decodeIfPresent(String.self, forKey: .digestId)
        overallGrade = try container.decodeIfPresent(String.self, forKey: .overallGrade)
        generatedAt = try container.decodeIfPresent(Date.self, forKey: .generatedAt)
    }

    var lifecycleStatus: String {
        if status == "completed" || currentStage == "completed" {
            return "completed"
        }
        if status == "failed" || currentStage == "failed" {
            return "failed"
        }
        if status == "partial" || currentStage == "partial" {
            return (digestReady == true || digestId != nil) ? "completed" : "failed"
        }
        switch status {
        case "queued", "running":
            return "running"
        default:
            return "running"
        }
    }

    var isTerminal: Bool {
        lifecycleStatus == "completed" || lifecycleStatus == "failed"
    }

    var displayErrorMessage: String {
        guard let errorMessage, !errorMessage.isEmpty else {
            return "Analysis failed. Please run a fresh review."
        }

        let normalized = errorMessage.lowercased()
        if normalized.contains("sequence item 0") || normalized.contains("nonetype found") {
            return "Analysis failed while compiling portfolio risk signals. Please run a fresh review."
        }

        return errorMessage
    }
}
