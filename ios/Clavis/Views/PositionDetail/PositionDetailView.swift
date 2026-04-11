import SwiftUI

struct PositionDetailView: View {
    let positionId: String
    @State private var detail: PositionDetailResponse?
    @State private var priceHistory: [PricePoint] = []
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var isRefreshingAnalysis = false
    @State private var hasLoaded = false
    @State private var selectedDays: Int = 30
    @State private var activeRun: AnalysisRun?

    var body: some View {
        ScrollView {
            if isLoading && detail == nil {
                ClavisLoadingCard(
                    title: "Loading position",
                    subtitle: "Pulling the latest analysis, score breakdown, and price history."
                )
                .padding()
            } else if let detail {
                VStack(spacing: ClavisTheme.sectionSpacing) {
                    PositionSummaryHero(position: detail.position, score: detail.currentScore)

                    AnalysisTimingCard(score: detail.currentScore, analysis: detail.currentAnalysis)

                    PositionSnapshotCard(position: detail.position)

                    PriceAndTrendSection(
                        ticker: detail.position.ticker,
                        priceHistory: priceHistory,
                        selectedDays: $selectedDays,
                        onDaysChange: { days in
                            Task { await loadPriceHistory(days: days) }
                        }
                    )

                    if let activeRun, activeRun.status == "running" || activeRun.status == "queued" {
                        AnalysisProgressCard(run: activeRun)
                    }

                    if let analysis = detail.currentAnalysis {
                        RiskDriversCard(score: detail.currentScore, analysis: analysis)
                        RecentDevelopmentsCard(analysis: analysis, events: detail.latestEventAnalyses, recentNews: detail.recentNews)
                        WhatToWatchCard(analysis: analysis)
                        EventAnalysesCard(events: detail.latestEventAnalyses, recentNews: detail.recentNews, ticker: detail.position.ticker)
                    } else {
                        NoAnalysisCard {
                            Task { await triggerFreshAnalysis() }
                        }
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.largeSpacing)
            }
        }
        .background(Color.appBackground)
        .navigationTitle(detail?.position.ticker ?? "Position")
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    Task { await triggerFreshAnalysis() }
                } label: {
                    if isRefreshingAnalysis {
                        ProgressView()
                    } else {
                        Text("Refresh")
                    }
                }
                .disabled(isRefreshingAnalysis)
            }
        }
        .overlay(alignment: .top) {
            if let errorMessage {
                InlineErrorBanner(message: errorMessage)
                    .padding(.horizontal)
                    .padding(.top, 8)
            }
        }
        .refreshable {
            await reloadAll()
        }
        .onAppear {
            guard !hasLoaded else { return }
            hasLoaded = true

            Task {
                await reloadAll()
            }
        }
    }

    private func reloadAll() async {
        await loadDetail()
        await loadPriceHistory(days: selectedDays)
    }

    private func loadDetail() async {
        isLoading = true
        errorMessage = nil

        do {
            detail = try await APIService.shared.fetchPositionDetail(id: positionId)
        } catch {
            errorMessage = "Failed to load position details: \(error.localizedDescription)"
        }

        isLoading = false
    }

    private func loadPriceHistory(days: Int = 30) async {
        guard let ticker = detail?.position.ticker else { return }
        do {
            let response = try await APIService.shared.fetchPriceHistory(ticker: ticker, days: days)
            withAnimation(.smooth(duration: 0.4)) {
                priceHistory = response.prices
            }
        } catch {
            errorMessage = "Failed to load price history: \(error.localizedDescription)"
        }
    }

    private func triggerFreshAnalysis() async {
        isRefreshingAnalysis = true
        errorMessage = nil
        activeRun = nil
        defer { isRefreshingAnalysis = false }

        do {
            let trigger = try await APIService.shared.triggerAnalysis(positionId: positionId)
            if let runId = trigger.analysisRunId {
                try await pollAnalysisRun(runId: runId)
            }
            await reloadAll()
        } catch {
            errorMessage = "Failed to trigger analysis: \(error.localizedDescription)"
        }
    }

    private func pollAnalysisRun(runId: String) async throws {
        for _ in 0..<30 {
            let run = try await APIService.shared.fetchAnalysisRun(id: runId)
            activeRun = run
            await loadDetail()

            switch run.lifecycleStatus {
            case "completed":
                activeRun = nil
                return
            case "failed":
                throw APIError.networkError(
                    NSError(
                        domain: "Clavis",
                        code: 1,
                        userInfo: [NSLocalizedDescriptionKey: run.errorMessage ?? "Analysis failed."]
                    )
                )
            default:
                break
            }

            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }

        activeRun = nil
        throw APIError.networkError(
            NSError(
                domain: "Clavis",
                code: 2,
                userInfo: [NSLocalizedDescriptionKey: "Analysis is still running. Please check back in a moment."]
            )
        )
    }
}

