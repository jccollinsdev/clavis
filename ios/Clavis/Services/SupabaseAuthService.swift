import Foundation
import Supabase

extension Notification.Name {
    static let supabaseAuthCallbackReceived = Notification.Name("supabaseAuthCallbackReceived")
    /// Posted when a final 401 is received after a token-refresh attempt,
    /// indicating the session is truly invalid. Observers should sign the user out.
    static let clavixSessionExpired = Notification.Name("clavixSessionExpired")
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
            let session = try await supabase.auth.session
            let diff = Date(timeIntervalSince1970: session.expiresAt).timeIntervalSinceNow
            print("[Auth] checkSession: isExpired=\(session.isExpired) expiresAt=\(Int(session.expiresAt)) diff=\(Int(diff))s")
            if session.isExpired {
                // Access token is past its expiry — must refresh now.
                // If the refresh token is also expired this throws, which
                // correctly returns false and routes the user to login.
                print("[Auth] checkSession: token expired — attempting refresh")
                try await supabase.auth.refreshSession()
                print("[Auth] checkSession: refresh succeeded")
            } else {
                // Pre-warm: refresh while still valid so the access token is
                // fresh for the API calls that fire immediately after launch.
                _ = try? await supabase.auth.refreshSession()
            }
            return true
        } catch {
            print("[Auth] checkSession: failed — \(error)")
            return false
        }
    }

    // Clears the local Supabase session without requiring a valid server token.
    // Use this when the session is known-expired and a normal signOut() would
    // fail because the server rejects the stale access token.
    @MainActor
    func clearLocalSession() async {
        // scope: .local tells the SDK to only clear device-side storage and
        // send a best-effort server notification — it does not block on a 401.
        try? await supabase.auth.signOut(scope: .local)
    }

    @MainActor
    func getAccessToken() async -> String? {
        if let debugBypassToken {
            return debugBypassToken
        }
        do {
            let session = try await supabase.auth.session
            let diff2 = Date(timeIntervalSince1970: session.expiresAt).timeIntervalSinceNow
            print("[Auth] getAccessToken: isExpired=\(session.isExpired) diff=\(Int(diff2))s")
            if session.isExpired {
                // Token is expired but the SDK didn't auto-refresh (e.g. the
                // SDK read from storage without triggering the refresh path).
                // Force a refresh now; if it fails, return nil so the caller
                // receives a 401 and the retry/sign-out chain fires.
                print("[Auth] getAccessToken: session expired — forcing refresh")
                try await supabase.auth.refreshSession()
                let fresh = try await supabase.auth.session
                print("[Auth] getAccessToken: refresh succeeded")
                return fresh.accessToken
            }
            return session.accessToken
        } catch {
            // Session missing or refresh failed — signal no token available.
            print("[Auth] getAccessToken: failed — \(error)")
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
