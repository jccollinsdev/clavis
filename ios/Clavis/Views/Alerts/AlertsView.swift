import SwiftUI

struct AlertsView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = AlertsViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ClavisTopBar(onLogoTap: { selectedTab = 0 }) {
                    Button {
                        Task { await viewModel.loadAlerts() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                    .disabled(viewModel.isLoading)

                    Divider()

                    Button {
                        selectedTab = 1
                    } label: {
                        Label("Holdings", systemImage: "briefcase.fill")
                    }

                    Button {
                        selectedTab = 2
                    } label: {
                        Label("Digest", systemImage: "newspaper.fill")
                    }

                    Button {
                        selectedTab = 3
                    } label: {
                        Label("Alerts", systemImage: "bell.fill")
                    }

                    Button {
                        selectedTab = 4
                    } label: {
                        Label("Settings", systemImage: "gearshape.fill")
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 8)
                .padding(.bottom, 12)

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
                            let groups = viewModel.groupAlerts()
                            if !groups.isEmpty {
                                AlertsSeveritySummaryCard(groups: groups)
                            }

                            ForEach(groups) { group in
                                AlertCard(group: group)
                            }
                        }
                    }
                    .padding(.horizontal, ClavisTheme.screenPadding)
                    .padding(.top, ClavisTheme.mediumSpacing)
                    .padding(.bottom, ClavisTheme.extraLargeSpacing)
                }
                .refreshable {
                    await viewModel.loadAlerts()
                }
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                if viewModel.alerts.isEmpty && !viewModel.isLoading {
                    Task { await viewModel.loadAlerts() }
                }
            }
        }
    }
}

// MARK: - Severity Summary Card

struct AlertsSeveritySummaryCard: View {
    let groups: [AlertGroup]

    private var criticalCount: Int {
        groups.filter { $0.type.severity == .critical }.count
    }

    private var warningCount: Int {
        groups.filter { $0.type.severity == .warning }.count
    }

    private var infoCount: Int {
        groups.filter { $0.type.severity == .informational }.count
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Recent Activity")
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.textPrimary)

            HStack(spacing: 8) {
                if criticalCount > 0 {
                    AlertsSeverityPill(
                        count: criticalCount,
                        label: "Critical",
                        tint: .riskF,
                        icon: "exclamationmark.triangle.fill"
                    )
                }
                if warningCount > 0 {
                    AlertsSeverityPill(
                        count: warningCount,
                        label: "Warning",
                        tint: .riskC,
                        icon: "exclamationmark.circle.fill"
                    )
                }
                if infoCount > 0 {
                    AlertsSeverityPill(
                        count: infoCount,
                        label: "Info",
                        tint: .informational,
                        icon: "info.circle.fill"
                    )
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .clavisCardStyle(fill: .surface)
    }
}

struct AlertsSeverityPill: View {
    let count: Int
    let label: String
    let tint: Color
    var icon: String? = nil

    var body: some View {
        HStack(spacing: 6) {
            if let icon {
                Image(systemName: icon)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(tint)
            }
            Text("\(count)")
                .font(.system(size: 15, weight: .semibold, design: .monospaced))
                .foregroundColor(tint)
                .monospacedDigit()
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
    }
}

// MARK: - Alert Card

struct AlertCard: View {
    let group: AlertGroup

    private var severity: AlertSeverity { group.type.severity }

    private var displayTitle: String {
        return group.type.displayName
    }

    private var displayBody: String {
        group.alerts.first?.message.sanitizedDisplayText ?? ""
    }

    private var timestampText: String {
        group.latestTimestamp.formatted(date: .abbreviated, time: .shortened)
    }

    private var gradeInfo: (String, String)? {
        guard group.type == .gradeChange,
              let alert = group.alerts.first,
              let from = alert.previousGrade,
              let to = alert.newGrade else {
            return nil
        }
        return (from, to)
    }

    @ViewBuilder
    private var tickerBadge: some View {
        if let ticker = group.ticker {
            Text(ticker.uppercased())
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.informational)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .clavisSecondaryCardStyle(fill: .surfaceElevated)
        }
    }

    private var cardContent: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                Rectangle()
                    .fill(severity.borderColor)
                    .frame(width: 2.5)
                    .clipShape(RoundedRectangle(cornerRadius: 1.25))

                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Text(displayTitle)
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.textPrimary)

                        Spacer()

                        Text(timestampText)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                    }

                    tickerBadge

                    if !displayBody.isEmpty {
                        Text(displayBody)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .lineLimit(2)
                    }

                    if let (from, to) = gradeInfo {
                        HStack(spacing: ClavisTheme.smallSpacing) {
                            GradeTag(grade: from, compact: true)
                            Image(systemName: "arrow.right")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(.textTertiary)
                            GradeTag(grade: to, compact: true)

                            let delta = gradeDelta(from: from, to: to)
                            if delta != 0 {
                                Text("\(delta > 0 ? "+" : "")\(delta) points")
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(delta > 0 ? .riskA : .riskF)
                            }
                        }
                    }
                }
            }

            if group.alerts.count > 1 {
                Text("\(group.alerts.count) events")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
                    .padding(.leading, ClavisTheme.cardPadding + 10)
            }
        }
        .padding(14)
        .clavisCardStyle(fill: .surface)
    }

    var body: some View {
        if let positionId = group.positionId {
            NavigationLink(destination: PositionDetailView(positionId: positionId)) {
                cardContent
            }
            .buttonStyle(.plain)
        } else {
            cardContent
        }
    }

    private func gradeDelta(from: String, to: String) -> Int {
        let values = ["F": 1, "D": 2, "C": 3, "B": 4, "A": 5]
        let fromVal = values[from] ?? 3
        let toVal = values[to] ?? 3
        return (toVal - fromVal) * 15
    }
}

// MARK: - Alert Group Model

struct AlertGroup: Identifiable {
    let id: String
    let type: AlertType
    let ticker: String?
    let positionId: String?
    let alerts: [Alert]
    let latestTimestamp: Date
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
        .clavisCardStyle(fill: .surface)
    }
}

// Backward compat alias
typealias AlertGroupCard = AlertCard
