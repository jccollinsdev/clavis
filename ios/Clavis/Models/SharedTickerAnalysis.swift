import Foundation

struct SharedTickerFreshness: Codable, Hashable {
    let status: String
    let coverageState: String?
    let coverageNote: String?
    let scoreAsOf: Date?
    let analysisAsOf: Date?
    let priceAsOf: Date?
    let newsAsOf: Date?
    let lastNewsRefreshAt: Date?
    let lastSuccessAt: Date?
    let lastFailureAt: Date?
    let latestAnalysisRunId: String?
    let latestAnalysisStatus: String?
    let latestRefreshJobId: String?
    let latestRefreshStatus: String?
    let analysisRunId: String?
    let methodologyVersion: String?

    enum CodingKeys: String, CodingKey {
        case status
        case coverageState = "coverage_state"
        case coverageNote = "coverage_note"
        case scoreAsOf = "score_as_of"
        case analysisAsOf = "analysis_as_of"
        case priceAsOf = "price_as_of"
        case newsAsOf = "news_as_of"
        case lastNewsRefreshAt = "last_news_refresh_at"
        case lastSuccessAt = "last_success_at"
        case lastFailureAt = "last_failure_at"
        case latestAnalysisRunId = "latest_analysis_run_id"
        case latestAnalysisStatus = "latest_analysis_status"
        case latestRefreshJobId = "latest_refresh_job_id"
        case latestRefreshStatus = "latest_refresh_status"
        case analysisRunId = "analysis_run_id"
        case methodologyVersion = "methodology_version"
    }
}

struct SharedTickerAnalysisSummary: Codable, Hashable {
    let ticker: String
    let companyName: String?
    let exchange: String?
    let sector: String?
    let industry: String?
    let currentScore: Double?
    let currentGrade: String?
    let gradeDirection: String?
    let scoreDelta: Int?
    let gradeRationale: String?
    let sourceCount: Int?
    let majorEventCount: Int?
    let minorEventCount: Int?
    let evidenceStrength: EvidenceStrength?
    let analysisRunId: String?
    let methodologyVersion: String?
    let analysisSource: String?
    let freshness: SharedTickerFreshness

    // v2 enrichment fields (post-2026-05-24 backfill). Backend may omit them on
    // older payloads — always optional, always nil-safe.
    let latestPrice: Double?
    let previousClose: Double?
    let dayChangeAmount: Double?
    let dayChangePct: Double?
    let riskDimensions: SharedRiskDimensions?
    let isSupported: Bool?
    let outsideUniverse: Bool?

    enum CodingKeys: String, CodingKey {
        case ticker
        case companyName = "company_name"
        case exchange
        case sector
        case industry
        case currentScore = "current_score"
        case currentGrade = "current_grade"
        case gradeDirection = "grade_direction"
        case scoreDelta = "score_delta"
        case gradeRationale = "grade_rationale"
        case sourceCount = "source_count"
        case majorEventCount = "major_event_count"
        case minorEventCount = "minor_event_count"
        case evidenceStrength = "evidence_strength"
        case analysisRunId = "analysis_run_id"
        case methodologyVersion = "methodology_version"
        case analysisSource = "analysis_source"
        case freshness
        case latestPrice = "latest_price"
        case previousClose = "previous_close"
        case dayChangeAmount = "day_change_amount"
        case dayChangePct = "day_change_pct"
        case riskDimensions = "risk_dimensions"
        case isSupported = "is_supported"
        case outsideUniverse = "outside_universe"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        ticker = try c.decode(String.self, forKey: .ticker)
        companyName = try c.decodeIfPresent(String.self, forKey: .companyName)
        exchange = try c.decodeIfPresent(String.self, forKey: .exchange)
        sector = try c.decodeIfPresent(String.self, forKey: .sector)
        industry = try c.decodeIfPresent(String.self, forKey: .industry)
        currentScore = try c.decodeFlexibleDoubleIfPresent(forKey: .currentScore)
        currentGrade = try c.decodeIfPresent(String.self, forKey: .currentGrade)
        gradeDirection = try c.decodeIfPresent(String.self, forKey: .gradeDirection)
        scoreDelta = try c.decodeIfPresent(Int.self, forKey: .scoreDelta)
        gradeRationale = try c.decodeIfPresent(String.self, forKey: .gradeRationale)
        sourceCount = try c.decodeIfPresent(Int.self, forKey: .sourceCount)
        majorEventCount = try c.decodeIfPresent(Int.self, forKey: .majorEventCount)
        minorEventCount = try c.decodeIfPresent(Int.self, forKey: .minorEventCount)
        evidenceStrength = try? c.decodeIfPresent(EvidenceStrength.self, forKey: .evidenceStrength)
        analysisRunId = try c.decodeIfPresent(String.self, forKey: .analysisRunId)
        methodologyVersion = try c.decodeIfPresent(String.self, forKey: .methodologyVersion)
        analysisSource = try c.decodeIfPresent(String.self, forKey: .analysisSource)
        freshness = try c.decode(SharedTickerFreshness.self, forKey: .freshness)
        latestPrice = try c.decodeFlexibleDoubleIfPresent(forKey: .latestPrice)
        previousClose = try c.decodeFlexibleDoubleIfPresent(forKey: .previousClose)
        dayChangeAmount = try c.decodeFlexibleDoubleIfPresent(forKey: .dayChangeAmount)
        dayChangePct = try c.decodeFlexibleDoubleIfPresent(forKey: .dayChangePct)
        riskDimensions = try c.decodeIfPresent(SharedRiskDimensions.self, forKey: .riskDimensions)
        isSupported = try c.decodeIfPresent(Bool.self, forKey: .isSupported)
        outsideUniverse = try c.decodeIfPresent(Bool.self, forKey: .outsideUniverse)
    }

