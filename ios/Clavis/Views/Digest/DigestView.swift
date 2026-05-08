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
                        DigestWatchlistAlertsSection(digest: digest)
                        DigestWhatMattersSection(digest: digest)
                    } else if shouldShowIdleState {
                        DigestEmptyStateCard {
                            Task { await viewModel.triggerAnalysis() }
                        }
                    }

                    if viewModel.isLoading && viewModel.todayDigest == nil && activeRunningRun == nil && viewModel.errorMessage == nil {
                        ClavisLoadingCard(title: "Loading Morning Rating", subtitle: "Fetching the latest portfolio summary.")
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 0)
                .padding(.bottom, ClavisTheme.floatingTabHeight + ClavisTheme.floatingTabInset + ClavisTheme.extraLargeSpacing)
            }
            .safeAreaInset(edge: .top, spacing: 0) {
                DigestTopHeader(onOpenHoldings: { selectedTab = 1 })
            }
            .refreshable {
                await viewModel.reloadDigestFromDatabase()
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                if selectedTab == 0, !hasLoaded {
                    hasLoaded = true
                    Task { await viewModel.loadDigest() }
                }
            }
            .onChange(of: selectedTab) { newValue in
                if newValue == 0 && !hasLoaded && !viewModel.isLoading {
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
            title: "Morning Rating",
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

private struct DigestPrototypePositionImpactsSection: View {
    let digest: Digest
    let holdings: [Position]

    private var impacts: [DigestPositionImpact] {
        digest.structuredSections?.positions ?? []
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
                                GradeBadge(grade: grade(for: impact.ticker), size: .compact)

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
                                Text(impact.watchItems.prefix(2).joined(separator: " • "))
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

                            if let db = impact.dimensionBreakdown {
                                VStack(alignment: .leading, spacing: 4) {
                                    DimensionBreakdownRow(label: "Financial Health", value: db.financialHealth)
                                    DimensionBreakdownRow(label: "News Sentiment", value: db.newsSentiment)
                                    DimensionBreakdownRow(label: "Macro Exposure", value: db.macroExposure)
                                    DimensionBreakdownRow(label: "Sector Exposure", value: db.sectorExposure)
                                    DimensionBreakdownRow(label: "Volatility", value: db.volatility)
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
        holdings.first(where: { $0.ticker == ticker })?.resolvedRiskGrade ?? digest.overallGrade ?? "—"
    }
}

private struct DigestPrototypeListCard<Content: View>: View {
    @ViewBuilder let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        ClavisFlushListCard(fill: .surface, padding: 14) {
            content
        }
    }
}


struct DigestHeroCard: View {
    let digest: Digest?
    let holdings: [Position]
    let activeRun: AnalysisRun?
    let isLoading: Bool
    let onRunDigest: () -> Void

    private var portfolioGrade: String {
        digest?.overallGrade ?? "—"
    }

    private var portfolioScore: Int? {
        guard let score = digest?.overallScore else { return nil }
        return Int(score.rounded())
    }

    private var summaryText: String {
        if let summary = digest?.summary?.sanitizedDisplayText, !summary.isEmpty {
            return summary
        }
        return "Your Morning Rating is ready below with the latest portfolio risks and changes."
    }

    private var ratingLabel: String {
        if let generatedAt = digest?.generatedAt {
            return "Rating · \(generatedAt.formatted(date: .omitted, time: .shortened))"
        }
        return "Rating"
    }

    private var riskDriverEntries: [String] {
        var drivers: [String] = []
        if let impacts = digest?.structuredSections?.positions {
            for impact in impacts.prefix(2) {
                let ticker = impact.ticker
                let summary = impact.impactSummary.sanitizedDisplayText
                if !summary.isEmpty {
                    let short = summary.split(separator: ".").first.map(String.init) ?? summary
                    drivers.append("\(ticker): \(short)")
                }
            }
        }
        if let warnings = digest?.structuredSections?.watchlistUpdates?.alerts, let first = warnings.first {
            drivers.append(first.sanitizedDisplayText)
        }
        return Array(drivers.prefix(2))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            CX2SectionLabel(text: ratingLabel)

            GradeDisplay(
                grade: portfolioGrade,
                score: portfolioScore,
                trend: portfolioTrend,
                evidence: nil,
                style: .hero
            )

            HStack(spacing: 6) {
                ScoreSourceChip(source: digest?.scoreSource)
                FreshnessChip(date: digest?.scoreAsOf ?? digest?.generatedAt)
            }

            if !riskDriverEntries.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(riskDriverEntries, id: \.self) { driver in
                        Text("• \(driver)")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }

            Text(summaryText)
                .font(.system(size: 15, weight: .regular))
                .foregroundColor(.textSecondary)
                .lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 10) {
                Text("\(holdings.count) holding\(holdings.count == 1 ? "" : "s")")
                Text("·")
                Text(activeRun == nil ? "Stable" : ClavisCopy.Status.label(for: activeRun?.status ?? "running"))

                Spacer()

                ClavisSmallButton(
                    title: isLoading ? "Updating" : "Refresh",
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

    private var portfolioTrend: RiskTrend? {
        guard digest?.structuredSections?.overnightMacro != nil else { return nil }
        let worsening = holdings.filter { $0.riskTrend == .worsening }.count
        let improving = holdings.filter { $0.riskTrend == .improving }.count
        if worsening > improving { return .worsening }
        if improving > worsening { return .improving }
        return .stable
    }
}

struct DigestMacroSectionView: View {
    let digest: Digest

    private var macro: DigestMacroSection? {
        digest.structuredSections?.overnightMacro
    }

    var body: some View {
        if let macro {
            let cleanBrief = macro.brief.sanitizedDisplayText
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                CX2SectionLabel(text: "Overnight macro")

                if cleanBrief.isEmpty {
                    Text("No macro commentary available")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textTertiary)
                } else {
                    Text(cleanBrief)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }

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
        digest.structuredSections?.sectorHeat ?? []
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
        digest.structuredSections?.whatToWatchToday?.catalysts ?? []
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
                        Text("Check the listed holdings for ticker-specific news, earnings, filings, or macro shocks.")
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
        digest.structuredSections?.watchlistUpdates?.alerts ?? []
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
        if run.status == "failed" { return ClavisCopy.Errors.analysisRefreshFailed }
        if let currentStageMessage = run.currentStageMessage, !currentStageMessage.isEmpty {
            return currentStageMessage
        }
        return "\(run.positionsProcessed ?? 0) holdings processed, \(run.eventsProcessed ?? 0) events analyzed."
    }

    private var statusTitle: String {
        if run.status == "failed" { return "Refresh interrupted" }
        if run.lifecycleStatus == "completed" { return "Rating ready" }

        switch run.currentStage {
        case "starting": return "Starting analysis"
        case "refreshing_metadata": return "Refreshing holdings metadata"
        case "fetching_news": return "Fetching market news"
        case "classifying_relevance": return "Filtering relevant stories"
        case "classifying_macro": return "Reading market backdrop"
        case "classifying_positions": return "Grouping holding themes"
        case "classifying_significance": return "Checking event importance"
        case "analyzing_events": return "Analyzing holding impact"
        case "building_position_reports": return "Building holding summaries"
        case "scoring_position": return "Scoring holdings"
        case "refreshing_prices": return "Refreshing prices"
        case "computing_portfolio_risk": return "Computing portfolio risk"
        case "building_digest": return "Building your rating"
        default:
            return run.status == "queued" ? "Pending analysis" : "Analysis in progress"
        }
    }

    private var statusBadge: String {
        switch run.lifecycleStatus {
        case "completed": return "Ready"
        case "failed": return "Unavailable"
        default: return ClavisCopy.Status.label(for: run.status)
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
            Text("No Morning Rating Yet")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Text("Generate your first Morning Digest to review the latest portfolio risk changes.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            ClavisPrimaryButton(title: "Generate Morning Rating", action: onRunFreshReview)
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

private struct DimensionBreakdownRow: View {
    let label: String
    let value: Double?

    var body: some View {
        if let v = value {
            HStack {
                Text(label)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                Spacer()
                Text("\(Int(v.rounded()))")
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundColor(.textPrimary)
            }
        }
    }
}
