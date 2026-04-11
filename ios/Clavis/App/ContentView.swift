import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var hasCheckedSession = false

    var body: some View {
        Group {
            if authViewModel.isAuthenticated {
                MainTabView()
            } else {
                LoginView()
            }
        }
        .onAppear {
            guard !hasCheckedSession else { return }
            hasCheckedSession = true

            Task {
                await authViewModel.checkSession()
            }
        }
    }
}