    var displayGrade: String {
        currentGrade ?? "—"
    }

    var displayScore: Double? {
        currentScore
    }

    var displaySummary: String? {
        gradeRationale?.sanitizedDisplayText
    }
}

struct SharedRiskDimensions: Codable, Hashable {
    let financialHealth: Double?
    let newsSentiment: Double?
    let macroExposure: Double?
    let sectorExposure: Double?
    let volatility: Double?

    enum CodingKeys: String, CodingKey {
        case financialHealth = "financial_health"
        case newsSentiment = "news_sentiment"
        case macroExposure = "macro_exposure"
        case sectorExposure = "sector_exposure"
        case volatility = "volatility"
    }
}

struct SharedRiskDriver: Codable, Hashable, Identifiable {
    let driverId: String
    let ticker: String
    let rank: Int
    let category: String?
    let title: String
    let summary: String
    let direction: String?
    let strength: EvidenceStrength?
    let sourceChips: [String]
    let evidenceEventIds: [String]
    let updatedAt: Date?
    let provenance: String?

    enum CodingKeys: String, CodingKey {
        case driverId = "driver_id"
        case ticker
        case rank
        case category
        case title
        case summary
        case direction
        case strength
        case sourceChips = "source_chips"
        case evidenceEventIds = "evidence_event_ids"
        case updatedAt = "updated_at"
        case provenance
    }

    var id: String { driverId }
}

struct SharedTickerAnalysisDetail: Codable {
    let summary: SharedTickerAnalysisSummary
    let latestPrice: Double?
    let previousClose: Double?
    let openPrice: Double?
    let dayHigh: Double?
    let dayLow: Double?
    let week52High: Double?
    let week52Low: Double?
    let avgVolume: Double?
    let peRatio: Double?
    let marketCap: Double?
    let riskDimensions: SharedRiskDimensions?
    let executiveSummary: String?
    let executiveSummaryBreakdown: SharedExecutiveSummaryBreakdown?
    let detailedReport: String?
    let methodologyNote: String?
    let riskDrivers: [SharedRiskDriver]
    let riskDriversState: DriverCardsState?
    let riskDriversProvenance: String?
    let events: [EventAnalysis]
    let keyImplications: [String]
    let followUpNotes: [String]
    let sourceLinks: [String]

