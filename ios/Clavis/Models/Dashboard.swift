import Foundation

struct DashboardResponse: Decodable {
    let digest: Digest?
    let savedDigest: Digest?
    let generatedDigest: Digest?
    let analysisRun: AnalysisRun?
    let positions: [Position]
    let alerts: [Alert]
    let portfolioRiskSnapshot: PortfolioRiskSnapshot?
    let overallScore: Double?
    let overallGrade: String?
    let scoreSource: String?
    let scoreAsOf: Date?
    let scoreVersion: String?
    let message: String?

    enum CodingKeys: String, CodingKey {
        case digest
        case savedDigest = "saved_digest"
        case generatedDigest = "generated_digest"
        case analysisRun = "analysis_run"
        case positions
        case alerts
        case portfolioRiskSnapshot = "portfolio_risk_snapshot"
        case overallScore = "overall_score"
        case overallGrade = "overall_grade"
        case scoreSource = "score_source"
        case scoreAsOf = "score_as_of"
        case scoreVersion = "score_version"
        case message
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        digest = try container.decodeIfPresent(Digest.self, forKey: .digest)
        savedDigest = try container.decodeIfPresent(Digest.self, forKey: .savedDigest)
        generatedDigest = try container.decodeIfPresent(Digest.self, forKey: .generatedDigest)
        analysisRun = try container.decodeIfPresent(AnalysisRun.self, forKey: .analysisRun)
        positions = (try? container.decode([Position].self, forKey: .positions)) ?? []
        alerts = (try? container.decode([Alert].self, forKey: .alerts)) ?? []
        portfolioRiskSnapshot = try container.decodeIfPresent(PortfolioRiskSnapshot.self, forKey: .portfolioRiskSnapshot)
        overallScore = try container.decodeFlexibleDoubleIfPresent(forKey: .overallScore)
        overallGrade = try container.decodeIfPresent(String.self, forKey: .overallGrade)
        scoreSource = try container.decodeIfPresent(String.self, forKey: .scoreSource)
        scoreAsOf = try container.decodeIfPresent(Date.self, forKey: .scoreAsOf)
        scoreVersion = try container.decodeIfPresent(String.self, forKey: .scoreVersion)
        message = try container.decodeIfPresent(String.self, forKey: .message)
    }
}

struct PortfolioRiskSnapshot: Decodable {
    let id: String?
    let userId: String?
    let asOfDate: String?
    let portfolioAllocationRiskScore: Double?
    let confidence: Double?
    let concentrationRisk: Double?
    let clusterRisk: Double?
    let correlationRisk: Double?
    let liquidityMismatch: Double?
    let macroStackRisk: Double?
    let factorBreakdown: [String: Double]?
    let topRiskDrivers: [PortfolioRiskDriver]?
    let dangerClusters: [String]?

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case asOfDate = "as_of_date"
        case portfolioAllocationRiskScore = "portfolio_allocation_risk_score"
        case confidence
        case concentrationRisk = "concentration_risk"
        case clusterRisk = "cluster_risk"
        case correlationRisk = "correlation_risk"
        case liquidityMismatch = "liquidity_mismatch"
        case macroStackRisk = "macro_stack_risk"
        case factorBreakdown = "factor_breakdown"
        case topRiskDrivers = "top_risk_drivers"
        case dangerClusters = "danger_clusters"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decodeIfPresent(String.self, forKey: .id)
        userId = try container.decodeIfPresent(String.self, forKey: .userId)
        asOfDate = try container.decodeIfPresent(String.self, forKey: .asOfDate)
        portfolioAllocationRiskScore = try container.decodeFlexibleDoubleIfPresent(forKey: .portfolioAllocationRiskScore)
        confidence = try container.decodeFlexibleDoubleIfPresent(forKey: .confidence)
        concentrationRisk = try container.decodeFlexibleDoubleIfPresent(forKey: .concentrationRisk)
        clusterRisk = try container.decodeFlexibleDoubleIfPresent(forKey: .clusterRisk)
        correlationRisk = try container.decodeFlexibleDoubleIfPresent(forKey: .correlationRisk)
        liquidityMismatch = try container.decodeFlexibleDoubleIfPresent(forKey: .liquidityMismatch)
        macroStackRisk = try container.decodeFlexibleDoubleIfPresent(forKey: .macroStackRisk)
        factorBreakdown = try container.decodeIfPresent([String: Double].self, forKey: .factorBreakdown)

        if let drivers = try? container.decodeIfPresent([PortfolioRiskDriver].self, forKey: .topRiskDrivers) {
            topRiskDrivers = drivers
        } else {
            topRiskDrivers = []
        }

        let rawClusters = try container.decodeIfPresent([String?].self, forKey: .dangerClusters) ?? []
        dangerClusters = rawClusters.compactMap { $0 }.filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }
}

struct PortfolioRiskDriver: Decodable {
    let type: String?
    let tickers: [String]?
    let clusters: [String]?
    let issues: [String]?

    enum CodingKeys: String, CodingKey {
        case type
        case tickers
        case clusters
        case issues
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decodeIfPresent(String.self, forKey: .type)

        let tickersRaw = try container.decodeIfPresent([String?].self, forKey: .tickers) ?? []
        tickers = tickersRaw.compactMap { $0 }.filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }

        let clustersRaw = try container.decodeIfPresent([String?].self, forKey: .clusters) ?? []
        clusters = clustersRaw.compactMap { $0 }.filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }

        let issuesRaw = try container.decodeIfPresent([String?].self, forKey: .issues) ?? []
        issues = issuesRaw.compactMap { $0 }.filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }

    var displayText: String {
        switch type {
        case "concentration":
            let tickersText = tickers?.prefix(3).joined(separator: ", ") ?? ""
            return tickersText.isEmpty ? "Concentration risk" : "Concentration: \(tickersText)"
        case "cluster":
            let clustersText = clusters?.prefix(3).joined(separator: ", ") ?? ""
            return clustersText.isEmpty ? "Cluster risk" : "Cluster: \(clustersText)"
        case "liquidity":
            let issuesText = issues?.prefix(2).joined(separator: ", ") ?? ""
            return issuesText.isEmpty ? "Liquidity mismatch" : "Liquidity: \(issuesText)"
        case "macro":
            let tickersText = tickers?.prefix(3).joined(separator: ", ") ?? ""
            return tickersText.isEmpty ? "Macro sensitivity" : "Macro: \(tickersText)"
        default:
            return type?.replacingOccurrences(of: "_", with: " ").capitalized ?? "Risk driver"
        }
    }
}
