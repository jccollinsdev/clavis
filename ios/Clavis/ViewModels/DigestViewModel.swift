import Foundation
import SwiftUI

@MainActor
class DigestViewModel: ObservableObject {
    @Published var todayDigest: Digest?
    @Published var digestHistory: [Digest] = []
    @Published var holdings: [Position] = []
    @Published var alerts: [Alert] = []
    @Published var lastTriggerResult: TriggerAnalysisResponse?
    @Published var activeRun: AnalysisRun?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var timeoutMessage: String?

    private let api = APIService.shared
    private var loadGeneration = 0

    func loadDigest(showLoading: Bool = true) async {
        loadGeneration += 1
        let generation = loadGeneration
        let previousDigest = todayDigest
        let previousRunningRun = activeRun?.lifecycleStatus == "running" ? activeRun : nil

        if showLoading {
            isLoading = true
        }
        errorMessage = nil
        timeoutMessage = nil

        async let dashboardResult: Result<DashboardResponse, Error> = {
            do {
                return .success(try await api.fetchDashboard())
            } catch {
                return .failure(error)
            }
        }()
        async let historyResult: Result<[Digest], Error> = {
            do {
                return .success(try await api.fetchDigestHistory(timeoutInterval: 75))
            } catch {
                return .failure(error)
            }
        }()

        let resolvedDashboard = await dashboardResult
        let resolvedHistory = await historyResult

        guard generation == loadGeneration else { return }

        var resolvedRun = previousRunningRun

        switch resolvedDashboard {
        case .success(let response):
            resolvedRun = response.analysisRun ?? previousRunningRun
            todayDigest = response.digest ?? previousDigest
            holdings = response.positions
            alerts = response.alerts

            if shouldRefreshDigest(todayDigest, holdingCount: holdings.count) {
                do {
                    let generated = try await api.fetchTodayDigest()
                    if generation == loadGeneration {
                        todayDigest = generated.digest ?? todayDigest
                        if let run = generated.analysisRun {
                            resolvedRun = run
                            let displayError = run.displayErrorMessage
                            activeRun = run.lifecycleStatus == "failed" && isTransientAnalysisError(displayError) ? nil : run
                        }
                    }
                } catch {
                    if previousDigest == nil && todayDigest == nil {
                        errorMessage = "We couldn't load the latest digest right now."
                    }
                }
            }

            switch resolvedRun?.lifecycleStatus {
            case "running", "queued":
                activeRun = resolvedRun
                errorMessage = nil
            case "failed":
                activeRun = resolvedRun
                let displayError = resolvedRun?.displayErrorMessage ?? "Analysis failed. Please run a fresh review."
                errorMessage = isTransientAnalysisError(displayError) ? nil : displayError
            case "completed":
                activeRun = response.digest == nil ? resolvedRun : nil
                errorMessage = nil
            default:
                activeRun = nil
                errorMessage = nil
            }

            if let run = resolvedRun,
               run.lifecycleStatus == "running",
               let startedAt = run.startedAt,
               Date().timeIntervalSince(startedAt) > 25 * 60 {
                timeoutMessage = "Analysis is taking longer than expected. You can leave this screen."
            }
        case .failure(let error):
            if error is CancellationError {
                if showLoading { isLoading = false }
                return
            }
            todayDigest = previousDigest
            activeRun = previousRunningRun
            if previousRunningRun?.lifecycleStatus == "running" || previousRunningRun?.lifecycleStatus == "queued" {
                errorMessage = nil
                if let startedAt = previousRunningRun?.startedAt,
                   Date().timeIntervalSince(startedAt) > 25 * 60 {
                    timeoutMessage = "Analysis is taking longer than expected. You can leave this screen."
                }
            } else if (error as? APIError) != nil {
                errorMessage = "We couldn't load the latest digest right now."
            } else {
                errorMessage = error.localizedDescription
            }
        }

        digestHistory = (try? resolvedHistory.get()) ?? []
        if let message = errorMessage, message.localizedCaseInsensitiveContains("cancelled") {
            errorMessage = nil
        }

        if showLoading {
            isLoading = false
        }
    }

    func triggerAnalysis() async {
        isLoading = true
        errorMessage = nil
        timeoutMessage = nil

        do {
            lastTriggerResult = try await api.triggerAnalysis()
            if let runId = lastTriggerResult?.analysisRunId {
                loadGeneration += 1
                let finished = await pollAnalysisRun(runId: runId)
                if finished {
                    await waitForDigestReady()
                    await loadDigest(showLoading: false)
                }
            }
        } catch {
            errorMessage = error.localizedDescription
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

    private func shouldRefreshDigest(_ digest: Digest?, holdingCount: Int) -> Bool {
        guard holdingCount > 0 else { return false }
        return digest?.structuredSections?.digestVersion != 2
    }

    func pollAnalysisRun(runId: String) async -> Bool {
        for _ in 0..<240 {
            do {
                let run = try await api.fetchAnalysisRun(id: runId)
                activeRun = run

                if run.isTerminal {
                    if run.lifecycleStatus == "failed" {
                        errorMessage = isTransientAnalysisError(run.displayErrorMessage) ? nil : run.displayErrorMessage
                        return false
                    }
                    return true
                }
            } catch {
                errorMessage = error.localizedDescription
                return false
            }

            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }

        timeoutMessage = "Analysis is still running. You can leave this screen and check back shortly."
        return false
    }

    private func waitForDigestReady() async {
        for _ in 0..<10 {
            do {
                let response = try await api.fetchTodayDigest(forceRefresh: true, timeoutInterval: 75)
                if let digest = response.digest {
                    todayDigest = digest
                    return
                }
            } catch {
                break
            }

            try? await Task.sleep(nanoseconds: 1_000_000_000)
        }
    }
}
