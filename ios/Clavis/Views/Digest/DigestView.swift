import SwiftUI

struct DigestView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = DigestViewModel()
    @State private var hasLoaded = false

    private var activeRunningRun: AnalysisRun? {
        guard let run = viewModel.activeRun,
              run.status == "running" || run.status == "queued" else {
            return nil
        }
        return run
    }

    private var shouldShowIdleState: Bool {
        !viewModel.isLoading && viewModel.todayDigest == nil && activeRunningRun == nil && viewModel.errorMessage == nil
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    DigestTopHeader(
                        onOpenHoldings: { selectedTab = 1 }
                    )

                    if NetworkStatusMonitor.shared.isOffline {
                        OfflineStatusBanner()
                    }

                    if let activeRun = activeRunningRun {
                        AnalysisRunStatusCard(run: activeRun)
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DigestErrorCard(message: errorMessage) {
                            Task { await viewModel.reloadDigestFromDatabase() }
                        }
                    }

                    if let timeoutMessage = viewModel.timeoutMessage {
                        DigestTimeoutCard(message: timeoutMessage)
                    }

                    if let digest = viewModel.todayDigest {
                        DigestHeroCard(
                            digest: digest,
                            holdings: viewModel.holdings,
                            activeRun: activeRunningRun,
                            isLoading: viewModel.isLoading,
                            onRunDigest: { Task { await viewModel.triggerAnalysis() } }
                        )
                        DigestMacroSectionView(digest: digest)
                        DigestSectorOverviewSection(digest: digest)
                        DigestPrototypePositionImpactsSection(digest: digest, holdings: viewModel.holdings)
                        DigestWhatMattersSection(digest: digest)
                        DigestWatchlistAlertsSection(digest: digest)
                        DigestWhatToWatchSection(digest: digest)
                    } else if shouldShowIdleState {
                        DigestEmptyStateCard {
                            Task { await viewModel.triggerAnalysis() }
                        }
                    }

                    if viewModel.isLoading && viewModel.todayDigest == nil && activeRunningRun == nil && viewModel.errorMessage == nil {
                        ClavisLoadingCard(title: "Loading digest", subtitle: "Fetching the latest morning summary.")
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 0)
                .padding(.bottom, ClavisTheme.floatingTabHeight + ClavisTheme.floatingTabInset + ClavisTheme.extraLargeSpacing)
            }
            .contentMargins(.top, 0, for: .scrollContent)
            .contentMargins(.bottom, 0, for: .scrollContent)
            .refreshable {
                await viewModel.reloadDigestFromDatabase()
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                if selectedTab == 2, !hasLoaded {
                    hasLoaded = true
                    Task { await viewModel.loadDigest() }
                }
            }
            .onChange(of: selectedTab) { _, newValue in
                if newValue == 2 && !hasLoaded && !viewModel.isLoading {
                    hasLoaded = true
                    Task { await viewModel.loadDigest() }
                }
            }
        }
    }

}

private struct DigestTopHeader: View {
    let onOpenHoldings: () -> Void

    var body: some View {
        ClavixPageHeader(
            title: "Digest",
            subtitle: Date().formatted(.dateTime.weekday(.abbreviated).month(.abbreviated).day())
        ) {
            Button(action: onOpenHoldings) {
                Image(systemName: "briefcase.fill")
                    .font(.system(size: 15, weight: .medium))
                    .foregroundColor(.textPrimary)
                    .frame(width: 32, height: 32)
            }
            .buttonStyle(.plain)
        }
    }
}

private struct DigestPrototypePositionImpactsSection: View {
    let digest: Digest
    let holdings: [Position]

    private var impacts: [DigestPositionImpact] {
        digest.structuredSections?.positionImpacts ?? []
    }

