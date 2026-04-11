import Foundation
import Supabase

class SupabaseAuthService {
    static let shared = SupabaseAuthService()

    private let supabase: SupabaseClient

    private init() {
        supabase = SupabaseClient(
            supabaseURL: URL(string: Config.supabaseUrl)!,
            supabaseKey: Config.supabaseAnonKey
        )
    }

    var client: SupabaseClient {
        return supabase
    }

    @MainActor
    func signIn(email: String, password: String) async throws {
        let session = try await supabase.auth.signIn(email: email, password: password)
        print("Signed in: \(session.user.id)")
    }

    @MainActor
    func signUp(email: String, password: String) async throws {
        let session = try await supabase.auth.signUp(
            email: email,
            password: password
        )
        print("Signed up: \(session.user.id)")
    }

    @MainActor
    func signOut() async throws {
        try await supabase.auth.signOut()
    }

    @MainActor
    func checkSession() async -> Bool {
        do {
            _ = try await supabase.auth.session
            return true
        } catch {
            return false
        }
    }

    @MainActor
    func getAccessToken() async -> String? {
        do {
            let session = try await supabase.auth.session
            return session.accessToken
        } catch {
            return nil
        }
    }

    @MainActor
    func getUserId() async -> String? {
        do {
            let user = try await supabase.auth.user()
            return user.id.uuidString
        } catch {
            return nil
        }
    }

    @MainActor
    func getUserEmail() async -> String? {
        do {
            let user = try await supabase.auth.user()
            return user.email
        } catch {
            return nil
        }
    }
}