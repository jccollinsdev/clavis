import SwiftUI

struct DashboardView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    DashboardTopHeader(refresh: { Task { await viewModel.loadData() } })

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

                        DashboardWhatChangedCard(viewModel: viewModel, openAlerts: { selectedTab = 3 })

                        DashboardDigestTeaserCard(
                            digest: viewModel.todayDigest,
                            openDigest: { selectedTab = 2 }
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
    let refresh: () -> Void

    var body: some View {
        ClavixPageHeader(
            title: "Good morning",
            subtitle: Date().formatted(.dateTime.weekday(.abbreviated).month(.abbreviated).day())
        ) {
            CX2IconButton(action: refresh) {
                Image(systemName: "clock")
                    .font(.system(size: 16, weight: .medium))
            }
        }
    }
}

private struct DashboardPrototypeHeroCard: View {
    @ObservedObject var viewModel: DashboardViewModel
    let onRefresh: () -> Void
    let onRunAnalysis: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            CX2SectionLabel(text: "Portfolio Score")
                .padding(.bottom, 10)

            HStack(alignment: .center, spacing: 12) {
                Text(viewModel.portfolioScoreText)
                    .font(.system(size: 64, weight: .bold, design: .monospaced))
                    .foregroundColor(.textPrimary)
                    .tracking(-2)

                GradeTag(grade: viewModel.portfolioGrade)
            }

            Text(viewModel.portfolioSummary)
                .font(.system(size: 15, weight: .regular))
                .foregroundColor(.textSecondary)
                .lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 10)

            HStack(spacing: 8) {
                ClavisSmallButton(title: "Refresh", systemImage: "arrow.clockwise", kind: .neutral) {
                    onRefresh()
                }

                ClavisSmallButton(
                    title: viewModel.isRefreshingAnalysis ? "Running" : "Run",
                    kind: .prominent,
                    isEnabled: !(viewModel.isRefreshingAnalysis || viewModel.isAnalysisRunning)
                ) {
                    onRunAnalysis()
                }
            }
            .padding(.top, 16)

            HStack(spacing: 8) {
                Text("Updated \(viewModel.lastUpdatedAt?.formatted(date: .omitted, time: .shortened) ?? "Pending")")
                Text("·")
                Text("Next \(viewModel.nextScheduledRunText)")
            }
            .font(.system(size: 11, weight: .regular))
            .foregroundColor(.textSecondary)
            .padding(.top, 8)
        }
    }
}

private struct DashboardStatStrip: View {
    @ObservedObject var viewModel: DashboardViewModel

    var body: some View {
        HStack(spacing: 0) {
            DashboardSummaryStatCard(label: "At risk", value: "\(viewModel.deterioratingCount)", detail: "of \(viewModel.holdings.count) holdings", showDivider: true)
            DashboardSummaryStatCard(label: "Alerts", value: "\(viewModel.changeAlerts.count)", detail: "recent changes", showDivider: true)
            DashboardSummaryStatCard(label: "Watchlist", value: "\(viewModel.morningFocusItems.count)", detail: "items tracked", showDivider: false)
        }
        .background(Color.surface)
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .stroke(Color.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }
}

private struct DashboardSummaryStatCard: View {
    let label: String
    let value: String
    let detail: String
    let showDivider: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.textSecondary)

            Text(value)
                .font(.system(size: 22, weight: .bold, design: .monospaced))
                .foregroundColor(.textPrimary)
                .monospacedDigit()

            Text(detail)
                .font(.system(size: 11, weight: .regular))
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 14)
        .padding(.vertical, 14)
        .overlay(alignment: .trailing) {
            if showDivider {
                Rectangle()
                    .fill(Color.border)
                    .frame(width: 1)
            }
        }
    }
}

private struct DashboardWhatChangedCard: View {
    @ObservedObject var viewModel: DashboardViewModel
    let openAlerts: () -> Void

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
                    grade: viewModel.portfolioGrade,
                    message: "Score \(viewModel.portfolioScoreText) · \(viewModel.portfolioRiskState?.displayName ?? "Unknown")",
                    time: viewModel.lastUpdatedAt?.relativeTimestamp ?? "Now"
                ),
                at: 0
            )
        }

        return Array(items.prefix(3))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .lastTextBaseline) {
                CX2SectionLabel(text: "What changed · \(entries.count)")
                Spacer()
                Button(action: openAlerts) {
                    Text("See all")
                        .font(.system(size: 13, weight: .regular))
                        .foregroundColor(.informational)
                }
                .buttonStyle(.plain)
            }

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
                        .font(.system(size: 11, weight: .regular, design: .monospaced))
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
                    CX2SectionLabel(text: "Morning digest")
                    Spacer()
                    if let grade = digest?.overallGrade {
                        GradeTag(grade: grade, compact: true)
                    }
                }

                Text(digest?.summary?.sanitizedDisplayText ?? "Open the latest morning digest for the current portfolio readout.")
                    .font(.system(size: 15, weight: .medium))
                    .foregroundColor(.textPrimary)
                    .multilineTextAlignment(.leading)

                DashboardDigestSectorPreview(items: sectorPreviewItems)

                HStack(spacing: 8) {
                    Text(digest?.generatedAt.formatted(date: .abbreviated, time: .shortened) ?? "Today")
                        .font(.system(size: 12, weight: .regular))
                        .foregroundColor(.textSecondary)
                    Text("·")
                        .foregroundColor(.textTertiary)
                    Text("Read digest →")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.informational)
                }
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
