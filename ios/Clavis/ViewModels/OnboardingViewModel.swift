import Foundation
import SwiftUI

@MainActor
class OnboardingViewModel: ObservableObject {
    @Published var currentPage: OnboardingPage = .welcome
    @Published var name: String = ""
    @Published var dateOfBirth: Date = Calendar.current.date(byAdding: .year, value: -18, to: Date()) ?? Date()
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
        let birthYear = Calendar.current.component(.year, from: dateOfBirth)
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

    func isValidDateOfBirth(_ date: Date) -> Bool {
        let now = Date()
        guard date <= now else { return false }

        let age = Calendar.current.dateComponents([.year], from: date, to: now).year ?? 0
        return age >= 18
    }
}
