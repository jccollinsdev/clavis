import SwiftUI

struct DashboardView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if viewModel.isLoading && viewModel.dashboard == nil {
                        DashboardLoadingCard()
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    PortfolioOverviewCard(viewModel: viewModel)

                    if viewModel.isAnalysisRunning, let activeRun = viewModel.activeRun {
                        DashboardAnalysisRunStatusCard(run: activeRun)
                    }

                    if !viewModel.holdings.isEmpty {
                        PriorityQueueSection(items: viewModel.priorityQueue)

                        SinceLastReviewSection(alerts: viewModel.majorEventAlerts)

                        MorningFocusSection(
                            summary: viewModel.morningFocusSummary,
                            mattersToday: viewModel.morningFocusItems,
                            actionItems: viewModel.actionItems,
                            openDigest: { selectedTab = 2 }
                        )
                    } else {
                        DashboardEmptyStateCard(openHoldings: { selectedTab = 1 })
                    }

                    QuickActionsCard(
                        runAnalysis: { Task { await viewModel.triggerFreshAnalysis() } },
                        openDigest: { selectedTab = 2 },
                        openAlerts: { selectedTab = 3 },
                        openHoldings: { selectedTab = 1 }
                    )
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.largeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Dashboard")
            .navigationBarTitleDisplayMode(.large)
            .refreshable {
                await viewModel.loadData()
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        Task { await viewModel.triggerFreshAnalysis() }
                    } label: {
                        if viewModel.isRefreshingAnalysis {
                            ProgressView()
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(viewModel.isRefreshingAnalysis)
                }
            }
            .onAppear {
                if viewModel.dashboard == nil && !viewModel.isLoading {
                    Task { await viewModel.loadData() }
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .positionAnalysisComplete)) { _ in
                Task { @MainActor in
                    await viewModel.loadData()
                }
            }
        }
    }
}

struct DashboardLoadingCard: View {
    var body: some View {
        ClavisLoadingCard(title: "Loading dashboard", subtitle: "Fetching your latest risk signals and digest.")
    }
}

struct PortfolioOverviewCard: View {
    @ObservedObject var viewModel: DashboardViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Portfolio Risk")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)

