import SwiftUI

struct DashboardView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ClavisTopBar(onLogoTap: { selectedTab = 0 }) {
                    Button {
                        Task { await viewModel.loadData() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }

                    Button {
                        Task { await viewModel.triggerFreshAnalysis() }
                    } label: {
                        Label("Run Analysis", systemImage: "waveform.path.ecg")
                    }
                    .disabled(viewModel.isRefreshingAnalysis)

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
                        if viewModel.isLoading && viewModel.holdings.isEmpty {
                            DashboardLoadingCard()
                        }

                        if let activeRun = viewModel.activeRun,
                           activeRun.lifecycleStatus == "running" || activeRun.lifecycleStatus == "queued" {
                            AnalysisRunStatusCard(run: activeRun)
                        }

                        if let errorMessage = viewModel.errorMessage {
                            DashboardErrorCard(message: errorMessage)
                        }

                        if viewModel.holdings.isEmpty {
                            DashboardEmptyStateCard(openHoldings: { selectedTab = 1 })
                        } else {
                            DashboardHeroCard(viewModel: viewModel)
                            DashboardSnapshotCard(viewModel: viewModel)

                            if !viewModel.needsAttentionPositions.isEmpty {
                                DashboardNeedsAttentionCard(items: viewModel.priorityQueue)
                            }

                            SinceLastReviewCard(
                                worseningCount: viewModel.deterioratingCount,
                                improvingCount: viewModel.improvingCount,
                                majorEventCount: viewModel.majorEventCount,
                                alerts: viewModel.changeAlerts
                            )

                            if let digest = viewModel.todayDigest {
                                DashboardPlaybookCard(
                                    digest: digest,
                                    openDigest: { selectedTab = 2 },
                                    openAlerts: { selectedTab = 3 }
                                )
                            }
                        }
                    }
                    .padding(.horizontal, ClavisTheme.screenPadding)
                    .padding(.top, ClavisTheme.mediumSpacing)
                    .padding(.bottom, ClavisTheme.extraLargeSpacing)
                }
                .refreshable {
                    await viewModel.loadData()
                }
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                if viewModel.holdings.isEmpty && viewModel.todayDigest == nil && !viewModel.isLoading {
                    Task { await viewModel.loadData() }
                }
            }
        }
    }
}

struct DashboardHeroCard: View {
    @ObservedObject var viewModel: DashboardViewModel

    private var summaryText: String {
        viewModel.todayDigest?.summary?.sanitizedDisplayText ?? viewModel.portfolioSummary
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Portfolio Risk")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)

                    Text("\(Int(viewModel.portfolioScore.rounded()))")
                        .font(ClavisTypography.portfolioScore)
                        .foregroundColor(ClavisGradeStyle.riskColor(for: viewModel.portfolioGrade))
                        .monospacedDigit()

                    Text(viewModel.portfolioRiskState.displayName)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textSecondary)
                }

                Spacer()

                GradeTag(grade: viewModel.portfolioGrade == "N/A" ? "C" : viewModel.portfolioGrade, large: true)
                    .padding(.top, 6)
                    .padding(.trailing, 10)
            }

            Text(summaryText)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            HStack(spacing: ClavisTheme.smallSpacing) {
                DashboardMetaPill(
                    title: "Updated",
                    value: viewModel.lastUpdatedAt?.formatted(date: .abbreviated, time: .shortened) ?? "Pending"
                )

                DashboardMetaPill(
                    title: "Pressure",
                    value: viewModel.portfolioActionPressure.displayName,
                    accent: ClavisDecisionStyle.tint(for: viewModel.portfolioActionPressure)
                )
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisHeroCardStyle(fill: .surface)
    }
}

struct DashboardSnapshotCard: View {
    @ObservedObject var viewModel: DashboardViewModel

    private var leadingInsight: String {
        if let summary = viewModel.todayDigest?.structuredSections?.overnightMacro?.brief.sanitizedDisplayText,
           !summary.isEmpty {
            return summary
        }
        return viewModel.morningFocusSummary
    }

    var body: some View {
        VStack(alignment: .center, spacing: ClavisTheme.mediumSpacing) {
            Text("Today at a Glance")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)
                .frame(maxWidth: .infinity, alignment: .center)

            Text(leadingInsight)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, alignment: .center)

        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct DashboardChipRow: View {
    let title: String
    let values: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text(title)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.textTertiary)

            FlowLayout(spacing: 8) {
                ForEach(values, id: \.self) { value in
                    Text(value)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textPrimary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .clavisSecondaryCardStyle(fill: .surfaceElevated)
                }
            }
        }
    }
}

