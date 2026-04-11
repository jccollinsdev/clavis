import Foundation
import SwiftUI

@MainActor
class DashboardViewModel: ObservableObject {
    @Published var holdings: [Position] = []
    @Published var todayDigest: Digest?
    @Published var activeRun: AnalysisRun?
    @Published var isLoading = false
    @Published var isRefreshingAnalysis = false
    @Published var errorMessage: String?

    private let api = APIService.shared

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
        if portfolioRiskTrend == .increasing {
            return "Portfolio risk is \(state), driven mainly by \(topRiskDriver ?? "recent deterioration")."
        } else if portfolioRiskTrend == .improving {
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

    var needsAttentionPositions: [Position] {
        holdings
            .filter { $0.riskGrade == "D" || $0.riskGrade == "F" || $0.riskTrend == .increasing }
            .sorted { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
            .prefix(3)
            .map { $0 }
    }

    var topRiskDriver: String? {
        let atRiskPositions = holdings.filter { $0.riskGrade == "D" || $0.riskGrade == "F" }
        return atRiskPositions.first?.ticker
    }

    var largestImprovingPosition: Position? {
        holdings
            .filter { $0.riskTrend == .improving }
            .max { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
    }

    var largestWorseningPosition: Position? {
        holdings
            .filter { $0.riskTrend == .increasing }
            .min { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
    }

    var lastUpdatedAt: Date? {
        if let generatedAt = todayDigest?.generatedAt {
            return generatedAt
        }
        return holdings.compactMap(\.lastAnalyzedAt).max()
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

    func loadData() async {
        isLoading = true
        errorMessage = nil

        async let holdingsResult: Result<[Position], Error> = {
            do {
                return .success(try await api.fetchHoldings())
            } catch {
                return .failure(error)
            }
        }()
        async let digestResult: Result<DigestResponse, Error> = {
            do {
                return .success(try await api.fetchTodayDigest())
            } catch {
                return .failure(error)
            }
        }()

        let resolvedHoldings = await holdingsResult
        let resolvedDigest = await digestResult

        switch resolvedHoldings {
        case .success(let fetchedHoldings):
            holdings = fetchedHoldings
        case .failure(let error):
            if error is CancellationError || error.localizedDescription.localizedCaseInsensitiveContains("cancelled") {
                errorMessage = nil
            } else {
                errorMessage = "We couldn't load holdings right now."
            }
        }

        switch resolvedDigest {
        case .success(let digestResponse):
            todayDigest = digestResponse.digest
        case .failure(let error):
            todayDigest = nil
            if !(error is CancellationError) && !error.localizedDescription.localizedCaseInsensitiveContains("cancelled") {
                if errorMessage == nil {
                    errorMessage = "Latest digest is temporarily unavailable."
                }
            }
        }

        isLoading = false
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
                if !finished && errorMessage == nil {
                    errorMessage = "Analysis taking longer than expected. You can leave this screen."
                }
            }
            if activeRun == nil && errorMessage == nil {
                await loadData()
            }
        } catch is CancellationError {
            errorMessage = nil
        } catch {
            let message = error.localizedDescription
            if message.localizedCaseInsensitiveContains("cancelled") {
                errorMessage = nil
            } else {
                errorMessage = message
            }
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
                    errorMessage = run.errorMessage ?? "Analysis failed."
                    activeRun = nil
                    return false
                default:
                    break
                }
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
}
