import SwiftUI

// MARK: - Evidence Item Model

private struct TDEvidItem: Identifiable {
    let id: String
    let title: String
    let summary: String
    let source: String
    let category: String
    let url: String?
    let publishedAt: Date?
    let eventAnalysis: EventAnalysis?
}

// MARK: - Main View

struct TickerDetailView: View {
    let ticker: String
    let positionId: String?

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var authViewModel: AuthViewModel
    @State private var detail: TickerDetailResponse?
    @State private var priceHistory: [PricePoint] = []
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var isMutatingWatchlist = false
    @State private var isRefreshingTicker = false
    @State private var selectedDays: Int = 30
    @State private var hasLoaded = false
    @State private var showFullSummary = false
    @State private var selectedEvidItem: TDEvidItem?

    init(ticker: String, positionId: String? = nil) {
        self.ticker = ticker
        self.positionId = positionId
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                if let errorMessage {
                    DashboardErrorCard(message: errorMessage)
                }

                if isLoading && detail == nil {
                    ClavisLoadingCard(
                        title: "Loading \(ticker)",
                        subtitle: "Pulling the latest market data and risk analysis."
                    )
                } else if let detail {
                    detailContent(detail)
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.top, ClavisTheme.sectionSpacing)
            .padding(.bottom, ClavisTheme.floatingTabHeight + ClavisTheme.floatingTabInset + ClavisTheme.extraLargeSpacing)
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            stickyHeader
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
        .sheet(isPresented: $showFullSummary) {
            if let analysis = detail?.currentAnalysis {
                TDExecSummarySheet(
                    ticker: ticker,
                    analysis: analysis
                )
            }
        }
        .sheet(item: $selectedEvidItem) { item in
            if let ev = item.eventAnalysis {
                TickerEventAnalysisDetailView(event: ev)
            } else {
                TDEvidDetailSheet(item: item)
            }
        }
    }

    // MARK: - Sticky Header

