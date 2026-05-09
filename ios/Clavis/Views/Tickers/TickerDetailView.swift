import SwiftUI

struct TickerDetailView: View {
    let ticker: String
    let positionId: String?

    @Environment(\.dismiss) private var dismiss
    @State private var detail: TickerDetailResponse?
    @State private var methodology: MethodologyResponse?
    @State private var priceHistory: [PricePoint] = []
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var hasLoaded = false
    @State private var isRefreshingTicker = false
    @State private var isMutatingWatchlist = false
    @State private var showMethodologyDrawer = false
    @State private var selectedDimensionKey = "financial_health"
    @State private var selectedArticle: MethodologyArticle?
    @State private var showAddHoldingSheet = false
    @State private var showAllArticles = false

    init(ticker: String, positionId: String? = nil) {
        self.ticker = ticker
        self.positionId = positionId
    }

    var body: some View {
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
        .background(ClavisAtmosphereBackground())
        .safeAreaInset(edge: .top, spacing: 0) {
            topHeader
        }
        .toolbar(.hidden, for: .navigationBar)
        .task {
            guard !hasLoaded else { return }
            hasLoaded = true
            await reloadAll()
        }
        .refreshable {
            await reloadAll()
        }
        .sheet(isPresented: $showMethodologyDrawer) {
            if let methodology {
                MethodologyDrawerSheet(
                    ticker: ticker,
                    methodology: methodology,
                    tappedDimension: selectedDimensionKey
                )
            }
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
        HStack(spacing: ClavisTheme.smallSpacing) {
            Button(action: { dismiss() }) {
                Image(systemName: "chevron.left")
                    .foregroundColor(.textPrimary)
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: 2) {
                Text(detail?.profile.companyName ?? ticker)
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                    .lineLimit(1)
                Text(ticker)
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.accentBurnt)
            }

            Spacer()

            Button(action: { Task { await toggleWatchlist() } }) {
                if isMutatingWatchlist {
                    ProgressView()
                        .tint(.textPrimary)
                } else {
                    Image(systemName: isInWatchlist ? "star.fill" : "star")
                        .foregroundColor(isInWatchlist ? .accentBurnt : .textPrimary)
                }
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.top, ClavisTheme.smallSpacing)
        .padding(.bottom, ClavisTheme.smallSpacing)
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

    @ViewBuilder
    private func content(_ detail: TickerDetailResponse) -> some View {
        heroSection(detail)
        riskDimensionsSection(detail)
        driversSection(detail)
        recentNewsSection(detail)
        bottomCtas(detail)
    }

    private var loadingState: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
            ClavisLoadingCard(title: "Loading \(ticker)", subtitle: "Pulling the latest rating, dimensions, and news.")
            ClavisLoadingCard(title: "Loading dimensions", subtitle: "Fetching methodology inputs and score components.")
            ClavisLoadingCard(title: "Loading recent news", subtitle: "Scoring the latest article set for this ticker.")

        }
    }

    private func heroSection(_ detail: TickerDetailResponse) -> some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                    VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                        Text(detail.profile.companyName ?? ticker)
                            .font(ClavisTypography.h2)
                            .foregroundColor(.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)
                        Text(ticker)
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(.accentBurnt)

                        HStack(alignment: .firstTextBaseline, spacing: ClavisTheme.smallSpacing) {
                            Text(currency(latestPrice))
                                .font(ClavisTypography.metric)
                                .foregroundColor(.textPrimary)
                            Text(dayChangeText(detail))
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(dayChangeColor(detail))
                        }