struct PositionSummaryHero: View {
    let position: Position
    let score: RiskScore?

    private var displayScoreValue: Double {
        score?.displayScore ?? 0
    }

    private var displayGradeValue: String {
        score?.displayGrade ?? position.riskGrade ?? "C"
    }

    private var riskTrend: RiskTrend {
        position.riskTrend ?? .stable
    }

    private var actionPressure: ActionPressure {
        ActionPressure.from(score: displayScoreValue, trend: riskTrend)
    }

    private var interpretation: String {
        if let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
            return summary.singleSentence
        }

        switch actionPressure {
        case .high:
            return "Risk is elevated."
        case .medium:
            return "Risk is manageable but requires monitoring."
        case .low:
            return "Risk is stable."
        }
    }

    private var actionText: String {
        switch actionPressure {
        case .high:
            return "Reduce position."
        case .medium:
            return "Monitor closely."
        case .low:
            return "No action required."
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(alignment: .center, spacing: ClavisTheme.mediumSpacing) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Risk Score")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)

                    Text("\(Int(displayScoreValue))")
                        .font(ClavisTypography.metric)
                        .foregroundColor(.textPrimary)
                }

                Spacer()

                Text(displayGradeValue)
                    .font(ClavisTypography.grade)
                    .foregroundColor(ClavisGradeStyle.color(for: displayGradeValue))
            }

            Text(interpretation)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            Text(actionText)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.textPrimary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct PositionSnapshotCard: View {
    let position: Position

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            HStack(spacing: 0) {
                SnapshotItem(label: "Shares", value: String(format: "%.2f", position.shares))
                SnapshotItem(label: "Cost Basis", value: String(format: "$%.2f", position.purchasePrice))
                SnapshotItem(label: "Current", value: currentPriceText)
            }

            HStack(spacing: 0) {
                SnapshotItem(label: "Value", value: currentValueText)
                SnapshotItem(label: "P/L", value: plText, tint: plColor)
            }
        }
        .padding(24)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private var currentPriceText: String {
        let price = position.currentPrice ?? position.purchasePrice
        return price.formatted(.currency(code: "USD").precision(.fractionLength(2)))
    }

    private var currentValueText: String {
        guard let value = position.currentValue else {
            let price = position.currentPrice ?? position.purchasePrice
            return (position.shares * price).formatted(.currency(code: "USD").precision(.fractionLength(2)))
        }
        return value.formatted(.currency(code: "USD").precision(.fractionLength(2)))
    }

    private var plText: String {
        guard let pl = position.unrealizedPL else {
            guard let current = position.currentPrice else { return "--" }
            let pl = (current - position.purchasePrice) * position.shares
            let sign = pl >= 0 ? "+" : ""
            return sign + pl.formatted(.currency(code: "USD").precision(.fractionLength(2)))
        }
        let sign = pl >= 0 ? "+" : ""
        return sign + pl.formatted(.currency(code: "USD").precision(.fractionLength(2)))
    }

    private var plColor: Color {
        guard let pl = position.unrealizedPL else { return .textPrimary }
        return pl >= 0 ? .successTone : .criticalTone
    }
}

