import Foundation
import SwiftUI

@MainActor
class AuthViewModel: ObservableObject {
    @Published var isAuthenticated = false
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let authService = SupabaseAuthService.shared

    func checkSession() async {
        isAuthenticated = await authService.checkSession()
    }

    func signIn(email: String, password: String) async {
        guard !email.isEmpty, !password.isEmpty else {
            errorMessage = "Please enter email and password"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            try await authService.signIn(email: email, password: password)
            isAuthenticated = true
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

        do {
            try await authService.signUp(email: email, password: password)
            isAuthenticated = true
        } catch let error as NSError {
            errorMessage = error.localizedDescription
            print("Sign up error: \(error)")
        } catch {
            errorMessage = error.localizedDescription
            print("Sign up error: \(error)")
        }

        isLoading = false
    }

    func signOut() async {
        do {
            try await authService.signOut()
            isAuthenticated = false
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}