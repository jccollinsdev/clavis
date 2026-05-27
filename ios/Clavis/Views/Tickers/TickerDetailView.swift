import SwiftUI

struct TickerDetailView: View {
    let ticker: String
    let positionId: String?
    let debugFixture: TickerDetailDebugFixture?
    let debugScrollTarget: String?

    @Environment(\.dismiss) private var dismiss
    @State private var detail: TickerDetailResponse?
    @State private var methodology: MethodologyResponse?
    @State private var priceHistory: [PricePoint] = []
    @State private var scoreHistory: [ScoreHistoryPoint] = []
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var hasLoaded = false
    @State private var isRefreshingTicker = false
    @State private var isMutatingWatchlist = false
    @State private var selectedArticle: MethodologyArticle?
    @State private var showAddHoldingSheet = false
    @State private var showAllArticles = false
    @State private var scoreHistoryDimensions: Set<String> = []
    @State private var selectedHistoryPeriod: TickerHistoryPeriod = .oneMonth

    init(
        ticker: String,
        positionId: String? = nil,
        debugFixture: TickerDetailDebugFixture? = nil,
        debugScrollTarget: String? = nil
    ) {
        self.ticker = ticker
        self.positionId = positionId
        self.debugFixture = debugFixture
        self.debugScrollTarget = debugScrollTarget
    }

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if let errorMessage, detail == nil {
                        DashboardErrorCard(message: errorMessage)
                    } else if isLoading && detail == nil {
                        loadingState
                    } else if let detail {
                        content(detail)
                    } else {
                        DashboardErrorCard(message: "Ticker detail unavailable.")
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.sectionSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .safeAreaInset(edge: .top, spacing: 0) {
                topHeader
            }
            .toolbar(.hidden, for: .navigationBar)
            .task {
                guard !hasLoaded else { return }
                hasLoaded = true
                if let debugFixture {
                    apply(debugFixture)
                    if let debugScrollTarget {
                        try? await Task.sleep(nanoseconds: 250_000_000)
                        withAnimation(.none) {
                            proxy.scrollTo(debugScrollTarget, anchor: .top)
                        }
                    }
                } else {
                    await reloadAll()
                }
            }
            .refreshable {
                if let debugFixture {
                    apply(debugFixture)
                    if let debugScrollTarget {
                        withAnimation(.none) {
                            proxy.scrollTo(debugScrollTarget, anchor: .top)
                        }
                    }
                } else {
                    await reloadAll()
                }
            }
        }
        .navigationDestination(for: AuditDestination.self) { destination in
            auditDestinationView(for: destination)
        }
        .sheet(item: $selectedArticle) { article in
            ArticleDetailSheet(article: article, ticker: ticker)
        }
        .sheet(isPresented: $showAddHoldingSheet) {
            TickerAddHoldingSheet(
                ticker: ticker,
                companyName: detail?.profile.companyName,
                onComplete: {
                    showAddHoldingSheet = false
                    Task { await reloadAll() }
                }
            )
        }
    }

    private var topHeader: some View {
        HStack(spacing: 10) {
            Button(action: { dismiss() }) {
                Image(systemName: "chevron.left")
                    .foregroundColor(.clavixInk)
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: 2) {
                Text(detail?.profile.companyName ?? ticker)
                    .font(ClavisTypography.clavixSerif(17, weight: .medium))
                    .foregroundColor(.clavixInk)
                    .lineLimit(1)
                Text(ticker)
                    .font(ClavisTypography.clavixMono(11, weight: .bold))
                    .foregroundColor(.clavixAccent)
            }

            Spacer()

            Button(action: { Task { await toggleWatchlist() } }) {
                if isMutatingWatchlist {
                    ProgressView()
                        .tint(.clavixInk)
                } else {
                    Image(systemName: isInWatchlist ? "star.fill" : "star")
                        .foregroundColor(isInWatchlist ? .clavixAccent : .clavixInk)
                }
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, ClavixLayout.pad)
        .padding(.top, 8)
        .padding(.bottom, 8)
        .background(Color.clavixPage.ignoresSafeArea(edges: .top))
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Color.clavixRule)
                .frame(height: 1)
        }
    }

    @ViewBuilder
    private func content(_ detail: TickerDetailResponse) -> some View {
        if isOutsideUniverse(detail) {
            outsideUniverseBanner
        }
        heroSection(detail)
            .id("hero")
        priceSection(detail)
            .id("price")
        riskDimensionsSection(detail)
            .id("dimensions")
        driversSection(detail)
            .id("drivers")
        executiveSummarySection(detail)
            .id("executive-summary")
        recentNewsSection(detail)
            .id("recent-news")
        scoreHistorySection
            .id("score-history")
        bottomCtas(detail)
            .id("cta")
    }

    private func isOutsideUniverse(_ detail: TickerDetailResponse) -> Bool {
        if detail.sharedAnalysis?.summary.outsideUniverse == true { return true }
        if detail.sharedAnalysis?.summary.isSupported == false { return true }
        return false
    }

    private var outsideUniverseBanner: some View {
        ClavixCard(fill: .clavixWarnSoft) {
            VStack(alignment: .leading, spacing: 6) {
                Text("OUTSIDE TRACKED UNIVERSE")
                    .font(ClavisTypography.clavixMono(10, weight: .bold))
                    .tracking(0.7)
                    .foregroundColor(.clavixWarnInk)
                Text("This ticker isn't in the Clavix tracked universe. Risk data may be limited until coverage is added.")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixWarnInk)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var scoreHistorySection: some View {
        VStack(alignment: .leading, spacing: 10) {
            hifiSectionHeader(eyebrow: "Composite · \(selectedHistoryPeriod.label)", title: "Score history")
            ClavixCard(fill: .clavixPaper) {
                let snapshots = filteredScoreSnapshots
                if snapshots.count >= 2 {
                    VStack(alignment: .leading, spacing: 10) {
                        HistoryPeriodChips(selected: $selectedHistoryPeriod)
                        HStack(spacing: 6) {
                            ForEach(scoreHistoryToggles, id: \.key) { toggle in
                                Button(action: { toggleScoreDimension(toggle.key) }) {
                                    ClavixPill(label: toggle.label, active: scoreHistoryDimensions.contains(toggle.key) || (toggle.key == "composite" && scoreHistoryDimensions.isEmpty))
                                }
                                .buttonStyle(.plain)
                            }
                            Spacer()
                        }
                        ScoreHistoryChart(
                            snapshots: snapshots,
                            showAllDimensions: !scoreHistoryDimensions.isEmpty,
                            toggledDimensions: $scoreHistoryDimensions
                        )
                    }
                } else {
                    Text("New — score history requires at least 2 days of data.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            }
        }
    }

    private var scoreHistoryToggles: [(key: String, label: String)] {
        [
            ("composite", "Composite"),
            ("news_sentiment", "News"),
            ("macro_exposure", "Macro"),
            ("volatility", "Vol")
        ]
    }

    private func toggleScoreDimension(_ key: String) {
        if key == "composite" {
            scoreHistoryDimensions = []
            return
        }
        if scoreHistoryDimensions.contains(key) {
            scoreHistoryDimensions.remove(key)
        } else {
            scoreHistoryDimensions.insert(key)
        }
    }

    private var loadingState: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
            ClavisLoadingCard(title: "Loading \(ticker)", subtitle: "Pulling the latest rating, dimensions, and news.")
            ClavisLoadingCard(title: "Loading dimensions", subtitle: "Fetching methodology inputs and score components.")
            ClavisLoadingCard(title: "Loading recent news", subtitle: "Scoring the latest article set for this ticker.")

        }
    }

    private func heroSection(_ detail: TickerDetailResponse) -> some View {
        ClavixCard(padding: 0) {
            VStack(alignment: .leading, spacing: 0) {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            ClavixEyebrow("Composite")
                            HStack(alignment: .lastTextBaseline, spacing: 10) {
                                ClavixGradeBadge(displayGrade, size: 40)
                                Text(displayScoreText)
                                    .font(ClavisTypography.clavixMono(30, weight: .semibold))
                                    .tracking(-0.6)
                                    .foregroundColor(.clavixInk)
                            }
                            scoreDeltaLine(detail)
                        }
                        Spacer(minLength: 8)
                        TickerRadarChart(dimensions: radarDimensions, size: 168)
                    }
                    if displayScoreValue == nil && filteredPriceHistory.count < 2 {
                        ratingPendingCard
                    }
                }
                .padding(14)

                if isHeld {
                    Rectangle().fill(Color.clavixRule2).frame(height: 1)
                    heroHoldRow(detail)
                }
            }
        }
    }

    private func priceSection(_ detail: TickerDetailResponse) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            ClavixCard(padding: 0) {
                VStack(alignment: .leading, spacing: 0) {
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            ClavixEyebrow("Price · \(selectedHistoryPeriod.label)")
                            Text(priceLineText(detail))
                                .font(ClavisTypography.clavixMono(14, weight: .semibold))
                                .foregroundColor(priceLineColor(detail))
                        }
                        Spacer(minLength: 8)
                        HistoryPeriodChips(selected: $selectedHistoryPeriod, compact: true)
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 12)

                    TickerPriceChart(
                        prices: filteredPriceHistory,
                        tone: priceLineColor(detail)
                    )
                    .padding(.horizontal, 16)
                    .padding(.vertical, 14)
                }
            }
        }
    }

    private func scoreDeltaLine(_ detail: TickerDetailResponse) -> some View {
        let delta = honestScoreDelta(detail)
        return Group {
            if let delta {
                HStack(spacing: 6) {
                    Text(delta > 0 ? "▲ \(delta)" : delta < 0 ? "▼ \(abs(delta))" : "—")
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(delta > 0 ? .clavixGood : delta < 0 ? .clavixBad : .clavixInk3)
                    Text("vs prior session")
                        .font(ClavisTypography.clavixMono(11, weight: .regular))
                        .foregroundColor(.clavixInk3)
                }
            } else {
                Text("— · no prior session score")
                    .font(ClavisTypography.clavixMono(11, weight: .regular))
                    .foregroundColor(.clavixInk3)
            }
        }
    }

    private func honestScoreDelta(_ detail: TickerDetailResponse) -> Int? {
        detail.sharedAnalysis?.summary.scoreDelta
    }

    private func heroHoldRow(_ detail: TickerDetailResponse) -> some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(alignment: .leading, spacing: 2) {
                ClavixEyebrow("You hold")
                Text(holdSummaryLine(detail))
                    .font(ClavisTypography.clavixMono(13, weight: .semibold))
                    .foregroundColor(.clavixInk)
                if let costLine = costSummaryLine(detail) {
                    Text(costLine)
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(costSummaryColor(detail))
                }
            }
            Spacer(minLength: 8)
            VStack(alignment: .trailing, spacing: 2) {
                ClavixEyebrow("Last")
                Text(currency(latestPrice))
                    .font(ClavisTypography.clavixMono(20, weight: .semibold))
                    .foregroundColor(.clavixInk)
                Text(dayChangeText(detail))
                    .font(ClavisTypography.clavixMono(11, weight: .semibold))
                    .foregroundColor(dayChangeColor(detail))
            }
        }
        .padding(14)
    }

    private func holdSummaryLine(_ detail: TickerDetailResponse) -> String {
        let shares = detail.portfolioOverlay?.shares ?? detail.position.shares
        let parts: [String] = [
            shares > 0 ? "\(shares.formatted()) sh" : nil,
            holdWeightText(detail)
        ].compactMap { $0 }
        return parts.isEmpty ? "Holding" : parts.joined(separator: " · ")
    }

    private func holdWeightText(_ detail: TickerDetailResponse) -> String? {
        guard let weight = detail.portfolioOverlay?.portfolioWeight else { return nil }
        // portfolioWeight is a fraction 0..1
        return String(format: "%.1f%% of book", weight * 100)
    }

    private func costSummaryLine(_ detail: TickerDetailResponse) -> String? {
        guard let pnl = detail.position.unrealizedPL else { return nil }
        let sign = pnl >= 0 ? "+" : "−"
        let amountText = currency(abs(pnl))
        if let pct = detail.position.unrealizedPLPercent {
            return "\(sign)\(amountText) · \(pct >= 0 ? "+" : "−")\(String(format: "%.1f", abs(pct)))% from cost"
        }
        return "\(sign)\(amountText) from cost"
    }

    private func costSummaryColor(_ detail: TickerDetailResponse) -> Color {
        guard let pnl = detail.position.unrealizedPL else { return .clavixInk3 }
        if pnl > 0 { return .clavixGood }
        if pnl < 0 { return .clavixBad }
        return .clavixInk3
    }

    private var ratingPendingCard: some View {
        HStack(spacing: ClavisTheme.smallSpacing) {
            Text("Rating pending — check back after market open")
                .font(ClavisTypography.footnote)
                .foregroundColor(.clavixInk3)
            Spacer()
        }
        .padding(ClavisTheme.cardPadding)
        .background(Color.clavixPaper2)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }

    private func riskDimensionsSection(_ detail: TickerDetailResponse) -> some View {
        let dimensions = dimensionItems(detail)

        return VStack(alignment: .leading, spacing: 8) {
            VStack(alignment: .leading, spacing: 4) {
                ClavixEyebrow("Tap any row for the full audit")
                Text("Five dimensions")
                    .font(ClavisTypography.clavixSerif(18, weight: .medium))
                    .foregroundColor(.clavixInk)
            }

            ClavixCard(padding: 0, fill: .clavixPaper) {
                VStack(spacing: 0) {
                    ForEach(Array(dimensions.enumerated()), id: \.element.key) { index, dimension in
                        if let destination = auditDestination(for: dimension.key) {
                            NavigationLink(value: destination) {
                                dimensionRow(dimension)
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 12)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier("dimension-row-\(dimension.key)")
                        } else {
                            dimensionRow(dimension)
                                .padding(.horizontal, 14)
                                .padding(.vertical, 12)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }

                        if index < dimensions.count - 1 {
                            Rectangle()
                                .fill(Color.clavixRule2)
                                .frame(height: 1)
                        }
                    }
                }
            }
        }
    }

    private func dimensionRow(_ dimension: TickerDimensionItem) -> some View {
        HStack(alignment: .center, spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(dimension.abbrev)
                    .font(ClavisTypography.clavixMono(9, weight: .bold))
                    .tracking(0.6)
                    .foregroundColor(.clavixInk3)
                Text(dimension.title)
                    .font(ClavisTypography.inter(12))
                    .foregroundColor(.clavixInk)
                    .lineLimit(1)
            }
            .frame(width: 92, alignment: .leading)

            ClavixScoreBar(score: dimension.score.map { Int($0.rounded()) } ?? 0)
                .frame(height: 5)
                .opacity(dimension.score == nil ? 0.25 : 1.0)

            Text(dimension.scoreText)
                .font(ClavisTypography.clavixMono(16, weight: .semibold))
                .foregroundColor(scoreToneColor(dimension.score))
                .frame(width: 38, alignment: .trailing)

            Image(systemName: "chevron.right")
                .font(.system(size: 11, weight: .semibold))
                .foregroundColor(.clavixInk4)
        }
        .contentShape(Rectangle())
    }

    private func scoreToneColor(_ score: Double?) -> Color {
        guard let score else { return .clavixInk3 }
        if score >= 70 { return .clavixGood }
        if score >= 50 { return .clavixInk }
        if score >= 30 { return .clavixWarn }
        return .clavixBad
    }

    private func driversSection(_ detail: TickerDetailResponse) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            hifiSectionHeader(eyebrow: "Why this rating", title: "Key drivers")

            let summary = driverSummary(detail)
            if !summary.isEmpty {
                Text(summary)
                    .font(ClavisTypography.inter(13))
                    .foregroundColor(.clavixInk2)
                    .lineSpacing(2)
                    .fixedSize(horizontal: false, vertical: true)
            }

            TickerDriverCardsSection(analysis: detail.currentAnalysis)
        }
    }

    @ViewBuilder
    private func executiveSummarySection(_ detail: TickerDetailResponse) -> some View {
        if let summary = detail.sharedAnalysis?.executiveSummaryBreakdown,
           summary.hasAnyContent {
            VStack(alignment: .leading, spacing: 10) {
                hifiSectionHeader(eyebrow: "Summary", title: "Executive summary")
                VStack(alignment: .leading, spacing: 8) {
                    if let bullCase = summary.bullCase?.sanitizedDisplayText, !bullCase.isEmpty {
                        executiveSummaryCard(
                            title: "Bull case",
                            body: bullCase,
                            fill: .clavixGoodSoft,
                            ink: .clavixGoodInk
                        )
                    }
                    if let riskCase = summary.riskCase?.sanitizedDisplayText, !riskCase.isEmpty {
                        executiveSummaryCard(
                            title: "Risk case",
                            body: riskCase,
                            fill: .clavixBadSoft,
                            ink: .clavixBadInk
                        )
                    }
                    if let watch = summary.whatToWatch?.sanitizedDisplayText, !watch.isEmpty {
                        executiveSummaryCard(
                            title: "What to watch",
                            body: watch,
                            fill: .clavixWarnSoft,
                            ink: .clavixWarnInk
                        )
                    }
                }
            }
        }
    }

    private func executiveSummaryCard(title: String, body: String, fill: Color, ink: Color) -> some View {
        ClavixCard(fill: fill) {
            VStack(alignment: .leading, spacing: 6) {
                Text(title)
                    .font(ClavisTypography.clavixSerif(16, weight: .medium))
                    .foregroundColor(ink)
                Text(body)
                    .font(ClavisTypography.body)
                    .foregroundColor(ink)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func hifiSectionHeader(eyebrow: String, title: String, action: String? = nil, onAction: (() -> Void)? = nil) -> some View {
        HStack(alignment: .lastTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                ClavixEyebrow(eyebrow)
                Text(title)
                    .font(ClavisTypography.clavixSerif(18, weight: .medium))
                    .foregroundColor(.clavixInk)
            }
            Spacer()
            if let action {
                Button(action: { onAction?() }) {
                    Text(action)
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(.clavixAccent)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func recentNewsSection(_ detail: TickerDetailResponse) -> some View {
        let articles = displayArticles(detail)
        let visibleArticles = showAllArticles ? articles : Array(articles.prefix(10))

        let articleCountText = articles.isEmpty ? "No articles in window" : "\(articles.count) article\(articles.count == 1 ? "" : "s") · 7d"

        return VStack(alignment: .leading, spacing: 10) {
            hifiSectionHeader(
                eyebrow: articleCountText,
                title: "Recent news",
                action: articles.count > 10 ? (showAllArticles ? "Show less" : "See all →") : nil,
                onAction: { showAllArticles.toggle() }
            )

            if visibleArticles.isEmpty {
                ClavixCard(fill: .clavixPaper) {
                    Text("No recent news for this ticker")
                        .font(ClavisTypography.body)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard(fill: .clavixPaper) {
                    VStack(spacing: 0) {
                        ForEach(Array(visibleArticles.enumerated()), id: \.element.id) { index, article in
                            Button(action: { selectedArticle = article }) {
                                newsCard(article)
                            }
                            .buttonStyle(.plain)

                            if index < visibleArticles.count - 1 {
                                Rectangle()
                                    .fill(Color.clavixRule2)
                                    .frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    private func newsCard(_ article: MethodologyArticle) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                if let tier = article.sourceTier {
                    Text("T\(tier)")
                        .font(ClavisTypography.clavixMono(9, weight: .bold))
                        .tracking(0.4)
                        .foregroundColor(.clavixInk2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .overlay(
                            RoundedRectangle(cornerRadius: 3, style: .continuous)
                                .stroke(Color.clavixRule, lineWidth: 1)
                        )
                        .fixedSize()
                }
                Text(article.source ?? "Unknown source")
                    .font(ClavisTypography.clavixMono(11, weight: .semibold))
                    .foregroundColor(.clavixInk2)
                    .lineLimit(1)
                Text("·")
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk4)
                Text(formatArticleTimestamp(article.publishedAt))
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk3)
                    .lineLimit(1)
                Spacer(minLength: 4)
                sentimentDot(article.sentimentScore)
            }

            Text(article.title ?? "Untitled article")
                .font(ClavisTypography.clavixSerif(16, weight: .medium))
                .foregroundColor(.clavixInk)
                .multilineTextAlignment(.leading)
                .lineLimit(3)
                .fixedSize(horizontal: false, vertical: true)

            if let tldr = article.tldr, !tldr.isEmpty {
                Text(tldr)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 12)
        .padding(.horizontal, 2)
    }

    private func sentimentDot(_ score: Double?) -> some View {
        HStack(spacing: 4) {
            Circle()
                .fill(sentimentColor(score))
                .frame(width: 7, height: 7)
            Text(score.map { "\(Int($0.rounded()))" } ?? "—")
                .font(ClavisTypography.clavixMono(10, weight: .bold))
                .foregroundColor(sentimentColor(score))
        }
        .fixedSize()
    }

    private static let isoDateParser: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let isoDateParserNoFraction: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private static let articleRelativeFormatter: RelativeDateTimeFormatter = {
        let f = RelativeDateTimeFormatter()
        f.unitsStyle = .abbreviated
        return f
    }()

    private static let articleShortDateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "MMM d"
        return f
    }()

    private func formatArticleTimestamp(_ raw: String?) -> String {
        guard let raw, !raw.isEmpty else { return "—" }
        let date = TickerDetailView.isoDateParser.date(from: raw)
            ?? TickerDetailView.isoDateParserNoFraction.date(from: raw)
        guard let date else { return raw.prefix(10).description }
        let interval = Date().timeIntervalSince(date)
        if interval < 60 * 60 * 24 * 3 {
            return TickerDetailView.articleRelativeFormatter.localizedString(for: date, relativeTo: Date())
        }
        return TickerDetailView.articleShortDateFormatter.string(from: date)
    }

    private func bottomCtas(_ detail: TickerDetailResponse) -> some View {
        ClavixCard(fill: .clavixPaper) {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                if isHeld {
                    VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                        Text("In your holdings")
                            .font(ClavisTypography.cardTitle)
                            .foregroundColor(.clavixInk)
                        Text(holdingSummary(detail))
                            .font(ClavisTypography.body)
                            .foregroundColor(.clavixInk3)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                } else {
                    HStack(spacing: ClavisTheme.smallSpacing) {
                        ClavisPrimaryButton(title: "Add to Holdings", action: { showAddHoldingSheet = true })
                        ClavisSecondaryButton(title: isInWatchlist ? "On Watchlist" : "Add to Watchlist") {
                            Task { await toggleWatchlist() }
                        }
                    }
                }

                if isInWatchlist {
                    Text("Watching")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.clavixAccent)
                }
            }
        }
    }

    private func auditDestination(for key: String) -> AuditDestination? {
        switch key {
        case "financial_health": return .financialHealth
        case "news_sentiment": return .newsSentiment
        case "macro_exposure": return .macroExposure
        case "sector_exposure": return .sectorExposure
        case "volatility": return .volatility
        default: return nil
        }
    }

    @ViewBuilder
    private func auditDestinationView(for destination: AuditDestination) -> some View {
        switch destination {
        case .financialHealth:
            FinancialHealthAuditView(ticker: ticker, methodology: methodology)
        case .newsSentiment:
            NewsSentimentAuditView(ticker: ticker, methodology: methodology)
        case .macroExposure:
            MacroExposureAuditView(ticker: ticker, methodology: methodology)
        case .sectorExposure:
            SectorExposureAuditView(ticker: ticker, methodology: methodology)
        case .volatility:
            VolatilityAuditView(
                ticker: ticker,
                methodology: methodology,
                scoreHistory: ScoreHistoryConversion.snapshots(from: scoreHistory)
            )
        }
    }

    private func reloadAll() async {
        isLoading = true
        defer { isLoading = false }

        do {
            let loadedDetail = try await APIService.shared.fetchTickerDetail(
                ticker: ticker,
                positionId: positionId,
                timeoutInterval: 15
            )

            await MainActor.run {
                detail = loadedDetail
                priceHistory = []
                scoreHistory = []
                errorMessage = nil
            }

            Task {
                let loadedPrice = try? await APIService.shared.fetchPriceHistory(ticker: ticker, days: 365)
                await MainActor.run {
                    priceHistory = loadedPrice?.prices ?? []
                }
            }

            Task {
                let loadedScore = try? await APIService.shared.fetchScoreHistory(ticker: ticker, days: 365)
                await MainActor.run {
                    scoreHistory = loadedScore?.points ?? []
                }
            }

            Task {
                do {
                    let loadedMethodology = try await APIService.shared.fetchTickerMethodology(ticker: ticker, timeoutInterval: 15)
                    await MainActor.run {
                        methodology = loadedMethodology
                    }
                } catch {
                    // Methodology payload is optional on Ticker Detail; the dimension
                    // rows fall back to honest "Limited Data" labels when absent.
                    await MainActor.run {
                        methodology = nil
                    }
                }
            }
        } catch {
            await MainActor.run {
                errorMessage = ClavisCopy.Errors.tickerLoad(ticker: ticker, error: error)
            }
        }
    }

    private func apply(_ fixture: TickerDetailDebugFixture) {
        detail = fixture.detail
        methodology = fixture.methodology
        priceHistory = fixture.priceHistory
        scoreHistory = fixture.scoreHistory
        errorMessage = nil
        isLoading = false
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
            await reloadAll()
        } catch {
            errorMessage = ClavisCopy.Errors.watchlistUpdate(error)
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
            errorMessage = ClavisCopy.Errors.tickerRefresh(error)
        }
    }

    private func sectionHeader(title: String) -> some View {
        Text(title)
            .font(ClavisTypography.label)
            .foregroundColor(.clavixInk3)
    }

    private func dimensionItems(_ detail: TickerDetailResponse) -> [TickerDimensionItem] {
        let shared = detail.sharedAnalysis?.riskDimensions
        let ai = detail.currentScore?.factorBreakdown?.aiDimensions
        let current = detail.currentScore

        return [
            TickerDimensionItem(
                key: "financial_health",
                title: "Financial Health",
                abbrev: "FIN",
                score: shared?.financialHealth ?? ai?.financialHealth ?? current?.financialHealth,
                subtitle: methodology?.dimensions.financialHealth.dataSource ?? "Quarterly fundamentals",
                isLimited: (shared?.financialHealth ?? ai?.financialHealth ?? current?.financialHealth) == nil
            ),
            TickerDimensionItem(
                key: "news_sentiment",
                title: "News Sentiment",
                abbrev: "NEWS",
                score: shared?.newsSentiment ?? ai?.newsSentiment ?? current?.newsSentiment,
                subtitle: newsSubtitle,
                isLimited: (methodology?.dimensions.newsSentiment.articleCount7d ?? 0) < 3
            ),
            TickerDimensionItem(
                key: "macro_exposure",
                title: "Macro Exposure",
                abbrev: "MAC",
                score: shared?.macroExposure ?? ai?.macroExposure ?? current?.macroExposure,
                subtitle: methodology?.dimensions.macroExposure.asOfDate ?? "Macro regression",
                isLimited: methodology?.dimensions.macroExposure.limitedData ?? false
            ),
            TickerDimensionItem(
                key: "sector_exposure",
                title: "Sector Exposure",
                abbrev: "SEC",
                score: shared?.sectorExposure ?? ai?.sectorExposure ?? current?.sectorExposure,
                subtitle: methodology?.dimensions.sectorExposure.sector ?? detail.profile.sector ?? "Sector state",
                isLimited: (shared?.sectorExposure ?? ai?.sectorExposure ?? current?.sectorExposure) == nil
            ),
            TickerDimensionItem(
                key: "volatility",
                title: "Volatility",
                abbrev: "VOL",
                score: shared?.volatility ?? ai?.volatility ?? current?.volatility,
                subtitle: methodology?.dimensions.volatility.asOfDate ?? "Daily price action",
                isLimited: (shared?.volatility ?? ai?.volatility ?? current?.volatility) == nil
            )
        ]
    }

    private var newsSubtitle: String {
        if let methodology {
            return "\(methodology.dimensions.newsSentiment.articleCount7d ?? 0) articles · 7d"
        }
        return "Recent article set"
    }

    private func displayArticles(_ detail: TickerDetailResponse) -> [MethodologyArticle] {
        if let methodologyArticles = methodology?.dimensions.newsSentiment.articles, !methodologyArticles.isEmpty {
            return methodologyArticles
        }
        return detail.recentNews
    }

    private func driverSummary(_ detail: TickerDetailResponse) -> String {
        let summary = detail.sharedAnalysis?.executiveSummary
            ?? detail.currentAnalysis?.summary
            ?? detail.currentScore?.reasoning
            ?? detail.sharedAnalysis?.detailedReport
            ?? "This rating is waiting on a fuller driver summary from the backend."

        return summary.sanitizedDisplayText
    }

    private func priceLineText(_ detail: TickerDetailResponse) -> String {
        guard let lastPrice = filteredPriceHistory.last?.price ?? latestPrice else {
            return "—"
        }
        let basePrice = filteredPriceHistory.first?.price
            ?? detail.latestPrice.previousClose
            ?? detail.sharedAnalysis?.previousClose
        guard let basePrice, basePrice != 0 else {
            return currency(lastPrice)
        }
        let changePct = ((lastPrice - basePrice) / basePrice) * 100
        return "\(currency(lastPrice)) · \(changePct >= 0 ? "+" : "−")\(String(format: "%.2f", abs(changePct)))%"
    }

    private func priceLineColor(_ detail: TickerDetailResponse) -> Color {
        let lastPrice = filteredPriceHistory.last?.price ?? latestPrice
        let basePrice = filteredPriceHistory.first?.price
            ?? detail.latestPrice.previousClose
            ?? detail.sharedAnalysis?.previousClose
        guard let lastPrice, let basePrice else { return .clavixInk3 }
        if lastPrice > basePrice { return .clavixGood }
        if lastPrice < basePrice { return .clavixBad }
        return .clavixInk3
    }

    private func dayChangeText(_ detail: TickerDetailResponse) -> String {
        guard let price = latestPrice, let previousClose = detail.latestPrice.previousClose, previousClose != 0 else {
            return "Day change unavailable"
        }

        let delta = price - previousClose
        let pct = (delta / previousClose) * 100
        return String(format: "%@%@ (%.2f%%)", delta >= 0 ? "+" : "", currency(delta), pct)
    }

    private func dayChangeColor(_ detail: TickerDetailResponse) -> Color {
        guard let price = latestPrice, let previousClose = detail.latestPrice.previousClose else {
            return .clavixInk3
        }
        if price > previousClose { return .clavixGood }
        if price < previousClose { return .clavixBad }
        return .clavixInk3
    }

    private func sentimentPill(score: Double?) -> some View {
        dimensionBadge(
            text: score.map { "\(Int($0.rounded()))" } ?? "—",
            foreground: sentimentColor(score),
            background: sentimentBackground(score)
        )
    }

    private func impactPill(text: String) -> some View {
        dimensionBadge(text: text, foreground: .clavixAccentInk, background: .clavixAccentSoft)
    }

    private func dimensionBadge(text: String, foreground: Color, background: Color) -> some View {
        Text(text)
            .font(ClavisTypography.label)
            .foregroundColor(foreground)
            .padding(.horizontal, 6)
            .padding(.vertical, 4)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }

    private func sentimentColor(_ score: Double?) -> Color {
        guard let score else { return .clavixInk3 }
        if score >= 70 { return .clavixGood }
        if score >= 50 { return .clavixWarn }
        return .clavixBad
    }

    private func sentimentBackground(_ score: Double?) -> Color {
        guard let score else { return .clavixPaper2 }
        if score >= 70 { return .clavixGoodSoft }
        if score >= 50 { return .clavixWarnSoft }
        return .clavixBadSoft
    }

    private func holdingSummary(_ detail: TickerDetailResponse) -> String {
        let sharesText = detail.portfolioOverlay?.shares ?? detail.position.shares
        let valueText = detail.portfolioOverlay?.marketValue ?? detail.position.currentValue
        let parts = [
            sharesText > 0 ? "\(sharesText.formatted()) shares" : nil,
            valueText.map { currency($0) }
        ].compactMap { $0 }

        if parts.isEmpty {
            return "Holding data is available in your portfolio."
        }
        return parts.joined(separator: " · ")
    }

    private func currency(_ value: Double?) -> String {
        guard let value else { return "—" }
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "—"
    }

    private var latestPrice: Double? {
        detail?.latestPrice.price ?? detail?.portfolioOverlay?.currentPrice
    }

    private var filteredPriceHistory: [PricePoint] {
        guard !priceHistory.isEmpty else { return [] }
        let sorted = priceHistory.sorted { $0.recordedAt < $1.recordedAt }
        if selectedHistoryPeriod == .oneDay {
            return Array(sorted.suffix(min(sorted.count, 2)))
        }
        guard let cutoff = Calendar.current.date(byAdding: .day, value: -selectedHistoryPeriod.dayWindow, to: Date()) else {
            return sorted
        }
        let filtered = sorted.filter { $0.recordedAt >= cutoff }
        return filtered.isEmpty ? sorted : filtered
    }

    private var filteredScoreSnapshots: [ScoreSnapshot] {
        let snapshots = ScoreHistoryConversion.snapshots(from: scoreHistory)
        if selectedHistoryPeriod == .oneDay {
            return Array(snapshots.suffix(min(snapshots.count, 2)))
        }
        guard let cutoff = Calendar.current.date(byAdding: .day, value: -selectedHistoryPeriod.dayWindow, to: Date()) else {
            return snapshots
        }
        let filtered = snapshots.filter { $0.date >= cutoff }
        return filtered.isEmpty ? snapshots : filtered
    }

    private var radarDimensions: [TickerRadarDimension] {
        guard let detail else {
            return [
                TickerRadarDimension(key: "financial_health", label: "FIN", score: nil),
                TickerRadarDimension(key: "news_sentiment", label: "NEWS", score: nil),
                TickerRadarDimension(key: "macro_exposure", label: "MAC", score: nil),
                TickerRadarDimension(key: "sector_exposure", label: "SEC", score: nil),
                TickerRadarDimension(key: "volatility", label: "VOL", score: nil),
            ]
        }
        let dimensions = dimensionItems(detail)
        return dimensions.map { item in
            TickerRadarDimension(key: item.key, label: item.abbrev, score: item.score)
        }
    }

    private var displayScoreValue: Double? {
        detail?.sharedAnalysis?.summary.currentScore
            ?? detail?.currentScore?.totalScore
            ?? detail?.currentScore?.safetyScore
            ?? detail?.position.totalScore
    }

    private var displayScoreText: String {
        displayScoreValue.map { "\(Int($0.rounded()))" } ?? "—"
    }

    private var displayGrade: String {
        detail?.sharedAnalysis?.summary.currentGrade
            ?? detail?.currentScore?.grade
            ?? detail?.position.riskGrade
            ?? "—"
    }

    private var isHeld: Bool {
        detail?.portfolioOverlay?.isHeld ?? detail?.userContext.isHeld ?? false
    }

    private var isInWatchlist: Bool {
        detail?.portfolioOverlay?.isInWatchlist ?? detail?.userContext.isInWatchlist ?? false
    }

}

private struct TickerDimensionItem {
    let key: String
    let title: String
    let abbrev: String
    let score: Double?
    let subtitle: String
    let isLimited: Bool

    var scoreText: String {
        score.map { "\(Int($0.rounded()))" } ?? "—"
    }

    var grade: String {
        guard let score else { return "F" }
        switch score {
        case 90...100: return "AAA"
        case 80..<90: return "AA"
        case 70..<80: return "A"
        case 60..<70: return "BBB"
        case 50..<60: return "BB"
        case 40..<50: return "B"
        case 30..<40: return "CCC"
        case 20..<30: return "CC"
        case 10..<20: return "C"
        default: return "F"
        }
    }
}

private enum TickerHistoryPeriod: String, CaseIterable {
    case oneDay = "1D"
    case oneWeek = "1W"
    case oneMonth = "1M"
    case threeMonths = "3M"
    case oneYear = "1Y"

    var label: String { rawValue }

    var dayWindow: Int {
        switch self {
        case .oneDay: return 1
        case .oneWeek: return 7
        case .oneMonth: return 30
        case .threeMonths: return 90
        case .oneYear: return 365
        }
    }
}

private struct HistoryPeriodChips: View {
    @Binding var selected: TickerHistoryPeriod
    var compact: Bool = false

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 4) {
                ForEach(TickerHistoryPeriod.allCases, id: \.self) { period in
                    Button(action: { selected = period }) {
                        Text(period.label)
                            .font(ClavisTypography.clavixMono(11, weight: .semibold))
                            .foregroundColor(selected == period ? .white : .clavixInk3)
                            .lineLimit(1)
                            .fixedSize(horizontal: true, vertical: false)
                            .padding(.horizontal, compact ? 8 : 10)
                            .padding(.vertical, 6)
                            .frame(minWidth: compact ? 30 : 38)
                            .background(selected == period ? Color.clavixAccent : Color.clavixPaper2)
                            .overlay(
                                RoundedRectangle(cornerRadius: 4, style: .continuous)
                                    .stroke(selected == period ? Color.clavixAccent : Color.clavixRule2, lineWidth: 1)
                            )
                            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .scrollBounceBehavior(.basedOnSize)
        .defaultScrollAnchor(.trailing)
    }
}

private struct TickerAddHoldingSheet: View {
    let ticker: String
    let companyName: String?
    let onComplete: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var shares = ""
    @State private var costBasis = ""
    @State private var purchaseDate = Date()
    @State private var isSubmitting = false
    @State private var errorMessage: String?

    private var isValid: Bool {
        (Double(shares) ?? 0) > 0 && (Double(costBasis) ?? 0) >= 0
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    ClavixCard(fill: .clavixPaper) {
                        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                            Text(companyName ?? ticker)
                                .font(ClavisTypography.cardTitle)
                                .foregroundColor(.clavixInk)
                            Text(ticker)
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.clavixAccent)
                        }
                    }

                    field(title: "Shares", text: $shares)
                    field(title: "Cost basis per share", text: $costBasis)

                    ClavixCard(fill: .clavixPaper) {
                        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                            Text("Purchase date")
                                .font(ClavisTypography.label)
                                .foregroundColor(.clavixInk3)
                            DatePicker("Purchase date", selection: $purchaseDate, displayedComponents: .date)
                                .datePickerStyle(.compact)
                                .labelsHidden()
                        }
                    }

                    if let errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Add to Holdings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .foregroundColor(.clavixInk3)
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button(isSubmitting ? "Adding..." : "Add") {
                        Task { await submit() }
                    }
                    .foregroundColor(isValid ? .clavixAccent : .clavixInk4)
                    .disabled(!isValid || isSubmitting)
                }
            }
        }
    }

    private func field(title: String, text: Binding<String>) -> some View {
        ClavixCard(fill: .clavixPaper) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(title)
                    .font(ClavisTypography.label)
                    .foregroundColor(.clavixInk3)
                TextField(title, text: text)
                    .keyboardType(.decimalPad)
                    .font(ClavisTypography.body)
                    .foregroundColor(.clavixInk)
            }
        }
    }

    private func submit() async {
        guard let sharesValue = Double(shares), let costBasisValue = Double(costBasis) else { return }
        isSubmitting = true
        defer { isSubmitting = false }

        do {
            _ = try await APIService.shared.createHolding(
                ticker: ticker,
                shares: sharesValue,
                purchasePrice: costBasisValue
            )
            onComplete()
        } catch {
            errorMessage = ClavisCopy.Errors.holdingAdd(error)
        }
    }
}
