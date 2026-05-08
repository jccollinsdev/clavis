import Foundation
import SwiftUI

@MainActor
class DashboardViewModel: ObservableObject {
    @Published private(set) var dashboard: DashboardResponse?
    @Published private(set) var schedulerStatus: SchedulerStatusResponse?
    @Published var isLoading = false
    @Published var isRefreshingAnalysis = false
    @Published var errorMessage: String?
    @Published var activeRun: AnalysisRun?

    private let api = APIService.shared

    var holdings: [Position] { dashboard?.positions ?? [] }
    var todayDigest: Digest? {
        dashboard?.digest ?? dashboard?.generatedDigest ?? dashboard?.savedDigest
    }
    var alerts: [Alert] { dashboard?.alerts ?? [] }
    var portfolioRiskSnapshot: PortfolioRiskSnapshot? { dashboard?.portfolioRiskSnapshot }

    var portfolioGrade: String {
        resolvedPortfolioGrade ?? "—"
    }

    var portfolioScore: Double? {
        resolvedPortfolioScore
    }

    var portfolioScoreText: String {
        portfolioScore.map { "\(Int($0.rounded()))" } ?? "Calculating..."
    }

    var portfolioRiskState: RiskState? {
        guard let portfolioScore else { return nil }
        return RiskState.from(score: portfolioScore)
    }

    var portfolioRiskTrend: RiskTrend {
        let improving = improvingCount
        let worseningCount = deterioratingCount
        if worseningCount > improving { return .worsening }
        if improving > worseningCount { return .improving }
        return .stable
    }

    var portfolioEvidenceStrength: EvidenceStrength? {
        dashboard?.evidenceStrength
    }

    var portfolioActionPressure: ActionPressure? {
        guard let portfolioScore else { return nil }
        return ActionPressure.from(score: portfolioScore, trend: portfolioRiskTrend)
    }

    var portfolioSummary: String {
        guard let state = portfolioRiskState?.displayName.lowercased() else {
            return "Score unavailable, analysis pending."
        }
        if let driver = topRiskDriverSummary, portfolioRiskTrend == .worsening {
            return "Portfolio risk is \(state), driven mainly by \(driver)."
        }
        if portfolioRiskTrend == .improving {
            return "Portfolio risk is \(state), with some positions improving."
        }
        return "Portfolio risk is \(state)."
    }

    var improvingCount: Int {
        holdings.filter { position in
            guard let current = position.resolvedRiskGrade,
                  let previous = position.previousGrade else {
                return false
            }
            return Grade.ordinalValue(for: current) > Grade.ordinalValue(for: previous)
        }.count
    }

    var deterioratingCount: Int {
        holdings.filter { position in
            guard let current = position.resolvedRiskGrade,
                  let previous = position.previousGrade else {
                return false
            }
            return Grade.ordinalValue(for: current) < Grade.ordinalValue(for: previous)
        }.count
    }

    var majorEventCount: Int {
        return (todayDigest?.structuredSections?.positions ?? []).count
    }

    var lastUpdatedAt: Date? {
        if let generatedAt = todayDigest?.generatedAt {
            return generatedAt
        }
        return holdings.compactMap(\.resolvedScoreAsOf).max()
    }

    var analysisStatusText: String? {
        guard let run = activeRun else { return nil }
        if run.lifecycleStatus == "running" || run.lifecycleStatus == "queued" {
            return run.currentStageMessage ?? ClavisCopy.Status.label(for: run.status)
        }
        if run.lifecycleStatus == "failed" {
            return run.displayErrorMessage
        }
        return nil
    }

    var isAnalysisRunning: Bool {
        guard let run = activeRun else { return false }
        return run.lifecycleStatus == "running" || run.lifecycleStatus == "queued"
    }

    var needsAttentionPositions: [Position] {
        holdings
            .filter { p in
                let g = p.resolvedRiskGrade ?? ""
                return Grade.ordinalValue(for: g) <= 4 || p.riskTrend == .worsening
            }
            .sorted { attentionRank(for: $0) < attentionRank(for: $1) }
            .prefix(3)
            .map { $0 }
    }

    var priorityQueue: [DashboardPriorityItem] {
        needsAttentionPositions.map { position in
            DashboardPriorityItem(
                id: position.id,
                position: position,
                reason: priorityReason(for: position)
            )
        }
    }

