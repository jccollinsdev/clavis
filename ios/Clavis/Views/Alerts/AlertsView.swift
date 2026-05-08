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
                    if NetworkStatusMonitor.shared.isOffline {
                        OfflineStatusBanner()
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    if viewModel.isLoading && viewModel.alerts.isEmpty {
                        ClavisLoadingCard(title: "Loading alerts", subtitle: "Checking recent alert activity.")
                    } else if viewModel.alerts.isEmpty {
                        AlertsEmptyStateCard(openHoldings: { selectedTab = 1 })
                    } else {
                        AlertsSummaryGrid(alerts: viewModel.sortedAlerts)
                        AlertFilterChipRow(selectedFilter: $selectedFilter, alerts: viewModel.sortedAlerts)

                        AlertsTimelineCard(
                            alerts: filteredAlerts,
                            evidenceForTicker: { ticker in
                                viewModel.holdings.first(where: { $0.ticker.caseInsensitiveCompare(ticker ?? "") == .orderedSame })?.evidenceStrength
                            },
                            onTapAlert: handleAlertTap
                        )
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 0)
                .padding(.bottom, ClavisTheme.largeSpacing)
            }
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
            .onChange(of: selectedTab) { newValue in
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
            selectedTab = 0
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
        if alert.type == .ratingReady || alert.type == .digestReady {
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
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.top, 8)
            .padding(.bottom, 6)
            .background(
                Color.backgroundPrimary.opacity(0.9)
                    .background(.ultraThinMaterial)
                    .ignoresSafeArea(edges: .top)
            )
            .overlay(alignment: .bottom) {
                Rectangle()
                    .fill(Color.border.opacity(0.5))
                    .frame(height: 0.5)
            }
    }
}

private struct AlertsSummaryGrid: View {
    let alerts: [Alert]

    var body: some View {
        ClavisStandardCard(fill: .surface, padding: ClavisTheme.cardPadding) {
            LazyVGrid(
                columns: [
                    GridItem(.flexible(), spacing: 8),
                    GridItem(.flexible(), spacing: 8),
                ],
                spacing: 8
            ) {
                summaryCell(label: "Critical", count: alerts.filter { $0.type.severity == .critical }.count, tint: .riskF)
                summaryCell(label: "High", count: alerts.filter { severityBucket(for: $0) == .high }.count, tint: .riskD)
                summaryCell(label: "Elevated", count: alerts.filter { severityBucket(for: $0) == .elevated }.count, tint: .riskC)
                summaryCell(label: "Info", count: alerts.filter { $0.type.severity == .informational }.count, tint: .textSecondary)
            }
        }
    }

    private func severityBucket(for alert: Alert) -> AlertSummaryBucket {
        switch alert.type.severity {
        case .critical:
            return .high
        case .warning:
            let currentOrd = Grade.ordinalValue(for: alert.newGrade ?? "")
            let prevOrd = Grade.ordinalValue(for: alert.previousGrade ?? "")
            if abs(currentOrd - prevOrd) >= 3 {
                return .high
            }
            return .elevated
        case .informational:
            return .info
        }
    }

    private func summaryCell(label: String, count: Int, tint: Color) -> some View {
        ClavisRaisedControlSurface(padding: 10) {
            VStack(alignment: .leading, spacing: 6) {
                HStack(alignment: .firstTextBaseline) {
                    Text(label)
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.textSecondary)

                    Spacer(minLength: 6)

                    Text("\(count)")
                        .font(.system(size: 22, weight: .bold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                        .monospacedDigit()
                }

                Rectangle()
                    .fill(tint)
                    .frame(height: 2)
                    .clipShape(RoundedRectangle(cornerRadius: 1))
            }
        }
    }
}

private enum AlertSummaryBucket {
    case high
    case elevated
    case info
}

private struct AlertFilterChipRow: View {
    @Binding var selectedFilter: AlertFeedFilter
    let alerts: [Alert]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
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
    let evidenceForTicker: (String?) -> EvidenceStrength?
    let onTapAlert: (Alert) -> Void

