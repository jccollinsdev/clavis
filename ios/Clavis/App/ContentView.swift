import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var hasCheckedSession = false

    var body: some View {
        Group {
            if debugVisualQAEnabled {
                ClavixVisualQARoot(open: debugVisualQAOpen)
            } else if authViewModel.isLoadingPreferences && !hasCheckedSession {
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
            guard !debugVisualQAEnabled else { return }
            guard !hasCheckedSession else { return }
            hasCheckedSession = true

            Task {
                await authViewModel.checkSession()
            }
        }
        .onChange(of: authViewModel.isAuthenticated) { isAuth in
            if !isAuth {
                hasCheckedSession = false
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .supabaseAuthCallbackReceived)) { notification in
            guard !debugVisualQAEnabled else { return }
            guard let url = notification.object as? URL else { return }
            Task { await authViewModel.handleAuthDeepLink(url: url) }
        }
        .preferredColorScheme(.light)
    }

    // Live tabs are now the default everywhere. The static VisualQA mock is
    // reachable in DEBUG only by explicitly setting CLAVIX_USE_VQA_MOCK=1.
    private var debugVisualQAEnabled: Bool {
        #if DEBUG
        ProcessInfo.processInfo.environment["CLAVIX_USE_VQA_MOCK"] == "1"
        #else
        false
        #endif
    }

    private var debugVisualQAOpen: String? {
        #if DEBUG
        ProcessInfo.processInfo.environment["CLAVIX_DEBUG_OPEN"]
        #else
        nil
        #endif
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
