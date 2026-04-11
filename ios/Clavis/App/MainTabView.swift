import SwiftUI

struct MainTabView: View {
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView(selectedTab: $selectedTab)
                .tabItem {
                    Label("Home", systemImage: "chart.pie.fill")
                }
                .tag(0)

            HoldingsListView()
                .tabItem {
                    Label("Holdings", systemImage: "briefcase.fill")
                }
                .tag(1)

            DigestView()
                .tabItem {
                    Label("Digest", systemImage: "newspaper.fill")
                }
                .tag(2)

            AlertsView()
                .tabItem {
                    Label("Alerts", systemImage: "bell.fill")
                }
                .tag(3)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
                .tag(4)
        }
        .tint(Color.accentBlue)
    }
}