    var body: some View {
        if !impacts.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("Position impacts")
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                DigestPrototypeListCard {
                    ForEach(impacts) { impact in
                        VStack(alignment: .leading, spacing: 10) {
                            HStack(alignment: .top, spacing: 12) {
                                GradeTag(grade: grade(for: impact.ticker), compact: true)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text(impact.ticker)
                                        .font(ClavisTypography.bodyEmphasis)
                                        .foregroundColor(.textPrimary)
                                    Text(impact.impactSummary.sanitizedDisplayText)
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.textSecondary)
                                        .fixedSize(horizontal: false, vertical: true)
                                }

                                Spacer()

                                Text(impact.macroRelevance.capitalized)
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                            }

                            NavigationLink(destination: TickerDetailView(ticker: impact.ticker)) {
                                Text("Open ticker")
                                    .font(ClavisTypography.footnoteEmphasis)
                                    .foregroundColor(.informational)
                            }
                            .buttonStyle(.plain)

                            if !impact.watchItems.isEmpty {
                                Text("Watch: \(impact.watchItems.prefix(2).joined(separator: " • "))")
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textTertiary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }

                            if !impact.topRisks.isEmpty {
                                Text("Risks: \(impact.topRisks.prefix(2).joined(separator: " • "))")
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textTertiary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }

                            if !impact.dimensionBreakdown.isEmpty {
                                VStack(alignment: .leading, spacing: 4) {
                                    ForEach(impact.dimensionBreakdown.keys.sorted(), id: \.self) { key in
                                        if let value = impact.dimensionBreakdown[key], !value.isEmpty {
                                            Text("\(key.replacingOccurrences(of: "_", with: " ").capitalized): \(value)")
                                                .font(ClavisTypography.footnote)
                                                .foregroundColor(.textSecondary)
                                                .fixedSize(horizontal: false, vertical: true)
                                        }
                                    }
                                }
                            }
                        }
                        .padding(.vertical, 12)
                    }
                }
            }
        }
    }

    private func grade(for ticker: String) -> String {
        holdings.first(where: { $0.ticker == ticker })?.riskGrade ?? digest.overallGrade ?? "C"
    }
}

private struct DigestPrototypeListCard<Content: View>: View {
    @ViewBuilder let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        VStack(spacing: 0) {
            content
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 2)
        .clavisCardStyle(fill: .surface)
    }
}

private struct DigestWhatToWatchSection: View {
    let digest: Digest

    private var items: [String] {
        let watch = digest.structuredSections?.watchList ?? []
        if !watch.isEmpty {
            return Array(watch.prefix(3))
        }
        return Array((digest.structuredSections?.portfolioImpact ?? []).prefix(3))
    }

    var body: some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("What to watch")
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                VStack(alignment: .leading, spacing: 8) {
                    ForEach(items, id: \.self) { item in
                        Text(item.sanitizedDisplayText)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .padding(ClavisTheme.cardPadding)
                .clavisCardStyle(fill: .surface)
            }
        }
    }

}

struct DigestHeroCard: View {
    let digest: Digest?
    let holdings: [Position]
    let activeRun: AnalysisRun?
    let isLoading: Bool
    let onRunDigest: () -> Void

    private var summaryText: String {
        if let summary = digest?.summary?.sanitizedDisplayText, !summary.isEmpty {
            return summary
        }
        return "Latest morning summary for your portfolio."
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            VStack(alignment: .leading, spacing: 10) {
                CX2SectionLabel(text: "Thesis · \(digest?.generatedAt.formatted(date: .omitted, time: .shortened) ?? "Pending")")

                Text(summaryText)
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundColor(.textPrimary)
                    .lineSpacing(4)
            }

            HStack(spacing: 10) {
                Text("\(holdings.count) holding\(holdings.count == 1 ? "" : "s")")
                Text("·")
                Text(activeRun == nil ? "Stable" : (activeRun?.status.capitalized ?? "Running"))

                Spacer()

                ClavisSmallButton(
                    title: isLoading ? "Running" : "Run",
                    systemImage: "arrow.clockwise",
                    kind: .neutral,
                    isEnabled: !(isLoading || activeRun?.status == "running")
                ) {
                    onRunDigest()
                }
            }
            .font(.system(size: 12, weight: .regular))
            .foregroundColor(.textSecondary)
        }
    }
}

