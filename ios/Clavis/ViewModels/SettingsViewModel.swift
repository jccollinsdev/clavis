import Foundation
import SwiftUI

enum SummaryLength: String, CaseIterable {
    case brief = "Brief"
    case standard = "Standard"
    case full = "Full"
}

@MainActor
class SettingsViewModel: ObservableObject {
    @Published var digestTime = Date()
    @Published var notificationsEnabled = true
    @Published var summaryLength: SummaryLength = .standard
    @Published var weekdayOnly = false
    @Published var alertsGradeChanges = true
    @Published var alertsMajorEvents = true
    @Published var alertsPortfolioRisk = true
    @Published var quietHoursEnabled = false
    @Published var quietHoursStart = Calendar.current.date(from: DateComponents(hour: 22, minute: 0)) ?? Date()
    @Published var quietHoursEnd = Calendar.current.date(from: DateComponents(hour: 7, minute: 0)) ?? Date()
    @Published var userEmail: String = "Loading..."
    @Published var isLoading = false

    private let api = APIService.shared

    func load() async {
        isLoading = true
        userEmail = await SupabaseAuthService.shared.getUserEmail() ?? "Unknown"

        do {
            let prefs = try await api.fetchPreferences()
            if let timeStr = prefs.digestTime {
                let parts = timeStr.split(separator: ":")
                if parts.count >= 2,
                   let hour = Int(parts[0]),
                   let minute = Int(parts[1]) {
                    var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
                    components.hour = hour
                    components.minute = minute
                    if let date = Calendar.current.date(from: components) {
                        digestTime = date
                    }
                }
            }
            if let enabled = prefs.notificationsEnabled {
                notificationsEnabled = enabled
            }
        } catch {
            print("Failed to load preferences: \(error)")
        }

        isLoading = false
    }

    func saveDigestTime() async {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        let timeStr = formatter.string(from: digestTime)
        do {
            try await api.updatePreferences(
                digestTime: timeStr,
                notificationsEnabled: nil,
                summaryLength: summaryLength.rawValue.lowercased(),
                weekdayOnly: weekdayOnly
            )
        } catch {
            print("Failed to save digest time: \(error)")
        }
    }

    func saveNotifications() async {
        do {
            try await api.updatePreferences(
                digestTime: nil,
                notificationsEnabled: notificationsEnabled,
                summaryLength: nil,
                weekdayOnly: nil
            )
        } catch {
            print("Failed to save notifications: \(error)")
        }
    }

    func saveSummaryLength() async {
        do {
            try await api.updatePreferences(
                digestTime: nil,
                notificationsEnabled: nil,
                summaryLength: summaryLength.rawValue.lowercased(),
                weekdayOnly: nil
            )
        } catch {
            print("Failed to save summary length: \(error)")
        }
    }

    func saveWeekdayOnly() async {
        do {
            try await api.updatePreferences(
                digestTime: nil,
                notificationsEnabled: nil,
                summaryLength: nil,
                weekdayOnly: weekdayOnly
            )
        } catch {
            print("Failed to save weekday only: \(error)")
        }
    }

    func saveAlertSettings() async {
        do {
            try await api.updateAlertPreferences(
                gradeChanges: alertsGradeChanges,
                majorEvents: alertsMajorEvents,
                portfolioRisk: alertsPortfolioRisk,
                quietHoursEnabled: quietHoursEnabled,
                quietHoursStart: quietHoursStart,
                quietHoursEnd: quietHoursEnd
            )
        } catch {
            print("Failed to save alert settings: \(error)")
        }
    }
}
