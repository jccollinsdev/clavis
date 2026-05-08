import Foundation
import SwiftUI

@MainActor
class AlertsViewModel: ObservableObject {
    @Published var alerts: [Alert] = []
    @Published var holdings: [Position] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var quietHoursEnabled = false
    @Published var quietHoursStart: String?
    @Published var quietHoursEnd: String?

    private let api = APIService.shared
    func loadAlerts() async {
        isLoading = true
        errorMessage = nil

        do {
            async let alertsResponse = api.fetchAlerts()
            async let holdingsResponse = api.fetchHoldings()
            async let preferencesResponse = api.fetchPreferences()

            alerts = try await alertsResponse
            holdings = (try? await holdingsResponse) ?? []
            let preferences = try await preferencesResponse
            quietHoursEnabled = preferences.quietHoursEnabled ?? false
            quietHoursStart = preferences.quietHoursStart
            quietHoursEnd = preferences.quietHoursEnd
        } catch is CancellationError {
            errorMessage = nil
        } catch {
            errorMessage = ClavisCopy.Errors.alertsLoad(error)
        }

        isLoading = false
    }

    var sortedAlerts: [Alert] {
        alerts.sorted { $0.createdAt > $1.createdAt }
    }

    func positionId(for ticker: String?) -> String? {
        guard let ticker else { return nil }
        return holdings.first(where: { $0.ticker.caseInsensitiveCompare(ticker) == .orderedSame })?.id
    }

    var unreadCount: Int {
        alerts.prefix(4).count
    }

    var quietHoursBannerText: String? {
        guard quietHoursEnabled, let quietHoursEnd else { return nil }
        return "Quiet hours active until \(quietHoursEnd) — alerts queued"
    }
}
