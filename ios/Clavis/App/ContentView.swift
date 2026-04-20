import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var hasCheckedSession = false

    var body: some View {
        Group {
            if authViewModel.isLoadingPreferences && !hasCheckedSession {
                LoadingView()
            } else if authViewModel.isAuthenticated {
                if authViewModel.hasCompletedOnboarding {
                    MainTabView()
                } else {
                    OnboardingContainerView()
                }
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
        .onChange(of: authViewModel.isAuthenticated) { _, isAuth in
            if !isAuth {
                hasCheckedSession = false
            }
        }
        .preferredColorScheme(.dark)
    }
}

struct LoadingView: View {
    var body: some View {
        ZStack {
            Color.backgroundPrimary.ignoresSafeArea()
            ProgressView()
                .tint(.informational)
                .scaleEffect(1.2)
        }
    }
}