struct DashboardNeedsAttentionCard: View {
    let items: [DashboardPriorityItem]

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Needs Attention")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            ForEach(items) { item in
                NavigationLink(destination: PositionDetailView(positionId: item.position.id)) {
                    DashboardAttentionRow(item: item)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct DashboardAttentionRow: View {
    let item: DashboardPriorityItem

    private var scoreText: String {
        if let score = item.position.totalScore {
            return "\(Int(score.rounded()))"
        }
        return "--"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.position.ticker)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)

                    Text(item.reason)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .lineLimit(2)
                }

                Spacer(minLength: 12)

                VStack(alignment: .trailing, spacing: 6) {
                    Text(scoreText)
                        .font(ClavisTypography.dataNumber)
                        .foregroundColor(ClavisGradeStyle.riskColor(for: item.position.riskGrade))
                        .monospacedDigit()

                    GradeTag(grade: item.position.riskGrade ?? "C", compact: true)
                }
            }

            RiskBar(score: item.position.totalScore ?? 50, grade: item.position.riskGrade ?? "C")
                .frame(height: 4)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
    }
}

struct SinceLastReviewCard: View {
    let worseningCount: Int
    let improvingCount: Int
    let majorEventCount: Int
    let alerts: [Alert]

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Since Last Review")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            HStack(spacing: ClavisTheme.smallSpacing) {
                ReviewMetricTile(value: worseningCount, label: "Worsening", tint: .riskF)
                ReviewMetricTile(value: improvingCount, label: "Improving", tint: .riskA)
                ReviewMetricTile(value: majorEventCount, label: "Events", tint: .riskC)
            }

            if !alerts.isEmpty {
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    ForEach(alerts.prefix(3)) { alert in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(alertHeadline(alert))
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.textPrimary)
                            Text(alert.message.sanitizedDisplayText)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                                .lineLimit(2)
                        }
                        .padding(ClavisTheme.cardPadding)
                        .clavisSecondaryCardStyle(fill: .surfaceElevated)
                    }
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }

    private func alertHeadline(_ alert: Alert) -> String {
        if let ticker = alert.positionTicker {
            return "\(ticker) · \(alert.type.displayName)"
        }
        return alert.type.displayName
    }
}

struct ReviewMetricTile: View {
    let value: Int
    let label: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
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

struct DashboardPlaybookCard: View {
    let digest: Digest
    let openDigest: () -> Void
    let openAlerts: () -> Void

    private var actions: [String] {
        let advice = digest.structuredSections?.portfolioAdvice ?? []
        return Array(advice.prefix(3))
    }

    private var watchList: [String] {
        Array((digest.structuredSections?.watchList ?? []).prefix(2))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack {
                Text("Digest")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Spacer()
                Button("See All", action: openDigest)
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.informational)
            }

            if !actions.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("What To Do")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textTertiary)

                    ForEach(Array(actions.enumerated()), id: \.offset) { index, action in
                        HStack(alignment: .top, spacing: 8) {
                            Text("\(index + 1)")
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.textPrimary)
                                .frame(width: 18, alignment: .leading)

                            Text(action)
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
                        }
                    }
                }
            }

            if !watchList.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Watch List")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textTertiary)

                    ForEach(watchList, id: \.self) { item in
                        Text(item)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }
                }
            }

            if actions.isEmpty && watchList.isEmpty {
                Text("Open the latest digest for portfolio-specific guidance.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }

            Button("Open Alerts", action: openAlerts)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.informational)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct DashboardMetaPill: View {
    let title: String
    let value: String
    var accent: Color = .textPrimary

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(ClavisTypography.label)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(accent)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
    }
}

struct DigestPreviewCard: View {
    let digest: Digest?
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 8) {
                Text("TODAY'S DIGEST")
                    .font(ClavisTypography.label)
                    .kerning(0.88)
                    .foregroundColor(.textSecondary)

                Text(previewText)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textPrimary)
                    .lineLimit(3)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surface)
        }
        .buttonStyle(.plain)
    }

    private var previewText: String {
        digest?.summary?.sanitizedDisplayText ?? "Open the latest digest summary."
    }
}

struct DashboardLoadingCard: View {
    var body: some View {
        ClavisLoadingCard(title: "Loading dashboard", subtitle: "Fetching holdings and digest data.")
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
                .tint(Color.informational)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct DashboardErrorCard: View {
    let message: String

    var body: some View {
        HStack(spacing: 0) {
            Rectangle().fill(Color.riskF).frame(width: 2.5)
            Text(message)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textPrimary)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
        }
        .background(Color.surface)
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

struct FlowLayout<Content: View>: View {
    let spacing: CGFloat
    @ViewBuilder let content: Content

    init(spacing: CGFloat = 8, @ViewBuilder content: () -> Content) {
        self.spacing = spacing
        self.content = content()
    }

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: spacing) { content }
            VStack(alignment: .leading, spacing: spacing) { content }
        }
    }
}

// MARK: - Backward compat alias used by other files
typealias CompactMetricReadout = ReviewMetricTile