struct AnalysisTimingCard: View {
    let score: RiskScore?
    let analysis: PositionAnalysis?

    private var scoreText: String? {
        guard let calculatedAt = score?.calculatedAt else { return nil }
        return "Risk score calculated " + calculatedAt.formatted(date: .abbreviated, time: .shortened)
    }

    private var analysisText: String? {
        guard let updatedAt = analysis?.updatedAt else { return nil }
        return "Analysis updated " + updatedAt.formatted(date: .abbreviated, time: .shortened)
    }

    var body: some View {
        if scoreText == nil && analysisText == nil {
            EmptyView()
        } else {
            VStack(alignment: .leading, spacing: 6) {
                Text("Timing")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)

                if let scoreText {
                    Text(scoreText)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }

                if let analysisText {
                    Text(analysisText)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
    }
}

struct SnapshotItem: View {
    let label: String
    let value: String
    var tint: Color = .textPrimary

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct PriceAndTrendSection: View {
    let ticker: String
    let priceHistory: [PricePoint]
    @Binding var selectedDays: Int
    let onDaysChange: (Int) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Price and Trend")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Picker("Timeframe", selection: $selectedDays) {
                Text("7D").tag(7)
                Text("30D").tag(30)
                Text("90D").tag(90)
            }
            .pickerStyle(.segmented)
            .onChange(of: selectedDays) { _, days in
                onDaysChange(days)
            }

            PriceChartView(ticker: ticker, prices: priceHistory, days: selectedDays)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct RiskDriversCard: View {
    let score: RiskScore?
    let analysis: PositionAnalysis

    private var meaningfulDrivers: [(String, Double)] {
        guard let score else { return [] }

        let drivers: [(String, Double)] = [
            ("News Sentiment", score.newsSentiment ?? 50),
            ("Macro Exposure", score.macroExposure ?? 50),
            ("Position Sizing", score.positionSizing ?? 50),
            ("Volatility Trend", score.volatilityTrend ?? 50),
            ("Market Integrity", score.structuralBaseScore ?? 50)
        ]

        return drivers
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Risk Drivers")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            if !meaningfulDrivers.isEmpty {
                ForEach(Array(meaningfulDrivers.enumerated()), id: \.offset) { _, driver in
                    RiskDriverRow(label: driver.0, score: driver.1)
                }
            }

            if let topRisk = analysis.topRisks?.first, !topRisk.isEmpty {
                Text(topRisk.singleSentence)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }

            if let watchItem = analysis.watchItems?.first, !watchItem.isEmpty {
                Text(watchItem.singleSentence)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct RiskDriverRow: View {
    let label: String
    let score: Double

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
            HStack {
                Text(label)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                Spacer()
                Text("\(Int(score))")
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.textPrimary)
            }

            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.surfaceSecondary)
                        .frame(height: 6)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(scoreColor)
                        .frame(width: geometry.size.width * (score / 100), height: 6)
                }
            }
            .frame(height: 6)
        }
    }

    private var scoreColor: Color {
        switch score {
        case 70...100: return .successTone
        case 50..<70: return .warningTone
        case 35..<50: return .criticalTone
        default: return .criticalTone
        }
    }
}

struct RecentDevelopmentsCard: View {
    let analysis: PositionAnalysis
    let events: [EventAnalysis]
    let recentNews: [NewsItem]

    private var developmentItems: [String] {
        let eventItems = events.compactMap { event in
            let text = event.scenarioSummary ?? event.summary ?? event.title
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : trimmed
        }

        if !eventItems.isEmpty {
            return Array(eventItems.prefix(3))
        }

        let newsItems = recentNews.compactMap { item in
            let trimmed = item.title.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : trimmed
        }

        if !newsItems.isEmpty {
            return Array(newsItems.prefix(3))
        }

        return Array((analysis.topRisks ?? []).prefix(3)).filter { !$0.isEmpty }
    }

