import SwiftUI

struct TickerDetailView: View {
    let ticker: String

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var authViewModel: AuthViewModel
    @State private var detail: TickerDetailResponse?
    @State private var priceHistory: [PricePoint] = []
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var isMutatingWatchlist = false
    @State private var isRefreshingTicker = false
    @State private var isRefreshingAnalysis = false
    @State private var selectedDays: Int = 30
    @State private var hasLoaded = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                TickerInlineNavBar(
                    title: navTitle,
                    isWatchlisted: isInWatchlist,
                    isRefreshing: isRefreshingTicker,
                    canRefresh: authViewModel.subscriptionTier == "pro" || authViewModel.subscriptionTier == "admin",
                    onBack: { dismiss() },
                    onToggleWatchlist: { Task { await toggleWatchlist() } },
                    onRefresh: { Task { await refreshTicker() } }
                )

                if let errorMessage {
                    DashboardErrorCard(message: errorMessage)
                }

                if isLoading && detail == nil {
                    ClavisLoadingCard(
                        title: "Loading \(ticker)",
                        subtitle: "Pulling the latest cached ticker snapshot."
                    )
                } else if let detail {
                    TickerHeroCard(
                        ticker: ticker,
                        companyName: detail.profile.companyName ?? ticker,
                        sector: detail.profile.sector ?? detail.profile.industry ?? "Shared ticker cache",
                        grade: displayGrade(for: detail),
                        score: displayScore(for: detail),
                        previousScore: estimatedPreviousScore(for: detail),
                        rationale: tickerRationale(for: detail)
                    )

                    TickerPriceCard(
                        price: currency(detail.latestPrice.price),
                        changeText: priceChangeText(for: detail),
                        changeDirection: priceChangeDirection(for: detail),
                        selectedDays: $selectedDays,
                        priceHistory: priceHistory,
                        onDaysChange: { days in
                            Task { await loadPriceHistory(days: days) }
                        }
                    )

                    if detail.userContext.isHeld {
                        TickerAnalysisActionCard(
                            isRefreshing: isRefreshingAnalysis,
                            onRefreshAnalysis: { Task { await refreshPositionAnalysis(positionId: detail.position.id) } }
                        )
                    }

                    TickerMetricGridCard(metrics: fundamentals(for: detail))

                    if !riskDimensionsForDisplay(detail).isEmpty {
                        TickerDimensionsCard(dimensions: riskDimensionsForDisplay(detail))
                    }

                    if !detail.latestEventAnalyses.isEmpty {
                        TickerEventAnalysesCard(events: Array(detail.latestEventAnalyses.prefix(4)))
                    }

                    if !watchItems(for: detail).isEmpty {
                        TickerBulletedListCard(title: "Urgent", items: watchItems(for: detail))
                    }

                    if !detail.recentNews.isEmpty {
                        TickerNewsListCard(news: Array(detail.recentNews.prefix(3)))
                    }

                    if !detail.recentAlerts.isEmpty {
                        TickerAlertsListCard(alerts: Array(detail.recentAlerts.prefix(3)))
                    }
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.largeSpacing)
            .padding(.bottom, ClavisTheme.extraLargeSpacing)
        }
        .background(ClavisAtmosphereBackground())
        .toolbar(.hidden, for: .navigationBar)
        .task {
            guard !hasLoaded else { return }
            hasLoaded = true
            await reloadAll()
        }
        .refreshable {
            await reloadAll()
        }
    }

    private var isInWatchlist: Bool {
        detail?.userContext.isInWatchlist ?? false
    }

    private var navTitle: String {
        if let companyName = detail?.profile.companyName, !companyName.isEmpty {
            return "\(ticker) · \(companyName)"
        }
        return ticker
    }

    private func displayScore(for detail: TickerDetailResponse) -> Int {
        Int((detail.currentScore?.displayScore ?? detail.latestRiskSnapshot?.safetyScore ?? detail.position.totalScore ?? 50).rounded())
    }

    private func displayGrade(for detail: TickerDetailResponse) -> String {
        detail.currentScore?.displayGrade ?? detail.latestRiskSnapshot?.grade ?? detail.position.riskGrade ?? "C"
    }

    private func estimatedPreviousScore(for detail: TickerDetailResponse) -> Int {
        if let previousGrade = detail.position.previousGrade {
            return previousScore(for: previousGrade)
        }
        return max(0, displayScore(for: detail) - 8)
    }

    private func previousScore(for grade: String) -> Int {
        switch grade {
        case "A": return 83
        case "B": return 65
        case "C": return 45
        case "D": return 25
        case "F": return 8
        default: return 50
        }
    }

    private func tickerRationale(for detail: TickerDetailResponse) -> String {
        if let reasoning = detail.currentScore?.reasoning?.trimmingCharacters(in: .whitespacesAndNewlines), !reasoning.isEmpty {
            return reasoning
        }
        if let reasoning = detail.latestRiskSnapshot?.reasoning?.trimmingCharacters(in: .whitespacesAndNewlines), !reasoning.isEmpty {
            return reasoning
        }
        if let summary = detail.latestRiskSnapshot?.newsSummary?.trimmingCharacters(in: .whitespacesAndNewlines), !summary.isEmpty {
            return summary
        }
        return "Analysis data is available, but the latest rationale is still being assembled."
    }

    private func priceChangePercent(for detail: TickerDetailResponse) -> Double? {
        guard let price = detail.latestPrice.price,
              let previous = detail.latestPrice.previousClose,
              previous != 0 else { return nil }
        return ((price - previous) / previous) * 100
    }

    private func priceChangeText(for detail: TickerDetailResponse) -> String {
        guard let change = priceChangePercent(for: detail) else { return "--" }
        return String(format: "%@%.1f%%", change >= 0 ? "+" : "", change)
    }

    private func priceChangeDirection(for detail: TickerDetailResponse) -> TickerChangeDirection {
        guard let change = priceChangePercent(for: detail) else { return .flat }
        if change > 0 { return .up }
        if change < 0 { return .down }
        return .flat
    }

    private func fundamentals(for detail: TickerDetailResponse) -> [TickerMetricItem] {
        [
            TickerMetricItem(label: "P/E", value: number(detail.profile.peRatio)),
            TickerMetricItem(label: "Mkt cap", value: compactCurrency(detail.profile.marketCap)),
            TickerMetricItem(label: "Volatility", value: score(detail.latestRiskSnapshot?.factorBreakdown?.volatilityScore))
        ]
    }

    private func riskDimensionsForDisplay(_ detail: TickerDetailResponse) -> [TickerDimensionItem] {
        if let breakdown = detail.latestRiskSnapshot?.factorBreakdown {
            return [
                TickerDimensionItem(label: "Liquidity", value: breakdown.liquidityScore),
                TickerDimensionItem(label: "Volatility", value: breakdown.volatilityScore),
                TickerDimensionItem(label: "Leverage", value: breakdown.leverageScore),
                TickerDimensionItem(label: "Profitability", value: breakdown.profitabilityScore),
                TickerDimensionItem(label: "Macro", value: breakdown.macroAdjustment)
            ]
        }

        return []
    }

    private func watchItems(for detail: TickerDetailResponse) -> [String] {
        if let items = detail.currentAnalysis?.watchItems, !items.isEmpty {
            return Array(items.prefix(3)).map { $0.sanitizedDisplayText }
        }

        let eventDrivenItems = detail.latestEventAnalyses.prefix(3).compactMap { event in
            let title = event.title.sanitizedDisplayText
            let summary = event.summary?.sanitizedDisplayText.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if summary.isEmpty { return title }
            return "\(title) — \(summary)"
        }
        if !eventDrivenItems.isEmpty {
            return eventDrivenItems
        }

        let articleDrivenItems = detail.recentNews.prefix(3).compactMap { article in
            let title = article.title.sanitizedDisplayText
            let summary = article.summary?.sanitizedDisplayText.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if summary.isEmpty { return title }
            return "\(title) — \(summary)"
        }
        if !articleDrivenItems.isEmpty {
            return articleDrivenItems
        }

        return detail.recentAlerts.prefix(2).map { $0.message.sanitizedDisplayText }
    }

    @ViewBuilder
    private func fundamentalsCard(_ detail: TickerDetailResponse) -> some View {
        HoldingsSectionCard(title: "Snapshot", subtitle: "Shared ticker cache") {
            HStack(spacing: ClavisTheme.smallSpacing) {
                metricPill(title: "P/E", value: number(detail.profile.peRatio))
                metricPill(title: "52W High", value: currency(detail.profile.week52High))
                metricPill(title: "52W Low", value: currency(detail.profile.week52Low))
            }

            HStack(spacing: ClavisTheme.smallSpacing) {
                metricPill(title: "Open", value: currency(detail.latestPrice.openPrice))
                metricPill(title: "Day High", value: currency(detail.latestPrice.dayHigh))
                metricPill(title: "Day Low", value: currency(detail.latestPrice.dayLow))
            }

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(detail.profile.companyName ?? ticker)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.textPrimary)
                Text(detail.profile.sector ?? detail.profile.industry ?? "Shared ticker cache")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)

                if let summary = detail.latestRiskSnapshot?.newsSummary ?? detail.latestRiskSnapshot?.reasoning {
                    Text(summary)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }

                HStack(spacing: ClavisTheme.smallSpacing) {
                    metricPill(title: "Price", value: currency(detail.latestPrice.price))
                    metricPill(title: "Score", value: score(detail.latestRiskSnapshot?.safetyScore))
                    metricPill(title: "Freshness", value: freshnessText(detail.freshness.analysisAsOf))
                }

                if detail.userContext.isHeld {
                    Text("Already in holdings")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.riskA)
                }
            }
        }
    }

    @ViewBuilder
    private func aiScoreRationaleCard(_ score: RiskScore) -> some View {
        HoldingsSectionCard(
            title: "AI Score Rationale",
            subtitle: "Generated from the backfill analysis path"
        ) {
            HStack(spacing: ClavisTheme.smallSpacing) {
                metricPill(title: "Grade", value: score.displayGrade)
                metricPill(title: "Score", value: String(format: "%.0f", score.displayScore))
                metricPill(title: "Confidence", value: score.confidenceLevel.rawValue)
            }

            if let dims = score.factorBreakdown?.aiDimensions {
                ForEach(aiDimensions(from: dims)) { dimension in
                    TickerRiskDimensionRow(dimension: dimension)
                }
            }

            if let reasoning = score.reasoning?.trimmingCharacters(in: .whitespacesAndNewlines), !reasoning.isEmpty {
                Text(reasoning)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .padding(.top, 4)
            }
        }
    }

    @ViewBuilder
    private func newsCard(_ detail: TickerDetailResponse) -> some View {
        HoldingsSectionCard(title: "Recent News", subtitle: "Shared ticker-level coverage") {
            ForEach(detail.recentNews.prefix(5)) { item in
                NavigationLink(destination: ArticleDetailView(articleId: item.id)) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(item.title)
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.textPrimary)

                        if let summary = item.summary?.trimmingCharacters(in: .whitespacesAndNewlines), !summary.isEmpty {
                            Text(summary)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                        }

                        HStack {
                            if let source = item.source {
                                Text(source)
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textTertiary)
                            }
                            Spacer()
                            Text("Read article →")
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.informational)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(ClavisTheme.cardPadding)
                    .clavisCardStyle(fill: .surfaceElevated)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func riskDimensions(from breakdown: FactorBreakdown) -> [TickerRiskDimensionRowData] {
        [
            TickerRiskDimensionRowData(label: "Liquidity", value: breakdown.liquidityScore, icon: "drop.fill"),
            TickerRiskDimensionRowData(label: "Volatility", value: breakdown.volatilityScore, icon: "waveform.path.ecg"),
            TickerRiskDimensionRowData(label: "Leverage", value: breakdown.leverageScore, icon: "scalemass"),
            TickerRiskDimensionRowData(label: "Profitability", value: breakdown.profitabilityScore, icon: "chart.line.uptrend.xyaxis"),
            TickerRiskDimensionRowData(label: "Macro", value: breakdown.macroAdjustment, icon: "globe"),
            TickerRiskDimensionRowData(label: "Events", value: breakdown.eventAdjustment, icon: "newspaper")
        ]
    }

    private func aiDimensions(from dims: AIDimensions) -> [TickerRiskDimensionRowData] {
        [
            TickerRiskDimensionRowData(label: "News Sentiment", value: dims.newsSentiment, icon: "newspaper"),
            TickerRiskDimensionRowData(label: "Macro Exposure", value: dims.macroExposure, icon: "globe"),
            TickerRiskDimensionRowData(label: "Position Sizing", value: dims.positionSizing, icon: "chart.pie"),
            TickerRiskDimensionRowData(label: "Volatility", value: dims.volatilityTrend, icon: "waveform.path.ecg"),
            TickerRiskDimensionRowData(label: "Durability", value: dims.thesisRisk, icon: "shield.lefthalf.filled")
        ]
    }

    private func hasDetailedDimensions(_ score: RiskScore?) -> Bool {
        guard let score else { return false }
        return score.newsSentiment != nil || score.macroExposure != nil || score.positionSizing != nil || score.volatilityTrend != nil
    }

    @ViewBuilder
    private func alertsCard(_ alerts: [Alert]) -> some View {
        HoldingsSectionCard(title: "Recent Alerts", subtitle: "Ticker-specific changes for your account") {
            ForEach(alerts.prefix(5)) { alert in
                VStack(alignment: .leading, spacing: 6) {
                    Text(alert.type.displayName)
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textPrimary)
                    Text(alert.message)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                    Text(alert.createdAt.formatted(date: .abbreviated, time: .shortened))
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(ClavisTheme.cardPadding)
                .clavisCardStyle(fill: .surfaceElevated)
            }
        }
    }

    private func metricPill(title: String, value: String, accent: Color = .textPrimary) -> some View {
        HoldingsStatPill(title: title, value: value, accent: accent)
    }

    private func loadDetail() async {
        isLoading = true
        defer { isLoading = false }
        do {
            detail = try await APIService.shared.fetchTickerDetail(ticker: ticker)
            errorMessage = nil
        } catch {
            errorMessage = "Failed to load \(ticker): \(error.localizedDescription)"
        }
    }

    private func loadPriceHistory(days: Int = 30) async {
        do {
            let response = try await APIService.shared.fetchPriceHistory(ticker: ticker, days: days)
            priceHistory = response.prices
            errorMessage = nil
        } catch {
            if priceHistory.isEmpty {
                errorMessage = nil
            }
        }
    }

    private func reloadAll() async {
        await loadDetail()
        await loadPriceHistory(days: selectedDays)
    }

    private func refreshPositionAnalysis(positionId: String) async {
        isRefreshingAnalysis = true
        defer { isRefreshingAnalysis = false }

        do {
            let trigger = try await APIService.shared.triggerAnalysis(positionId: positionId)
            if let runId = trigger.analysisRunId {
                for _ in 0..<60 {
                    let run = try await APIService.shared.fetchAnalysisRun(id: runId)
                    if run.isTerminal {
                        break
                    }
                    try? await Task.sleep(nanoseconds: 1_500_000_000)
                }
            }
            await loadDetail()
        } catch {
            errorMessage = "Analysis refresh failed: \(error.localizedDescription)"
        }
    }

    private func toggleWatchlist() async {
        isMutatingWatchlist = true
        defer { isMutatingWatchlist = false }
        do {
            if isInWatchlist {
                _ = try await APIService.shared.removeFromWatchlist(ticker: ticker)
            } else {
                _ = try await APIService.shared.addToWatchlist(ticker: ticker)
            }
            await loadDetail()
        } catch {
            errorMessage = "Watchlist update failed: \(error.localizedDescription)"
        }
    }

    private func refreshTicker() async {
        isRefreshingTicker = true
        defer { isRefreshingTicker = false }
        do {
            _ = try await APIService.shared.refreshTicker(ticker: ticker)
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            await reloadAll()
        } catch {
            errorMessage = "Refresh failed: \(error.localizedDescription)"
        }
    }

    private func currency(_ value: Double?) -> String {
        guard let value else { return "--" }
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "--"
    }

    private func number(_ value: Double?) -> String {
        guard let value else { return "--" }
        return String(format: "%.1f", value)
    }

    private func compactCurrency(_ value: Double?) -> String {
        guard let value else { return "--" }

        let absValue = abs(value)
        if absValue >= 1_000_000_000_000 {
            return String(format: "$%.1fT", value / 1_000_000_000_000)
        }
        if absValue >= 1_000_000_000 {
            return String(format: "$%.1fB", value / 1_000_000_000)
        }
        if absValue >= 1_000_000 {
            return String(format: "$%.1fM", value / 1_000_000)
        }
        return currency(value)
    }

    private func score(_ value: Double?) -> String {
        guard let value else { return "--" }
        return "\(Int(value.rounded()))"
    }

    private func freshnessText(_ date: Date?) -> String {
        guard let date else { return "Pending" }
        return date.formatted(date: .abbreviated, time: .shortened)
    }
}

