import Foundation
import SwiftUI

@MainActor
class AlertsViewModel: ObservableObject {
    @Published var alerts: [Alert] = []
    @Published var holdings: [Position] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService.shared
    private let groupingWindowMinutes: Double = 60

    func loadAlerts() async {
        isLoading = true
        errorMessage = nil

        do {
            alerts = try await api.fetchAlerts()
            holdings = (try? await api.fetchHoldings()) ?? []
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func groupAlerts() -> [AlertGroup] {
        let sortedAlerts = alerts.sorted { $0.createdAt > $1.createdAt }
        var groups: [AlertGroup] = []
        var usedAlertIds: Set<String> = []

        for alert in sortedAlerts {
            if usedAlertIds.contains(alert.id) { continue }

            let similarAlerts = sortedAlerts.filter { otherAlert in
                guard otherAlert.id != alert.id,
                      !usedAlertIds.contains(otherAlert.id) else { return false }
                return shouldGroup(alert, otherAlert)
            }

            if similarAlerts.isEmpty {
                groups.append(AlertGroup(
                    id: alert.id,
                    type: alert.type,
                    ticker: alert.positionTicker,
                    positionId: positionId(for: alert.positionTicker),
                    alerts: [alert],
                    latestTimestamp: alert.createdAt
                ))
                usedAlertIds.insert(alert.id)
            } else {
                var groupAlerts = [alert]
                groupAlerts.append(contentsOf: similarAlerts)
                let allTimestamps = groupAlerts.map { $0.createdAt }
                let latestTimestamp = allTimestamps.max() ?? alert.createdAt

                groups.append(AlertGroup(
                    id: alert.id,
                    type: alert.type,
                    ticker: alert.positionTicker,
                    positionId: positionId(for: alert.positionTicker),
                    alerts: groupAlerts,
                    latestTimestamp: latestTimestamp
                ))

                usedAlertIds.insert(alert.id)
                usedAlertIds.formUnion(similarAlerts.map { $0.id })
            }
        }

        return groups.sorted { $0.latestTimestamp > $1.latestTimestamp }
    }

    var sortedAlerts: [Alert] {
        alerts.sorted { $0.createdAt > $1.createdAt }
    }

    private func shouldGroup(_ alert1: Alert, _ alert2: Alert) -> Bool {
        if alert1.type != alert2.type { return false }

        if alert1.positionTicker != alert2.positionTicker { return false }

        let timeDifference = abs(alert1.createdAt.timeIntervalSince(alert2.createdAt))
        return timeDifference <= groupingWindowMinutes * 60
    }

    func positionId(for ticker: String?) -> String? {
        guard let ticker else { return nil }
        return holdings.first(where: { $0.ticker.caseInsensitiveCompare(ticker) == .orderedSame })?.id
    }
}
