import SwiftUI
import UIKit

struct MainTabView: View {
    @AppStorage("clavix.selectedTab") private var selectedTab = 0
    @State private var pendingTickerDetail: String?

    init() {
        let navAppearance = UINavigationBarAppearance()
        navAppearance.configureWithOpaqueBackground()
        navAppearance.backgroundColor = UIColor(Color.backgroundPrimary)
        navAppearance.shadowColor = .clear
        navAppearance.titleTextAttributes = [
            .foregroundColor: UIColor(Color.textPrimary),
            .font: UIFont(name: "Inter", size: 17) ?? UIFont.systemFont(ofSize: 17, weight: .medium)
        ]
        navAppearance.largeTitleTextAttributes = [
            .foregroundColor: UIColor(Color.textPrimary)
        ]
        UINavigationBar.appearance().standardAppearance = navAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navAppearance
        UINavigationBar.appearance().compactAppearance = navAppearance

        let tabAppearance = UITabBarAppearance()
        tabAppearance.configureWithOpaqueBackground()
        tabAppearance.backgroundColor = UIColor(Color.surface)
        tabAppearance.shadowColor = UIColor(Color.border)

        let selectedColor = UIColor(Color.textPrimary)
        let normalColor = UIColor(Color.textSecondary)
        let compactFont = UIFont(name: "Inter", size: 10) ?? UIFont.systemFont(ofSize: 10, weight: .medium)
        let selectedFont = UIFont(name: "Inter", size: 10) ?? UIFont.systemFont(ofSize: 10, weight: .semibold)
        let appearances = [
            tabAppearance.stackedLayoutAppearance,
            tabAppearance.inlineLayoutAppearance,
            tabAppearance.compactInlineLayoutAppearance,
        ]

        for appearance in appearances {
            appearance.normal.iconColor = normalColor
            appearance.normal.titleTextAttributes = [
                .foregroundColor: normalColor,
                .font: compactFont,
            ]
            appearance.selected.iconColor = selectedColor
            appearance.selected.titleTextAttributes = [
                .foregroundColor: selectedColor,
                .font: selectedFont,
            ]
        }

        UITabBar.appearance().standardAppearance = tabAppearance
        UITabBar.appearance().scrollEdgeAppearance = tabAppearance
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView(selectedTab: $selectedTab)
                .tabItem {
                    Label("Home", systemImage: "house")
                }
                .tag(0)

            HoldingsListView(selectedTab: $selectedTab, deepLinkTicker: $pendingTickerDetail)
                .tabItem {
                    Label("Holdings", systemImage: "briefcase")
                }
                .tag(1)

            DigestView(selectedTab: $selectedTab)
                .tabItem {
                    Label("Digest", systemImage: "doc.text")
                }
                .tag(2)

            AlertsView(selectedTab: $selectedTab)
                .tabItem {
                    Label("Alerts", systemImage: "bell")
                }
                .tag(3)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape")
                }
                .tag(4)
        }
        .tint(Color.textPrimary)
        .onReceive(NotificationCenter.default.publisher(for: .openDigest)) { _ in
            selectedTab = 2
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
