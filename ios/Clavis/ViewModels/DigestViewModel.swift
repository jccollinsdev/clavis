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
    @Published var holdings: [Position] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var activeRun: AnalysisRun?
    @Published var summaryLength: DigestLengthOption = .standard
    @Published var subscriptionTier: String = "free"

    private let api = APIService.shared

    func loadDigest(showLoading: Bool = true) async {
        if showLoading {
            isLoading = true
        }
        errorMessage = nil

        do {
            async let digestResponse = api.fetchTodayDigest(timeoutInterval: 75)
            async let holdingsResponse = api.fetchHoldings()
            async let preferencesResponse = api.fetchPreferences()
            async let latestRunResponse = api.fetchLatestAnalysisRun()

            let digest = try await digestResponse
            let holdings = try await holdingsResponse
            let preferences = try await preferencesResponse
            let latestRun = try await latestRunResponse

            self.todayDigest = digest.digest ?? digest.generatedDigest ?? digest.savedDigest
            self.holdings = holdings
            self.activeRun = digest.analysisRun ?? latestRun
            self.summaryLength = DigestLengthOption(rawValue: preferences.summaryLength?.lowercased() ?? "standard") ?? .standard
            self.subscriptionTier = preferences.subscriptionTier?.lowercased() ?? "free"
        } catch {
            self.errorMessage = ClavisCopy.Errors.digestLoad(error)
        }

        if showLoading {
            isLoading = false
        }
    }

    func reloadDigestFromDatabase() async {
        await loadDigest(showLoading: false)
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
}
