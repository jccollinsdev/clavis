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
                CX2NavBar(
                    title: ticker,
                    subtitle: detail?.profile.companyName ?? detail?.profile.sector ?? "Ticker detail"
                ) {
                    Button(action: { dismiss() }) {
                        HStack(spacing: 1) {
                            Image(systemName: "chevron.left")
                                .font(.system(size: 12, weight: .semibold))
                            Text("Holdings")
                                .font(.system(size: 15, weight: .regular))
                                .lineLimit(1)
                                .fixedSize(horizontal: true, vertical: false)
                        }
                        .foregroundColor(.informational)
                    }
                    .buttonStyle(.plain)
                } trailing: {
                    if authViewModel.subscriptionTier == "pro" || authViewModel.subscriptionTier == "admin" {
                        CX2IconButton(action: { Task { await refreshTicker() } }) {
                            Image(systemName: isRefreshingTicker ? "hourglass" : "arrow.clockwise")
                                .font(.system(size: 15, weight: .medium))
                        }
                    }

                    CX2IconButton(action: { Task { await toggleWatchlist() } }) {
                        Image(systemName: isInWatchlist ? "star.fill" : "star")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(isInWatchlist ? .informational : .textPrimary)
                    }
                }

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

                    if let analysisState = detail.analysisState {
                        TickerAnalysisStateCard(
                            source: detail.source ?? analysisState.source ?? "shared",
                            status: analysisState.status,
                            coverageState: analysisState.coverageState ?? detail.coverageState,
                            analysisAsOf: analysisState.analysisAsOf ?? detail.freshness.analysisAsOf,
                            lastNewsRefreshAt: analysisState.lastNewsRefreshAt ?? detail.freshness.lastNewsRefreshAt,
                            newsRefreshStatus: analysisState.newsRefreshStatus ?? detail.freshness.newsRefreshStatus,
                            priceAsOf: analysisState.priceAsOf ?? detail.freshness.priceAsOf,
                            newsAsOf: analysisState.newsAsOf ?? detail.freshness.newsAsOf,
                            latestAnalysisRun: detail.latestAnalysisRun,
                            latestRefreshJob: detail.latestRefreshJob
                        )
                    }

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

                    if let dimensions = riskDimensions(for: detail) {
                        TickerRiskDimensionsCard(dimensions: dimensions)
                    }

                    if detail.currentScore != nil || detail.currentAnalysis != nil {
                        aiScoreRationaleCard(detail)
                    }

                    if !detail.latestEventAnalyses.isEmpty {
                        TickerEventAnalysesCard(events: Array(detail.latestEventAnalyses.prefix(4)))
                    }

                    if !watchItems(for: detail).isEmpty {
                        TickerBulletedListCard(title: "Urgent", items: watchItems(for: detail))
                    }

                    if !detail.recentAlerts.isEmpty {
                        TickerAlertsListCard(alerts: Array(detail.recentAlerts.prefix(3)))
                    }
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.top, 0)
            .padding(.bottom, ClavisTheme.floatingTabHeight + ClavisTheme.floatingTabInset + ClavisTheme.extraLargeSpacing)
        }
        .contentMargins(.top, 0, for: .scrollContent)
        .contentMargins(.bottom, 0, for: .scrollContent)
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
        Int((detail.currentScore?.displayScore ?? detail.position.totalScore ?? detail.latestRiskSnapshot?.safetyScore ?? 50).rounded())
    }

    private func displayGrade(for detail: TickerDetailResponse) -> String {
        detail.currentScore?.displayGrade ?? detail.position.riskGrade ?? detail.latestRiskSnapshot?.grade ?? "C"
    }

    private func estimatedPreviousScore(for detail: TickerDetailResponse) -> Int? {
        if let previousGrade = detail.position.previousGrade {
            return previousScore(for: previousGrade)
        }
        return nil
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
        if let methodology = detail.currentAnalysis?.methodology?.trimmingCharacters(in: .whitespacesAndNewlines), !methodology.isEmpty {
            return methodology
        }
        if let coverageNote = detail.currentScore?.coverageNote?.trimmingCharacters(in: .whitespacesAndNewlines), !coverageNote.isEmpty {
            return coverageNote
        }
        if let reasoning = detail.latestRiskSnapshot?.reasoning?.trimmingCharacters(in: .whitespacesAndNewlines), !reasoning.isEmpty {
            return reasoning
        }
        if let summary = detail.latestRiskSnapshot?.newsSummary?.trimmingCharacters(in: .whitespacesAndNewlines), !summary.isEmpty {
            return summary
        }
        return "Coverage is still being assembled for this ticker."
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

    private func riskDimensions(for detail: TickerDetailResponse) -> [TickerRiskDimensionItem]? {
        if let ai = detail.currentScore?.factorBreakdown?.aiDimensions ?? detail.latestRiskSnapshot?.factorBreakdown?.aiDimensions {
            var dimensions = [
                TickerRiskDimensionItem(title: "News sentiment", value: ai.newsSentiment, accent: .riskA),
                TickerRiskDimensionItem(title: "Macro exposure", value: ai.macroExposure, accent: .riskB),
                TickerRiskDimensionItem(title: "Volatility trend", value: ai.volatilityTrend, accent: .riskD),
            ]
            if detail.userContext.isHeld {
                dimensions.insert(TickerRiskDimensionItem(title: "Position sizing", value: ai.positionSizing, accent: .riskC), at: 2)
            }
            return dimensions
        }

        guard let score = detail.currentScore else { return nil }
        var dimensions = [
            TickerRiskDimensionItem(title: "News sentiment", value: score.newsSentiment, accent: .riskA),
            TickerRiskDimensionItem(title: "Macro exposure", value: score.macroExposure, accent: .riskB),
            TickerRiskDimensionItem(title: "Volatility trend", value: score.volatilityTrend, accent: .riskD),
        ]
        if detail.userContext.isHeld {
            dimensions.insert(TickerRiskDimensionItem(title: "Position sizing", value: score.positionSizing, accent: .riskC), at: 2)
        }
        return dimensions
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
                    metricPill(title: "Score", value: score(Double(displayScore(for: detail))))
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
    private func aiScoreRationaleCard(_ detail: TickerDetailResponse) -> some View {
        let rationale = tickerRationale(for: detail)
        let methodology = detail.currentAnalysis?.methodology?.trimmingCharacters(in: .whitespacesAndNewlines)
            ?? detail.currentScore?.coverageNote?.trimmingCharacters(in: .whitespacesAndNewlines)
            ?? detail.methodology?.trimmingCharacters(in: .whitespacesAndNewlines)

        HoldingsSectionCard(
            title: "Risk Score Rationale",
            subtitle: "Method and summary"
        ) {
            Text(rationale)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)

            if let methodology, !methodology.isEmpty {
                Text(methodology)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .padding(.top, 4)
            }
        }
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
                    if let reason = alert.changeReason?.sanitizedDisplayText, !reason.isEmpty {
                        Text(reason)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                    }
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

            Spacer()

            if canRefresh {
                Button(action: onRefresh) {
                    Image(systemName: isRefreshing ? "hourglass" : "arrow.clockwise")
                        .font(.system(size: 15, weight: .semibold))
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
    let previousScore: Int?
    let rationale: String

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .center, spacing: 14) {
                GradeTag(grade: grade, large: true)

                VStack(alignment: .leading, spacing: 4) {
                    CX2SectionLabel(text: "Risk score")

                    Text("\(score)")
                        .font(.system(size: 44, weight: .bold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                        .monospacedDigit()

                    if let previousScore {
                        HStack(spacing: 8) {
                            Text(scoreDeltaText(previousScore: previousScore))
                                .font(.system(size: 13, weight: .semibold, design: .monospaced))
                                .foregroundColor(score >= previousScore ? .riskA : .riskD)

                            Text("was \(previousScore)")
                                .font(.system(size: 12, weight: .regular))
                                .foregroundColor(.textSecondary)
                        }
                    }

                    Text(sector)
                        .font(.system(size: 12, weight: .regular))
                        .foregroundColor(.textSecondary)
                }
            }

            Text(rationale)
                .font(.system(size: 14, weight: .regular))
                .foregroundColor(.textSecondary)
                .lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func scoreDeltaText(previousScore: Int) -> String {
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

private struct TickerAnalysisStateCard: View {
    let source: String
    let status: String
    let coverageState: String?
    let analysisAsOf: Date?
    let lastNewsRefreshAt: Date?
    let newsRefreshStatus: String?
    let priceAsOf: Date?
    let newsAsOf: Date?
    let latestAnalysisRun: AnalysisRun?
    let latestRefreshJob: TickerRefreshJob?

    var body: some View {
        HoldingsSectionCard(title: "State", subtitle: "Freshness and job status") {
            HStack(spacing: 8) {
                stateChip(text: statusLabel)
                stateChip(text: source.capitalized)
                if let coverageState, !coverageState.isEmpty {
                    stateChip(text: coverageState.capitalized)
                }
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(detailLine)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)

                if let lastNewsRefreshAt {
                    Text("News refreshed \(lastNewsRefreshAt.formatted(date: .abbreviated, time: .shortened))")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }

                if let runStatus = latestAnalysisRun?.status, !runStatus.isEmpty {
                    Text("Analysis run: \(runStatus.capitalized)")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }

                if let refreshStatus = latestRefreshJob?.status, !refreshStatus.isEmpty {
                    Text("Refresh job: \(refreshStatus.capitalized)")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }

                if let newsRefreshStatus, !newsRefreshStatus.isEmpty {
                    Text("News cache: \(newsRefreshStatus.capitalized)")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }
            }
        }
    }

    private var statusLabel: String {
        switch status {
        case "queued": return "Queued"
        case "running": return "Running"
        case "failed": return "Failed"
        case "ready", "fresh": return "Ready"
        case "thin", "stale": return "Thin"
        default: return status.capitalized
        }
    }

    private var detailLine: String {
        let analysisText = analysisAsOf?.formatted(date: .abbreviated, time: .shortened) ?? "pending"
        let priceText = priceAsOf?.formatted(date: .abbreviated, time: .shortened) ?? "pending"
        let newsText = newsAsOf?.formatted(date: .abbreviated, time: .shortened) ?? "pending"
        return "Analysis \(analysisText) · Price \(priceText) · News \(newsText)"
    }

    @ViewBuilder
    private func stateChip(text: String) -> some View {
        Text(text)
            .font(.system(size: 11, weight: .semibold))
            .foregroundColor(.textPrimary)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.surfaceElevated)
            .clipShape(Capsule())
    }
}

private struct TickerPriceCard: View {
    let price: String
    let changeText: String
    let changeDirection: TickerChangeDirection
    @Binding var selectedDays: Int
    let priceHistory: [PricePoint]
    let onDaysChange: (Int) -> Void

    private let dayOptions: [Int] = [1, 7, 30, 90, 365]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(price)
                        .font(.system(size: 26, weight: .bold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                    Text(labelForDays(selectedDays).lowercased())
                        .font(.system(size: 12, weight: .regular))
                        .foregroundColor(.textSecondary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text(changeText)
                        .font(.system(size: 14, weight: .semibold, design: .monospaced))
                        .foregroundColor(changeColor)
                    Text("Today")
                        .font(.system(size: 11, weight: .regular))
                        .foregroundColor(.textSecondary)
                }
            }

            TickerSparkline(priceHistory: priceHistory, direction: changeDirection)
                .frame(height: 56)

            HStack(spacing: 6) {
                ForEach(dayOptions, id: \.self) { days in
                    Button {
                        selectedDays = days
                        onDaysChange(days)
                    } label: {
                        Text(labelForDays(days))
                            .font(.system(size: 11, weight: .semibold, design: .monospaced))
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
        case 1: return "1D"
        case 7: return "1W"
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
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                CX2SectionLabel(text: "Position analysis")
                Text("Queue a fresh backend run for this held position.")
                    .font(.system(size: 13, weight: .regular))
                    .foregroundColor(.textSecondary)
            }

            Spacer()

            Button(action: onRefreshAnalysis) {
                Text(isRefreshing ? "Refreshing" : "Refresh")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.backgroundPrimary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.textPrimary)
                    .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
            }
            .buttonStyle(.plain)
            .disabled(isRefreshing)
        }
        .padding(14)
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
            .padding(.bottom, ClavisTheme.largeSpacing)
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
            CX2SectionLabel(text: "Fundamentals")

            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 0), count: 3), spacing: 0) {
                ForEach(metrics) { metric in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(metric.label)
                            .font(.system(size: 11, weight: .regular))
                            .foregroundColor(.textSecondary)
                        Text(metric.value)
                            .font(.system(size: 15, weight: .bold, design: .monospaced))
                            .foregroundColor(.textPrimary)
                            .monospacedDigit()
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                    .background(Color.surface)
                    .overlay(alignment: .trailing) {
                        Rectangle()
                            .fill(Color.border)
                            .frame(width: 1)
                            .opacity(metric.id == metrics.last?.id ? 0 : 1)
                    }
                }
            }
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Color.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
    }
}

private struct TickerRiskDimensionItem: Identifiable {
    let id = UUID()
    let title: String
    let value: Double?
    let accent: Color
}

private struct TickerRiskDimensionsCard: View {
    let dimensions: [TickerRiskDimensionItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            CX2SectionLabel(text: "Risk dimensions")

            VStack(spacing: 10) {
                ForEach(dimensions) { item in
                    TickerRiskDimensionRow(item: item)
                }
            }
        }
    }
}

