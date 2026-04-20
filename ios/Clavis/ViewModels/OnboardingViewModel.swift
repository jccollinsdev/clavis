import Foundation
import SwiftUI
import UserNotifications

@MainActor
class OnboardingViewModel: ObservableObject {
    @Published var currentPage: OnboardingPage = .welcome
    @Published var name: String = ""
    @Published var dateOfBirthText: String = ""
    @Published var morningDigestEnabled = true
    @Published var alertsGradeChangesEnabled = true
    @Published var alertsMajorEventsEnabled = true
    @Published var alertsLargePriceMovesEnabled = false
    @Published var isCompleting = false
    @Published var errorMessage: String?

    private let api = APIService.shared

    func nextPage() {
        guard let nextIndex = OnboardingPage(rawValue: currentPage.rawValue + 1) else {
            return
        }
        withAnimation(.easeInOut(duration: 0.3)) {
            currentPage = nextIndex
        }
    }

    func previousPage() {
        guard let prevIndex = OnboardingPage(rawValue: currentPage.rawValue - 1) else {
            return
        }
        withAnimation(.easeInOut(duration: 0.3)) {
            currentPage = prevIndex
        }
    }

    func saveProfile() async throws {
        guard !name.isEmpty else { return }
        let birthYear = parseBirthYear(from: dateOfBirthText)
        try await api.updateProfile(name: name, birthYear: birthYear)
    }

    func completeOnboarding(completion: @escaping () -> Void) {
        guard !isCompleting else { return }
        isCompleting = true

        Task {
            do {
                try await saveProfile()
                try await api.updatePreferences(
                    digestTime: nil,
                    notificationsEnabled: morningDigestEnabled,
                    summaryLength: nil,
                    weekdayOnly: nil
                )
                try await api.updateAlertPreferences(
                    gradeChanges: alertsGradeChangesEnabled,
                    majorEvents: alertsMajorEventsEnabled,
                    portfolioRisk: true,
                    largePriceMoves: alertsLargePriceMovesEnabled,
                    quietHoursEnabled: false,
                    quietHoursStart: Date(),
                    quietHoursEnd: Date()
                )
                try await api.acknowledgeOnboarding()
                completion()
            } catch {
                errorMessage = error.localizedDescription
                isCompleting = false
            }
        }
    }

    private func parseBirthYear(from text: String) -> Int? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        let digits = trimmed.filter(
            { $0.isNumber }
        )
        if digits.count >= 4, let year = Int(digits.suffix(4)) {
            return year
        }

        return Int(trimmed)
    }

    func isValidDateOfBirth(_ text: String) -> Bool {
        let digits = text.filter(\.isNumber)
        guard digits.count == 8 else { return false }

        let dayText = String(digits.prefix(2))
        let monthText = String(digits.dropFirst(2).prefix(2))
        let yearText = String(digits.suffix(4))

        guard let day = Int(dayText),
              let month = Int(monthText),
              let year = Int(yearText),
              year > 1900 else {
            return false
        }

        var components = DateComponents()
        components.day = day
        components.month = month
        components.year = year

        guard let date = Calendar.current.date(from: components) else { return false }

        let now = Date()
        guard date <= now else { return false }

        let age = Calendar.current.dateComponents([.year], from: date, to: now).year ?? 0
        return age >= 18
    }
}