    var portfolioRiskHighlights: [String] {
        guard let snapshot = portfolioRiskSnapshot else { return [] }
        var highlights: [String] = []

        if let allocation = snapshot.portfolioAllocationRiskScore {
            highlights.append("Allocation \(Int(allocation.rounded()))")
        }
        if let concentration = snapshot.concentrationRisk {
            highlights.append("Concentration \(Int(concentration.rounded()))")
        }
        if let cluster = snapshot.clusterRisk {
            highlights.append("Cluster \(Int(cluster.rounded()))")
        }
        if let macro = snapshot.macroStackRisk {
            highlights.append("Macro \(Int(macro.rounded()))")
        }
        return Array(highlights.prefix(4))
    }

    var riskDriverHighlights: [String] {
        guard let drivers = portfolioRiskSnapshot?.topRiskDrivers else { return [] }
        return Array(drivers.map(\.displayText).prefix(3))
    }

    var morningFocusSummary: String {
        if let summary = todayDigest?.summary?.sanitizedDisplayText, !summary.isEmpty {
            return firstSentence(summary)
        }
        return "Open the digest for the latest portfolio briefing."
    }

    var morningFocusItems: [String] {
        var items: [String] = []
        if let wl = todayDigest?.structuredSections?.watchlistUpdates {
            items.append(contentsOf: wl.alerts.prefix(2))
            items.append(contentsOf: wl.watchList.prefix(2))
        }
        if let catalysts = todayDigest?.structuredSections?.whatToWatchToday?.catalysts {
            items.append(contentsOf: catalysts.map(\.catalyst).prefix(2))
        }
        return dedupe(items)
    }

    var actionItems: [String] {
        todayDigest?.structuredSections?.whatToWatchToday?.monitoring.prefix(3).map { $0 } ?? []
    }

    var nextScheduledRunText: String {
        if let nextRun = schedulerStatus?.runtimeNextRunAt {
            return nextRun.formatted(date: .omitted, time: .shortened)
        }
        let calendar = Calendar.current
        let now = Date()
        var nextComponents = calendar.dateComponents([.year, .month, .day], from: now)
        nextComponents.hour = 9
        nextComponents.minute = 30

        let todayRun = calendar.date(from: nextComponents) ?? now
        let nextRun = todayRun > now ? todayRun : calendar.date(byAdding: .day, value: 1, to: todayRun) ?? todayRun
        return nextRun.formatted(date: .omitted, time: .shortened)
    }

    var changeAlerts: [Alert] {
        let relevantTypes: Set<AlertType> = [
            .majorEvent,
            .safetyDeterioration,
            .concentrationDanger,
            .clusterRisk,
            .macroShock,
            .structuralFragility,
        ]
        return alerts.filter { relevantTypes.contains($0.type) }.prefix(4).map { $0 }
    }

    private var resolvedPortfolioScore: Double? {
        dashboard?.overallScore
            ?? todayDigest?.overallScore
            ?? dashboard?.generatedDigest?.overallScore
            ?? dashboard?.savedDigest?.overallScore
    }

    private var resolvedPortfolioGrade: String? {
        dashboard?.overallGrade
            ?? todayDigest?.overallGrade
            ?? dashboard?.generatedDigest?.overallGrade
            ?? dashboard?.savedDigest?.overallGrade
    }

    var majorEventAlerts: [Alert] {
        let types: Set<AlertType> = [.majorEvent]
        return alerts.filter { types.contains($0.type) }.prefix(4).map { $0 }
    }

    func loadData() async {
        if dashboard == nil {
            isLoading = true
        }
        errorMessage = nil

        do {
            async let fetchedDashboard = api.fetchDashboard()
            async let fetchedSchedulerStatus = api.fetchSchedulerStatus()
            let fetched = try await fetchedDashboard
            let scheduler = try? await fetchedSchedulerStatus
            dashboard = fetched
            schedulerStatus = scheduler

#if DEBUG
            let authUserId = await SupabaseAuthService.shared.getUserId() ?? "nil"
            let formattedScore: (Double?) -> String = { value in
                guard let value else { return "nil" }
                return String(format: "%.1f", value)
            }
            let payloadSummary = [
                "baseURL=\(Config.backendBaseUrl)",
                "authUserId=\(authUserId)",
                "topLevelScore=\(formattedScore(fetched.overallScore))",
                "digestScore=\(formattedScore(fetched.digest?.overallScore))",
                "savedDigestScore=\(formattedScore(fetched.savedDigest?.overallScore))",
                "generatedDigestScore=\(formattedScore(fetched.generatedDigest?.overallScore))",
                "overallGrade=\(fetched.overallGrade ?? "nil")",
                "scoreSource=\(fetched.scoreSource ?? "nil")",
                "scoreAsOf=\(fetched.scoreAsOf?.formatted() ?? "nil")",
            ].joined(separator: " | ")
            print("[DashboardScorePayload] \(payloadSummary)")
#endif

            switch fetched.analysisRun?.lifecycleStatus {
            case "running", "queued":
                activeRun = fetched.analysisRun
            case "failed":
                activeRun = fetched.analysisRun
                let displayError = fetched.analysisRun?.displayErrorMessage ?? ClavisCopy.Errors.analysisRefreshFailed
                errorMessage = isTransientAnalysisError(displayError) ? nil : ClavisCopy.Errors.analysisRefreshFailed
            default:
                activeRun = nil
            }
        } catch is CancellationError {
            errorMessage = nil
        } catch {
            if dashboard == nil {
                errorMessage = ClavisCopy.Errors.dashboardLoad(error)
            }
        }

        isLoading = false
    }

