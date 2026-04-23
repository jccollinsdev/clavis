import SwiftUI

struct DashboardView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    DashboardTopHeader()

                    if NetworkStatusMonitor.shared.isOffline {
                        OfflineStatusBanner()
                    }

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

                    DashboardPrototypeHeroCard(
                        viewModel: viewModel,
                        onRefresh: { Task { await viewModel.loadData() } },
                        onRunAnalysis: { Task { await viewModel.triggerFreshAnalysis() } }
                    )

                    DashboardStatStrip(viewModel: viewModel)

                    if viewModel.holdings.isEmpty {
                        DashboardEmptyStateCard(openHoldings: { selectedTab = 1 })
                    } else {
                        if !viewModel.needsAttentionPositions.isEmpty {
                            DashboardNeedsAttentionCard(items: viewModel.priorityQueue)
                        }

                        DashboardWhatChangedCard(viewModel: viewModel)

                        DashboardDigestTeaserCard(
                            digest: viewModel.todayDigest,
                            openDigest: { selectedTab = 2 }
                        )
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.mediumSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .refreshable {
                await viewModel.loadData()
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

private struct DashboardTopHeader: View {
    var body: some View {
        ClavixWordmarkHeader(subtitle: Date().formatted(.dateTime.weekday(.wide).month(.abbreviated).day()))
    }
}

private struct DashboardHeaderButton<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        content
            .frame(width: 40, height: 40)
            .background(Color.surface)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color.border, lineWidth: 1))
    }
}

private struct DashboardPrototypeHeroCard: View {
    @ObservedObject var viewModel: DashboardViewModel
    let onRefresh: () -> Void
    let onRunAnalysis: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 14) {
                ClavixGauge(
                    score: Int(viewModel.portfolioScore.rounded()),
                    grade: viewModel.portfolioGrade == "N/A" ? "—" : viewModel.portfolioGrade,
                    size: 112
                )

                VStack(alignment: .leading, spacing: 8) {
                    Text(viewModel.portfolioSummary)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)

                    HStack(spacing: 7) {
                        Button(action: onRefresh) {
                            Label("Refresh", systemImage: "clock.arrow.circlepath")
                                .font(ClavisTypography.footnoteEmphasis)
                                .padding(.horizontal, 11)
                                .padding(.vertical, 6)
                        }
                        .buttonStyle(.plain)
                        .background(Color.surfaceElevated)
                        .overlay(
                            RoundedRectangle(cornerRadius: 6, style: .continuous)
                                .stroke(Color.border, lineWidth: 1)
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))

                        Button(action: onRunAnalysis) {
                            Text(viewModel.isRefreshingAnalysis ? "Running..." : "Run analysis")
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.white)
                                .padding(.horizontal, 11)
                                .padding(.vertical, 6)
                        }
                        .buttonStyle(.plain)
                        .background(Color.informational)
                        .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                        .disabled(viewModel.isRefreshingAnalysis || viewModel.isAnalysisRunning)
                    }
                }
            }

            Divider()
                .overlay(Color.border)

            HStack {
                Text("Updated \(viewModel.lastUpdatedAt?.formatted(date: .omitted, time: .shortened) ?? "Pending") · \(viewModel.holdings.count) holdings")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)

                Spacer()

                Text("Next run \(viewModel.nextScheduledRunText)")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct DashboardStatStrip: View {
    @ObservedObject var viewModel: DashboardViewModel

    var body: some View {
        HStack(spacing: 9) {
            DashboardSummaryStatCard(label: "At risk", value: "\(viewModel.deterioratingCount)", detail: "of \(viewModel.holdings.count) holdings")
            DashboardSummaryStatCard(label: "Alerts", value: "\(viewModel.changeAlerts.count)", detail: "recent changes")
            DashboardSummaryStatCard(label: "Watchlist", value: "\(viewModel.morningFocusItems.count)", detail: "items tracked")
        }
    }
}

private struct DashboardSummaryStatCard: View {
    let label: String
    let value: String
    let detail: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label.uppercased())
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            Text(value)
                .font(ClavisTypography.dataNumber)
                .foregroundColor(.textPrimary)
                .monospacedDigit()

            Text(detail)
                .font(.system(size: 15, weight: .regular))
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .clavisCardStyle(fill: .surface)
    }
}

private struct DashboardWhatChangedCard: View {
    @ObservedObject var viewModel: DashboardViewModel

