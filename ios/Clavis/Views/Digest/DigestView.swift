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
                        onRefresh: { Task { await viewModel.triggerAnalysis() } },
                        onOpenHoldings: { selectedTab = 1 },
                        isLoading: viewModel.isLoading || viewModel.activeRun?.status == "running"
                    )

                    if let activeRun = activeRunningRun {
                        AnalysisRunStatusCard(run: activeRun)
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DigestErrorCard(message: errorMessage) {
                            Task { await viewModel.loadDigest() }
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
                            onRunDigest: { Task { await viewModel.triggerAnalysis() } },
                            onRefresh: { Task { await viewModel.triggerAnalysis() } }
                        )
                        DigestMacroSectionView(digest: digest)
                        DigestSectorOverviewSection(digest: digest)
                        DigestPrototypePositionImpactsSection(digest: digest, holdings: viewModel.holdings)
                        DigestWhatMattersSection(digest: digest)
                        DigestWatchlistAlertsSection(digest: digest)
                        DigestWhatToWatchSection(digest: digest)
                        FullNarrativeSection(digest: digest)
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
                .padding(.top, ClavisTheme.largeSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .refreshable {
                await viewModel.triggerAnalysis()
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

    private var recentDigests: [Digest] {
        var seen = Set<String>()
        return ([viewModel.todayDigest].compactMap { $0 } + viewModel.digestHistory)
            .filter {
                guard $0.overallScore != nil else { return false }
                return seen.insert($0.id).inserted
            }
            .sorted { $0.generatedAt < $1.generatedAt }
    }
}

private struct DigestTopHeader: View {
    let onRefresh: () -> Void
    let onOpenHoldings: () -> Void
    let isLoading: Bool

    var body: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 3) {
                Text(Date().formatted(.dateTime.weekday(.wide).month(.abbreviated).day()))
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)
                Text("Digest")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
            }

            Spacer()

            Button(action: onRefresh) {
                DigestHeaderButton(systemName: isLoading ? "hourglass" : "arrow.clockwise")
            }
            .buttonStyle(.plain)
            .disabled(isLoading)

            Button(action: onOpenHoldings) {
                DigestHeaderButton(systemName: "briefcase.fill")
            }
            .buttonStyle(.plain)
        }
    }
}

private struct DigestHeaderButton: View {
    let systemName: String

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: 13, weight: .semibold))
            .foregroundColor(.textSecondary)
            .frame(width: 40, height: 40)
            .background(Color.surface)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color.border, lineWidth: 1))
    }
}

private struct DigestThesisCard: View {
    let digest: Digest

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text("Thesis · generated \(digest.generatedAt.formatted(date: .omitted, time: .shortened))")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            Text(digest.summary?.sanitizedDisplayText ?? digest.content.sanitizedDisplayText.firstParagraph ?? "")
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
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
                        NavigationLink(destination: tickerDestination(for: impact.ticker)) {
                            HStack(alignment: .top, spacing: 12) {
                                GradeTag(grade: grade(for: impact.ticker), compact: true)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text(impact.ticker)
                                        .font(ClavisTypography.bodyEmphasis)
                                        .foregroundColor(.textPrimary)
                                    Text(impact.impactSummary.sanitizedDisplayText)
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.textSecondary)
                                        .lineLimit(2)
                                }

                                Spacer()

