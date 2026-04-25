import SwiftUI

struct AlertsView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = AlertsViewModel()
    @State private var selectedFilter: AlertFeedFilter = .all
    @State private var hasLoaded = false

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    AlertsTopHeader()

                    if NetworkStatusMonitor.shared.isOffline {
                        OfflineStatusBanner()
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    if viewModel.isLoading && viewModel.alerts.isEmpty {
                        ClavisLoadingCard(title: "Loading alerts", subtitle: "Checking recent alert activity.")
                    } else if viewModel.alerts.isEmpty {
                        AlertsEmptyStateCard()
                    } else {
                        AlertsSummaryGrid(alerts: viewModel.sortedAlerts)
                        AlertFilterChipRow(selectedFilter: $selectedFilter, alerts: viewModel.sortedAlerts)

                        AlertsTimelineCard(
                            alerts: filteredAlerts,
                            positionIdForTicker: { viewModel.positionId(for: $0) },
                            onTapAlert: handleAlertTap
                        )
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 0)
                .padding(.bottom, ClavisTheme.largeSpacing)
            }
            .contentMargins(.top, 0, for: .scrollContent)
            .contentMargins(.bottom, 0, for: .scrollContent)
            .refreshable {
                await viewModel.loadAlerts()
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                if selectedTab == 3 && !hasLoaded {
                    hasLoaded = true
                    Task { await viewModel.loadAlerts() }
                }
            }
            .onChange(of: selectedTab) { _, newValue in
                if newValue == 3 && !hasLoaded && !viewModel.isLoading {
                    hasLoaded = true
                    Task { await viewModel.loadAlerts() }
                }
            }
        }
    }

    private var filteredAlerts: [Alert] {
        selectedFilter.apply(to: viewModel.sortedAlerts)
    }

    private func handleAlertTap(_ alert: Alert) {
        switch alertDestination(for: alert) {
        case .digest:
            selectedTab = 2
        case .home:
            selectedTab = 0
        case .ticker(let ticker):
            NotificationCenter.default.post(name: .openPositionDetail, object: ticker)
            selectedTab = 1
        case .none:
            break
        }
    }

    private func alertDestination(for alert: Alert) -> AlertDestination? {
        if alert.type == .digestReady {
            return .digest
        }

        if alert.type == .concentrationDanger || alert.type == .portfolioSafetyThresholdBreach {
            return .home
        }

        if let ticker = alert.positionTicker, !ticker.isEmpty {
            return .ticker(ticker)
        }

        return nil
    }
}

private struct AlertsTopHeader: View {
    var body: some View {
        ClavixPageHeader(title: "Alerts", subtitle: "Last 24h")
    }
}

private struct AlertsSummaryGrid: View {
    let alerts: [Alert]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                summaryCell(label: "Critical", count: alerts.filter { $0.type.severity == .critical }.count, tint: .riskF, fill: .dangerSurface, border: .riskF)
                summaryCell(label: "High", count: alerts.filter { severityBucket(for: $0) == .high }.count, tint: .riskD, fill: .warningSurface, border: .riskD)
                summaryCell(label: "Watch", count: alerts.filter { severityBucket(for: $0) == .watch }.count, tint: .riskC, fill: .warningSurface, border: .riskC)
                summaryCell(label: "Info", count: alerts.filter { $0.type.severity == .informational }.count, tint: .textPrimary, fill: .surface, border: .border)
            }
        }
    }

    private func severityBucket(for alert: Alert) -> AlertSummaryBucket {
        switch alert.type.severity {
        case .critical:
            return .high
        case .warning:
            if alert.newGrade == "C" || alert.previousGrade == "C" || alert.type == .majorEvent {
                return .watch
            }
            return .high
        case .informational:
            return .info
        }
    }

    private func summaryCell(label: String, count: Int, tint: Color, fill: Color, border: Color) -> some View {
        VStack(spacing: 3) {
            Text(label)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.textSecondary)

            Text("\(count)")
                .font(.system(size: 22, weight: .bold, design: .monospaced))
                .foregroundColor(.textPrimary)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(Color.surface)
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(Color.border, lineWidth: 1)
        )
        .overlay(alignment: .top) {
            Rectangle()
                .fill(tint)
                .frame(height: 2)
                .clipShape(RoundedRectangle(cornerRadius: 1))
        }
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}

