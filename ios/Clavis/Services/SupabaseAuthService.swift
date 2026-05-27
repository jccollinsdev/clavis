import Foundation
import Supabase

extension Notification.Name {
    static let supabaseAuthCallbackReceived = Notification.Name("supabaseAuthCallbackReceived")
}

class SupabaseAuthService {
    static let shared = SupabaseAuthService()

    private let supabase: SupabaseClient
    private let processInfo = ProcessInfo.processInfo

    private init() {
        supabase = SupabaseClient(
            supabaseURL: URL(string: Config.supabaseUrl)!,
            supabaseKey: Config.supabaseAnonKey
        )
    }

    private var debugBypassToken: String? {
        #if DEBUG
        guard debugFlag(envKey: "CLAVIX_DEBUG_AUTH_BYPASS", argumentKey: "--clavix-debug-auth-bypass") else { return nil }
        let raw = debugValue(envKey: "CLAVIX_DEBUG_JWT", argumentKey: "--clavix-debug-jwt")
        guard let raw, !raw.isEmpty else { return nil }
        return raw
        #else
        return nil
        #endif
    }

    private var debugBypassEmail: String? {
        #if DEBUG
        guard debugBypassToken != nil else { return nil }
        let raw = debugValue(envKey: "CLAVIX_DEBUG_USER_EMAIL", argumentKey: "--clavix-debug-user-email")
        guard let raw, !raw.isEmpty else { return nil }
        return raw
        #else
        return nil
        #endif
    }

    private var debugBypassUserId: String? {
        #if DEBUG
        guard debugBypassToken != nil else { return nil }
        let raw = debugValue(envKey: "CLAVIX_DEBUG_USER_ID", argumentKey: "--clavix-debug-user-id")
        guard let raw, !raw.isEmpty else { return nil }
        return raw
        #else
        return nil
        #endif
    }

    var client: SupabaseClient {
        return supabase
    }

    #if DEBUG
    private func debugFlag(envKey: String, argumentKey: String) -> Bool {
        let envValue = processInfo.environment[envKey]?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if envValue == "1" || envValue == "true" || envValue == "yes" {
            return true
        }
        return processInfo.arguments.contains(argumentKey)
    }

    private func debugValue(envKey: String, argumentKey: String) -> String? {
        if let envValue = processInfo.environment[envKey]?.trimmingCharacters(in: .whitespacesAndNewlines),
           !envValue.isEmpty {
            return envValue
        }

        let arguments = processInfo.arguments
        guard let index = arguments.firstIndex(of: argumentKey) else { return nil }
        let valueIndex = arguments.index(after: index)
        guard valueIndex < arguments.endIndex else { return nil }
        let raw = arguments[valueIndex].trimmingCharacters(in: .whitespacesAndNewlines)
        return raw.isEmpty ? nil : raw
    }
    #endif

    var isUsingDebugBypass: Bool {
        #if DEBUG
        debugBypassToken != nil
        #else
        false
        #endif
    }

    @MainActor
    func signIn(email: String, password: String) async throws {
        let session = try await supabase.auth.signIn(email: email, password: password)
        print("Signed in: \(session.user.id)")
    }

    @MainActor
    func signUp(email: String, password: String) async throws -> Bool {
        let response = try await supabase.auth.signUp(
            email: email,
            password: password,
            redirectTo: URL(string: "https://getclavix.com/confirm")
        )
        let sessionEstablished = response.session != nil
        print("[Auth] signUp userId=\(response.user.id) sessionEstablished=\(sessionEstablished)")
        return sessionEstablished
    }

    @MainActor
    func refreshSession() async throws {
        if debugBypassToken != nil {
            return
        }
        try await supabase.auth.refreshSession()
    }

    @MainActor
    func signOut() async throws {
        if debugBypassToken != nil {
            return
        }
        try await supabase.auth.signOut()
    }

    @MainActor
    func resetPassword(email: String) async throws {
        try await supabase.auth.resetPasswordForEmail(
            email,
            redirectTo: URL(string: "https://getclavix.com/confirm")
        )
    }

    // Called from AppDelegate when the OS opens a clavis://auth/callback URL.
    // Exchanges the PKCE authorization code for a live session.
    @MainActor
    func handleAuthCallback(url: URL) async throws {
        try await supabase.auth.session(from: url)
    }

    @MainActor
    func checkSession() async -> Bool {
        if debugBypassToken != nil {
            return true
        }
        do {
            _ = try await supabase.auth.session
            return true
        } catch {
            return false
        }
    }

    @MainActor
    func getAccessToken() async -> String? {
        if let debugBypassToken {
            return debugBypassToken
        }
        do {
            let session = try await supabase.auth.session
            return session.accessToken
        } catch {
            return nil
        }
    }

    @MainActor
    func getUserId() async -> String? {
        if let debugBypassUserId {
            return debugBypassUserId
        }
        do {
            let user = try await supabase.auth.user()
            return user.id.uuidString
        } catch {
            return nil
        }
    }

    @MainActor
    func getUserEmail() async -> String? {
        if let debugBypassEmail {
            return debugBypassEmail
        }
        do {
            let user = try await supabase.auth.user()
            return user.email
        } catch {
            return nil
        }
    }
}