private struct TickerRiskDimensionRow: View {
    let item: TickerRiskDimensionItem

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(item.title)
                    .font(.system(size: 13, weight: .regular))
                    .foregroundColor(.textPrimary)
                Spacer()
                Text(valueText)
                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                    .foregroundColor(.textPrimary)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 2, style: .continuous)
                        .fill(Color.border)
                        .frame(height: 4)
                    RoundedRectangle(cornerRadius: 2, style: .continuous)
                        .fill(Color.textPrimary.opacity(0.55))
                        .frame(width: geo.size.width * progress, height: 4)
                }
            }
            .frame(height: 4)
        }
    }

    private var progress: CGFloat {
        guard let value = item.value else { return 0.1 }
        return CGFloat(max(0, min(value, 100)) / 100)
    }

    private var valueText: String {
        guard let value = item.value else { return "--" }
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

private struct TickerAlertsListCard: View {
    let alerts: [Alert]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .lastTextBaseline) {
                CX2SectionLabel(text: "Recent alerts")
                Spacer()
                Text("All alerts")
                    .font(.system(size: 13, weight: .regular))
                    .foregroundColor(.informational)
            }

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
            let fetched = try await APIService.shared.searchTickers(query: trimmed, limit: 50)
            results = prioritizedResults(fetched, query: trimmed)
            errorMessage = nil
        } catch {
            results = []
            errorMessage = error.localizedDescription
        }
    }

    private func prioritizedResults(_ results: [TickerSearchResult], query: String) -> [TickerSearchResult] {
        let normalizedQuery = query.uppercased()

        return results.sorted { left, right in
            let leftRank = searchRank(for: left, query: normalizedQuery)
            let rightRank = searchRank(for: right, query: normalizedQuery)

            if leftRank != rightRank {
                return leftRank < rightRank
            }

            return left.ticker < right.ticker
        }
    }

    private func searchRank(for result: TickerSearchResult, query: String) -> Int {
        let ticker = result.ticker.uppercased()
        let company = result.companyName.uppercased()

        if ticker == query { return 0 }
        if ticker.hasPrefix(query) { return 1 }
        if company.hasPrefix(query) { return 2 }
        if ticker.contains(query) { return 3 }
        if company.contains(query) { return 4 }
        return 5
    }
}