private struct TickerInlineNavBar: View {
    let title: String
    let isWatchlisted: Bool
    let isRefreshing: Bool
    let canRefresh: Bool
    let onBack: () -> Void
    let onToggleWatchlist: () -> Void
    let onRefresh: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Button(action: onBack) {
                Text("‹ Back")
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.informational)
            }
            .buttonStyle(.plain)

            Text(title)
                .font(.system(size: 17, weight: .semibold))
                .foregroundColor(.textPrimary)
                .lineLimit(1)

            Spacer()

            if canRefresh {
                Button(action: onRefresh) {
                    Image(systemName: isRefreshing ? "hourglass" : "arrow.clockwise")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(.textSecondary)
                }
                .buttonStyle(.plain)
            }

            Button(action: onToggleWatchlist) {
                Image(systemName: isWatchlisted ? "star.fill" : "star")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(isWatchlisted ? .informational : .textSecondary)
            }
            .buttonStyle(.plain)
        }
    }
}

private struct TickerHeroCard: View {
    let ticker: String
    let companyName: String
    let sector: String
    let grade: String
    let score: Int
    let previousScore: Int
    let rationale: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 16) {
                GradeTag(grade: grade, large: true)

                VStack(alignment: .leading, spacing: 4) {
                    Text("\(score)")
                        .font(ClavisTypography.dataNumber)
                        .foregroundColor(.textPrimary)
                        .monospacedDigit()

                    HStack(spacing: 8) {
                        Text("Risk score · was \(previousScore)")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)

                        Text(scoreDeltaText)
                            .font(.system(size: 12, weight: .semibold, design: .monospaced))
                            .foregroundColor(score >= previousScore ? .riskA : .riskD)
                    }

                    Text(sector.uppercased())
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)
                }
            }

            Divider()
                .overlay(Color.border)

            Text(rationale)
                .font(ClavisTypography.bodySmall)
                .foregroundColor(.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }

    private var scoreDeltaText: String {
        let delta = score - previousScore
        let arrow = delta >= 0 ? "▲" : "▼"
        return "\(arrow) \(abs(delta))"
    }
}

