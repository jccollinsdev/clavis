import SwiftUI
import UIKit

/// Custom tab shell that uses `ClavixTabBar` for the bottom bar, so the
/// chrome matches `ClavixVisualQA` exactly (cream/paper, no iOS rounded pill).
/// Replaces SwiftUI `TabView` whose chrome can't be styled to the VQA spec.
struct MainTabView: View {
    @AppStorage("clavix.selectedTab") private var selectedTab = 0
    @State private var pendingTickerDetail: String?
    @State private var mountedTabs: Set<Int> = []

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
                cachedTab(0) {
                    DigestView(selectedTab: $selectedTab)
                }
                cachedTab(1) {
                    HoldingsListView(selectedTab: $selectedTab, deepLinkTicker: $pendingTickerDetail)
                }
                cachedTab(2) {
                    SearchView()
                }
                cachedTab(3) {
                    AlertsView(selectedTab: $selectedTab)
                }
                cachedTab(4) {
                    SettingsView()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            ClavixTabBar(selectedTab: $selectedTab)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .preferredColorScheme(.light)
        .onAppear {
            mountedTabs.insert(selectedTab)
        }
        .onChange(of: selectedTab) { _, tab in
            mountedTabs.insert(tab)
        }
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

    @ViewBuilder
    private func cachedTab<Content: View>(_ index: Int, @ViewBuilder content: () -> Content) -> some View {
        if mountedTabs.contains(index) || selectedTab == index {
            content()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .opacity(selectedTab == index ? 1 : 0)
                .allowsHitTesting(selectedTab == index)
                .accessibilityHidden(selectedTab != index)
                .zIndex(selectedTab == index ? 1 : 0)
        }
    }
}
