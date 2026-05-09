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
                print("[Onboarding] Starting acknowledgeOnboarding")
                print("[Onboarding] Auth token present: \(await SupabaseAuthService.shared.getAccessToken() != nil)")
                try await api.acknowledgeOnboarding()
                print("[Onboarding] acknowledgeOnboarding succeeded")
                completion()
            } catch let error as APIError {
                print("[Onboarding] APIError: \(error.localizedDescription)")
                switch error {
                case .unauthorized:
                    errorMessage = "Session expired — please sign in again."
                case .serverError(let code):
                    errorMessage = "Server error (\(code)). Please try again."
                case .networkError:
                    errorMessage = "No connection — please check your internet and try again."
                default:
                    errorMessage = "Couldn't complete setup — please check your connection and try again."
                }
                isCompleting = false
            } catch {
                print("[Onboarding] Unexpected error: \(error.localizedDescription)")
                errorMessage = "Couldn't complete setup — please check your connection and try again."
                isCompleting = false
            }
        }
    }
}