    private var countsText: String {
        if !events.isEmpty {
            let major = events.filter { $0.significance == "major" }.count
            let minor = events.filter { $0.significance == "minor" }.count
            return "\(major) major • \(minor) minor"
        }

        let recentMajor = recentNews.filter { $0.significance == "major" }.count
        let recentMinor = recentNews.filter { $0.significance == "minor" }.count
        let major = (analysis.majorEventCount ?? 0) > 0 ? (analysis.majorEventCount ?? 0) : recentMajor
        let minor = (analysis.minorEventCount ?? 0) > 0 ? (analysis.minorEventCount ?? 0) : recentMinor
        return "\(major) major • \(minor) minor"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack {
                Text("Recent Developments")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                Spacer()

                Text(countsText)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }

            if !developmentItems.isEmpty {
                ForEach(Array(developmentItems.enumerated()), id: \.offset) { _, item in
                    HStack(alignment: .top, spacing: ClavisTheme.smallSpacing) {
                        Circle()
                            .fill(Color.criticalTone)
                            .frame(width: 6, height: 6)
                            .padding(.top, 7)
                        Text(item)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                    }
                }
            } else {
                Text("No material developments surfaced in the latest cycle.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct WhatToWatchCard: View {
    let analysis: PositionAnalysis

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("What to Watch")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            if let watchItems = analysis.watchItems, !watchItems.isEmpty {
                ForEach(Array(watchItems.prefix(3).enumerated()), id: \.offset) { index, item in
                    HStack(alignment: .top, spacing: ClavisTheme.smallSpacing) {
                        Text("\(index + 1).")
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.textTertiary)
                            .frame(width: 20, alignment: .leading)
                        Text(item)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                    }
                }
            } else {
                Text("Monitor for any deterioration in risk factors.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct EventAnalysesCard: View {
    let events: [EventAnalysis]
    let recentNews: [NewsItem]
    let ticker: String

    var body: some View {
        if events.isEmpty {
            if recentNews.isEmpty { return AnyView(EmptyView()) }

            return AnyView(
                VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                    Text("Recent Coverage")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)

                    ForEach(recentNews.prefix(5)) { item in
                        RecentNewsRow(item: item)
                    }
                }
                .padding(ClavisTheme.cardPadding)
                .clavisCardStyle(fill: .surfacePrimary)
            )
        }

        return AnyView(
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("Event Analyses")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                ForEach(events.prefix(5)) { event in
                    NavigationLink(destination: EventAnalysisDetailView(event: event, ticker: ticker)) {
                        EventAnalysisCompactRow(event: event)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        )
    }
}

struct RecentNewsRow: View {
    let item: NewsItem

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(item.title)
                .font(ClavisTypography.body)
                .foregroundColor(.textPrimary)
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 8) {
                if let significance = item.significance, !significance.isEmpty {
                    Text(significance.uppercased())
                        .font(ClavisTypography.footnote)
                        .foregroundColor(significance == "major" ? .criticalTone : .textTertiary)
                }

                if let source = item.source, !source.isEmpty {
                    Text(source)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }

                if let publishedAt = item.publishedAt {
                    Text(publishedAt.formatted(date: .abbreviated, time: .omitted))
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }
            }

            Text("Detailed event analysis was not available for this article in the latest cycle.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
        }
        .padding(.vertical, ClavisTheme.smallSpacing)
    }
}

struct EventAnalysisCompactRow: View {
    let event: EventAnalysis

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            VStack(alignment: .leading, spacing: 4) {
                Text(event.title)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textPrimary)
                    .lineLimit(2)

                if let significance = event.significance {
                    Text(significance.uppercased())
                        .font(ClavisTypography.footnote)
                        .foregroundColor(significance == "major" ? .criticalTone : .textTertiary)
                }
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.textTertiary)
        }
        .padding(.vertical, ClavisTheme.smallSpacing)
    }
}

struct EventAnalysisDetailView: View {
    let event: EventAnalysis
    let ticker: String

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                EventAnalysisHeader(event: event, ticker: ticker)

