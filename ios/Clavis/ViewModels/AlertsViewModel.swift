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

    // Local "last seen" tracking until backend ships alerts.read_at (P1).
    private let lastSeenKey = "clavix.alerts.lastSeenAt"

    private var lastSeenAt: Date? {
        get { UserDefaults.standard.object(forKey: lastSeenKey) as? Date }
        set { UserDefaults.standard.set(newValue, forKey: lastSeenKey) }
    }

    /// Public read-only accessor so views can dim/highlight rows.
    var lastSeenAtPublic: Date? { lastSeenAt }

    func loadAlerts() async {
        isLoading = true
        errorMessage = nil

        do {
            alerts = try await api.fetchAlerts()
            errorMessage = nil

            Task {
                let loadedHoldings = (try? await api.fetchHoldings()) ?? []
                let preferences = try? await api.fetchPreferences()

                await MainActor.run {
                    holdings = loadedHoldings
                    quietHoursEnabled = preferences?.quietHoursEnabled ?? false
                    quietHoursStart = preferences?.quietHoursStart
                    quietHoursEnd = preferences?.quietHoursEnd
                }
            }
        } catch is CancellationError {
            errorMessage = nil
        } catch {
            print("Failed to load alerts: \(error)")
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

    /// Alerts newer than the locally-stored last-seen timestamp. When the user
    /// has never opened the alerts screen, every alert counts as unread.
    var unreadCount: Int {
        guard !alerts.isEmpty else { return 0 }
        let cutoff = lastSeenAt
        if let cutoff {
            return alerts.filter { $0.createdAt > cutoff }.count
        }
        return alerts.count
    }

    /// Call when the user opens the alerts screen so future loads reflect
    /// "new since last visit".
    func markAlertsSeen() {
        let mostRecent = alerts.map(\.createdAt).max() ?? Date()
        lastSeenAt = mostRecent
        objectWillChange.send()
    }

    var quietHoursBannerText: String? {
        guard quietHoursEnabled, let quietHoursEnd else { return nil }
        return "Quiet hours active until \(quietHoursEnd) — alerts queued"
    }
}
