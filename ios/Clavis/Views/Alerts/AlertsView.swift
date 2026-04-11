import SwiftUI

struct AlertsView: View {
    @StateObject private var viewModel = AlertsViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    if viewModel.isLoading && viewModel.alerts.isEmpty {
                        ClavisLoadingCard(title: "Loading alerts", subtitle: "Checking recent alert activity.")
                    } else if viewModel.alerts.isEmpty {
                        AlertsEmptyStateCard()
                    } else {
                        ForEach(viewModel.groupAlerts()) { group in
                            AlertGroupCard(group: group)
                        }
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.largeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Alerts")
            .navigationBarTitleDisplayMode(.large)
            .refreshable {
                await viewModel.loadAlerts()
            }
            .onAppear {
                if viewModel.alerts.isEmpty && !viewModel.isLoading {
                    Task { await viewModel.loadAlerts() }
                }
            }
        }
    }
}

struct AlertGroup: Identifiable {
    let id: String
    let type: AlertType
    let ticker: String?
    let alerts: [Alert]
    let latestTimestamp: Date
}

struct AlertGroupCard: View {
    let group: AlertGroup

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            HStack {
                Text(group.ticker ?? group.type.displayName)
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Spacer()
                Text(group.latestTimestamp.formatted(date: .abbreviated, time: .shortened))
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }

            ForEach(group.alerts) { alert in
                Text(alert.message.sanitizedDisplayText)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct AlertsEmptyStateCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text("No alerts")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)
            Text("You don't have any recent alerts.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}