    enum CodingKeys: String, CodingKey {
        case summary
        case latestPrice = "latest_price"
        case previousClose = "previous_close"
        case openPrice = "open_price"
        case dayHigh = "day_high"
        case dayLow = "day_low"
        case week52High = "week_52_high"
        case week52Low = "week_52_low"
        case avgVolume = "avg_volume"
        case peRatio = "pe_ratio"
        case marketCap = "market_cap"
        case riskDimensions = "risk_dimensions"
        case executiveSummary = "executive_summary"
        case executiveSummaryBreakdown = "executive_summary_breakdown"
        case detailedReport = "detailed_report"
        case methodologyNote = "methodology_note"
        case riskDrivers = "risk_drivers"
        case riskDriversState = "risk_drivers_state"
        case riskDriversProvenance = "risk_drivers_provenance"
        case events
        case keyImplications = "key_implications"
        case followUpNotes = "follow_up_notes"
        case sourceLinks = "source_links"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        summary = try container.decode(SharedTickerAnalysisSummary.self, forKey: .summary)
        latestPrice = try container.decodeFlexibleDoubleIfPresent(forKey: .latestPrice)
        previousClose = try container.decodeFlexibleDoubleIfPresent(forKey: .previousClose)
        openPrice = try container.decodeFlexibleDoubleIfPresent(forKey: .openPrice)
        dayHigh = try container.decodeFlexibleDoubleIfPresent(forKey: .dayHigh)
        dayLow = try container.decodeFlexibleDoubleIfPresent(forKey: .dayLow)
        week52High = try container.decodeFlexibleDoubleIfPresent(forKey: .week52High)
        week52Low = try container.decodeFlexibleDoubleIfPresent(forKey: .week52Low)
        avgVolume = try container.decodeFlexibleDoubleIfPresent(forKey: .avgVolume)
        peRatio = try container.decodeFlexibleDoubleIfPresent(forKey: .peRatio)
        marketCap = try container.decodeFlexibleDoubleIfPresent(forKey: .marketCap)
        riskDimensions = try container.decodeIfPresent(SharedRiskDimensions.self, forKey: .riskDimensions)
        executiveSummary = try container.decodeIfPresent(String.self, forKey: .executiveSummary)
        executiveSummaryBreakdown = try container.decodeIfPresent(SharedExecutiveSummaryBreakdown.self, forKey: .executiveSummaryBreakdown)
        detailedReport = try container.decodeIfPresent(String.self, forKey: .detailedReport)
        methodologyNote = try container.decodeIfPresent(String.self, forKey: .methodologyNote)
        riskDrivers = (try? container.decode([SharedRiskDriver].self, forKey: .riskDrivers)) ?? []
        riskDriversState = try? container.decodeIfPresent(DriverCardsState.self, forKey: .riskDriversState)
        riskDriversProvenance = try container.decodeIfPresent(String.self, forKey: .riskDriversProvenance)
        events = (try? container.decode([EventAnalysis].self, forKey: .events)) ?? []
        keyImplications = (try? container.decode([String].self, forKey: .keyImplications)) ?? []
        followUpNotes = (try? container.decode([String].self, forKey: .followUpNotes)) ?? []
        sourceLinks = (try? container.decode([String].self, forKey: .sourceLinks)) ?? []
    }
}

struct SharedExecutiveSummaryBreakdown: Codable, Hashable {
    let bullCase: String?
    let riskCase: String?
    let whatToWatch: String?

    enum CodingKeys: String, CodingKey {
        case bullCase = "bull_case"
        case riskCase = "risk_case"
        case whatToWatch = "what_to_watch"
    }

    var hasAnyContent: Bool {
        [bullCase, riskCase, whatToWatch].contains { value in
            guard let value else { return false }
            return !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
    }
}

struct PortfolioOverlay: Codable, Hashable {
    let positionId: String?
    let holdingIds: [String]
    let isHeld: Bool
    let isInWatchlist: Bool
    let shares: Double?
    let costBasis: Double?
    let currentPrice: Double?
    let marketValue: Double?
    let portfolioWeight: Double?
    let riskContributionScore: Double?
    let recentAlertCount: Int?
    let latestAlertAt: Date?
    let userNotes: String?
    let overlayAsOf: Date?

    enum CodingKeys: String, CodingKey {
        case positionId = "position_id"
        case holdingIds = "holding_ids"
        case isHeld = "is_held"
        case isInWatchlist = "is_in_watchlist"
        case shares
        case costBasis = "cost_basis"
        case currentPrice = "current_price"
        case marketValue = "market_value"
        case portfolioWeight = "portfolio_weight"
        case riskContributionScore = "risk_contribution_score"
        case recentAlertCount = "recent_alert_count"
        case latestAlertAt = "latest_alert_at"
        case userNotes = "user_notes"
        case overlayAsOf = "overlay_as_of"
    }
}

struct DimensionBreakdown: Codable, Hashable {
    let financialHealth: Double?
    let newsSentiment: Double?
    let macroExposure: Double?
    let sectorExposure: Double?
    let volatility: Double?
    let compositeScore: Double?

    enum CodingKeys: String, CodingKey {
        case financialHealth = "financial_health"
        case newsSentiment = "news_sentiment"
        case macroExposure = "macro_exposure"
        case sectorExposure = "sector_exposure"
        case volatility = "volatility"
        case compositeScore = "composite_score"
    }
}
