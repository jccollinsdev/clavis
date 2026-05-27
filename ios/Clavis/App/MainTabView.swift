import SwiftUI
import UIKit

/// Custom tab shell that uses `ClavixTabBar` for the bottom bar, so the
/// chrome matches `ClavixVisualQA` exactly (cream/paper, no iOS rounded pill).
/// Replaces SwiftUI `TabView` whose chrome can't be styled to the VQA spec.
struct MainTabView: View {
    @AppStorage("clavix.selectedTab") private var selectedTab = 0
    @State private var pendingTickerDetail: String?

    init() {
        // Keep nav bar appearance cream/paper for any sheet that does present
        // a `NavigationStack` title.
        let navAppearance = UINavigationBarAppearance()
        navAppearance.configureWithOpaqueBackground()
        navAppearance.backgroundColor = UIColor(Color.clavixPage)
        navAppearance.shadowColor = .clear
        navAppearance.titleTextAttributes = [
            .foregroundColor: UIColor(Color.clavixInk),
            .font: UIFont(name: "Inter", size: 17) ?? UIFont.systemFont(ofSize: 17, weight: .medium)
        ]
        navAppearance.largeTitleTextAttributes = [
            .foregroundColor: UIColor(Color.clavixInk)
        ]
        UINavigationBar.appearance().standardAppearance = navAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navAppearance
        UINavigationBar.appearance().compactAppearance = navAppearance
    }

    var body: some View {
        VStack(spacing: 0) {
            Group {
                switch selectedTab {
                case 0:
                    DigestView(selectedTab: $selectedTab)
                case 1:
                    HoldingsListView(selectedTab: $selectedTab, deepLinkTicker: $pendingTickerDetail)
                case 2:
                    SearchView()
                case 3:
                    AlertsView(selectedTab: $selectedTab)
                case 4:
                    SettingsView()
                default:
                    DigestView(selectedTab: $selectedTab)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            ClavixTabBar(selectedTab: $selectedTab)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .preferredColorScheme(.light)
        .onReceive(NotificationCenter.default.publisher(for: .openDigest)) { _ in
            selectedTab = 0
        }
        .onReceive(NotificationCenter.default.publisher(for: .openPositionDetail)) { notification in
            selectedTab = 1
            pendingTickerDetail = notification.object as? String
        }
        .onReceive(NotificationCenter.default.publisher(for: .positionAnalysisComplete)) { notification in
            selectedTab = 1
            pendingTickerDetail = notification.object as? String
        }
    }
}