private enum AlertSummaryBucket {
    case high
    case watch
    case info
}

private struct AlertFilterChipRow: View {
    @Binding var selectedFilter: AlertFeedFilter
    let alerts: [Alert]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 7) {
                ForEach(AlertFeedFilter.allCases, id: \.self) { filter in
                    Button {
                        selectedFilter = filter
                    } label: {
                        Text(filter.label(with: alerts))
                            .font(.system(size: 13, weight: selectedFilter == filter ? .semibold : .medium))
                            .foregroundColor(selectedFilter == filter ? .textPrimary : .textSecondary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 7)
                            .background(selectedFilter == filter ? Color.surfaceElevated : Color.surface)
                            .overlay(
                                RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                                    .stroke(selectedFilter == filter ? Color.textPrimary : Color.border, lineWidth: 1)
                            )
                            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}

private struct AlertsTimelineCard: View {
    let alerts: [Alert]
    let positionIdForTicker: (String?) -> String?
    let onTapAlert: (Alert) -> Void

    var body: some View {
        VStack(spacing: 0) {
            ForEach(Array(alerts.enumerated()), id: \.element.id) { index, alert in
                AlertsTimelineRow(
                    alert: alert,
                    showsConnector: index < alerts.count - 1,
                    positionId: positionIdForTicker(alert.positionTicker),
                    onTap: { onTapAlert(alert) }
                )
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 4)
        .clavisCardStyle(fill: .surface)
    }
}

private struct AlertsTimelineRow: View {
    let alert: Alert
    let showsConnector: Bool
    let positionId: String?
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            rowContent
        }
        .buttonStyle(.plain)
    }

    private var rowContent: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(spacing: 5) {
                GradeTag(grade: displayGrade, compact: true)
                if showsConnector {
                    Rectangle()
                        .fill(Color.border)
                        .frame(width: 1)
                        .frame(maxHeight: .infinity)
                }
            }
            .frame(width: 24)

            VStack(alignment: .leading, spacing: 3) {
                HStack(alignment: .firstTextBaseline) {
                    Text(alert.type.displayName)
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)

                    Spacer()

                    Text(alert.createdAt.formatted(date: .abbreviated, time: .shortened))
                        .font(.system(size: 11, weight: .regular, design: .monospaced))
                        .foregroundColor(.textSecondary)
                }

                Text(alert.message.sanitizedDisplayText)
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.textPrimary)
                    .multilineTextAlignment(.leading)

                if let ticker = alert.positionTicker {
                    Text(ticker)
                        .font(.system(size: 12, weight: .semibold, design: .monospaced))
                        .foregroundColor(.textSecondary)
                }

                if let previous = alert.previousGrade, let next = alert.newGrade {
                    HStack(spacing: 8) {
                        GradeTag(grade: previous, compact: true)
                        Image(systemName: "arrow.right")
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundColor(.textTertiary)
                        GradeTag(grade: next, compact: true)
                    }
                    .padding(.top, 2)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.vertical, 12)
        .overlay(alignment: .bottom) {
            if showsConnector {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 1)
                    .offset(x: 18)
            }
        }
    }

    private var displayGrade: String {
        alert.newGrade ?? alert.previousGrade ?? fallbackGrade
    }

    private var fallbackGrade: String {
        switch alert.type.severity {
        case .critical: return "F"
        case .warning: return "C"
        case .informational: return "B"
        }
    }
}

private enum AlertDestination {
    case digest
    case home
    case ticker(String)
}

private enum AlertFeedFilter: CaseIterable {
    case all
    case critical
    case grade
    case events

    func apply(to alerts: [Alert]) -> [Alert] {
        switch self {
        case .all:
            return alerts
        case .critical:
            return alerts.filter { $0.type.severity == .critical }
        case .grade:
            return alerts.filter { $0.type == .gradeChange || $0.type == .portfolioGradeChange }
        case .events:
            return alerts.filter { $0.type == .majorEvent || $0.type == .macroShock }
        }
    }

    func label(with alerts: [Alert]) -> String {
        switch self {
        case .all:
            return "All · \(alerts.count)"
        case .critical:
            return "Critical"
        case .grade:
            return "Grade"
        case .events:
            return "Events"
        }
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
