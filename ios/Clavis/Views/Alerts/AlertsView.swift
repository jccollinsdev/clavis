import SwiftUI

struct AlertsView: View {
    @StateObject private var viewModel = AlertsViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 1) {
                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                            .padding(.horizontal, ClavisTheme.screenPadding)
                            .padding(.bottom, ClavisTheme.smallSpacing)
                    }

                    if viewModel.isLoading && viewModel.alerts.isEmpty {
                        ClavisLoadingCard(title: "Loading alerts", subtitle: "Checking recent alert activity.")
                            .padding(.horizontal, ClavisTheme.screenPadding)
                    } else if viewModel.alerts.isEmpty {
                        AlertsEmptyStateCard()
                            .padding(.horizontal, ClavisTheme.screenPadding)
                    } else {
                        ForEach(viewModel.groupAlerts()) { group in
                            AlertRow(group: group)
                        }
                    }
                }
                .padding(.vertical, ClavisTheme.largeSpacing)
            }
            .background(Color.backgroundPrimary.ignoresSafeArea())
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

// MARK: - Alert Group Model

struct AlertGroup: Identifiable {
    let id: String
    let type: AlertType
    let ticker: String?
    let alerts: [Alert]
    let latestTimestamp: Date
}

// MARK: - Alert Row
// Left border encodes severity. No icons. Factual titles. — spec Step 06

struct AlertRow: View {
    let group: AlertGroup

    private var severity: AlertSeverity { group.type.severity }

    private var factualTitle: String {
        if let ticker = group.ticker {
            return "\(ticker) — \(group.type.displayName)"
        }
        return group.type.displayName
    }

    private var bodyText: String {
        let msg = group.alerts.first?.message.sanitizedDisplayText ?? ""
        let time = group.latestTimestamp.formatted(.dateTime.hour().minute())
        if msg.isEmpty { return time }
        return "\(msg) · \(time)"
    }

    var body: some View {
        HStack(spacing: 0) {
            // Left severity border — 2.5px, color = severity state
            Rectangle()
                .fill(severity.borderColor)
                .frame(width: 2.5)

            VStack(alignment: .leading, spacing: 4) {
                Text(factualTitle)
                    .font(ClavisTypography.rowTicker)
                    .foregroundColor(.textPrimary)

                Text(bodyText)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .lineLimit(2)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)

            Spacer()
        }
        .background(Color.surface)
        .overlay(
            Rectangle()
                .stroke(Color.border, lineWidth: 1)
        )
    }
}

// MARK: - Alert Severity

enum AlertSeverity {
    case critical, warning, informational

    var borderColor: Color {
        switch self {
        case .critical:      return .riskF
        case .warning:       return .riskC
        case .informational: return .informational
        }
    }
}

extension AlertType {
    var severity: AlertSeverity {
        switch self {
        case .gradeChange, .safetyDeterioration, .concentrationDanger,
             .portfolioSafetyThresholdBreach:
            return .critical
        case .majorEvent, .portfolioGradeChange, .clusterRisk,
             .macroShock, .structuralFragility:
            return .warning
        case .digestReady:
            return .informational
        }
    }
}

// MARK: - Empty State

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
        .clavisCardStyle()
    }
}

// Backward compat alias
typealias AlertGroupCard = AlertRow
