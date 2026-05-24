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
            ZStack {
                // Keep each tab's view alive so navigation state survives tab switches.
                DigestView(selectedTab: $selectedTab)
                    .opacity(selectedTab == 0 ? 1 : 0)
                    .allowsHitTesting(selectedTab == 0)

                HoldingsListView(selectedTab: $selectedTab, deepLinkTicker: $pendingTickerDetail)
                    .opacity(selectedTab == 1 ? 1 : 0)
                    .allowsHitTesting(selectedTab == 1)

                SearchView()
                    .opacity(selectedTab == 2 ? 1 : 0)
                    .allowsHitTesting(selectedTab == 2)

                AlertsView(selectedTab: $selectedTab)
                    .opacity(selectedTab == 3 ? 1 : 0)
                    .allowsHitTesting(selectedTab == 3)

                SettingsView()
                    .opacity(selectedTab == 4 ? 1 : 0)
                    .allowsHitTesting(selectedTab == 4)
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