                                Text(impact.macroRelevance.capitalized)
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                            }
                            .padding(.vertical, 12)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func tickerDestination(for ticker: String) -> some View {
        if let position = holdings.first(where: { $0.ticker == ticker }) {
            TickerDetailView(ticker: position.ticker)
        } else {
            TickerDetailView(ticker: ticker)
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
            return Array(watch.prefix(3)).map(condensedWatchItem)
        }
        return Array((digest.structuredSections?.portfolioImpact ?? []).prefix(3)).map(condensedWatchItem)
    }

    var body: some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("What to watch")
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                VStack(alignment: .leading, spacing: 8) {
                    ForEach(items, id: \.self) { item in
                        Text(item)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                    }
                }
                .padding(ClavisTheme.cardPadding)
                .clavisCardStyle(fill: .surface)
            }
        }
    }

    private func condensedWatchItem(_ raw: String) -> String {
        let cleaned = raw.sanitizedDisplayText.replacingOccurrences(of: "_", with: " ")
        guard let firstMarker = cleaned.range(of: " — ") else { return cleaned }
        let prefix = String(cleaned[..<firstMarker.lowerBound])
        let suffix = String(cleaned[firstMarker.upperBound...])
        guard let ticker = prefix.split(separator: " ").first?.uppercased(), !ticker.isEmpty else {
            return cleaned
        }
        let repeatedPattern = "\\b\(ticker)\\b\\s*[—:-]\\s*"
        let collapsed = suffix.replacingOccurrences(
            of: repeatedPattern,
            with: "",
            options: .regularExpression
        )
        return "\(prefix) — \(collapsed)".replacingOccurrences(of: "  ", with: " ")
    }
}

struct DigestHeroCard: View {
    let digest: Digest?
    let holdings: [Position]
    let activeRun: AnalysisRun?
    let isLoading: Bool
    let onRunDigest: () -> Void
    let onRefresh: () -> Void