    private func isTransientAnalysisError(_ message: String?) -> Bool {
        guard let message = message?.lowercased() else { return false }
        return message.contains("high traffic")
            || message.contains("rate limit")
            || message.contains("overload")
            || message.contains("temporarily unavailable")
    }

    func triggerFreshAnalysis() async {
        isRefreshingAnalysis = true
        errorMessage = nil
        activeRun = nil
        defer { isRefreshingAnalysis = false }

        do {
            let trigger = try await api.triggerAnalysis()
            if let runId = trigger.analysisRunId {
                let finished = await pollAnalysisRun(runId: runId)
                if finished {
                    await loadData()
                }
            } else {
                await loadData()
            }
        } catch is CancellationError {
            errorMessage = nil
        } catch {
            errorMessage = ClavisCopy.Errors.dashboardRefresh(error)
        }
    }

    private func pollAnalysisRun(runId: String) async -> Bool {
        for _ in 0..<30 {
            do {
                let run = try await api.fetchAnalysisRun(id: runId)
                activeRun = run

                switch run.lifecycleStatus {
                case "completed":
                    errorMessage = nil
                    activeRun = nil
                    return true
                case "failed":
                    errorMessage = isTransientAnalysisError(run.displayErrorMessage) ? nil : ClavisCopy.Errors.analysisRefreshFailed
                    activeRun = run
                    return false
                default:
                    break
                }
            } catch is CancellationError {
                return false
            } catch {
                errorMessage = ClavisCopy.Errors.dashboardRefresh(error)
                activeRun = nil
                return false
            }

            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }

        errorMessage = "Analysis taking longer than expected. You can leave this screen."
        activeRun = nil
        return false
    }

    private func attentionRank(for position: Position) -> Int {
        let g = position.resolvedRiskGrade ?? ""
        let ord = Grade.ordinalValue(for: g)
        if ord <= 2 { return 0 }
        if ord <= 4 { return 1 }
        if position.riskTrend == .worsening { return 2 }
        return 3
    }

    private func priorityReason(for position: Position) -> String {
        if let tickerAlert = alerts.first(where: { $0.positionTicker == position.ticker && $0.type != .digestReady }) {
            return tickerAlert.message.sanitizedDisplayText
        }

        if Grade.ordinalValue(for: position.resolvedRiskGrade ?? "") <= 4 {
            return "Low-grade holding."
        }

        if position.riskTrend == .worsening {
            return "Risk trend is worsening."
        }

        if let summary = position.resolvedSummary?.sanitizedDisplayText, !summary.isEmpty {
            return firstSentence(summary)
        }

        return "Rating active."
    }

    private var topRiskDriverSummary: String? {
        if let first = riskDriverHighlights.first {
            return first.lowercased()
        }
        if let atRisk = holdings.first(where: { p in
            let g = p.resolvedRiskGrade ?? ""
            return Grade.ordinalValue(for: g) <= 4
        }) {
            return atRisk.ticker
        }
        return nil
    }

    private func dedupe(_ items: [String]) -> [String] {
        var seen = Set<String>()
        return items.filter { seen.insert($0).inserted }
    }

    private func firstSentence(_ text: String) -> String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return text }

        let separators = CharacterSet(charactersIn: ".!?")
        if let range = trimmed.rangeOfCharacter(from: separators) {
            return String(trimmed[..<range.upperBound]).trimmingCharacters(in: .whitespacesAndNewlines)
        }

        if let newlineRange = trimmed.range(of: "\n") {
            return String(trimmed[..<newlineRange.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
        }

        return trimmed
    }
}

struct DashboardPriorityItem: Identifiable {
    let id: String
    let position: Position
    let reason: String
}
