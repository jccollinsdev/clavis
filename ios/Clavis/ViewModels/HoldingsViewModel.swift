import Foundation
import SwiftUI

@MainActor
class HoldingsViewModel: ObservableObject {
    @Published var holdings: [Position] = []
    @Published var watchlistItems: [WatchlistItem] = []
    @Published var isLoading = false
    @Published var isRefreshing = false
    @Published var errorMessage: String?
    @Published var showAddSheet = false
    @Published var showError = false
    @Published var showProgressSheet = false
    @Published var progressMessage = "Adding position..."
    @Published var progressValue: Float = 0.0
    @Published var activeRun: AnalysisRun?
    @Published var pendingTicker: String?
    @Published var createdPositionId: String?
    @Published var lastRefreshedAt: Date?
    @Published var brokerageLastSyncedAt: Date?
    @Published var subscriptionTier: String = "free"

    private let api = APIService.shared
    private var analysisTask: Task<Void, Never>?
    private let softTimeoutSeconds: TimeInterval = 60
    private let brokerageAutoSyncInterval: TimeInterval = 4 * 60 * 60

    func loadHoldings(showLoading: Bool = true) async {
        if showLoading {
            isLoading = true
        } else {
            isRefreshing = true
        }
        errorMessage = nil
        showError = false

        do {
            holdings = try await api.fetchHoldings()
            lastRefreshedAt = Date()

            Task {
                let watchlists = try? await api.fetchWatchlists()
                let preferences = try? await api.fetchPreferences()

                await MainActor.run {
                    self.watchlistItems = watchlists?.first?.items ?? []
                    self.subscriptionTier = preferences?.subscriptionTier?.lowercased() ?? "free"
                }
            }

            Task {
                guard let brokerageStatus = try? await api.fetchBrokerageStatus() else { return }

                await MainActor.run {
                    self.applyBrokerageStatus(brokerageStatus)
                }

                if shouldAutoSyncBrokerage(brokerageStatus) {
                    _ = try? await api.syncBrokerage(refreshRemote: false)
                    let refreshedHoldings = try? await api.fetchHoldings()
                    let refreshedStatus = try? await api.fetchBrokerageStatus()

                    await MainActor.run {
                        if let refreshedHoldings {
                            self.holdings = refreshedHoldings
                            self.lastRefreshedAt = Date()
                            self.brokerageLastSyncedAt = Date()
                        }
                        if let refreshedStatus {
                            self.applyBrokerageStatus(refreshedStatus)
                        }
                    }
                }
            }
        } catch is CancellationError {
            errorMessage = nil
        } catch {
            errorMessage = ClavisCopy.Errors.holdingsLoad(error)
        }

        isLoading = false
        isRefreshing = false
    }

    func refreshHoldings() async {
        await loadHoldings(showLoading: false)
    }

    func refreshWatchlist() async {
        do {
            let watchlists = try await api.fetchWatchlists()
            watchlistItems = watchlists.first?.items ?? []
        } catch {
            // Silent — watchlist refresh failure shouldn't block UI
        }
    }

    func addHolding(
        ticker: String,
        shares: Double,
        purchasePrice: Double,
        allowOutsideUniverse: Bool = false
    ) async {
        errorMessage = nil
        showError = false
        showAddSheet = false
        showProgressSheet = true
        pendingTicker = ticker.uppercased()
        createdPositionId = nil
        progressMessage = "Adding position..."
        progressValue = 0.1

        do {
            let workflow = try await api.createHolding(
                ticker: ticker.uppercased(),
                shares: shares,
                purchasePrice: purchasePrice,
                allowOutsideUniverse: allowOutsideUniverse ? true : nil
            )
            if let createdPosition = workflow.position {
                createdPositionId = createdPosition.id
                insertOrUpdateHolding(createdPosition)
            } else {
                createdPositionId = workflow.holdingId
            }

            progressMessage = workflowMessage(for: workflow)
            progressValue = workflowProgressValue(for: workflow.analysisState)
            await loadHoldings(showLoading: false)

            switch workflow.analysisState {
            case "queued", "running":
                if let runId = workflow.analysisRunId {
                    await pollAnalysisRun(runId: runId)
                } else {
                    await finishAddWorkflow(after: 1.0)
                }
            case "ready", "thin", "failed":
                await finishAddWorkflow(after: 1.0)
            default:
                await finishAddWorkflow(after: 1.0)
            }
        } catch {
            showProgressSheet = false
            progressValue = 0.0
            pendingTicker = nil
            errorMessage = ClavisCopy.Errors.holdingAdd(error)
            showError = true
        }
    }

    private func workflowProgressValue(for state: String) -> Float {
        switch state {
        case "queued":
            return 0.2
        case "running":
            return 0.45
        case "ready":
            return 1.0
        case "thin":
            return 0.35
        case "failed":
            return 1.0
        default:
            return 0.25
        }
    }