struct DigestMacroSectionView: View {
    let digest: Digest

    private var macro: DigestMacroSection? {
        digest.structuredSections?.overnightMacro
    }

    var body: some View {
        if let macro {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                CX2SectionLabel(text: "Overnight macro")

                Text(macro.brief.sanitizedDisplayText)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)

                if !macro.themes.isEmpty {
                    Text(macro.themes.map { $0.humanizedTitleCasedDisplayText }.joined(separator: " • "))
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }

                ForEach(Array(macro.headlines.prefix(3).enumerated()), id: \.offset) { _, headline in
                    Text("• \(headline)")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
    }
}

struct DigestSectorOverviewSection: View {
    let digest: Digest

    private var sectors: [DigestSectorOverviewItem] {
        digest.structuredSections?.sectorOverview ?? []
    }

    var body: some View {
        if !sectors.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("Sector overview")
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                DigestPrototypeListCard {
                    ForEach(Array(sectors.enumerated()), id: \.element.id) { index, sector in
                        VStack(alignment: .leading, spacing: 0) {
                            HStack(alignment: .top, spacing: 10) {
                                Circle()
                                    .fill(Color.textSecondary.opacity(0.55))
                                    .frame(width: 8, height: 8)
                                    .padding(.top, 4)

                                VStack(alignment: .leading, spacing: 3) {
                                    Text(sector.sector.humanizedTitleCasedDisplayText)
                                        .font(ClavisTypography.bodyEmphasis)
                                        .foregroundColor(.textPrimary)
                                    Text(sector.brief.sanitizedDisplayText)
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.textSecondary)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                            .padding(.vertical, 12)

                            if index < sectors.count - 1 {
                                Divider()
                                    .overlay(Color.border)
                            }
                        }
                    }
                }
            }
        }
    }
}

struct DigestWhatMattersSection: View {
    let digest: Digest

    private var items: [DigestWhatMattersItem] {
        digest.structuredSections?.whatMattersToday ?? []
    }

    var body: some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("What matters today")
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                DigestPrototypeListCard {
                    ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                        VStack(alignment: .leading, spacing: 0) {
                            HStack(alignment: .top, spacing: 10) {
                                Circle()
                                    .fill(Color.textSecondary.opacity(0.55))
                                    .frame(width: 8, height: 8)
                                    .padding(.top, 4)

                                VStack(alignment: .leading, spacing: 3) {
                                    Text(item.catalyst.sanitizedDisplayText)
                                        .font(ClavisTypography.bodyEmphasis)
                                        .foregroundColor(.textPrimary)
                                    Text("\(item.urgency.capitalized) urgency")
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.textSecondary)
                                    if !item.impactedPositions.isEmpty {
                                        Text(item.impactedPositions.joined(separator: ", "))
                                            .font(ClavisTypography.footnote)
                                            .foregroundColor(.textTertiary)
                                    }
                                }
                            }
                            .padding(.vertical, 12)

                            if index < items.count - 1 {
                                Divider()
                                    .overlay(Color.border)
                            }
                        }
                    }
                }
            }
        } else {
            VStack(alignment: .leading, spacing: 8) {
                Text("What matters today")
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                DigestPrototypeListCard {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("No immediate portfolio-level risk driver found today.")
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.textPrimary)
                        Text("Monitor the listed holdings for ticker-specific news, earnings, filings, or macro shocks.")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }
                    .padding(.vertical, 12)
                }
            }
        }
    }
}

struct DigestWatchlistAlertsSection: View {
    let digest: Digest

    private var items: [String] {
        digest.structuredSections?.watchlistAlerts ?? []
    }

    var body: some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                CX2SectionLabel(text: "Watchlist alerts")

