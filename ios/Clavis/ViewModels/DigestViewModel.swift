import Foundation
import SwiftUI

enum DigestLengthOption: String, CaseIterable {
    case brief = "brief"
    case standard = "standard"
    case verbose = "verbose"

    var title: String {
        rawValue.capitalized
    }
}

@MainActor
final class DigestViewModel: ObservableObject {
    @Published var todayDigest: Digest?
    @Published var digestHistory: [Digest] = []
    @Published var holdings: [Position] = []
    @Published var alerts: [Alert] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var activeRun: AnalysisRun?
    @Published var summaryLength: DigestLengthOption = .standard
    @Published var subscriptionTier: String = "free"
    @Published var morningReportState: MorningReportState = .placeholder
    @Published var today: TodayResponse?

    private let api = APIService.shared

    func loadDigest(showLoading: Bool = true) async {
        if showLoading {
            isLoading = true
        }
        errorMessage = nil

        // Fire all requests concurrently — nothing depends on another completing first.
        // Previously holdings was awaited sequentially before the other Tasks launched,
        // adding one serial round-trip to every Today screen load.
        Task {
            let h = try? await api.fetchHoldings()
            await MainActor.run {
                if let h { self.holdings = h }
                self.updateMorningReportState(digest: self.todayDigest)
            }
        }

        Task {
            let preferences = try? await api.fetchPreferences()
            await MainActor.run {
                self.summaryLength = DigestLengthOption(rawValue: preferences?.summaryLength?.lowercased() ?? "standard") ?? .standard
                self.subscriptionTier = preferences?.subscriptionTier?.lowercased() ?? "free"
            }
        }

        Task {
            let digestResponse = try? await api.fetchTodayDigest(timeoutInterval: 30)
            let latestRun = try? await api.fetchLatestAnalysisRun()
            await MainActor.run {
                let digest = digestResponse?.digest ?? digestResponse?.generatedDigest ?? digestResponse?.savedDigest
                self.todayDigest = digest
                self.activeRun = digestResponse?.analysisRun ?? latestRun
                self.updateMorningReportState(digest: digest)
            }
            if digestResponse == nil {
                await refreshMorningReportStatus()
            }
        }

        Task {
            let history = (try? await api.fetchDigestHistory(limit: 7, timeoutInterval: 30)) ?? []
            await MainActor.run {
                self.digestHistory = history.sorted { $0.generatedAt < $1.generatedAt }
            }
        }

        Task {
            let alerts = (try? await api.fetchAlerts()) ?? []
            await MainActor.run { self.alerts = alerts }
        }

        Task {
            let today = try? await api.fetchToday()
            await MainActor.run { self.today = today }
        }

        isLoading = false
    }

    func reloadDigestFromDatabase() async {
        await loadDigest(showLoading: false)
    }

    func refreshMorningReportStatus() async {
        do {
            let status = try await api.fetchDigestStatus()
            switch status.state {
            case "ready":
                if let digest = status.digest {
                    todayDigest = digest
                    morningReportState = .ready(digest)
                } else {
                    morningReportState = .placeholder
                }
            case "generating":
                morningReportState = .generating(startedAt: status.startedAt)
            default:
                morningReportState = .placeholder
            }
        } catch {
            morningReportState = todayDigest.map { .ready($0) } ?? .placeholder
        }
    }

    func saveSummaryLength(_ option: DigestLengthOption) async {
        do {
            try await api.updatePreferences(
                digestTime: nil,
                notificationsEnabled: nil,
                summaryLength: option.rawValue,
                weekdayOnly: nil
            )
            summaryLength = option
        } catch {
            errorMessage = ClavisCopy.Errors.digestRefresh(error)
        }
    }

    var isGenerating: Bool {
        if case .generating = morningReportState {
            return true
        }
        guard let activeRun else { return false }
        return activeRun.lifecycleStatus == "running" || activeRun.lifecycleStatus == "queued"
    }

    var hasHoldings: Bool {
        !holdings.isEmpty
    }

    var isFreeTier: Bool {
        subscriptionTier == "free"
    }

    func grade(for ticker: String) -> String {
        holdings.first(where: { $0.ticker.caseInsensitiveCompare(ticker) == .orderedSame })?.resolvedRiskGrade ?? "—"
    }

    func scoreDelta(for ticker: String) -> Int? {
        holdings.first(where: { $0.ticker.caseInsensitiveCompare(ticker) == .orderedSame })?.scoreDelta
    }

    private func updateMorningReportState(digest: Digest?) {
        if let digest {
            morningReportState = .ready(digest)
        } else if let activeRun, activeRun.lifecycleStatus == "running" || activeRun.lifecycleStatus == "queued" {
            morningReportState = .generating(startedAt: activeRun.startedAt)
        } else {
            morningReportState = .placeholder
        }
    }
}