    private var summaryText: String {
        if let summary = digest?.summary?.sanitizedDisplayText, !summary.isEmpty {
            return summary
        }
        return "Latest morning summary for your portfolio."
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            ClavisEyebrowHeader(eyebrow: "Digest", title: "Morning summary")

            Text(summaryText)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            HStack(spacing: ClavisTheme.smallSpacing) {
                ClavisMetricLabel(label: "Updated", value: digest?.generatedAt.formatted(date: .abbreviated, time: .shortened) ?? "Pending")
                ClavisMetricLabel(label: "Holdings", value: "\(holdings.count)")
            }

            HStack(spacing: ClavisTheme.smallSpacing) {
                Button(action: onRunDigest) {
                    Label(isLoading ? "Running" : "Run digest", systemImage: "arrow.clockwise")
                        .font(ClavisTypography.footnoteEmphasis)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.informational)
                .disabled(isLoading || activeRun?.status == "running")

                Button(action: onRefresh) {
                    Label("Refresh", systemImage: "clock.arrow.circlepath")
                        .font(ClavisTypography.footnoteEmphasis)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }

            Text("Informational only. Not financial advice.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisHeroCardStyle(fill: .surface)
    }
}

struct DigestScoreSummaryCard: View {
    let digest: Digest
    let holdings: [Position]

    private var portfolioGrade: String {
        if let grade = digest.overallGrade { return grade }
        let grades = holdings.compactMap { $0.riskGrade }
        guard !grades.isEmpty else { return "C" }
        let avg = Double(grades.map(gradeRank).reduce(0, +)) / Double(grades.count)
        return gradeFromAverage(avg)
    }

    private var portfolioScore: Double {
        digest.overallScore ?? 50
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 6) {
                Text("Portfolio Risk")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text("\(Int(portfolioScore.rounded()))")
                    .font(ClavisTypography.metric)
                    .foregroundColor(.textPrimary)
                Text(digest.summary?.sanitizedDisplayText ?? "Latest portfolio summary.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }

            Spacer()

            Text(portfolioGrade)
                .font(ClavisTypography.grade)
                .foregroundColor(ClavisGradeStyle.color(for: portfolioGrade))
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)

        VStack(alignment: .leading, spacing: 2) {
            Text("Score as of \(digest.generatedAt.formatted(date: .abbreviated, time: .shortened))")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
            Text("Informational only. Not financial advice.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
        }
        .padding(.horizontal, ClavisTheme.cardPadding)
        .padding(.bottom, ClavisTheme.smallSpacing)
    }

    private func gradeRank(_ grade: String) -> Int {
        switch grade {
        case "A": return 5
        case "B": return 4
        case "C": return 3
        case "D": return 2
        case "F": return 1
        default: return 3
        }
    }

    private func gradeFromAverage(_ value: Double) -> String {
        if value >= 4.5 { return "A" }
        if value >= 3.5 { return "B" }
        if value >= 2.5 { return "C" }
        if value >= 1.5 { return "D" }
        return "F"
    }
}

struct DigestLeadCard: View {
    let digest: Digest

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text("Generated \(digest.generatedAt.formatted(date: .abbreviated, time: .shortened))")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)

            Text(digest.summary?.sanitizedDisplayText ?? digest.content.sanitizedDisplayText.firstParagraph ?? "")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
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
                Text("Overnight Macro")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

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

struct DigestPositionImpactsSection: View {
    let digest: Digest

    private var impacts: [DigestPositionImpact] {
        digest.structuredSections?.positionImpacts ?? []
    }

    var body: some View {
        if !impacts.isEmpty {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("Position Impacts")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                ForEach(impacts) { impact in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(impact.ticker)
                                .font(ClavisTypography.bodyEmphasis)
                                .foregroundColor(.textPrimary)
                            Spacer()
                            Text(impact.macroRelevance.capitalized)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textTertiary)
                        }
                        Text(impact.impactSummary.sanitizedDisplayText)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                    }
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
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
                Text("Watchlist alerts")
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                DigestPrototypeListCard {
                    ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                        VStack(alignment: .leading, spacing: 0) {
                            HStack(alignment: .top, spacing: 10) {
                                Circle()
                                    .fill(Color.criticalTone.opacity(0.7))
                                    .frame(width: 8, height: 8)
                                    .padding(.top, 4)

                                Text(item.sanitizedDisplayText)
                                    .font(ClavisTypography.footnote)
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

struct WhatChangedSection: View {
    let digest: Digest
    let holdings: [Position]
    let alerts: [Alert]

    private var gradeChanges: [Alert] { alerts.filter { $0.type == .gradeChange } }
    private var majorEvents: [String] { digest.structuredSections?.majorEvents ?? [] }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("What Changed")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            if !gradeChanges.isEmpty {
                ChangedRow(title: "Grade Changes", detail: "\(gradeChanges.count) position\(gradeChanges.count == 1 ? "" : "s") changed")
            }

            if let firstEvent = majorEvents.first {
                ChangedRow(title: "Major Events", detail: firstEvent)
            }

            if gradeChanges.isEmpty && majorEvents.isEmpty {
                Text("No major changes detected.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct ChangedRow: View {
    let title: String
    let detail: String

    var body: some View {
        HStack(alignment: .top) {
            Text(title)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.textPrimary)
            Spacer()
            Text(detail)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
                .multilineTextAlignment(.trailing)
        }
    }
}

struct WhatToDoSection: View {
    let digest: Digest

    private var actions: [String] {
        let notes = digest.structuredSections?.portfolioImpact ?? []
        if !notes.isEmpty {
            return Array(notes.prefix(5))
        }
        return Array((digest.structuredSections?.watchList ?? []).prefix(3))
    }

    var body: some View {
        if !actions.isEmpty {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("What Changed")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                ForEach(Array(actions.enumerated()), id: \.offset) { _, action in
                    Text(action)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
    }
}

struct PositionsSection: View {
    let holdings: [Position]

    private var sortedHoldings: [Position] {
        holdings.sorted { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
    }

    var body: some View {
        if !holdings.isEmpty {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("Positions")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                ForEach(sortedHoldings) { holding in
                    NavigationLink(destination: TickerDetailView(ticker: holding.ticker)) {
                        HStack(spacing: ClavisTheme.mediumSpacing) {
                            Text(holding.riskGrade ?? "--")
                                .font(.system(size: 18, weight: .bold))
                                .foregroundColor(ClavisGradeStyle.color(for: holding.riskGrade))
                                .frame(width: 32)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(holding.ticker)
                                    .font(ClavisTypography.bodyEmphasis)
                                    .foregroundColor(.textPrimary)
                                Text(holding.summary?.sanitizedDisplayText ?? "")
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                                    .lineLimit(1)
                            }

                            Spacer()

                            Text("\(Int(holding.totalScore ?? 0))")
                                .font(ClavisTypography.bodyEmphasis)
                                .foregroundColor(.textPrimary)
                        }
                        .padding(ClavisTheme.cardPadding)
                        .clavisCardStyle(fill: .surfacePrimary)
                    }
                    .buttonStyle(.plain)
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
                            .font(.system(size: 12, weight: .semibold))
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
