import Foundation
import SwiftUI

@MainActor
class DashboardViewModel: ObservableObject {
    @Published private(set) var dashboard: DashboardResponse?
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
        if let digestGrade = todayDigest?.overallGrade {
            return digestGrade
        }
        guard !holdings.isEmpty else { return "N/A" }
        let grades = holdings.compactMap { $0.riskGrade }
        guard !grades.isEmpty else { return "N/A" }
        let gradeValues = grades.map { gradeValue($0) }
        let avg = gradeValues.reduce(0, +) / Double(gradeValues.count)
        return scoreToGrade(avg)
    }

    var portfolioScore: Double {
        if let digestScore = todayDigest?.overallScore {
            return digestScore
        }
        let scores = holdings.compactMap { $0.totalScore }
        guard !scores.isEmpty else { return 0 }
        return scores.reduce(0, +) / Double(scores.count)
    }

    var portfolioRiskState: RiskState {
        RiskState.from(score: portfolioScore)
    }

    var portfolioRiskTrend: RiskTrend {
        let improving = improvingCount
        let worsening = deterioratingCount
        if worsening > improving { return .increasing }
        if improving > worsening { return .improving }
        return .stable
    }

    var portfolioActionPressure: ActionPressure {
        ActionPressure.from(score: portfolioScore, trend: portfolioRiskTrend)
    }

    var portfolioSummary: String {
        let state = portfolioRiskState.displayName.lowercased()
        if let driver = topRiskDriverSummary, portfolioRiskTrend == .increasing {
            return "Portfolio risk is \(state), driven mainly by \(driver)."
        }
        if portfolioRiskTrend == .improving {
            return "Portfolio risk is \(state), with some positions improving."
        }
        return "Portfolio risk is \(state) and stable."
    }

    var improvingCount: Int {
        holdings.filter { position in
            guard let current = position.riskGrade,
                  let previous = position.previousGrade else {
                return false
            }
            return gradeValue(current) > gradeValue(previous)
        }.count
    }

    var deterioratingCount: Int {
        holdings.filter { position in
            guard let current = position.riskGrade,
                  let previous = position.previousGrade else {
                return false
            }
            return gradeValue(current) < gradeValue(previous)
        }.count
    }

    var majorEventCount: Int {
        todayDigest?.structuredSections?.majorEvents.count ?? 0
    }

    var lastUpdatedAt: Date? {
        if let generatedAt = todayDigest?.generatedAt {
            return generatedAt
        }
        return holdings.compactMap(\.lastAnalyzedAt).max()
    }

    var analysisStatusText: String? {
        guard let run = activeRun else { return nil }
        if run.lifecycleStatus == "running" || run.lifecycleStatus == "queued" {
            return run.currentStageMessage ?? run.status.capitalized
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
            .filter { $0.riskGrade == "D" || $0.riskGrade == "F" || $0.riskTrend == .increasing }
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
        if let watchlistAlerts = todayDigest?.structuredSections?.watchlistAlerts {
            items.append(contentsOf: watchlistAlerts.prefix(2))
        }
        if let watchList = todayDigest?.structuredSections?.watchList {
            items.append(contentsOf: watchList.prefix(2))
        }
        if let majorEvents = todayDigest?.structuredSections?.majorEvents {
            items.append(contentsOf: majorEvents.prefix(2))
        }
        return dedupe(items)
    }

    var actionItems: [String] {
        Array(todayDigest?.structuredSections?.portfolioImpact.prefix(3) ?? [])
    }

    var nextScheduledRunText: String {
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
            let fetched = try await api.fetchDashboard()
            dashboard = fetched

            switch fetched.analysisRun?.lifecycleStatus {
            case "running", "queued":
                activeRun = fetched.analysisRun
            case "failed":
                activeRun = fetched.analysisRun
                let displayError = fetched.analysisRun?.displayErrorMessage ?? "Analysis failed. Please run a fresh review."
                errorMessage = isTransientAnalysisError(displayError) ? nil : displayError
            default:
                activeRun = nil
            }
        } catch is CancellationError {
            errorMessage = nil
        } catch {
            if dashboard == nil {
                errorMessage = "We couldn't load the dashboard right now."
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
            errorMessage = error.localizedDescription
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
                    errorMessage = isTransientAnalysisError(run.displayErrorMessage) ? nil : run.displayErrorMessage
                    activeRun = run
                    return false
                default:
                    break
                }
            } catch is CancellationError {
                return false
            } catch {
                errorMessage = error.localizedDescription
                activeRun = nil
                return false
            }

            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }

        errorMessage = "Analysis taking longer than expected. You can leave this screen."
        activeRun = nil
        return false
    }

    private func gradeValue(_ grade: String) -> Double {
        switch grade {
        case "A": return 90
        case "B": return 72
        case "C": return 57
        case "D": return 42
        case "F": return 25
        default: return 50
        }
    }

    private func scoreToGrade(_ score: Double) -> String {
        if score >= 75 { return "A" }
        if score >= 55 { return "B" }
        if score >= 35 { return "C" }
        if score >= 15 { return "D" }
        return "F"
    }

    private func attentionRank(for position: Position) -> Int {
        if position.riskGrade == "F" { return 0 }
        if position.riskGrade == "D" { return 1 }
        if position.riskTrend == .increasing { return 2 }
        return 3
    }

    private func priorityReason(for position: Position) -> String {
        if let tickerAlert = alerts.first(where: { $0.positionTicker == position.ticker && $0.type != .digestReady }) {
            return tickerAlert.message.sanitizedDisplayText
        }

        if position.riskGrade == "F" || position.riskGrade == "D" {
            return "Low-grade holding needs review."
        }

        if position.riskTrend == .increasing {
            return "Risk trend is worsening."
        }

        if let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
            return firstSentence(summary)
        }

        return "Monitoring this position."
    }

    private var topRiskDriverSummary: String? {
        if let first = riskDriverHighlights.first {
            return first.lowercased()
        }
        if let atRisk = holdings.first(where: { $0.riskGrade == "D" || $0.riskGrade == "F" }) {
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