                    Text("\(Int(viewModel.portfolioScore.rounded()))")
                        .font(ClavisTypography.metric)
                        .foregroundColor(.textPrimary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Text(viewModel.portfolioGrade)
                        .font(ClavisTypography.grade)
                        .foregroundColor(ClavisGradeStyle.color(for: viewModel.portfolioGrade))

                    Text(viewModel.portfolioRiskState.displayName)
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textSecondary)
                }
            }

            Text(viewModel.portfolioSummary)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            HStack(spacing: ClavisTheme.smallSpacing) {
                if let updatedAt = viewModel.lastUpdatedAt {
                    StatusPill(text: "Updated \(updatedAt.formatted(date: .abbreviated, time: .shortened))")
                }

                if let status = viewModel.analysisStatusText {
                    StatusPill(text: status)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct PortfolioRiskCard: View {
    let snapshot: PortfolioRiskSnapshot?
    let highlights: [String]
    let drivers: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Portfolio Construction Risk")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            if let snapshot {
                if let score = snapshot.portfolioAllocationRiskScore {
                    Text("Allocation risk \(Int(score.rounded())) / 100")
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)
                }

                if !highlights.isEmpty {
                    HStack(spacing: ClavisTheme.smallSpacing) {
                        ForEach(highlights, id: \.self) { highlight in
                            StatusPill(text: highlight)
                        }
                    }
                }

                if !drivers.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Top drivers")
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(.textSecondary)

                        ForEach(drivers, id: \.self) { driver in
                            Text(driver)
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
                        }
                    }
                }
            } else {
                Text("No portfolio-risk snapshot is available yet.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct PriorityQueueSection: View {
    let items: [DashboardPriorityItem]

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Needs Attention")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            if items.isEmpty {
                Text("No positions currently need attention.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            } else {
                ForEach(items) { item in
                    NavigationLink(destination: PositionDetailView(positionId: item.position.id)) {
                        DashboardPriorityRow(item: item)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}

struct DashboardPriorityRow: View {
    let item: DashboardPriorityItem

    var body: some View {
        HStack(alignment: .center, spacing: ClavisTheme.mediumSpacing) {
            Text(item.position.riskGrade ?? "--")
                .font(.system(size: 22, weight: .bold))
                .foregroundColor(ClavisGradeStyle.color(for: item.position.riskGrade))
                .frame(width: 36)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(item.position.ticker)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)
                    Spacer()
                    if let state = item.position.riskState {
                        StatusPill(text: state.displayName)
                    }
                }

                Text(item.reason)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .lineLimit(2)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct SinceLastReviewSection: View {
    let alerts: [Alert]

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Since Last Review")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            if alerts.isEmpty {
                Text("No major changes detected.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            } else {
                ForEach(alerts) { alert in
                    HStack(alignment: .top, spacing: ClavisTheme.smallSpacing) {
                        Image(systemName: alert.type.iconName)
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(alertColor(for: alert.type))
                            .frame(width: 18)

                        VStack(alignment: .leading, spacing: 4) {
                            Text(alertHeadline(for: alert))
                                .font(ClavisTypography.bodyEmphasis)
                                .foregroundColor(.textPrimary)

                            Text(alert.message.sanitizedDisplayText)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                                .lineLimit(2)
                        }

                        Spacer()
                    }
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private func alertHeadline(for alert: Alert) -> String {
        if let ticker = alert.positionTicker {
            return "\(ticker) · \(alert.type.displayName)"
        }
        return alert.type.displayName
    }

    private func alertColor(for type: AlertType) -> Color {
        switch type {
        case .gradeChange, .safetyDeterioration, .portfolioSafetyThresholdBreach:
            return .criticalTone
        case .majorEvent, .macroShock, .clusterRisk, .concentrationDanger, .structuralFragility:
            return .warningTone
        default:
            return .textSecondary
        }
    }
}

struct MorningFocusSection: View {
    let summary: String
    let mattersToday: [String]
    let actionItems: [String]
    let openDigest: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack {
                Text("Morning Focus")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                Spacer()

                Button("Open Digest", action: openDigest)
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.accentBlue)
            }

            Text(summary)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            if !mattersToday.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("What matters today")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textSecondary)

                    ForEach(Array(mattersToday.enumerated()), id: \.offset) { index, item in
                        HStack(alignment: .top, spacing: ClavisTheme.smallSpacing) {
                            Text("\(index + 1).")
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.textTertiary)
                            Text(item)
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
                        }
                    }
                }
            }

            if !actionItems.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("What to do")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textSecondary)

                    ForEach(actionItems, id: \.self) { item in
                        Text(item)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                    }
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct QuickActionsCard: View {
    let runAnalysis: () -> Void
    let openDigest: () -> Void
    let openAlerts: () -> Void
    let openHoldings: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Quick Actions")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: ClavisTheme.smallSpacing) {
                DashboardActionButton(title: "Run Analysis", systemImage: "arrow.clockwise", action: runAnalysis)
                DashboardActionButton(title: "Open Digest", systemImage: "doc.text", action: openDigest)
                DashboardActionButton(title: "View Alerts", systemImage: "bell", action: openAlerts)
                DashboardActionButton(title: "Holdings", systemImage: "briefcase", action: openHoldings)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct DashboardActionButton: View {
    let title: String
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 8) {
                Image(systemName: systemImage)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(.accentBlue)

                Text(title)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.textPrimary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(ClavisTheme.cardPadding)
            .frame(maxWidth: .infinity, minHeight: 74, alignment: .leading)
            .background(Color.surfaceSecondary)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
        }
        .buttonStyle(.plain)
    }
}

struct DashboardEmptyStateCard: View {
    let openHoldings: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text("No holdings yet")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)
            Text("Add your first position to start tracking downside risk and portfolio updates.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            Button("Open Holdings", action: openHoldings)
                .buttonStyle(.borderedProminent)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct DashboardAnalysisRunStatusCard: View {
    let run: AnalysisRun

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            HStack {
                Text(run.status == "queued" ? "Queued" : "Analysis Running")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Spacer()
                Text("\(run.progress ?? 0)%")
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.textSecondary)
            }

            Text(run.currentStageMessage ?? "Refreshing portfolio data.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            ProgressView(value: Double(run.progress ?? 0), total: 100)
                .progressViewStyle(ClavisProgressStyle())
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct StatusPill: View {
    let text: String

    var body: some View {
        Text(text)
            .font(ClavisTypography.footnoteEmphasis)
            .foregroundColor(.textSecondary)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(Color.surfaceSecondary)
            .clipShape(Capsule())
    }
}

struct DashboardErrorCard: View {
    let message: String

    var body: some View {
        Text(message)
            .font(ClavisTypography.footnote)
            .foregroundColor(.criticalTone)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(ClavisTheme.cardPadding)
            .background(Color.warningSurface)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }
}