                EventRiskBriefCard(event: event, ticker: ticker)
            }
            .padding(ClavisTheme.cardPadding)
        }
        .background(Color.appBackground)
        .navigationTitle("Event Analysis")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private extension String {
    var singleSentence: String {
        let trimmed = sanitizedDisplayText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return trimmed }

        var endIndex: String.Index?
        var chars = Array(trimmed.dropFirst())
        var prevWasPeriod = false

        for (i, char) in chars.enumerated() {
            if ".!?".contains(char) {
                if prevWasPeriod {
                    let nextIdx = chars.index(chars.startIndex, offsetBy: i + 1, limitedBy: chars.endIndex)
                    if let ni = nextIdx, ni < chars.endIndex {
                        let next = chars[ni]
                        if next.isWhitespace || next.isUppercase {
                            endIndex = trimmed.index(trimmed.startIndex, offsetBy: i + 1)
                            break
                        }
                    }
                    prevWasPeriod = false
                } else {
                    let nextIdx = chars.index(chars.startIndex, offsetBy: i + 1, limitedBy: chars.endIndex)
                    if let ni = nextIdx, ni < chars.endIndex {
                        let next = chars[ni]
                        if next.isWhitespace || i == chars.count - 1 {
                            endIndex = trimmed.index(trimmed.startIndex, offsetBy: i + 1)
                            break
                        }
                    }
                    prevWasPeriod = true
                }
            } else {
                prevWasPeriod = false
            }
        }

        guard let end = endIndex else { return trimmed }
        return String(trimmed[..<end]).trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct EventAnalysisHeader: View {
    let event: EventAnalysis
    let ticker: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text(event.title)
                    .font(ClavisTypography.sectionTitle)
                    .foregroundColor(.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                if let significance = event.significance, !significance.isEmpty {
                    Text(significance.uppercased())
                        .font(ClavisTypography.footnote)
                        .foregroundColor(significance == "major" ? .criticalTone : .textTertiary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.surfaceSecondary)
                        .clipShape(Capsule())
                }
            }

            HStack(spacing: 8) {
                Text(ticker)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)

                if let source = event.source, !source.isEmpty {
                    Text("•")
                        .foregroundColor(.textTertiary)
                    Text(source)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }

                if let publishedAt = event.publishedAt {
                    Text("•")
                        .foregroundColor(.textTertiary)
                    Text(publishedAt.formatted(date: .abbreviated, time: .omitted))
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }
            }
        }
    }
}

struct EventRiskBriefCard: View {
    let event: EventAnalysis
    let ticker: String

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            BriefSection(
                title: "EVENT SUMMARY",
                content: fullAnalysisText,
                bullets: nil,
                accent: .textPrimary
            )

            Divider().overlay(Color.borderSubtle)

            BriefSection(
                title: "MARKET INTERPRETATION",
                content: marketInterpretationText,
                bullets: nil,
                accent: .textSecondary
            )

            Divider().overlay(Color.borderSubtle)

            BriefSection(
                title: "POSITION IMPACT",
                content: nil,
                bullets: positionImpactBullets,
                accent: .textSecondary
            )

            Divider().overlay(Color.borderSubtle)

            ActionSignalSection(actionText: actionSignalText, confidenceText: confidenceText)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private var fullAnalysisText: String {
        if let longAnalysis = normalizedLongAnalysis {
            return longAnalysis
        }

        if let summary = firstMeaningfulLine(event.summary) {
            return summary
        }

        return event.title
    }

    private var marketInterpretationText: String {
        if let scenario = firstMeaningfulLine(event.scenarioSummary) {
            return scenario
        }

        if let analysis = firstMeaningfulSentence(event.longAnalysis) {
            return analysis
        }

        return "The market is reacting to a new information set with mixed near-term implications."
    }

