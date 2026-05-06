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
    var syncedFromBrokerage: Bool?
    var brokerageAuthorizationId: String?
    var brokerageAccountId: String?
    var brokerageLastSyncedAt: Date?
    var riskGrade: String?
    var totalScore: Double?
    var previousGrade: String?
    var gradeDirection: String?
    var scoreDelta: Int?
    var inferredLabels: [String]?
    var summary: String?
    var lastAnalyzedAt: Date?
    var analysisState: String?
    var coverageState: String?
    var coverageNote: String?
    var evidenceStrength: EvidenceStrength?
    var analysisRunId: String?
    var latestAnalysisRunStatus: String?
    var latestRefreshJobId: String?
    var latestRefreshJobStatus: String?
    var analysisAsOf: Date?
    var scoreSource: String?
    var scoreAsOf: Date?
    var scoreVersion: String?
    var lastNewsRefreshAt: Date?
    var newsRefreshStatus: String?
    var priceAsOf: Date?
    var newsAsOf: Date?
    var source: String?
    var companyName: String?
    var latestEventAnalyses: [EventAnalysis]?
    var analysisStartedAt: Date?
    var sharedAnalysis: SharedTickerAnalysisSummary?
    var portfolioOverlay: PortfolioOverlay?

    var resolvedRiskGrade: String? {
        sharedAnalysis?.currentGrade ?? riskGrade
    }

    var resolvedTotalScore: Double? {
        sharedAnalysis?.currentScore ?? totalScore
    }

    var resolvedSummary: String? {
        sharedAnalysis?.gradeRationale ?? summary
    }

    var resolvedAnalysisState: String? {
        sharedAnalysis?.freshness.status ?? analysisState
    }

    var resolvedCoverageState: String? {
        sharedAnalysis?.freshness.coverageState ?? coverageState
    }

    var resolvedCoverageNote: String? {
        sharedAnalysis?.freshness.coverageNote ?? coverageNote
    }

    var resolvedScoreAsOf: Date? {
        sharedAnalysis?.freshness.scoreAsOf ?? scoreAsOf ?? lastAnalyzedAt
    }

    var resolvedCurrentPrice: Double? {
        portfolioOverlay?.currentPrice ?? currentPrice
    }

    var resolvedCompanyName: String? {
        sharedAnalysis?.companyName ?? companyName
    }

    var riskState: RiskState? {
        guard let score = resolvedTotalScore else { return nil }
        return RiskState.from(score: score)
    }

    var riskTrend: RiskTrend? {
        switch gradeDirection {
        case "up":
            return .improving
        case "down":
            return .worsening
        case "flat":
            return .stable
        default:
            if let current = resolvedRiskGrade, let previous = previousGrade {
                if Grade.ordinalValue(for: current) > Grade.ordinalValue(for: previous) {
                    return .improving
                } else if Grade.ordinalValue(for: current) < Grade.ordinalValue(for: previous) {
                    return .worsening
                }
            }
            return .stable
        }
    }

    var actionPressure: ActionPressure? {
        guard let score = resolvedTotalScore else { return nil }
        let trend = riskTrend ?? .stable
        return ActionPressure.from(score: score, trend: trend)
    }

    var currentValue: Double? {
        guard let price = resolvedCurrentPrice else { return nil }
        return shares * price
    }

    var unrealizedPL: Double? {
        guard let current = resolvedCurrentPrice else { return nil }
        return (current - purchasePrice) * shares
    }

    var unrealizedPLPercent: Double? {
        guard let current = resolvedCurrentPrice, purchasePrice > 0 else { return nil }
        return ((current - purchasePrice) / purchasePrice) * 100
    }

    var isBrokerageSynced: Bool {
        syncedFromBrokerage ?? false
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
        case syncedFromBrokerage = "synced_from_brokerage"
        case brokerageAuthorizationId = "brokerage_authorization_id"
        case brokerageAccountId = "brokerage_account_id"
        case brokerageLastSyncedAt = "brokerage_last_synced_at"
        case riskGrade = "risk_grade"
        case totalScore = "total_score"
        case previousGrade = "previous_grade"
        case gradeDirection = "grade_direction"
        case scoreDelta = "score_delta"
        case inferredLabels = "inferred_labels"
        case summary
        case lastAnalyzedAt = "last_analyzed_at"
        case analysisState = "analysis_state"
        case coverageState = "coverage_state"
        case coverageNote = "coverage_note"
        case evidenceStrength = "evidence_strength"
        case analysisRunId = "analysis_run_id"
        case latestAnalysisRunStatus = "latest_analysis_run_status"
        case latestRefreshJobId = "latest_refresh_job_id"
        case latestRefreshJobStatus = "latest_refresh_job_status"
        case analysisAsOf = "analysis_as_of"
        case scoreSource = "score_source"
        case scoreAsOf = "score_as_of"
        case scoreVersion = "score_version"
        case lastNewsRefreshAt = "last_news_refresh_at"
        case newsRefreshStatus = "news_refresh_status"
        case priceAsOf = "price_as_of"
        case newsAsOf = "news_as_of"
        case source
        case companyName = "company_name"
        case latestEventAnalyses = "latest_event_analyses"
        case analysisStartedAt = "analysis_started_at"
        case sharedAnalysis = "shared_analysis"
        case portfolioOverlay = "portfolio_overlay"
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
        syncedFromBrokerage = try container.decodeIfPresent(Bool.self, forKey: .syncedFromBrokerage)
        brokerageAuthorizationId = try container.decodeIfPresent(String.self, forKey: .brokerageAuthorizationId)
        brokerageAccountId = try container.decodeIfPresent(String.self, forKey: .brokerageAccountId)
        brokerageLastSyncedAt = try container.decodeIfPresent(Date.self, forKey: .brokerageLastSyncedAt)
        riskGrade = try container.decodeIfPresent(String.self, forKey: .riskGrade)
        totalScore = try container.decodeFlexibleDoubleIfPresent(forKey: .totalScore)
        previousGrade = try container.decodeIfPresent(String.self, forKey: .previousGrade)
        gradeDirection = try container.decodeIfPresent(String.self, forKey: .gradeDirection)
        scoreDelta = try container.decodeIfPresent(Int.self, forKey: .scoreDelta)
        inferredLabels = try container.decodeIfPresent([String].self, forKey: .inferredLabels)
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        lastAnalyzedAt = try container.decodeIfPresent(Date.self, forKey: .lastAnalyzedAt)
        analysisState = try container.decodeIfPresent(String.self, forKey: .analysisState)
        coverageState = try container.decodeIfPresent(String.self, forKey: .coverageState)
        coverageNote = try container.decodeIfPresent(String.self, forKey: .coverageNote)
        evidenceStrength = try? container.decodeIfPresent(EvidenceStrength.self, forKey: .evidenceStrength)
        analysisRunId = try container.decodeIfPresent(String.self, forKey: .analysisRunId)
        latestAnalysisRunStatus = try container.decodeIfPresent(String.self, forKey: .latestAnalysisRunStatus)
        latestRefreshJobId = try container.decodeIfPresent(String.self, forKey: .latestRefreshJobId)
        latestRefreshJobStatus = try container.decodeIfPresent(String.self, forKey: .latestRefreshJobStatus)
        analysisAsOf = try container.decodeIfPresent(Date.self, forKey: .analysisAsOf)
        scoreSource = try container.decodeIfPresent(String.self, forKey: .scoreSource)
        scoreAsOf = try container.decodeIfPresent(Date.self, forKey: .scoreAsOf)
        scoreVersion = try container.decodeIfPresent(String.self, forKey: .scoreVersion)
        lastNewsRefreshAt = try container.decodeIfPresent(Date.self, forKey: .lastNewsRefreshAt)
        newsRefreshStatus = try container.decodeIfPresent(String.self, forKey: .newsRefreshStatus)
        priceAsOf = try container.decodeIfPresent(Date.self, forKey: .priceAsOf)
        newsAsOf = try container.decodeIfPresent(Date.self, forKey: .newsAsOf)
        source = try container.decodeIfPresent(String.self, forKey: .source)
        companyName = try container.decodeIfPresent(String.self, forKey: .companyName)
        latestEventAnalyses = try container.decodeIfPresent([EventAnalysis].self, forKey: .latestEventAnalyses)
        analysisStartedAt = try container.decodeIfPresent(Date.self, forKey: .analysisStartedAt)
        sharedAnalysis = try container.decodeIfPresent(SharedTickerAnalysisSummary.self, forKey: .sharedAnalysis)
        portfolioOverlay = try container.decodeIfPresent(PortfolioOverlay.self, forKey: .portfolioOverlay)
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