                        HStack(alignment: .center, spacing: ClavisTheme.smallSpacing) {
                            Text(displayScoreText)
                                .font(ClavisTypography.portfolioScore)
                                .foregroundColor(.textPrimary)
                            GradeBadge(grade: displayGrade, size: .standard)
                        }
                    }

                    Spacer(minLength: ClavisTheme.smallSpacing)
                }

                if let score = displayScoreValue {
                    Text("New")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.gradeCBBB)
                        .padding(.vertical, 4)
                } else {
                    ratingPendingCard
                }
            }
        }
    }

    private var ratingPendingCard: some View {
        HStack(spacing: ClavisTheme.smallSpacing) {
            Text("Rating pending — check back after market open")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
            Spacer()
        }
        .padding(ClavisTheme.cardPadding)
        .background(Color.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }

    private func riskDimensionsSection(_ detail: TickerDetailResponse) -> some View {
        let dimensions = dimensionItems(detail)

        return VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionHeader(title: "Risk Dimensions")

            ClavisStandardCard(fill: .surface) {
                VStack(spacing: 0) {
                    ForEach(Array(dimensions.enumerated()), id: \.element.key) { index, dimension in
                        VStack(spacing: 0) {
                            Button(action: { openMethodology(dimension.key) }) {
                                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                                    HStack(alignment: .center, spacing: ClavisTheme.smallSpacing) {
                                        Text(dimension.title)
                                            .font(ClavisTypography.bodyEmphasis)
                                            .foregroundColor(.textPrimary)
                                        Spacer()
                                        if dimension.isLimited {
                                            dimensionBadge(text: "Limited Data", foreground: .warn, background: .warnSoft)
                                        }
                                        Text(dimension.scoreText)
                                            .font(ClavisTypography.rowScore)
                                            .foregroundColor(.textSecondary)
                                    }

                                    RiskBar(score: dimension.score ?? 0, grade: dimension.grade)
                                        .frame(height: 4)

                                    HStack(spacing: ClavisTheme.smallSpacing) {
                                        Text(dimension.subtitle)
                                            .font(ClavisTypography.footnote)
                                            .foregroundColor(.textSecondary)
                                            .lineLimit(2)
                                        Spacer()
                                        Button(action: { openMethodology(dimension.key) }) {
                                            Text("Full audit ↗")
                                                .font(ClavisTypography.label)
                                                .foregroundColor(.accentBurnt)
                                        }
                                        .buttonStyle(.plain)
                                    }
                                }
                                .padding(.vertical, ClavisTheme.mediumSpacing)
                            }
                            .buttonStyle(.plain)

                            if index < dimensions.count - 1 {
                                Divider().overlay(Color.border)
                            }
                        }
                    }
                }
            }
        }
    }

    private func driversSection(_ detail: TickerDetailResponse) -> some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionHeader(title: "What's Driving It")

            ClavisStandardCard(fill: .surface) {
                VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                    Text(driverSummary(detail))
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)

                    TickerDriverCardsSection(analysis: detail.currentAnalysis)
                }
            }
        }
    }

    private func recentNewsSection(_ detail: TickerDetailResponse) -> some View {
        let articles = displayArticles(detail)
        let visibleArticles = showAllArticles ? articles : Array(articles.prefix(10))

        return VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            HStack {
                sectionHeader(title: "Recent News")
                Spacer()
                if articles.count > 10 {
                    Button(showAllArticles ? "Show less" : "See all") {
                        showAllArticles.toggle()
                    }
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.accentBurnt)
                    .buttonStyle(.plain)
                }
            }

            if visibleArticles.isEmpty {
                ClavisStandardCard(fill: .surface) {
                    Text("No recent news for this ticker")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            } else {
                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: 0) {
                        ForEach(Array(visibleArticles.enumerated()), id: \.element.id) { index, article in
                            Button(action: { selectedArticle = article }) {
                                newsCard(article)
                            }
                            .buttonStyle(.plain)

                            if index < visibleArticles.count - 1 {
                                Divider().overlay(Color.border)
                            }
                        }
                    }
                }
            }
        }
    }

    private func newsCard(_ article: MethodologyArticle) -> some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text(article.title ?? "Untitled article")
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.textPrimary)
                .multilineTextAlignment(.leading)
                .lineLimit(2)

            HStack(spacing: ClavisTheme.smallSpacing) {
                Text(article.source ?? "Unknown source")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                Text("•")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
                Text(article.publishedAt ?? "Date unavailable")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
                Spacer()
                sentimentPill(score: article.sentimentScore)
                impactPill(text: article.impactTag?.humanizedTitleCasedDisplayText ?? "Limited Data")
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, ClavisTheme.mediumSpacing)
    }

    private func bottomCtas(_ detail: TickerDetailResponse) -> some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                if isHeld {
                    VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                        Text("In your holdings")
                            .font(ClavisTypography.cardTitle)
                            .foregroundColor(.textPrimary)
                        Text(holdingSummary(detail))
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
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
                        .foregroundColor(.accentBurnt)
                }
            }
        }
    }

    private func openMethodology(_ key: String) {
        selectedDimensionKey = key
        if methodology != nil {
            showMethodologyDrawer = true
            return
        }

        Task {
            do {
                let response = try await APIService.shared.fetchTickerMethodology(ticker: ticker)
                await MainActor.run {
                    methodology = response
                    showMethodologyDrawer = true
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                }
            }
        }
    }

    private func reloadAll() async {
        isLoading = true
        defer { isLoading = false }

        do {
            async let detailResponse = APIService.shared.fetchTickerDetail(ticker: ticker, positionId: positionId)
            async let priceResponse = APIService.shared.fetchPriceHistory(ticker: ticker, days: 30)

            let loadedDetail = try await detailResponse
            let loadedPrice = try await priceResponse

            await MainActor.run {
                detail = loadedDetail
                priceHistory = loadedPrice.prices
                errorMessage = nil
            }

            do {
                let loadedMethodology = try await APIService.shared.fetchTickerMethodology(ticker: ticker)
                await MainActor.run {
                    methodology = loadedMethodology
                }
            } catch {
                // TODO: backend should always return methodology payloads for rated tickers.
                await MainActor.run {
                    methodology = nil
                }
            }
        } catch {
            await MainActor.run {
                errorMessage = ClavisCopy.Errors.tickerLoad(ticker: ticker, error: error)
            }
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
            .foregroundColor(.textSecondary)
    }

    private func dimensionItems(_ detail: TickerDetailResponse) -> [TickerDimensionItem] {
        let shared = detail.sharedAnalysis?.riskDimensions
        let ai = detail.currentScore?.factorBreakdown?.aiDimensions
        let current = detail.currentScore

        return [
            TickerDimensionItem(
                key: "financial_health",
                title: "Financial Health",
                score: shared?.financialHealth ?? ai?.financialHealth ?? current?.financialHealth,
                subtitle: methodology?.dimensions.financialHealth.dataSource ?? "Quarterly fundamentals",
                isLimited: (shared?.financialHealth ?? ai?.financialHealth ?? current?.financialHealth) == nil
            ),
            TickerDimensionItem(
                key: "news_sentiment",
                title: "News Sentiment",
                score: shared?.newsSentiment ?? ai?.newsSentiment ?? current?.newsSentiment,
                subtitle: newsSubtitle,
                isLimited: (methodology?.dimensions.newsSentiment.articleCount7d ?? 0) < 3
            ),
            TickerDimensionItem(
                key: "macro_exposure",
                title: "Macro Exposure",
                score: shared?.macroExposure ?? ai?.macroExposure ?? current?.macroExposure,
                subtitle: methodology?.dimensions.macroExposure.asOfDate ?? "Macro regression",
                isLimited: methodology?.dimensions.macroExposure.limitedData ?? false
            ),
            TickerDimensionItem(
                key: "sector_exposure",
                title: "Sector Exposure",
                score: shared?.sectorExposure ?? ai?.sectorExposure ?? current?.sectorExposure,
                subtitle: methodology?.dimensions.sectorExposure.sector ?? detail.profile.sector ?? "Sector state",
                isLimited: (shared?.sectorExposure ?? ai?.sectorExposure ?? current?.sectorExposure) == nil
            ),
            TickerDimensionItem(
                key: "volatility",
                title: "Volatility",
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
            return .textSecondary
        }
        if price > previousClose { return .good }
        if price < previousClose { return .bad }
        return .textSecondary
    }

    private func sentimentPill(score: Double?) -> some View {
        dimensionBadge(
            text: score.map { "\(Int($0.rounded()))" } ?? "—",
            foreground: sentimentColor(score),
            background: sentimentBackground(score)
        )
    }

    private func impactPill(text: String) -> some View {
        dimensionBadge(text: text, foreground: .accentInk, background: .accentSoft)
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
        guard let score else { return .textSecondary }
        if score >= 70 { return .good }
        if score >= 50 { return .warn }
        return .bad
    }

    private func sentimentBackground(_ score: Double?) -> Color {
        guard let score else { return .surfaceElevated }
        if score >= 70 { return .goodSoft }
        if score >= 50 { return .warnSoft }
        return .badSoft
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
                    ClavisStandardCard(fill: .surface) {
                        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                            Text(companyName ?? ticker)
                                .font(ClavisTypography.cardTitle)
                                .foregroundColor(.textPrimary)
                            Text(ticker)
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.accentBurnt)
                        }
                    }

                    field(title: "Shares", text: $shares)
                    field(title: "Cost basis per share", text: $costBasis)

                    ClavisStandardCard(fill: .surface) {
                        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                            Text("Purchase date")
                                .font(ClavisTypography.label)
                                .foregroundColor(.textSecondary)
                            DatePicker("Purchase date", selection: $purchaseDate, displayedComponents: .date)
                                .datePickerStyle(.compact)
                                .labelsHidden()
                        }
                    }

                    if let errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    ClavisStandardCard(fill: .surfaceElevated) {
                        // TODO: backend add-holding contract does not yet accept purchase_date; send it once supported.
                        Text("The purchase date is collected for the V2 flow and will be sent once the backend add-holding contract is updated.")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
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
                        .foregroundColor(.textSecondary)
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button(isSubmitting ? "Adding..." : "Add") {
                        Task { await submit() }
                    }
                    .foregroundColor(isValid ? .accentBurnt : .textTertiary)
                    .disabled(!isValid || isSubmitting)
                }
            }
        }
    }

    private func field(title: String, text: Binding<String>) -> some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(title)
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)
                TextField(title, text: text)
                    .keyboardType(.decimalPad)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textPrimary)
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