                DigestPrototypeListCard {
                    ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                        VStack(alignment: .leading, spacing: 0) {
                            HStack(alignment: .top, spacing: 10) {
                                Circle()
                                    .fill(Color.criticalTone.opacity(0.7))
                                    .frame(width: 8, height: 8)
                                    .padding(.top, 4)

                                Text(item.sanitizedDisplayText)
                                    .font(ClavisTypography.bodyEmphasis)
                                    .foregroundColor(.textSecondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            .padding(.vertical, 12)

                            if index < items.count - 1 {
                                Divider()
                                    .overlay(Color.border)
                            }
                        }
                    }
                }
            }
        }
    }
}

struct FullNarrativeSection: View {
    let digest: Digest
    @State private var isExpanded = false

    var body: some View {
        if !digest.content.isEmpty {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) { isExpanded.toggle() }
                } label: {
                    HStack {
                        Text("Full Narrative")
                            .font(ClavisTypography.cardTitle)
                            .foregroundColor(.textPrimary)
                        Spacer()
                        Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundColor(.textTertiary)
                    }
                }

                if isExpanded {
                    MarkdownText(digest.content.sanitizedDisplayText, font: ClavisTypography.body, color: .textSecondary)
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfaceSecondary)
        }
    }
}

struct AnalysisRunStatusCard: View {
    let run: AnalysisRun

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack {
                Text(statusTitle)
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Spacer()
                Text(statusBadge)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }

            ProgressView(value: progressValue)
                .tint(.accentBlue)

            Text(statusMessage)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private var progressValue: Double {
        switch run.status {
        case "queued": return 0.12
        case "running": return min(0.95, 0.2 + Double(run.positionsProcessed ?? 0) * 0.18)
        default: return 1
        }
    }

    private var statusMessage: String {
        if run.status == "failed" { return run.displayErrorMessage }
        if let currentStageMessage = run.currentStageMessage, !currentStageMessage.isEmpty {
            return currentStageMessage
        }
        return "\(run.positionsProcessed ?? 0) positions processed, \(run.eventsProcessed ?? 0) events analyzed."
    }

    private var statusTitle: String {
        if run.status == "failed" { return "Analysis interrupted" }
        if run.lifecycleStatus == "completed" { return "Digest ready" }

        switch run.currentStage {
        case "starting": return "Starting analysis"
        case "refreshing_metadata": return "Refreshing holdings metadata"
        case "fetching_news": return "Fetching market news"
        case "classifying_relevance": return "Filtering relevant stories"
        case "classifying_macro": return "Reading market backdrop"
        case "classifying_positions": return "Grouping position themes"
        case "classifying_significance": return "Checking event importance"
        case "analyzing_events": return "Analyzing position impact"
        case "building_position_reports": return "Building position reports"
        case "scoring_position": return "Scoring positions"
        case "refreshing_prices": return "Refreshing prices"
        case "computing_portfolio_risk": return "Computing portfolio risk"
        case "building_digest": return "Building your digest"
        default:
            return run.status == "queued" ? "Queued for analysis" : "Analysis in progress"
        }
    }

    private var statusBadge: String {
        switch run.lifecycleStatus {
        case "completed": return "Done"
        case "failed": return "Failed"
        default: return run.status.capitalized
        }
    }
}

struct DigestErrorCard: View {
    let message: String
    var onRetry: (() -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text(message.sanitizedDisplayText)
                .font(ClavisTypography.body)
                .foregroundColor(.criticalTone)

            if let onRetry {
                Button("Retry", action: onRetry)
                    .buttonStyle(.bordered)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfaceSecondary)
    }
}

struct DigestTimeoutCard: View {
    let message: String

    var body: some View {
        Text(message)
            .font(ClavisTypography.body)
            .foregroundColor(.textSecondary)
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfaceSecondary)
    }
}

struct DigestEmptyStateCard: View {
    let onRunFreshReview: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("No Digest Yet")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Text("Run a fresh review to generate the first digest.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            Button("Run Fresh Review", action: onRunFreshReview)
                .buttonStyle(.borderedProminent)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

private extension String {
    var firstParagraph: String? {
        let paragraphs = components(separatedBy: "\n\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        return paragraphs.first
    }
}