private enum TickerChangeDirection {
    case up
    case down
    case flat
}

private struct TickerPriceCard: View {
    let price: String
    let changeText: String
    let changeDirection: TickerChangeDirection
    @Binding var selectedDays: Int
    let priceHistory: [PricePoint]
    let onDaysChange: (Int) -> Void

    private let dayOptions: [Int] = [30, 90, 365]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Price · \(labelForDays(selectedDays))")
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)
                    Text(price)
                        .font(ClavisTypography.dataNumber)
                        .foregroundColor(.textPrimary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text(changeText)
                        .font(.system(size: 16, weight: .semibold, design: .monospaced))
                        .foregroundColor(changeColor)
                    Text("Today")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }
            }

            TickerSparkline(priceHistory: priceHistory, direction: changeDirection)
                .frame(height: 64)

            HStack(spacing: 6) {
                ForEach(dayOptions, id: \.self) { days in
                    Button {
                        selectedDays = days
                        onDaysChange(days)
                    } label: {
                        Text(labelForDays(days))
                            .font(.system(size: 11, weight: .medium, design: .monospaced))
                            .foregroundColor(selectedDays == days ? .textPrimary : .textSecondary)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 6)
                            .background(selectedDays == days ? Color.surfaceElevated : Color.clear)
                            .overlay(
                                RoundedRectangle(cornerRadius: 6, style: .continuous)
                                    .stroke(selectedDays == days ? Color.border : Color.clear, lineWidth: 1)
                            )
                            .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }

    private var changeColor: Color {
        switch changeDirection {
        case .up: return .riskA
        case .down: return .riskD
        case .flat: return .textSecondary
        }
    }

    private func labelForDays(_ days: Int) -> String {
        switch days {
        case 30: return "1M"
        case 90: return "3M"
        default: return "1Y"
        }
    }
}

    private struct TickerSparkline: View {
        let priceHistory: [PricePoint]
        let direction: TickerChangeDirection

        private var orderedHistory: [PricePoint] {
            priceHistory.sorted { $0.recordedAt < $1.recordedAt }
        }

        var body: some View {
            GeometryReader { geometry in
                Path { path in
                    let points = normalizedPoints(in: geometry.size)
                    guard let first = points.first else { return }
                    path.move(to: first)
                    for point in points.dropFirst() {
                        path.addLine(to: point)
                    }
                }
                .stroke(lineColor, style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
            }
        }

        private var lineColor: Color {
            switch direction {
            case .up: return .riskA
            case .down: return .riskD
            case .flat: return .textSecondary
            }
        }

        private func normalizedPoints(in size: CGSize) -> [CGPoint] {
            let values = orderedHistory.map(\.price)
            guard values.count > 1,
                  let minValue = values.min(),
                  let maxValue = values.max() else {
                return [CGPoint(x: 0, y: size.height / 2), CGPoint(x: size.width, y: size.height / 2)]
            }

            let range = max(maxValue - minValue, 0.001)
            return values.enumerated().map { index, value in
                let x = (CGFloat(index) / CGFloat(max(values.count - 1, 1))) * size.width
                let y = size.height - ((CGFloat(value - minValue) / CGFloat(range)) * (size.height - 6)) - 3
                return CGPoint(x: x, y: y)
            }
        }
    }

private struct TickerEventAnalysesCard: View {
    let events: [EventAnalysis]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Event analysis")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            VStack(spacing: 0) {
                ForEach(events) { event in
                    NavigationLink(destination: TickerEventAnalysisDetailView(event: event)) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(event.title)
                                .font(ClavisTypography.bodyEmphasis)
                                .foregroundColor(.textPrimary)
                                .multilineTextAlignment(.leading)

                            if let summary = event.summary?.trimmingCharacters(in: .whitespacesAndNewlines), !summary.isEmpty {
                                Text(summary)
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                                    .lineLimit(2)
                                    .multilineTextAlignment(.leading)
                            }

                            HStack {
                                if let source = event.source {
                                    Text(source)
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.textTertiary)
                                }
                                Spacer()
                                Text("Open")
                                    .font(ClavisTypography.footnoteEmphasis)
                                    .foregroundColor(.informational)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 12)
                    }
                    .buttonStyle(.plain)

                    if event.id != events.last?.id {
                        Divider().overlay(Color.border)
                    }
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct TickerAnalysisActionCard: View {
    let isRefreshing: Bool
    let onRefreshAnalysis: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Position analysis")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            Text("Queue a fresh backend run for this held position.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            Button(action: onRefreshAnalysis) {
                Label(isRefreshing ? "Refreshing" : "Refresh analysis", systemImage: "arrow.clockwise")
                    .font(ClavisTypography.footnoteEmphasis)
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.informational)
            .disabled(isRefreshing)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct TickerEventAnalysisDetailView: View {
    @Environment(\.dismiss) private var dismiss
    let event: EventAnalysis

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                HStack {
                    Button(action: { dismiss() }) {
                        Text("‹ Back")
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(.informational)
                    }
                    .buttonStyle(.plain)

                    Spacer()
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text(event.title)
                        .font(ClavisTypography.h2)
                        .foregroundColor(.textPrimary)
                        .multilineTextAlignment(.leading)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    HStack {
                        if let source = event.source {
                            Text(source)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                        }
                        Spacer()
                        Text(event.publishedAt?.formatted(date: .abbreviated, time: .shortened) ?? "")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }
                }
                .padding(ClavisTheme.cardPadding)
                .clavisCardStyle(fill: .surface)

                if let summary = event.summary?.trimmingCharacters(in: .whitespacesAndNewlines), !summary.isEmpty {
                    TickerAnalysisDetailSection(title: "What happened", text: strippedAnalysis(summary, title: event.title))
                }

                if let longAnalysis = event.longAnalysis?.trimmingCharacters(in: .whitespacesAndNewlines), !longAnalysis.isEmpty {
                    TickerAnalysisDetailSection(title: "Analysis", text: strippedAnalysis(longAnalysis, title: event.title))
                }

                if let scenario = event.scenarioSummary?.trimmingCharacters(in: .whitespacesAndNewlines), !scenario.isEmpty {
                    TickerAnalysisDetailSection(title: "What it means", text: strippedAnalysis(scenario, title: event.title))
                }

                if let implications = event.keyImplications, !implications.isEmpty {
                    TickerAnalysisListSection(title: "Key implications", items: implications)
                }

                if let followups = event.recommendedFollowups, !followups.isEmpty {
                    TickerAnalysisListSection(title: "Follow-up notes", items: followups)
                }

                if let sourceURLString = event.sourceURL,
                   let url = URL(string: sourceURLString) {
                    Link(destination: url) {
                        Text("Open source article →")
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(.informational)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .padding(ClavisTheme.cardPadding)
                    .clavisCardStyle(fill: .surfaceElevated)
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.largeSpacing)
            .padding(.bottom, ClavisTheme.extraLargeSpacing)
        }
        .background(ClavisAtmosphereBackground())
        .toolbar(.hidden, for: .navigationBar)
    }

    private func strippedAnalysis(_ text: String, title: String) -> String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalizedTitle = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !normalizedTitle.isEmpty else { return trimmed }

        let lowerText = trimmed.lowercased()
        let lowerTitle = normalizedTitle.lowercased()
        if lowerText == lowerTitle {
            return ""
        }
        if lowerText.hasPrefix(lowerTitle) {
            let startIndex = trimmed.index(trimmed.startIndex, offsetBy: min(trimmed.count, normalizedTitle.count))
            let remainder = trimmed[startIndex...].trimmingCharacters(in: CharacterSet(charactersIn: " \n\t:-—–"))
            if !remainder.isEmpty {
                return String(remainder)
            }
        }
        return trimmed
    }
}