    var body: some View {
        ClavisFlushListCard(fill: .surface, padding: 14) {
            VStack(spacing: 0) {
                ForEach(Array(alerts.enumerated()), id: \.element.id) { index, alert in
                    AlertsTimelineRow(
                        alert: alert,
                        showsConnector: index < alerts.count - 1,
                        positionEvidence: evidenceForTicker(alert.positionTicker),
                        onTap: { onTapAlert(alert) }
                    )
                }
            }
        }
    }
}

private struct AlertsTimelineRow: View {
    let alert: Alert
    let showsConnector: Bool
    var positionEvidence: EvidenceStrength? = nil
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            rowContent
        }
        .buttonStyle(.plain)
    }

    private var rowContent: some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(spacing: 4) {
                GradeBadge(grade: displayGrade, size: .compact)
                if showsConnector {
                    Rectangle()
                        .fill(Color.border)
                        .frame(width: 1)
                        .frame(maxHeight: .infinity)
                }
            }
            .frame(width: 24)

            VStack(alignment: .leading, spacing: 6) {
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
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.textPrimary)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)

                if let ticker = alert.positionTicker {
                    Text(ticker.uppercased())
                        .font(.system(size: 12, weight: .semibold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 3)
                        .background(Color.surfaceElevated)
                        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                }

                if let previous = alert.previousGrade, let next = alert.newGrade {
                    HStack(spacing: 6) {
                        GradeBadge(grade: previous, size: .compact)
                        Image(systemName: "arrow.right")
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundColor(.textTertiary)
                        GradeBadge(grade: next, size: .compact)
                        if let direction = alertGradeDirection(previous: previous, new: next) {
                            RiskDirectionLabel(trend: direction)
                        }
                    }
                    .padding(.top, 2)
                }

                if let reason = alert.changeReason?.sanitizedDisplayText, !reason.isEmpty {
                    Text(reason)
                        .font(.system(size: 12, weight: .regular))
                        .foregroundColor(.textSecondary)
                        .padding(.top, 2)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if let details = alert.changeDetails, !details.isEmpty {
                    let detailValues = Array(details.values.prefix(2)).map { $0.sanitizedDisplayText }.filter { !$0.isEmpty }
                    if !detailValues.isEmpty {
                        HStack(spacing: 6) {
                            ForEach(detailValues, id: \.self) { detail in
                                Text(detail)
                                    .font(.system(size: 11, weight: .medium))
                                    .foregroundColor(.textTertiary)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 3)
                                    .background(Color.surfaceElevated)
                                    .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                            }
                        }
                        .padding(.top, 2)
                    }
                }

                if let evidence = positionEvidence {
                    EvidenceDots(evidence: evidence, grade: displayGrade)
                        .padding(.top, 2)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.vertical, 10)
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
        alert.newGrade ?? alert.previousGrade ?? "—"
    }

    private func alertGradeDirection(previous: String, new: String) -> RiskTrend? {
        let prevVal = Grade.ordinalValue(for: previous)
        let newVal = Grade.ordinalValue(for: new)
        if newVal < prevVal { return .worsening }
        if newVal > prevVal { return .improving }
        return .stable
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
            return "Critical · \(alerts.filter { $0.type.severity == .critical }.count)"
        case .grade:
            return "Grade · \(alerts.filter { $0.type == .gradeChange || $0.type == .portfolioGradeChange }.count)"
        case .events:
            return "Events · \(alerts.filter { $0.type == .majorEvent || $0.type == .macroShock }.count)"
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
        case .ratingReady, .digestReady:
            return .informational
        }
    }
}

// MARK: - Empty State

struct AlertsEmptyStateCard: View {
    let openHoldings: () -> Void

    var body: some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("No alerts")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text("You don't have any recent alerts.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)

                ClavisPrimaryButton(title: "Open holdings", action: openHoldings)
            }
        }
    }
}