    private var entries: [DashboardChangeEntry] {
        var items = viewModel.changeAlerts.prefix(3).map {
            DashboardChangeEntry(
                title: $0.positionTicker ?? $0.type.displayName,
                grade: $0.newGrade ?? $0.previousGrade ?? "C",
                message: $0.message.sanitizedDisplayText,
                time: $0.createdAt.relativeTimestamp
            )
        }

        if !viewModel.holdings.isEmpty {
            items.insert(
                DashboardChangeEntry(
                    title: "Portfolio",
                    grade: viewModel.portfolioGrade == "N/A" ? "—" : viewModel.portfolioGrade,
                    message: "Score \(Int(viewModel.portfolioScore.rounded())) · \(viewModel.portfolioRiskState.displayName)",
                    time: viewModel.lastUpdatedAt?.relativeTimestamp ?? "Now"
                ),
                at: 0
            )
        }

        return Array(items.prefix(3))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("What changed")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            ForEach(entries) { entry in
                HStack(alignment: .top, spacing: 10) {
                    GradeTag(grade: entry.grade, compact: true)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(entry.title)
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(.textPrimary)
                        Text(entry.message)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .lineLimit(2)
                    }

                    Spacer()

                    Text(entry.time)
                        .font(.system(size: 15, weight: .medium, design: .monospaced))
                        .foregroundColor(.textSecondary)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct DashboardDigestTeaserCard: View {
    let digest: Digest?
    let openDigest: () -> Void

    private var sectorPreviewItems: [DigestSectorOverviewItem] {
        Array((digest?.structuredSections?.sectorOverview ?? []).prefix(3))
    }

    var body: some View {
        Button(action: openDigest) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top) {
                    Text("Morning digest")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)
                    Spacer()
                    if let grade = digest?.overallGrade {
                        GradeTag(grade: grade, compact: true)
                    }
                }

                Text(digest?.summary?.sanitizedDisplayText ?? "Open the latest morning digest for the current portfolio readout.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                    .multilineTextAlignment(.leading)

                DashboardDigestSectorPreview(items: sectorPreviewItems)

                Text("Read full digest →")
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.informational)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surface)
        }
        .buttonStyle(.plain)
    }
}

private struct DashboardDigestSectorPreview: View {
    let items: [DigestSectorOverviewItem]

    var body: some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("Sector overview")
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                ForEach(items) { item in
                    HStack(alignment: .top, spacing: 8) {
                        Circle()
                            .fill(Color.textSecondary.opacity(0.55))
                            .frame(width: 6, height: 6)
                            .padding(.top, 5)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(item.sector.capitalized)
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.textPrimary)
                            Text(item.brief.sanitizedDisplayText)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                                .lineLimit(2)
                        }
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(Color.surfaceElevated)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.border, lineWidth: 1)
            )
        }
    }
}

private struct DashboardChangeEntry: Identifiable {
    let id = UUID()
    let title: String
    let grade: String
    let message: String
    let time: String
}

private extension Date {
    var relativeTimestamp: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: self, relativeTo: Date())
    }
}

struct DashboardMastheadCard: View {
    @ObservedObject var viewModel: DashboardViewModel
    let onOpenHoldings: () -> Void
    let onOpenDigest: () -> Void
    let onOpenAlerts: () -> Void
    let onRefresh: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            ClavisEyebrowHeader(eyebrow: "Home", title: "Portfolio triage")

            Text(viewModel.portfolioSummary)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Risk score")
                        .font(ClavisTypography.label)
                        .foregroundColor(.textTertiary)

                    Text("\(Int(viewModel.portfolioScore.rounded()))")
                        .font(ClavisTypography.portfolioScore)
                        .foregroundColor(ClavisGradeStyle.riskColor(for: viewModel.portfolioGrade))
                        .monospacedDigit()
                }

                Spacer()

                GradeTag(grade: viewModel.portfolioGrade == "N/A" ? "C" : viewModel.portfolioGrade, large: true)
            }

            HStack(spacing: ClavisTheme.smallSpacing) {
                DashboardMetaPill(title: "Updated", value: viewModel.lastUpdatedAt?.formatted(date: .abbreviated, time: .shortened) ?? "Pending")
                DashboardMetaPill(title: "Pressure", value: viewModel.portfolioActionPressure.displayName, accent: ClavisDecisionStyle.tint(for: viewModel.portfolioActionPressure))
            }

            HStack(spacing: ClavisTheme.smallSpacing) {
                Button(action: onOpenHoldings) {
                    Label("Holdings", systemImage: "briefcase.fill")
                        .font(ClavisTypography.footnoteEmphasis)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button(action: onOpenDigest) {
                    Label("Digest", systemImage: "newspaper.fill")
                        .font(ClavisTypography.footnoteEmphasis)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button(action: onOpenAlerts) {
                    Label("Alerts", systemImage: "bell.fill")
                        .font(ClavisTypography.footnoteEmphasis)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }

            HStack {
                Text("Informational only. Not financial advice.")
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

        VStack(alignment: .leading, spacing: 2) {
            if let updatedAt = viewModel.lastUpdatedAt {
                Text("Score as of \(updatedAt.formatted(date: .abbreviated, time: .shortened))")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
            Text("Informational only. Not financial advice.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
        }
        .padding(.horizontal, ClavisTheme.cardPadding)
        .padding(.bottom, ClavisTheme.smallSpacing)
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
                NavigationLink(destination: TickerDetailView(ticker: item.position.ticker)) {
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
        Array((digest.structuredSections?.portfolioImpact ?? []).prefix(3))
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
                    Text("What Changed")
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
                Text("Open the latest digest for the current portfolio readout.")
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
