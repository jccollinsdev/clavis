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
    private var sessionExpiredObserver: NSObjectProtocol?

    init() {
        // Observe session-expired notifications posted by APIService after a
        // final 401-after-refresh. Force sign-out so the user can re-authenticate
        // instead of being stuck on an error screen with no way forward.
        sessionExpiredObserver = NotificationCenter.default.addObserver(
            forName: .clavixSessionExpired,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            guard let self else { return }
            print("[Auth] clavixSessionExpired received — clearing local session")
            Task { @MainActor in
                // The token is expired so a normal signOut() call would itself
                // get a 401 and fail before clearing Keychain. Use the local-only
                // path so the SDK removes the stored session unconditionally.
                await self.authService.clearLocalSession()
                self.isAuthenticated = false
                self.hasCompletedOnboarding = false
            }
        }
    }

    func checkSession() async {
        isAuthenticated = await authService.checkSession()
        if isAuthenticated {
            #if DEBUG
            if authService.isUsingDebugBypass {
                hasCompletedOnboarding = true
                subscriptionTier = "free"
                return
            }
            #endif
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
            let sessionEstablished = try await authService.signUp(email: email, password: password)
            if sessionEstablished {
                isAuthenticated = true
                hasCompletedOnboarding = false
                await checkOnboardingStatus()
            } else {
                // Supabase requires email confirmation — no session yet.
                // Don't enter the app; user must verify email then sign in.
                statusMessage = "Check your email and click the verification link, then sign in."
            }
        } catch let error as NSError {
            errorMessage = error.localizedDescription
            print("[Auth] signUp error: \(error)")
        } catch {
            errorMessage = error.localizedDescription
            print("[Auth] signUp error: \(error)")
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
        } catch {
            // Server-side revocation failed (e.g. expired token causes 401).
            // Fall back to local-only sign-out so the Keychain entry is cleared
            // regardless of the server response.
            await authService.clearLocalSession()
        }
        isAuthenticated = false
        hasCompletedOnboarding = false
    }

    func checkOnboardingStatus() async {
        isLoadingPreferences = true
        do {
            let prefs = try await api.fetchPreferences()
            hasCompletedOnboarding = prefs.hasCompletedOnboarding ?? false
            subscriptionTier = prefs.subscriptionTier ?? "free"
        } catch let error as APIError {
            print("[Auth] checkOnboardingStatus failed: \(error.localizedDescription)")
            if case .unauthorized = error {
                print("[Auth] 401 after token refresh — preserving onboarding state")
            } else {
                hasCompletedOnboarding = false
                subscriptionTier = "free"
            }
        } catch {
            print("[Auth] checkOnboardingStatus failed: \(error.localizedDescription)")
            hasCompletedOnboarding = false
            subscriptionTier = "free"
        }
        isLoadingPreferences = false
    }

    func markOnboardingComplete() {
        hasCompletedOnboarding = true
    }

    // Called when the OS delivers a clavis://auth/callback URL (email confirm or password reset).
    // Exchanges the PKCE code for a session, then determines where to route the user.
    func handleAuthDeepLink(url: URL) async {
        do {
            try await authService.handleAuthCallback(url: url)
            print("[Auth] handleAuthDeepLink session established from url=\(url.absoluteString)")
            isAuthenticated = true
            await checkOnboardingStatus()
        } catch {
            print("[Auth] handleAuthDeepLink failed: \(error)")
            errorMessage = "Email confirmation failed. Please try signing in directly."
        }
    }
}
