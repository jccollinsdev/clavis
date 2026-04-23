import SwiftUI
import Network

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
        .preferredColorScheme(.dark)
    }
}

@MainActor
final class NetworkStatusMonitor: ObservableObject {
    static let shared = NetworkStatusMonitor()

    @Published private(set) var isOffline = false

    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "clavis.network.monitor")

    private init() {
        monitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in
                self?.isOffline = path.status != .satisfied
            }
        }
        monitor.start(queue: queue)
    }
}

struct OfflineStatusBanner: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Offline")
                .font(.system(size: 15, weight: .semibold))
                .foregroundColor(.red)
            Text("Showing cached data. Actions will retry when the network returns.")
                .font(.system(size: 15))
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(12)
        .background(Color(white: 0.14))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color(white: 0.28), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
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