private struct TickerAnalysisDetailSection: View {
    let title: String
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)
                .frame(maxWidth: .infinity, alignment: .leading)

            Text(text)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
                .multilineTextAlignment(.leading)
                .lineSpacing(4)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct TickerAnalysisListSection: View {
    let title: String
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)
                .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .leading, spacing: 8) {
                ForEach(items, id: \.self) { item in
                    Text("• \(item)")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .multilineTextAlignment(.leading)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct TickerMetricItem: Identifiable {
    let id = UUID()
    let label: String
    let value: String
}

private struct TickerMetricGridCard: View {
    let metrics: [TickerMetricItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Snapshot & fundamentals")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 3), spacing: 8) {
                ForEach(metrics) { metric in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(metric.label)
                            .font(ClavisTypography.label)
                            .foregroundColor(.textSecondary)
                        Text(metric.value)
                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                            .foregroundColor(.textPrimary)
                            .monospacedDigit()
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(10)
                    .clavisSecondaryCardStyle(fill: .surfaceElevated)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct TickerDimensionItem: Identifiable {
    let id = UUID()
    let label: String
    let value: Double?
}

private struct TickerDimensionsCard: View {
    let dimensions: [TickerDimensionItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Risk dimensions")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            ForEach(dimensions) { dimension in
                VStack(alignment: .leading, spacing: 5) {
                    HStack {
                        Text(dimension.label)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                        Spacer()
                        Text(valueText(for: dimension.value))
                            .font(.system(size: 12, weight: .semibold, design: .monospaced))
                            .foregroundColor(.textPrimary)
                    }

                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Rectangle()
                                .fill(Color.border)
                                .frame(height: 4)
                            Rectangle()
                                .fill(Color.textPrimary.opacity(0.5))
                                .frame(width: geo.size.width * normalizedValue(dimension.value), height: 4)
                        }
                    }
                    .frame(height: 4)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }

    private func normalizedValue(_ value: Double?) -> CGFloat {
        CGFloat(min(max((value ?? 20) / 100, 0.05), 1.0))
    }

    private func valueText(for value: Double?) -> String {
        guard let value else { return "--" }
        return "\(Int(value.rounded()))"
    }
}

private struct TickerBulletedListCard: View {
    let title: String
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            ForEach(items, id: \.self) { item in
                HStack(alignment: .top, spacing: 10) {
                    Circle()
                        .fill(Color.textSecondary)
                        .frame(width: 5, height: 5)
                        .padding(.top, 6)
                    Text(item)
                        .font(ClavisTypography.bodySmall)
                        .foregroundColor(.textPrimary)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct TickerNewsListCard: View {
    let news: [NewsItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Recent news")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            VStack(spacing: 0) {
                ForEach(news) { item in
                    NavigationLink(destination: ArticleDetailView(articleId: item.id)) {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(item.source ?? "")
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                                Spacer()
                                Text(item.publishedAt?.formatted(date: .omitted, time: .shortened) ?? "")
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                            }

                            Text(item.title)
                                .font(ClavisTypography.bodySmall)
                                .foregroundColor(.textPrimary)
                                .multilineTextAlignment(.leading)

                            Text("Read article →")
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.informational)
                        }
                        .padding(.vertical, 12)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 2)
            .clavisCardStyle(fill: .surface)
        }
    }
}

private struct TickerAlertsListCard: View {
    let alerts: [Alert]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Recent alerts")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            VStack(spacing: 0) {
                ForEach(alerts) { alert in
                    HStack(alignment: .top, spacing: 12) {
                        GradeTag(grade: alert.newGrade ?? alert.previousGrade ?? fallbackGrade(for: alert), compact: true)

                        VStack(alignment: .leading, spacing: 3) {
                            Text(alert.type.displayName)
                                .font(ClavisTypography.label)
                                .foregroundColor(.textSecondary)
                            Text(alert.message)
                                .font(ClavisTypography.bodySmall)
                                .foregroundColor(.textPrimary)
                        }

                        Spacer()

                        Text(alert.createdAt.formatted(date: .omitted, time: .shortened))
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }
                    .padding(.vertical, 12)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 2)
            .clavisCardStyle(fill: .surface)
        }
    }

    private func fallbackGrade(for alert: Alert) -> String {
        switch alert.type.severity {
        case .critical: return "F"
        case .warning: return "C"
        case .informational: return "B"
        }
    }
}

struct TickerRiskDimensionRowData: Identifiable {
    let id = UUID()
    let label: String
    let value: Double?
    let icon: String
}

struct TickerRiskDimensionRow: View {
    let dimension: TickerRiskDimensionRowData

    var body: some View {
        HStack(spacing: ClavisTheme.mediumSpacing) {
            Image(systemName: dimension.icon)
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(dimensionColor)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(dimension.label)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                    Spacer()
                    Text(valueText)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(dimensionColor)
                }

                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 3)
                            .fill(Color.surfaceSecondary)
                            .frame(height: 4)
                        RoundedRectangle(cornerRadius: 3)
                            .fill(dimensionColor)
                            .frame(width: max(8, geo.size.width * normalizedValue), height: 4)
                    }
                }
                .frame(height: 4)
            }
        }
    }

    private var normalizedValue: Double {
        guard let value = dimension.value else { return 0.2 }
        return min(max(value / 100.0, 0.05), 1.0)
    }

    private var valueText: String {
        guard let value = dimension.value else { return "--" }
        return "\(Int(value.rounded()))"
    }

    private var dimensionColor: Color {
        guard let value = dimension.value else { return .textTertiary }
        switch value {
        case ..<35:
            return .criticalTone
        case ..<65:
            return .warningTone
        default:
            return .successTone
        }
    }
}

struct TickerSearchSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var results: [TickerSearchResult] = []
    @State private var isSearching = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                Section {
                    TextField("Search shared tickers", text: $query)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                        .onChange(of: query) { _, newValue in
                            Task { await search(newValue) }
                        }
                }

                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .foregroundColor(.riskF)
                    }
                }

                if isSearching {
                    Section {
                        ProgressView()
                    }
                }

                Section("Results") {
                    ForEach(results) { result in
                        NavigationLink(destination: TickerDetailView(ticker: result.ticker)) {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(result.ticker)
                                        .font(ClavisTypography.bodyEmphasis)
                                    Text(result.companyName)
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.textSecondary)
                                }
                                Spacer()
                                GradeTag(grade: result.grade ?? "C", compact: true)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Search Tickers")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private func search(_ value: String) async {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            results = []
            errorMessage = nil
            return
        }

        isSearching = true
        defer { isSearching = false }

        do {
            results = try await APIService.shared.searchTickers(query: trimmed)
            errorMessage = nil
        } catch {
            results = []
            errorMessage = error.localizedDescription
        }
    }
}