    private var stickyHeader: some View {
        VStack(spacing: 0) {
            HStack {
                Button(action: { dismiss() }) {
                    HStack(spacing: 4) {
                        Image(systemName: "chevron.left")
                            .font(.system(size: 13, weight: .semibold))
                        Text("Holdings")
                            .font(ClavisTypography.inter(15, weight: .regular))
                    }
                    .foregroundColor(.informational)
                }
                .buttonStyle(.plain)

                Spacer()

                VStack(spacing: 3) {
                    Text(ticker)
                        .font(ClavisTypography.inter(17, weight: .bold))
                        .foregroundColor(Color(hex: "#F3D58C"))
                    if let company = detail?.profile.companyName, !company.isEmpty {
                        Text(company)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }
                }

                Spacer()

                Button(action: { Task { await toggleWatchlist() } }) {
                    Image(systemName: isInWatchlist ? "star.fill" : "star")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(isInWatchlist ? .informational : .textSecondary)
                }
                .buttonStyle(.plain)
                .frame(width: 44, height: 44)
            }
            .frame(height: 54)
            .padding(.horizontal, ClavisTheme.screenPadding)

        }
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

    // MARK: - Content Sections

    @ViewBuilder
    private func detailContent(_ detail: TickerDetailResponse) -> some View {
        heroCard(detail)

        if let analysis = detail.currentAnalysis {
            executiveSummaryCard(analysis)
        }

        if detail.latestPrice.price != nil {
            priceSection(detail)
        }

        positionRefreshCard()

        let fundItems = fundamentalsItems(for: detail)
        if fundItems.contains(where: { $0.value != "--" }) {
            tdSectionLabel("FUNDAMENTALS")
            fundamentalsGrid(fundItems)
        }

        if let dims = riskDimensions(for: detail) {
            tdSectionLabel("RISK DIMENSIONS")
            riskDimensionsList(dims)
        }

        let dCards = detail.currentAnalysis?.driverCards ?? []
        let dState = detail.currentAnalysis?.driverCardsState ?? (dCards.isEmpty ? .pending : .ready)
        if !dCards.isEmpty || dState == .limited {
            keyDriversSection(detail, cards: dCards, state: dState)
        }

        let evidence = flatEvidence(from: detail)
        if !evidence.isEmpty {
            eventAnalysisSection(evidence)
        }
    }

    // MARK: - Hero Card

    private func heroCard(_ detail: TickerDetailResponse) -> some View {
        let grade = displayGrade(for: detail)
        let score = displayScore(for: detail)
        let trend = detail.position.riskTrend

        return ClavisStandardCard(fill: .surface, padding: 0) {
            VStack(spacing: 0) {
                HStack(alignment: .center, spacing: 18) {
                    gradeTile(grade)

                    VStack(alignment: .leading, spacing: 14) {
                        Text(ticker)
                            .font(.system(size: 22, weight: .bold, design: .monospaced))
                            .foregroundColor(Color(hex: "#F3D58C"))

                        if let company = detail.profile.companyName, !company.isEmpty {
                            Text(company)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                                .lineLimit(1)
                        }

                        if let trend {
                            HStack(spacing: 6) {
                                Text(trendArrow(trend))
                                    .font(.system(size: 18))
                                Text(trend.displayName)
                                    .font(ClavisTypography.inter(16, weight: .bold))
                            }
                            .foregroundColor(trendColor(trend))
                        } else {
                            Text("Updating")
                                .font(ClavisTypography.inter(16, weight: .bold))
                                .foregroundColor(.textTertiary)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text("Risk Score")
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                            Text("\(score)")
                                .font(.system(size: 34, weight: .bold, design: .monospaced))
                                .foregroundColor(.textPrimary)
                        }
                    }

                    Spacer()
                }
                .padding(.horizontal, 17)
                .padding(.vertical, 18)
            }
        }
    }

    private func gradeTile(_ grade: String) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            ClavisGradeStyle.gradeBandBg(for: grade),
                            ClavisGradeStyle.gradeBandBg(for: grade).opacity(0.75)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(width: 90, height: 90)

            Text(grade == "—" ? "—" : grade)
                .font(.system(size: 52, weight: .medium, design: .monospaced))
                .foregroundColor(ClavisGradeStyle.gradeBandText(for: grade))
        }
    }

    // MARK: - Executive Summary Card

    private func executiveSummaryCard(_ analysis: PositionAnalysis) -> some View {
        let teaser = (analysis.summary ?? analysis.longReport ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !teaser.isEmpty else { return AnyView(EmptyView()) }
        return AnyView(
            Button(action: { showFullSummary = true }) {
                ClavisStandardCard(fill: .surface) {
                    HStack(spacing: 13) {
                        ZStack {
                            Circle()
                                .fill(
                                    LinearGradient(
                                        colors: [Color(hex: "#9b3030"), Color(hex: "#6f1c1e")],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                            Image(systemName: "doc.text")
                                .font(.system(size: 17, weight: .medium))
                                .foregroundColor(Color(hex: "#ffd7d3"))
                        }
                        .frame(width: 40, height: 40)

                        VStack(alignment: .leading, spacing: 4) {
                            Text("Executive Summary")
                                .font(ClavisTypography.inter(17, weight: .semibold))
                                .foregroundColor(.textPrimary)
                            Text(teaser.count > 100 ? String(teaser.prefix(100)) + "…" : teaser)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                                .lineLimit(2)
                        }

                        Spacer(minLength: 4)

                        Image(systemName: "chevron.right")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(.textTertiary)
                    }
                }
            }
            .buttonStyle(.plain)
        )
    }

    // MARK: - Price Section

    private func priceSection(_ detail: TickerDetailResponse) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 5) {
                    Text(currency(detail.latestPrice.price))
                        .font(.system(size: 30, weight: .bold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                    Text(labelForDays(selectedDays))
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Text(priceChangeText(for: detail))
                        .font(ClavisTypography.inter(17, weight: .bold))
                        .foregroundColor(priceChangeColor(for: detail))
                    Text("Today")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }
            }
            .padding(.top, 4)

            HStack(spacing: 0) {
                ForEach([7, 30, 90, 365], id: \.self) { days in
                    Button(action: {
                        selectedDays = days
                        Task { await loadPriceHistory(days: days) }
                    }) {
                        Text(labelForDays(days))
                            .font(ClavisTypography.inter(13, weight: .semibold))
                            .foregroundColor(selectedDays == days ? .textPrimary : .textSecondary)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 11)
                            .background {
                                if selectedDays == days {
                                    RoundedRectangle(cornerRadius: 9, style: .continuous)
                                        .fill(Color.surfaceElevated)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 9, style: .continuous)
                                                .stroke(Color.border, lineWidth: 1)
                                        )
                                }
                            }
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.top, 16)

            TDSparkline(priceHistory: priceHistory, direction: priceChangeDirection(for: detail))
                .frame(height: 112)
                .padding(.top, 4)
        }
    }

    // MARK: - Position Refresh Card

    private func positionRefreshCard() -> some View {
        ClavisStandardCard(fill: .surface) {
            HStack(alignment: .center, spacing: 14) {
                VStack(alignment: .leading, spacing: 7) {
                    Text("POSITION ANALYSIS")
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)
                        .tracking(1.6)
                    Text("Refresh the latest risk review for this holding.")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer()

                Button(action: { Task { await refreshTicker() } }) {
                    Group {
                        if isRefreshingTicker {
                            HStack(spacing: 6) {
                                ProgressView().scaleEffect(0.65).tint(Color(hex: "#14171d"))
                                Text("Updating")
                            }
                        } else {
                            Text("Refresh")
                        }
                    }
                    .font(ClavisTypography.inter(14, weight: .bold))
                    .foregroundColor(Color(hex: "#14171d"))
                    .padding(.horizontal, 18)
                    .padding(.vertical, 11)
                    .background(Color(hex: "#f3f5f8"))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                }
                .buttonStyle(.plain)
                .disabled(isRefreshingTicker)
            }
        }
    }

    // MARK: - Section Label

    private func tdSectionLabel(_ text: String) -> some View {
        Text(text)
            .font(ClavisTypography.label)
            .foregroundColor(.textSecondary)
            .tracking(2)
            .padding(.top, 8)
            .padding(.bottom, 2)
    }

    // MARK: - Fundamentals Grid

    private struct TDFundItem: Identifiable {
        let id = UUID()
        let label: String
        let value: String
        var isLast = false
    }

    private func fundamentalsItems(for detail: TickerDetailResponse) -> [TDFundItem] {
        let pe = peDisplay(detail.profile.peRatio)
        let cap = compactCurrency(detail.profile.marketCap)
        let volScore = detail.currentScore?.factorBreakdown?.aiDimensions?.volatilityTrend
            ?? detail.latestRiskSnapshot?.factorBreakdown?.volatilityScore
        let vol = score(volScore)
        return [
            TDFundItem(label: "P/E", value: pe),
            TDFundItem(label: "Mkt cap", value: cap),
            TDFundItem(label: "Volatility", value: vol, isLast: true),
        ]
    }

    private func fundamentalsGrid(_ items: [TDFundItem]) -> some View {
        ClavisStandardCard(fill: .surface, padding: 0) {
            HStack(spacing: 0) {
                ForEach(items) { item in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(item.label)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                        Text(item.value)
                            .font(.system(size: 18, weight: .semibold, design: .monospaced))
                            .foregroundColor(.textPrimary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 13)
                    .padding(.vertical, 15)

                    if !item.isLast {
                        Rectangle()
                            .fill(Color.border)
                            .frame(width: 1)
                            .padding(.vertical, 10)
                    }
                }
            }
        }
    }

    // MARK: - Risk Dimensions

    private struct TDDimItem: Identifiable {
        let id = UUID()
        let title: String
        let value: Double?
    }

    private func riskDimensions(for detail: TickerDetailResponse) -> [TDDimItem]? {
        var news: Double?
        var macro: Double?
        var sizing: Double?
        var vol: Double?

        if let ai = detail.currentScore?.factorBreakdown?.aiDimensions
            ?? detail.latestRiskSnapshot?.factorBreakdown?.aiDimensions {
            news = ai.newsSentiment; macro = ai.macroExposure
            sizing = ai.positionSizing; vol = ai.volatilityTrend
        } else if let sc = detail.currentScore {
            news = sc.newsSentiment; macro = sc.macroExposure
            sizing = sc.positionSizing; vol = sc.volatilityTrend
        }

        guard news != nil || macro != nil || vol != nil else { return nil }

        var dims: [TDDimItem] = [
            TDDimItem(title: "News risk signals", value: news),
            TDDimItem(title: "Macro exposure", value: macro),
        ]
        if detail.userContext.isHeld {
            dims.append(TDDimItem(title: "Position sizing", value: sizing))
        }
        dims.append(TDDimItem(title: "Volatility trend", value: vol))
        return dims
    }

    private func riskDimensionsList(_ dims: [TDDimItem]) -> some View {
        VStack(spacing: 12) {
            ForEach(dims) { dim in
                VStack(spacing: 7) {
                    HStack {
                        Text(dim.title)
                            .font(ClavisTypography.inter(14, weight: .regular))
                            .foregroundColor(.textSecondary)
                        Spacer()
                        Text(dim.value.map { "\(Int($0.rounded()))" } ?? "—")
                            .font(ClavisTypography.inter(14, weight: .bold))
                            .foregroundColor(.textPrimary)
                    }
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: 999, style: .continuous)
                                .fill(Color.surfaceElevated)
                                .frame(height: 4)
                            if let v = dim.value {
                                RoundedRectangle(cornerRadius: 999, style: .continuous)
                                    .fill(Color(hex: "#9ba4b3"))
                                    .frame(width: max(0, geo.size.width * CGFloat(min(max(v, 0), 100) / 100.0)), height: 4)
                            }
                        }
                    }
                    .frame(height: 4)
                }
            }
        }
    }

    // MARK: - Key Drivers

    private func keyDriversSection(
        _ detail: TickerDetailResponse,
        cards: [DriverCard],
        state: DriverCardsState
    ) -> some View {
        let grade = displayGrade(for: detail)

        return ClavisStandardCard(fill: .surface, padding: 0) {
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .top, spacing: 8) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Key Drivers")
                            .font(ClavisTypography.inter(18, weight: .semibold))
                            .foregroundColor(.textPrimary)
                        Text("Why \(ticker) receives this grade.")
                            .font(ClavisTypography.inter(13, weight: .regular))
                            .foregroundColor(.textSecondary)
                    }
                    Spacer()
                    if grade != "—" {
                        Text("\(grade) RISK")
                            .font(.system(size: 11, weight: .heavy))
                            .foregroundColor(Color(hex: "#ff8178"))
                            .padding(.horizontal, 9)
                            .padding(.vertical, 6)
                            .background(Color(hex: "#ff665b").opacity(0.13))
                            .clipShape(Capsule())
                            .overlay(Capsule().stroke(Color(hex: "#ff665b").opacity(0.24), lineWidth: 1))
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 18)
                .padding(.bottom, 14)

                if state == .limited && cards.isEmpty {
                    Divider().overlay(Color.border.opacity(0.6))
                    VStack(alignment: .leading, spacing: 5) {
                        Text("Limited data")
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.textPrimary)
                        Text("Not enough coverage yet to build structured drivers for this holding.")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 14)
                } else {
                    ForEach(Array(cards.prefix(3).enumerated()), id: \.element.id) { _, card in
                        Divider().overlay(Color.border.opacity(0.6))
                        driverRow(card)
                    }
                }
            }
        }
    }

    private func driverRow(_ card: DriverCard) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 12) {
                Text("\(card.rank)")
                    .font(ClavisTypography.inter(14, weight: .semibold))
                    .foregroundColor(Color(hex: "#cbd3df"))
                    .frame(width: 30, height: 30)
                    .background(Color(hex: "#1b2431"))
                    .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))

                VStack(alignment: .leading, spacing: 4) {
                    if !card.title.isEmpty {
                        Text(card.title)
                            .font(ClavisTypography.inter(15, weight: .semibold))
                            .foregroundColor(.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    if !card.summary.isEmpty {
                        Text(card.summary)
                            .font(ClavisTypography.inter(13, weight: .regular))
                            .foregroundColor(.textSecondary)
                            .lineSpacing(3)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                Text(card.strength.displayName)
                    .font(ClavisTypography.inter(11, weight: .regular))
                    .foregroundColor(.textSecondary)
                    .fixedSize()
            }

            if !card.sourceChips.isEmpty {
                HStack(spacing: 6) {
                    ForEach(Array(card.sourceChips.prefix(3)), id: \.self) { chip in
                        Text(chip)
                            .font(.system(size: 11))
                            .foregroundColor(Color(hex: "#aab3c2"))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 5)
                            .background(Color.white.opacity(0.045))
                            .clipShape(Capsule())
                            .overlay(Capsule().stroke(Color.white.opacity(0.06), lineWidth: 1))
                    }
                }
                .padding(.leading, 42)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
    }

    // MARK: - Supporting Evidence

    private func flatEvidence(from detail: TickerDetailResponse) -> [TDEvidItem] {
        var seen = Set<String>()
        var result: [TDEvidItem] = []

        // Primary: latest event analyses (richest data — has AI scenario summaries)
        for ev in detail.latestEventAnalyses {
            guard !seen.contains(ev.id) else { continue }
            seen.insert(ev.id)
            let summary = ev.tldr ?? ev.whatHappened ?? ev.summary ?? ""
            let category = ev.eventType
                .map { $0.replacingOccurrences(of: "_", with: " ").capitalized } ?? "Event"
            result.append(TDEvidItem(
                id: ev.id,
                title: ev.title,
                summary: summary,
                source: ev.source ?? "",
                category: category,
                url: ev.sourceURL,
                publishedAt: ev.publishedAt,
                eventAnalysis: ev
            ))
            if result.count >= 5 { break }
        }

        // Supplement: driver card supporting evidence not already shown
        let cards = detail.currentAnalysis?.driverCards ?? []
        for card in cards where result.count < 5 {
            for item in card.supportingEvidence where result.count < 5 {
                guard !seen.contains(item.id) else { continue }
                seen.insert(item.id)
                result.append(TDEvidItem(
                    id: item.id,
                    title: item.title,
                    summary: item.summary,
                    source: item.source,
                    category: card.theme.displayName + " risk",
                    url: item.url,
                    publishedAt: item.publishedAt,
                    eventAnalysis: nil
                ))
            }
        }

        // Fallback: recent news
        for item in detail.recentNews where result.count < 5 {
            guard !seen.contains(item.id) else { continue }
            seen.insert(item.id)
            result.append(TDEvidItem(
                id: item.id,
                title: item.title,
                summary: item.summary ?? "",
                source: item.source ?? "",
                category: "News",
                url: item.url,
                publishedAt: item.publishedAt,
                eventAnalysis: nil
            ))
        }

        return result
    }

    private func eventAnalysisSection(_ items: [TDEvidItem]) -> some View {
        ClavisStandardCard(fill: .surface, padding: 0) {
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .bottom) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Event Analysis")
                            .font(ClavisTypography.inter(18, weight: .semibold))
                            .foregroundColor(.textPrimary)
                        Text("Analysis of recent events affecting the rating.")
                            .font(ClavisTypography.inter(12, weight: .regular))
                            .foregroundColor(.textSecondary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 16)

                ForEach(items) { item in
                    Divider().overlay(Color.border.opacity(0.6))
                    eventAnalysisRow(item)
                }
            }
        }
    }

    private func eventAnalysisRow(_ item: TDEvidItem) -> some View {
        Button(action: { selectedEvidItem = item }) {
            HStack(alignment: .center, spacing: 12) {
                VStack(alignment: .leading, spacing: 7) {
                    if !item.title.isEmpty {
                        Text(item.title)
                            .font(ClavisTypography.inter(15, weight: .semibold))
                            .foregroundColor(.textPrimary)
                            .lineLimit(2)
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    if !item.summary.isEmpty {
                        Text(item.summary)
                            .font(ClavisTypography.inter(13, weight: .regular))
                            .foregroundColor(.textSecondary)
                            .lineSpacing(2)
                            .lineLimit(3)
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    HStack(spacing: 6) {
                        if !item.source.isEmpty {
                            Text(item.source)
                                .font(ClavisTypography.inter(11, weight: .regular))
                                .foregroundColor(.textTertiary)
                                .padding(.horizontal, 7)
                                .padding(.vertical, 3)
                                .background(Color.white.opacity(0.05))
                                .clipShape(Capsule())
                        }
                        if !item.category.isEmpty {
                            Text(item.category)
                                .font(ClavisTypography.inter(11, weight: .regular))
                                .foregroundColor(.textTertiary)
                                .padding(.horizontal, 7)
                                .padding(.vertical, 3)
                                .background(Color.white.opacity(0.05))
                                .clipShape(Capsule())
                        }
                        if let date = item.publishedAt {
                            Text(date.formatted(.dateTime.month(.abbreviated).day().year()))
                                .font(ClavisTypography.inter(11, weight: .regular))
                                .foregroundColor(Color(hex: "#5a6470"))
                        }
                    }
                }

                Image(systemName: "chevron.right")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.textTertiary)
                    .frame(minWidth: 12)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Helpers

    private var isInWatchlist: Bool { detail?.userContext.isInWatchlist ?? false }

    private func displayScore(for detail: TickerDetailResponse) -> Int {
        Int((detail.currentScore?.displayScore ?? detail.position.totalScore ?? 50).rounded())
    }

    private func displayGrade(for detail: TickerDetailResponse) -> String {
        detail.currentScore?.displayGrade ?? detail.position.riskGrade ?? "—"
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

    private func priceChangeDirection(for detail: TickerDetailResponse) -> TDChangeDir {
        guard let change = priceChangePercent(for: detail) else { return .flat }
        if change > 0 { return .up }
        if change < 0 { return .down }
        return .flat
    }

    private func priceChangeColor(for detail: TickerDetailResponse) -> Color {
        switch priceChangeDirection(for: detail) {
        case .up:   return Color(hex: "#25c58a")
        case .down: return .riskD
        case .flat: return .textSecondary
        }
    }

    private func trendColor(_ trend: RiskTrend) -> Color {
        switch trend {
        case .worsening: return .riskF
        case .improving: return .riskA
        case .stable:    return .textSecondary
        }
    }

    private func trendArrow(_ trend: RiskTrend) -> String {
        switch trend {
        case .worsening: return "↓"
        case .improving: return "↑"
        case .stable:    return "→"
        }
    }

    private func updatedText(_ detail: TickerDetailResponse) -> String {
        let date = detail.currentScore?.scoreAsOf ?? detail.freshness.analysisAsOf
        guard let date else { return "Updated recently" }
        let diff = max(0, Date().timeIntervalSince(date))
        if diff < 3600 { return "Updated \(Int(diff / 60))m ago" }
        if diff < 86400 { return "Updated \(Int(diff / 3600))h ago" }
        return "Updated \(Int(diff / 86400))d ago"
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

    // MARK: - Formatters

    private func currency(_ value: Double?) -> String {
        guard let value else { return "--" }
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.maximumFractionDigits = 2
        return f.string(from: NSNumber(value: value)) ?? "--"
    }

    private func peDisplay(_ value: Double?) -> String {
        guard let value, value > 0 else { return "--" }
        return String(format: "%.1f", value)
    }

    private func compactCurrency(_ value: Double?) -> String {
        guard let value else { return "--" }
        let abs = Swift.abs(value)
        if abs >= 1_000_000_000_000 { return String(format: "$%.1fT", value / 1_000_000_000_000) }
        if abs >= 1_000_000_000 { return String(format: "$%.1fB", value / 1_000_000_000) }
        if abs >= 1_000_000 { return String(format: "$%.1fM", value / 1_000_000) }
        return currency(value)
    }

    private func score(_ value: Double?) -> String {
        guard let value else { return "--" }
        return "\(Int(value.rounded()))"
    }

    // MARK: - Networking

    private func loadDetail() async {
        isLoading = true
        defer { isLoading = false }
        do {
            detail = try await APIService.shared.fetchTickerDetail(ticker: ticker, positionId: positionId)
            errorMessage = nil
        } catch {
            errorMessage = ClavisCopy.Errors.tickerLoad(ticker: ticker, error: error)
        }
    }

    private func loadPriceHistory(days: Int = 30) async {
        do {
            let response = try await APIService.shared.fetchPriceHistory(ticker: ticker, days: days)
            priceHistory = response.prices
            errorMessage = nil
        } catch {
            if priceHistory.isEmpty { errorMessage = nil }
        }
    }

    private func reloadAll() async {
        await loadDetail()
        await loadPriceHistory(days: selectedDays)
    }

    private func toggleWatchlist() async {
        isMutatingWatchlist = true
        defer { isMutatingWatchlist = false }
        do {
            if isInWatchlist {
                _ = try await APIService.shared.removeFromWatchlist(ticker: ticker)
                await loadDetail()
            } else {
                _ = try await APIService.shared.addToWatchlist(ticker: ticker)
                dismiss()
            }
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
}

// MARK: - Sparkline

private enum TDChangeDir { case up, down, flat }

private struct TDSparkline: View {
    let priceHistory: [PricePoint]
    let direction: TDChangeDir

    private var ordered: [PricePoint] {
        priceHistory.sorted { $0.recordedAt < $1.recordedAt }
    }

    var body: some View {
        GeometryReader { geo in
            let pts = normalized(in: geo.size)
            if pts.count > 1 {
                ZStack {
                    Path { path in
                        path.move(to: CGPoint(x: pts[0].x, y: geo.size.height))
                        for p in pts { path.addLine(to: p) }
                        path.addLine(to: CGPoint(x: pts.last!.x, y: geo.size.height))
                        path.closeSubpath()
                    }
                    .fill(
                        LinearGradient(
                            colors: [lineColor.opacity(0.28), lineColor.opacity(0)],
                            startPoint: .top, endPoint: .bottom
                        )
                    )

                    Path { path in
                        path.move(to: pts[0])
                        for p in pts.dropFirst() { path.addLine(to: p) }
                    }
                    .stroke(lineColor, style: StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))
                }
            }
        }
    }

    private var lineColor: Color {
        switch direction {
        case .up:   return Color(hex: "#24bf86")
        case .down: return .riskD
        case .flat: return .textSecondary
        }
    }

    private func normalized(in size: CGSize) -> [CGPoint] {
        let values = ordered.map(\.price)
        guard values.count > 1,
              let minV = values.min(), let maxV = values.max() else {
            return []
        }
        let range = max(maxV - minV, 0.001)
        return values.enumerated().map { i, v in
            CGPoint(
                x: CGFloat(i) / CGFloat(max(values.count - 1, 1)) * size.width,
                y: size.height - ((CGFloat(v - minV) / CGFloat(range)) * (size.height - 6)) - 3
            )
        }
    }
}

// MARK: - Executive Summary Sheet

private struct TDExecSummarySheet: View {
    let ticker: String
    let analysis: PositionAnalysis
    @Environment(\.dismiss) private var dismiss

    private var positiveCards: [DriverCard] {
        analysis.driverCards.filter { $0.direction == .positive }
    }
    private var negativeCards: [DriverCard] {
        analysis.driverCards.filter { $0.direction == .negative }
    }
    private var headwinds: [String] {
        if let r = analysis.topRisks, !r.isEmpty { return r }
        return negativeCards.map(\.title)
    }
    private var tailwinds: [String] {
        positiveCards.map(\.title)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if let tldr = analysis.summary, !tldr.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        execSection(label: "TL;DR", body: tldr)
                    }
                    if !tailwinds.isEmpty {
                        execBullets(label: "Bullish Tailwinds", items: tailwinds)
                    }
                    if !headwinds.isEmpty {
                        execBullets(label: "Bearish Headwinds", items: headwinds)
                    }
                    if let watchItems = analysis.watchItems, !watchItems.isEmpty {
                        execBullets(label: "What Would Change the Rating", items: watchItems)
                    }
                }
                .padding(ClavisTheme.screenPadding)
                .padding(.bottom, ClavisTheme.largeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("\(ticker) — Executive Summary")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundColor(.informational)
                }
            }
        }
    }

    @ViewBuilder
    private func execSection(label: String, body: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(label.uppercased())
                .font(ClavisTypography.inter(11, weight: .semibold))
                .foregroundColor(.textTertiary)
                .tracking(0.6)
            Text(body)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
                .lineSpacing(5)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }

    @ViewBuilder
    private func execBullets(label: String, items: [String]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(label.uppercased())
                .font(ClavisTypography.inter(11, weight: .semibold))
                .foregroundColor(.textTertiary)
                .tracking(0.6)
            VStack(alignment: .leading, spacing: 10) {
                ForEach(items, id: \.self) { item in
                    HStack(alignment: .top, spacing: 10) {
                        Text("•")
                            .font(ClavisTypography.body)
                            .foregroundColor(.textTertiary)
                            .frame(width: 8)
                        Text(item)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                            .lineSpacing(3)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

// MARK: - Evidence Detail Sheet (for non-EventAnalysis items)

private struct TDEvidDetailSheet: View {
    let item: TDEvidItem
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    VStack(alignment: .leading, spacing: 8) {
                        if !item.title.isEmpty {
                            Text(item.title)
                                .font(ClavisTypography.h2)
                                .foregroundColor(.textPrimary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        HStack {
                            if !item.source.isEmpty {
                                Text(item.source)
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                            }
                            Spacer()
                            if let date = item.publishedAt {
                                Text(date.formatted(date: .abbreviated, time: .omitted))
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                            }
                        }
                    }
                    .padding(ClavisTheme.cardPadding)
                    .clavisCardStyle(fill: .surface)

                    if !item.summary.isEmpty {
                        TDAnalysisDetailSection(title: "What this means", text: item.summary)
                    }

                    if let urlStr = item.url, let url = URL(string: urlStr) {
                        Link(destination: url) {
                            HStack {
                                Text("Open Source")
                                    .font(ClavisTypography.bodyEmphasis)
                                    .foregroundColor(.informational)
                                Spacer()
                                Image(systemName: "arrow.up.right")
                                    .font(.system(size: 13, weight: .semibold))
                                    .foregroundColor(.informational)
                            }
                        }
                        .padding(ClavisTheme.cardPadding)
                        .clavisCardStyle(fill: .surfaceElevated)
                    }
                }
                .padding(ClavisTheme.screenPadding)
                .padding(.bottom, ClavisTheme.largeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle(item.category.isEmpty ? "Event" : item.category)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundColor(.informational)
                }
            }
        }
    }
}

// MARK: - Preserved for Event Detail Navigation

private struct TDAnalysisDetailSection: View {
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

private struct TDAnalysisListSection: View {
    let title: String
    let items: [String]
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)
                .frame(maxWidth: .infinity, alignment: .leading)
            VStack(alignment: .leading, spacing: 8) {
                ForEach(items, id: \.self) {
                    Text("• \($0)")
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

struct TickerEventAnalysisDetailView: View {
    @Environment(\.dismiss) private var dismiss
    let event: EventAnalysis

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                HStack {
                    Button(action: { dismiss() }) {
                        Text("Close")
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

                if let s = event.whatHappened?.trimmingCharacters(in: .whitespacesAndNewlines), !s.isEmpty {
                    TDAnalysisDetailSection(title: "What happened", text: s)
                }
                if let l = event.tldr?.trimmingCharacters(in: .whitespacesAndNewlines), !l.isEmpty {
                    TDAnalysisDetailSection(title: "TL;DR", text: l)
                }
                if let sc = event.whatItMeans?.trimmingCharacters(in: .whitespacesAndNewlines), !sc.isEmpty {
                    TDAnalysisDetailSection(title: "What it means", text: sc)
                }
                if let impl = event.keyImplications, !impl.isEmpty {
                    TDAnalysisListSection(title: "Key implications", items: impl)
                }
                if let fu = event.recommendedFollowups, !fu.isEmpty {
                    TDAnalysisListSection(title: "Follow-up notes", items: fu)
                }
                if let urlStr = event.sourceURL, let url = URL(string: urlStr) {
                    Link(destination: url) {
                        HStack {
                            Text("Open Source")
                                .font(ClavisTypography.bodyEmphasis)
                                .foregroundColor(.informational)
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundColor(.informational)
                        }
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
}
