import Foundation
import SwiftUI

@MainActor
class AuthViewModel: ObservableObject {
    @Published var isAuthenticated = false
    @Published var isLoading = false
    @Published var isLoadingPreferences = false
    @Published var hasCompletedOnboarding = false
    @Published var subscriptionTier = "free"
    @Published var errorMessage: String?
    @Published var statusMessage: String?

    private let authService = SupabaseAuthService.shared
    private let api = APIService.shared

    func checkSession() async {
        isAuthenticated = await authService.checkSession()
        if isAuthenticated {
            await checkOnboardingStatus()
        }
    }

    func signIn(email: String, password: String) async {
        guard !email.isEmpty, !password.isEmpty else {
            errorMessage = "Please enter email and password"
            return
        }

        isLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            try await authService.signIn(email: email, password: password)
            isAuthenticated = true
            await checkOnboardingStatus()
        } catch let error as NSError {
            errorMessage = error.localizedDescription
            print("Sign in error: \(error)")
        } catch {
            errorMessage = error.localizedDescription
            print("Sign in error: \(error)")
        }

        isLoading = false
    }

    func signUp(email: String, password: String) async {
        guard !email.isEmpty, !password.isEmpty else {
            errorMessage = "Please enter email and password"
            return
        }

        guard password.count >= 6 else {
            errorMessage = "Password must be at least 6 characters"
            return
        }

        isLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            try await authService.signUp(email: email, password: password)
            isAuthenticated = true
            hasCompletedOnboarding = false
            await checkOnboardingStatus()
        } catch let error as NSError {
            errorMessage = error.localizedDescription
            print("Sign up error: \(error)")
        } catch {
            errorMessage = error.localizedDescription
            print("Sign up error: \(error)")
        }

        isLoading = false
    }

    func resetPassword(email: String) async {
        guard !email.isEmpty else {
            errorMessage = "Please enter your email address"
            return
        }

        isLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            try await authService.resetPassword(email: email)
            statusMessage = "Password reset email sent."
        } catch let error as NSError {
            errorMessage = error.localizedDescription
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func signOut() async {
        do {
            try await authService.signOut()
            isAuthenticated = false
            hasCompletedOnboarding = false
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func checkOnboardingStatus() async {
        isLoadingPreferences = true
        do {
            let prefs = try await api.fetchPreferences()
            hasCompletedOnboarding = prefs.hasCompletedOnboarding ?? false
            subscriptionTier = prefs.subscriptionTier ?? "free"
        } catch {
            hasCompletedOnboarding = false
            subscriptionTier = "free"
        }
        isLoadingPreferences = false
    }

    func markOnboardingComplete() {
        hasCompletedOnboarding = true
    }
}