    private var positionImpactBullets: [String] {
        var bullets = event.keyImplications?.compactMap { firstMeaningfulLine($0) } ?? []

        if bullets.isEmpty, let followups = event.recommendedFollowups?.compactMap({ firstMeaningfulLine($0) }), !followups.isEmpty {
            bullets = followups
        }

        if bullets.isEmpty {
            bullets = ["For \(ticker), this changes the risk profile but not necessarily the core thesis."]
        }

        return Array(bullets.prefix(2))
    }

    private var actionSignalText: String {
        let direction = normalizedDirection
        let confidence = event.confidence ?? 0.5

        switch direction {
        case let value where value.contains("bull"):
            return confidence >= 0.7 ? "Add" : "Monitor"
        case let value where value.contains("bear"):
            return confidence >= 0.8 && significanceIsMajor ? "Exit" : "Reduce"
        case let value where value.contains("neutral"):
            return "Monitor"
        default:
            return "Monitor"
        }
    }

    private var confidenceText: String? {
        guard let confidence = event.confidence else { return nil }

        switch confidence {
        case 0.8...:
            return "High"
        case 0.6..<0.8:
            return "Medium"
        default:
            return "Low"
        }
    }

    private var significanceIsMajor: Bool {
        event.significance?.lowercased() == "major"
    }

    private var normalizedDirection: String {
        event.riskDirection?.lowercased().replacingOccurrences(of: "_", with: "-") ?? ""
    }

    private func cleanText(_ text: String) -> String {
        text.sanitizedDisplayText
    }

    private var normalizedLongAnalysis: String? {
        guard let longAnalysis = event.longAnalysis else { return nil }
        let cleaned = cleanText(longAnalysis)
        return cleaned.isEmpty ? nil : cleaned
    }

    private func firstMeaningfulLine(_ text: String?) -> String? {
        guard let text else { return nil }
        let cleaned = cleanText(text)
        return cleaned.isEmpty ? nil : cleaned
    }

    private func firstMeaningfulSentence(_ text: String?) -> String? {
        guard let text else { return nil }
        let cleaned = cleanText(text)
        guard !cleaned.isEmpty else { return nil }

        let sentence = cleaned.split(whereSeparator: { ".!?".contains($0) }).first.map(String.init)
        return sentence?.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct BriefSection: View {
    let title: String
    let content: String?
    let bullets: [String]?
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(ClavisTypography.footnote.weight(.bold))
                .foregroundColor(.textTertiary)

            if let content {
                Text(content)
                    .font(ClavisTypography.body)
                    .foregroundColor(accent)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if let bullets, !bullets.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(Array(bullets.prefix(2).enumerated()), id: \.offset) { _, bullet in
                        HStack(alignment: .top, spacing: 8) {
                            Circle()
                                .fill(Color.textTertiary)
                                .frame(width: 5, height: 5)
                                .padding(.top, 7)
                            Text(bullet)
                                .font(ClavisTypography.body)
                                .foregroundColor(accent)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
        }
    }
}

struct ActionSignalSection: View {
    let actionText: String
    let confidenceText: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("ACTION SIGNAL")
                .font(ClavisTypography.footnote.weight(.bold))
                .foregroundColor(.textTertiary)

            Text("Action: \(actionText)")
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.textPrimary)

            if let confidenceText {
                Text("Confidence: \(confidenceText)")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
        }
    }
}

struct NoAnalysisCard: View {
    let onRunAnalysis: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("No Analysis Yet")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Text("Run a fresh analysis to generate a detailed report for this holding.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            Button("Run Fresh Analysis") {
                onRunAnalysis()
            }
            .buttonStyle(.borderedProminent)
            .tint(.trustNavy)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct AnalysisProgressCard: View {
    let run: AnalysisRun

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack {
                Label("Analysis in progress", systemImage: "waveform.path.ecg")
                    .font(ClavisTypography.cardTitle)
                Spacer()
                if let positions = run.positionsProcessed {
                    Text("\(positions) positions")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }
            }

            Text(run.currentStageMessage ?? "Processing...")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .background(Color.warningSurface)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }
}

struct InlineErrorBanner: View {
    let message: String

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(.orange)
            Text(message)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
            Spacer()
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}
