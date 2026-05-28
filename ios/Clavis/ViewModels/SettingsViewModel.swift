import Foundation
import SwiftUI

enum SummaryLength: String, CaseIterable {
    case brief = "Brief"
    case standard = "Standard"
    case verbose = "Verbose"
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
    @Published var alertsLargePriceMoves = false
    @Published var quietHoursEnabled = false
    @Published var quietHoursStart = Calendar.current.date(from: DateComponents(hour: 22, minute: 0)) ?? Date()
    @Published var quietHoursEnd = Calendar.current.date(from: DateComponents(hour: 7, minute: 0)) ?? Date()
    @Published var userEmail: String = "Loading..."
    @Published var userName: String = ""
    @Published var birthYear: Int?
    @Published var subscriptionTier: String = "free"
    @Published var isLoading = false
    @Published var accountMessage: String?
    @Published var preferencesMessage: String?
    @Published var isExportingAccount = false
    @Published var isDeletingAccount = false

    private let api = APIService.shared
    private var isHydrating = false

    func load() async {
        isLoading = true
        isHydrating = true
        accountMessage = nil
        preferencesMessage = nil
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
            userName = prefs.name ?? ""
            birthYear = prefs.birthYear
            subscriptionTier = prefs.subscriptionTier?.lowercased() ?? "free"
            if let sl = prefs.summaryLength, let length = SummaryLength(rawValue: sl.capitalized) {
                summaryLength = length
            }
            if let wo = prefs.weekdayOnly {
                weekdayOnly = wo
            }
            if let agc = prefs.alertsGradeChanges {
                alertsGradeChanges = agc
            }
            if let ame = prefs.alertsMajorEvents {
                alertsMajorEvents = ame
            }
            if let apr = prefs.alertsPortfolioRisk {
                alertsPortfolioRisk = apr
            }
            if let alpm = prefs.alertsLargePriceMoves {
                alertsLargePriceMoves = alpm
            }
            if let qhe = prefs.quietHoursEnabled {
                quietHoursEnabled = qhe
            }
            if let qhs = prefs.quietHoursStart {
                let parts = qhs.split(separator: ":")
                if parts.count >= 2, let hour = Int(parts[0]), let minute = Int(parts[1]) {
                    var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
                    components.hour = hour
                    components.minute = minute
                    if let date = Calendar.current.date(from: components) {
                        quietHoursStart = date
                    }
                }
            }
            if let qhe = prefs.quietHoursEnd {
                let parts = qhe.split(separator: ":")
                if parts.count >= 2, let hour = Int(parts[0]), let minute = Int(parts[1]) {
                    var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
                    components.hour = hour
                    components.minute = minute
                    if let date = Calendar.current.date(from: components) {
                        quietHoursEnd = date
                    }
                }
            }
        } catch {
            print("Failed to load preferences: \(error)")
            preferencesMessage = "Live settings are unavailable right now. Showing local defaults until the connection recovers."
        }

        isLoading = false

        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 500_000_000)
            isHydrating = false
        }
    }

    func exportAccount() async {
        guard !isExportingAccount else { return }
        isExportingAccount = true
        accountMessage = nil

        do {
            let data = try await api.exportAccount()
            let object = try JSONSerialization.jsonObject(with: data)
            let topLevelCount: Int
            if let dict = object as? [String: Any] {
                topLevelCount = dict.count
            } else if let array = object as? [Any] {
                topLevelCount = array.count
            } else {
                topLevelCount = 1
            }
            accountMessage = "Account export ready (\(topLevelCount) top-level items)."
        } catch {
            accountMessage = ClavisCopy.Errors.accountExport(error)
        }

        isExportingAccount = false
    }

    func deleteAccount() async -> Bool {
        guard !isDeletingAccount else { return false }
        isDeletingAccount = true
        accountMessage = nil

        do {
            _ = try await api.deleteAccount()
            isDeletingAccount = false
            return true
        } catch let error as APIError {
            switch error {
            case .unauthorized:
                accountMessage = "Session expired. Please sign out and sign in again before deleting your account."
            case .serverError:
                accountMessage = "Something went wrong on our end. Please try again or contact support."
            case .networkError:
                accountMessage = "No connection. Please check your internet and try again."
            default:
                accountMessage = ClavisCopy.Errors.accountDelete(error)
            }
        } catch {
            accountMessage = ClavisCopy.Errors.accountDelete(error)
        }

        isDeletingAccount = false
        return false
    }

    func saveDigestTime() async {
        guard !isHydrating else { return }
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
            preferencesMessage = nil
        } catch {
            print("Failed to save digest time: \(error)")
            preferencesMessage = "Couldn't save your settings. Your live preferences were not updated."
        }
    }

    func saveNotifications() async {
        guard !isHydrating else { return }
        do {
            try await api.updatePreferences(
                digestTime: nil,
                notificationsEnabled: notificationsEnabled,
                summaryLength: nil,
                weekdayOnly: nil
            )
            preferencesMessage = nil
        } catch {
            print("Failed to save notifications: \(error)")
            preferencesMessage = "Couldn't save your settings. Your live preferences were not updated."
        }
    }

    func saveSummaryLength() async {
        guard !isHydrating else { return }
        do {
            try await api.updatePreferences(
                digestTime: nil,
                notificationsEnabled: nil,
                summaryLength: summaryLength.rawValue.lowercased(),
                weekdayOnly: nil
            )
            preferencesMessage = nil
        } catch {
            print("Failed to save summary length: \(error)")
            preferencesMessage = "Couldn't save your settings. Your live preferences were not updated."
        }
    }

    func saveWeekdayOnly() async {
        guard !isHydrating else { return }
        do {
            try await api.updatePreferences(
                digestTime: nil,
                notificationsEnabled: nil,
                summaryLength: nil,
                weekdayOnly: weekdayOnly
            )
            preferencesMessage = nil
        } catch {
            print("Failed to save weekday only: \(error)")
            preferencesMessage = "Couldn't save your settings. Your live preferences were not updated."
        }
    }

    func saveAlertSettings() async {
        guard !isHydrating else { return }
        do {
            try await api.updateAlertPreferences(
                gradeChanges: alertsGradeChanges,
                majorEvents: alertsMajorEvents,
                portfolioRisk: alertsPortfolioRisk,
                largePriceMoves: nil,
                quietHoursEnabled: quietHoursEnabled,
                quietHoursStart: quietHoursStart,
                quietHoursEnd: quietHoursEnd
            )
            preferencesMessage = nil
        } catch {
            print("Failed to save alert settings: \(error)")
            preferencesMessage = "Couldn't save your settings. Your live preferences were not updated."
        }
    }

    func saveProfile(name: String, birthYear: Int?) async {
        let trimmedName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        do {
            try await api.updateProfile(
                name: trimmedName.isEmpty ? nil : trimmedName,
                birthYear: birthYear
            )
            userName = trimmedName
            self.birthYear = birthYear
            accountMessage = "Profile updated."
        } catch {
            accountMessage = "Couldn't update your profile. Your live account details were not changed."
        }
    }
}
