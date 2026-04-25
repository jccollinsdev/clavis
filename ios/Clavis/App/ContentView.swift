import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var hasCheckedSession = false

    var body: some View {
        Group {
            if authViewModel.isLoadingPreferences && !hasCheckedSession {
                LoadingView()
            } else if authViewModel.isAuthenticated && authViewModel.isLoadingPreferences {
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
        .onReceive(NotificationCenter.default.publisher(for: .supabaseAuthCallbackReceived)) { notification in
            guard let url = notification.object as? URL else { return }
            Task { await authViewModel.handleAuthDeepLink(url: url) }
        }
        .preferredColorScheme(.dark)
    }
}

struct LoadingView: View {
    var body: some View {
        ZStack {
            Color.backgroundPrimary.ignoresSafeArea()
            VStack(spacing: 20) {
                ClavisMonogram(size: 56, cornerRadius: 14)
                ProgressView()
                    .tint(.textSecondary)
            }
        }
    }
}
