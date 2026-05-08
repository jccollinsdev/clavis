import Foundation
import SwiftUI

enum OnboardingPage: Int, CaseIterable {
    case welcome = 0
    case addPortfolio = 1
}

@MainActor
final class OnboardingViewModel: ObservableObject {
    @Published var currentPage: OnboardingPage = .welcome
    @Published var isCompleting = false
    @Published var errorMessage: String?

    private let api = APIService.shared

    func nextPage() {
        withAnimation(.easeInOut(duration: 0.2)) {
            currentPage = .addPortfolio
        }
    }

    func previousPage() {
        withAnimation(.easeInOut(duration: 0.2)) {
            currentPage = .welcome
        }
    }

    func completeOnboarding(completion: @escaping () -> Void) {
        guard !isCompleting else { return }
        isCompleting = true
        errorMessage = nil

        Task {
            do {
                try await api.acknowledgeOnboarding()
                completion()
            } catch {
                errorMessage = "Couldn't complete setup — please check your connection and try again."
                isCompleting = false
            }
        }
    }
}
