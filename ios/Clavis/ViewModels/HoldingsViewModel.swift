import Foundation
import SwiftUI

@MainActor
class HoldingsViewModel: ObservableObject {
    @Published var holdings: [Position] = []
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

    private let api = APIService.shared
    private var analysisTask: Task<Void, Never>?
    private let softTimeoutSeconds: TimeInterval = 60

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
        } catch is CancellationError {
            errorMessage = nil
        } catch {
            errorMessage = "Failed to load: \(error.localizedDescription)"
        }

        isLoading = false
        isRefreshing = false
    }

    func refreshHoldings() async {
        await loadHoldings(showLoading: false)
    }

    func addHolding(ticker: String, shares: Double, purchasePrice: Double, archetype: Archetype) async {
        errorMessage = nil
        showError = false
        showAddSheet = false
        showProgressSheet = true
        pendingTicker = ticker.uppercased()
        createdPositionId = nil
        progressMessage = "Adding position..."
        progressValue = 0.1

        do {
            let createdPosition = try await api.createHolding(
                ticker: ticker.uppercased(),
                shares: shares,
                purchasePrice: purchasePrice,
                archetype: archetype
            )
            createdPositionId = createdPosition.id
            insertOrUpdateHolding(createdPosition)
            progressMessage = "Queueing analysis..."
            progressValue = 0.2

            analysisTask?.cancel()
            analysisTask = Task { [weak self] in
                guard let self else { return }
                await self.runAnalysisFlow()
            }
        } catch {
            showProgressSheet = false
            progressValue = 0.0
            pendingTicker = nil
            errorMessage = "Failed to add: \(error.localizedDescription)"
            showError = true
        }
    }

    private func runAnalysisFlow() async {
        do {
            let trigger = try await api.triggerAnalysis(positionId: createdPositionId)
            if let runId = trigger.analysisRunId {
                await pollAnalysisRun(runId: runId)
            } else {
                progressMessage = "Analysis queued"
                progressValue = 0.45
            }
        } catch is CancellationError {
            return
        } catch {
            errorMessage = "Failed to analyze: \(error.localizedDescription)"
            showError = false
            activeRun = nil
            showProgressSheet = false
            progressValue = 0.0
            pendingTicker = nil
            return
        }
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
            errorMessage = "Failed to delete: \(error.localizedDescription)"
            showError = true
        }
    }

    func pollAnalysisRun(runId: String) async {
        let startedPollingAt = Date()
        var showedSoftTimeout = false

        while !Task.isCancelled {
            do {
                let run = try await api.fetchAnalysisRun(id: runId)
                activeRun = run

                switch run.lifecycleStatus {
                case "queued":
                    progressMessage = run.currentStageMessage ?? "Queued for analysis..."
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
                case "completed":
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
                    return
                case "failed":
                    throw APIError.networkError(NSError(domain: "Clavis", code: 1, userInfo: [
                        NSLocalizedDescriptionKey: run.errorMessage ?? "Analysis failed."
                    ]))
                default:
                    progressMessage = "Processing..."
                }
            } catch {
                showProgressSheet = false
                progressValue = 0.0
                errorMessage = "Failed to analyze: \(error.localizedDescription)"
                showError = true
                activeRun = nil
                pendingTicker = nil
                createdPositionId = nil
                return
            }

            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }
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
        case "running_mirofish":
            return 0.7
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
}