    private func workflowMessage(for workflow: APIService.HoldingWorkflowResponse) -> String {
        switch workflow.analysisState {
        case "queued":
            return workflow.coverageNote ?? "Analysis pending."
        case "running":
            return workflow.coverageNote ?? "Analysis in progress."
        case "ready":
            return workflow.coverageNote ?? "Position is ready."
        case "thin":
            return workflow.coverageNote ?? "Limited data available."
        case "failed":
            return workflow.coverageNote ?? "Analysis unavailable."
        default:
            return workflow.coverageNote ?? "Updating position."
        }
    }

    private func finishAddWorkflow(after delay: TimeInterval) async {
        if delay > 0 {
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
        }
        showProgressSheet = false
        pendingTicker = nil
        createdPositionId = nil
    }

    func deleteHolding(_ position: Position) async {
        guard let index = holdings.firstIndex(where: { $0.id == position.id }) else { return }
        let backup = holdings[index]
        holdings.remove(at: index)
        showError = false
        errorMessage = nil

        do {
            try await api.deleteHolding(id: position.id)
        } catch {
            holdings.insert(backup, at: index)
            errorMessage = ClavisCopy.Errors.holdingDelete(error)
            showError = true
        }
    }

    func searchTickers(query: String, limit: Int = 50) async throws -> [TickerSearchResult] {
        try await api.searchTickers(query: query, limit: limit)
    }

    func addTickerToWatchlist(_ ticker: String) async throws {
        let watchlist = try await api.addToWatchlist(ticker: ticker)
        watchlistItems = watchlist.items
    }

    func removeTickerFromWatchlist(_ ticker: String) async throws {
        let watchlist = try await api.removeFromWatchlist(ticker: ticker)
        watchlistItems = watchlist.items
    }

    func pollAnalysisRun(runId: String) async {
        let startedPollingAt = Date()
        var showedSoftTimeout = false

        while !Task.isCancelled {
            do {
                let run = try await api.fetchAnalysisRun(id: runId)
                activeRun = run

                if run.isTerminal {
                    if run.lifecycleStatus == "failed" {
                        throw APIError.networkError(
                            "analysis-run",
                                NSError(domain: "Clavis", code: 1, userInfo: [
                                NSLocalizedDescriptionKey: run.errorMessage ?? "Analysis unavailable."
                            ])
                        )
                    }
                    await handleAnalysisCompletion()
                    return
                }

                switch run.lifecycleStatus {
                case "queued":
                    progressMessage = run.currentStageMessage ?? "Pending analysis..."
                    progressValue = 0.18
                case "running":
                    progressMessage = run.currentStageMessage ?? "Analyzing \(pendingTicker ?? "position")..."
                    progressValue = analysisProgressValue(for: run)
                    await loadHoldings(showLoading: false)
                    if !showedSoftTimeout,
                       Date().timeIntervalSince(startedPollingAt) > softTimeoutSeconds {
                        progressMessage = "Analysis taking longer than expected. You can leave this screen."
                        showedSoftTimeout = true
                    }
                default:
                    progressMessage = run.currentStageMessage ?? "Processing..."
                }
            } catch {
                showProgressSheet = false
                progressValue = 0.0
                if let apiError = error as? APIError {
                    errorMessage = ClavisCopy.Errors.holdingRefresh(apiError)
                } else {
                    errorMessage = ClavisCopy.Errors.holdingRefresh(error)
                }
                showError = true
                activeRun = nil
                pendingTicker = nil
                createdPositionId = nil
                return
            }

            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }
    }

    private func handleAnalysisCompletion() async {
        progressMessage = "\(pendingTicker ?? "Position") is ready"
        progressValue = 1.0
        errorMessage = nil
        showError = false
        activeRun = nil
        await loadHoldings(showLoading: false)
        try? await Task.sleep(nanoseconds: 700_000_000)
        showProgressSheet = false
        pendingTicker = nil
        createdPositionId = nil
    }

    private func analysisProgressValue(for run: AnalysisRun) -> Float {
        switch run.currentStage {
        case "starting":
            return 0.22
        case "fetching_news":
            return 0.34
        case "classifying_relevance":
            return 0.46
        case "analyzing_events":
            return 0.62
        case "scoring_position":
            return 0.76
        case "refreshing_prices":
            return 0.86
        case "building_digest":
            return 0.94
        case "completed":
            return 1.0
        case "failed":
            return 0.0
        default:
            return 0.28
        }
    }

    private func insertOrUpdateHolding(_ position: Position) {
        if let index = holdings.firstIndex(where: { $0.id == position.id }) {
            holdings[index] = position
        } else {
            holdings.insert(position, at: 0)
        }
    }

    private func applyBrokerageStatus(_ status: APIService.BrokerageStatusResponse) {
        brokerageLastSyncedAt = status.lastSyncAt
    }

    private func shouldAutoSyncBrokerage(_ status: APIService.BrokerageStatusResponse) -> Bool {
        guard status.connected, status.autoSyncEnabled else { return false }
        guard let lastSyncAt = status.lastSyncAt else { return true }
        return Date().timeIntervalSince(lastSyncAt) >= brokerageAutoSyncInterval
    }
}
