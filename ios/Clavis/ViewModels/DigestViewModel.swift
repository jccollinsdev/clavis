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

        async let todayDigestResult: Result<DigestResponse, Error> = {
            do {
                return .success(try await api.fetchTodayDigest())
            } catch {
                return .failure(error)
            }
        }()
        async let historyResult: Result<[Digest], Error> = {
            do {
                return .success(try await api.fetchDigestHistory())
            } catch {
                return .failure(error)
            }
        }()
        async let holdingsResult: Result<[Position], Error> = {
            do {
                return .success(try await api.fetchHoldings())
            } catch {
                return .failure(error)
            }
        }()
        async let alertsResult: Result<[Alert], Error> = {
            do {
                return .success(try await api.fetchAlerts())
            } catch {
                return .failure(error)
            }
        }()

        let resolvedTodayDigest = await todayDigestResult
        let resolvedHistory = await historyResult
        let resolvedHoldings = await holdingsResult
        let resolvedAlerts = await alertsResult

        guard generation == loadGeneration else { return }

        var resolvedRun = previousRunningRun

        switch resolvedTodayDigest {
        case .success(let response):
            resolvedRun = response.analysisRun ?? previousRunningRun
            todayDigest = response.digest ?? previousDigest
            switch resolvedRun?.lifecycleStatus {
            case "running", "queued":
                activeRun = resolvedRun
                errorMessage = nil
            case "failed":
                activeRun = resolvedRun
                errorMessage = resolvedRun?.displayErrorMessage ?? "Analysis failed. Please run a fresh review."
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
        holdings = (try? resolvedHoldings.get()) ?? []
        alerts = (try? resolvedAlerts.get()) ?? []

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

    func pollAnalysisRun(runId: String) async -> Bool {
        for _ in 0..<30 {
            do {
                let run = try await api.fetchAnalysisRun(id: runId)
                activeRun = run

                if run.isTerminal {
                    activeRun = nil
                    if run.lifecycleStatus == "failed" {
                        errorMessage = run.displayErrorMessage
                        return false
                    }
                    return true
                }
            } catch {
                errorMessage = error.localizedDescription
                activeRun = nil
                return false
            }

            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }

        timeoutMessage = "Analysis taking longer than expected. You can leave this screen."
        activeRun = nil
        return false
    }

    private func waitForDigestReady() async {
        for _ in 0..<10 {
            do {
                let response = try await api.fetchTodayDigest()
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
