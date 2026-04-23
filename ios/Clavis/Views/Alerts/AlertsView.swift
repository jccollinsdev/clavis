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
                    CX2LargeTitle("Alerts") {
                        Text("Last 24h")
                            .font(.system(size: 13, weight: .regular))
                            .foregroundColor(.textSecondary)
                    }

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
                            positionIdForTicker: { viewModel.positionId(for: $0) }
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
}

private struct AlertsTopHeader: View {
    var body: some View {
        CX2NavBar(transparent: true, showBorder: false)
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
                            .font(.system(size: 15, weight: selectedFilter == filter ? .semibold : .medium))
                            .foregroundColor(selectedFilter == filter ? .textPrimary : .textSecondary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(selectedFilter == filter ? Color.surfaceElevated : Color.surface)
                            .overlay(
                                RoundedRectangle(cornerRadius: 999, style: .continuous)
                                    .stroke(selectedFilter == filter ? Color.textPrimary : Color.border, lineWidth: 1)
                            )
                            .clipShape(Capsule())
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

    var body: some View {
        VStack(spacing: 0) {
            ForEach(Array(alerts.enumerated()), id: \.element.id) { index, alert in
                AlertsTimelineRow(
                    alert: alert,
                    showsConnector: index < alerts.count - 1,
                    positionId: positionIdForTicker(alert.positionTicker)
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

    var body: some View {
        Group {
            if let ticker = alert.positionTicker {
                NavigationLink(destination: TickerDetailView(ticker: ticker)) {
                    rowContent
                }
                .buttonStyle(.plain)
            } else {
                rowContent
            }
        }
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
                        .font(.system(size: 15, weight: .medium, design: .monospaced))
                        .foregroundColor(.textSecondary)
                }

                Text(alert.message.sanitizedDisplayText)
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.textPrimary)
                    .multilineTextAlignment(.leading)

                if let ticker = alert.positionTicker {
                    Text(ticker)
                        .font(.system(size: 15, weight: .medium, design: .monospaced))
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

struct AlertsHeroCard: View {
    let groups: [AlertGroup]
    let isLoading: Bool
    let onRefresh: () -> Void

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
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            ClavisEyebrowHeader(eyebrow: "Alerts", title: "Recent changes")

            Text("Grouped by severity so the most urgent changes stay visible first.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            HStack(spacing: ClavisTheme.smallSpacing) {
                AlertsHeroStat(label: "Critical", value: criticalCount, tint: .riskF)
                AlertsHeroStat(label: "Warnings", value: warningCount, tint: .riskC)
                AlertsHeroStat(label: "Info", value: infoCount, tint: .informational)
            }

            HStack {
                Text(isLoading ? "Refreshing alert feed…" : "Alerts update as the portfolio changes.")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
                Spacer()
                Button(action: onRefresh) {
                    Label("Refresh", systemImage: "arrow.clockwise")
                        .font(ClavisTypography.footnoteEmphasis)
                }
                .buttonStyle(.plain)
                .foregroundColor(.informational)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisHeroCardStyle(fill: .surface)
    }
}

struct AlertsHeroStat: View {
    let label: String
    let value: Int
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("\(value)")
                .font(ClavisTypography.dataNumber)
                .foregroundColor(tint)
                .monospacedDigit()
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(ClavisTheme.cardPadding)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
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
                    .font(.system(size: 15, weight: .semibold))
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

    private var changeReasonText: String? {
        group.alerts.first?.changeReason?.sanitizedDisplayText
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

                    if let changeReasonText, !changeReasonText.isEmpty {
                        Text(changeReasonText)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    if let (from, to) = gradeInfo {
                        HStack(spacing: ClavisTheme.smallSpacing) {
                            GradeTag(grade: from, compact: true)
                            Image(systemName: "arrow.right")
                                .font(.system(size: 15, weight: .semibold))
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
        if let ticker = group.ticker {
            NavigationLink(destination: TickerDetailView(ticker: ticker)) {
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
