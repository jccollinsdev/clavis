import SwiftUI

extension Notification.Name {
    static let openAddHoldingFromOnboarding = Notification.Name("openAddHoldingFromOnboarding")
}

struct HoldingsListView: View {
    @Binding var selectedTab: Int
    @Binding var deepLinkTicker: String?

    @StateObject private var viewModel = HoldingsViewModel()
    @State private var searchQuery = ""
    @State private var tickerSearchResults: [TickerSearchResult] = []
    @State private var isSearchingTickers = false
    @State private var tickerSearchError: String?
    @State private var tickerSearchTask: Task<Void, Never>?
    @State private var deleteCandidate: Position?
    @State private var showUpgradeSheet = false
    @State private var showAddHoldingSheet = false

    private var trimmedSearchQuery: String {
        searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var watchlistTickers: Set<String> {
        Set(viewModel.watchlistItems.map { $0.ticker.uppercased() })
    }

    private var totalMarketValue: Double {
        viewModel.holdings.compactMap(\.currentValue).reduce(0, +)
    }

    private var weightedScore: Double? {
        PortfolioMath.weightedScore(viewModel.holdings)
    }

    private var weightedGrade: String {
        PortfolioMath.weightedGrade(viewModel.holdings)
    }

    private var biggestMover: Position? {
        viewModel.holdings.max { abs($0.scoreDelta ?? 0) < abs($1.scoreDelta ?? 0) }
    }

    private var isFreeTier: Bool {
        viewModel.subscriptionTier == "free"
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    syncSummary
                    portfolioHeader
                    holdingsToolbar
                    searchBar

                    if isSearchingUniverse {
                        searchResultsSection
                    }

                    holdingsLedgerHeader
                    holdingsSection
                    watchlistSection
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.sectionSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .safeAreaInset(edge: .top, spacing: 0) {
                ClavixLargeHeader(
                    eyebrow: holdingsCountEyebrow,
                    title: "Holdings",
                    trailing: AnyView(
                        HStack(spacing: 14) {
                            Image(systemName: "slider.horizontal.3")
                                .foregroundColor(.clavixInk)
                            Button(action: openAddHolding) {
                                Image(systemName: "plus")
                                    .foregroundColor(.clavixInk)
                            }
                            .buttonStyle(.plain)
                        }
                    )
                )
            }
            .toolbar(.hidden, for: .navigationBar)
            .task {
                await viewModel.loadHoldings()
            }
            .refreshable {
                await viewModel.refreshHoldings()
            }
            .onChange(of: searchQuery) { newValue in
                scheduleTickerSearch(for: newValue)
            }
            .onChange(of: deepLinkTicker) { newValue in
                guard newValue != nil else { return }
                deepLinkTicker = nil
            }
            .sheet(isPresented: $showAddHoldingSheet) {
                HoldingsAddSheet(viewModel: viewModel)
            }
            .fullScreenCover(isPresented: $viewModel.showProgressSheet) {
                AddPositionProgressView(viewModel: viewModel)
            }
            .sheet(isPresented: $showUpgradeSheet) {
                HoldingsUpgradeSheet()
            }
            .alert("Delete holding?", isPresented: Binding(get: { deleteCandidate != nil }, set: { if !$0 { deleteCandidate = nil } })) {
                Button("Delete", role: .destructive) {
                    guard let deleteCandidate else { return }
                    Task { await viewModel.deleteHolding(deleteCandidate) }
                    self.deleteCandidate = nil
                }
                Button("Cancel", role: .cancel) { deleteCandidate = nil }
            } message: {
                Text("This removes the holding from your portfolio.")
            }
            .navigationDestination(for: TickerSearchResult.self) { result in
                TickerDetailView(ticker: result.ticker)
            }
            .navigationDestination(for: String.self) { ticker in
                TickerDetailView(ticker: ticker)
            }
            .onReceive(NotificationCenter.default.publisher(for: .openAddHoldingFromOnboarding)) { _ in
                openAddHolding()
            }
        }
    }

    // MARK: - VQA parity sections

    private var holdingsCountEyebrow: String {
        let h = viewModel.holdings.count
        let t = viewModel.watchlistItems.count
        return "\(h) position\(h == 1 ? "" : "s") · \(t) watched"
    }

    @ViewBuilder
    private var syncSummary: some View {
        if let subtitle = holdingsSubtitle {
            Text(subtitle)
                .font(ClavisTypography.clavixCaption)
                .foregroundColor(.clavixInk3)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var holdingsToolbar: some View {
        HStack(alignment: .center) {
            HStack(spacing: 4) {
                ClavixPill(label: "Weight", active: true)
                ClavixPill(label: "Grade")
                ClavixPill(label: "Δ Today")
                ClavixPill(label: "P&L")
            }
            Spacer()
            Text("\(viewModel.holdings.count) / \(viewModel.holdings.count)")
                .font(ClavisTypography.clavixMono(11, weight: .regular))
                .foregroundColor(.clavixInk3)
        }
    }

    @ViewBuilder
    private var holdingsLedgerHeader: some View {
        if !viewModel.holdings.isEmpty {
            HStack(spacing: 8) {
                ClavixColumnHeader("Sym · w%")
                    .frame(width: 70, alignment: .leading)
                ClavixColumnHeader("Last · day")
                    .frame(maxWidth: .infinity, alignment: .leading)
                ClavixColumnHeader("P&L", align: .trailing)
                    .frame(width: 70, alignment: .trailing)
                ClavixColumnHeader("Grade · Δ", align: .trailing)
                    .frame(width: 60, alignment: .trailing)
            }
            .padding(.horizontal, ClavixLayout.pad)
            .padding(.vertical, 8)
            .background(Color.clavixPaper2)
            .overlay(alignment: .top) { Rectangle().fill(Color.clavixRule).frame(height: 1) }
            .overlay(alignment: .bottom) { Rectangle().fill(Color.clavixRule).frame(height: 1) }
            .padding(.horizontal, -ClavixLayout.pad)
        }
    }

    private var topHeader: some View {
        ClavixPageHeader(title: "Holdings", subtitle: holdingsSubtitle) {
            HStack(spacing: ClavisTheme.smallSpacing) {
                Button(action: openAddHolding) {
                    Image(systemName: "plus")
                        .foregroundColor(.clavixInk)
                }
                .buttonStyle(.plain)

                Button(action: { Task { await viewModel.refreshHoldings() } }) {
                    Image(systemName: viewModel.isRefreshing ? "hourglass" : "arrow.clockwise")
                        .foregroundColor(.clavixInk)
                }
                .buttonStyle(.plain)
                .disabled(viewModel.isRefreshing)
            }
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.top, ClavisTheme.smallSpacing)
        .padding(.bottom, 6)
        .background(
            Color.backgroundPrimary.opacity(0.9)
                .background(.ultraThinMaterial)
                .ignoresSafeArea(edges: .top)
        )
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Color.clavixRule.opacity(0.5))
                .frame(height: 0.5)
        }
    }

    private var portfolioHeader: some View {
        ClavixCard {
            HStack(alignment: .center, spacing: 14) {
                ClavixGradeBadge(weightedGrade, size: 44)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Portfolio composite · weighted")
                        .font(ClavisTypography.clavixMono(10, weight: .bold))
                        .tracking(0.7)
                        .foregroundColor(.clavixInk3)
                    Text(weightedScore.map { "\(Int($0.rounded()))/100" } ?? "—")
                        .font(ClavisTypography.clavixMono(22, weight: .semibold))
                        .foregroundColor(.clavixInk)
                    Text(biggestMoverSummary)
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk2)
                }

                Spacer()
            }
        }
    }

    private var searchBar: some View {
        ClavixCard(padding: 12) {
            HStack(spacing: ClavisTheme.smallSpacing) {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.clavixInk3)
                TextField("Search ticker or company", text: $searchQuery)
                    .font(ClavisTypography.clavixSerif(15))
                    .foregroundColor(.clavixInk)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.characters)
                if !trimmedSearchQuery.isEmpty {
                    Button("Clear") {
                        searchQuery = ""
                        tickerSearchResults = []
                        tickerSearchError = nil
                    }
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.clavixAccent)
                    .buttonStyle(.plain)
                }
            }
        }
    }

    @ViewBuilder
    private var holdingsSection: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionHeader("Holdings")

            if viewModel.isLoading && viewModel.holdings.isEmpty {
                ClavisLoadingCard(title: "Loading holdings", subtitle: "Pulling your latest positions and ratings.")
            } else if viewModel.holdings.isEmpty {
                HoldingsEmptyState(onAddPosition: openAddHolding)
            } else {
                // VQA ledger: flush rows, no card padding around the list; the
                // ledger header bar sits flush above and dividers separate rows.
                VStack(spacing: 0) {
                    ForEach(Array(viewModel.holdings.enumerated()), id: \.element.id) { index, position in
                        NavigationLink(value: position.ticker) {
                            HoldingsRow(position: position, totalPortfolioValue: totalMarketValue)
                        }
                        .buttonStyle(.plain)
                        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                            Button(role: .destructive) {
                                deleteCandidate = position
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                        if index < viewModel.holdings.count - 1 {
                            Rectangle().fill(Color.clavixRule2).frame(height: 1)
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var watchlistSection: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            HStack {
                sectionHeader(isFreeTier ? "Watchlist · \(viewModel.watchlistItems.count) of 5 free" : "Watchlist")
                Spacer()
                Button("Add") {
                    selectedTab = 2
                }
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.clavixAccent)
                .buttonStyle(.plain)
            }

            if viewModel.watchlistItems.isEmpty {
                ClavixCard(fill: .clavixPaper) {
                    Button(action: { selectedTab = 2 }) {
                        Text("Add tickers to watch")
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.clavixAccent)
                    }
                    .buttonStyle(.plain)
                }
            } else {
                ClavixCard(fill: .clavixPaper) {
                    VStack(spacing: 0) {
                        ForEach(Array(viewModel.watchlistItems.enumerated()), id: \.element.id) { index, item in
                            NavigationLink(value: item.ticker) {
                                WatchlistRow(item: item)
                            }
                            .buttonStyle(.plain)

                            if index < viewModel.watchlistItems.count - 1 {
                                Divider().overlay(Color.clavixRule)
                            }
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var searchResultsSection: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionHeader("Search Results")

            if let tickerSearchError {
                DashboardErrorCard(message: tickerSearchError)
            } else if isSearchingTickers {
                ClavisLoadingCard(title: "Searching tickers", subtitle: "Checking the tracked universe.")
            } else if tickerSearchResults.isEmpty {
                ClavixCard(fill: .clavixPaper) {
                    Text("No search results yet.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard(fill: .clavixPaper) {
                    VStack(spacing: 0) {
                        ForEach(Array(tickerSearchResults.enumerated()), id: \.element.id) { index, result in
                            NavigationLink(value: result) {
                                SearchResultRow(result: result, isWatchlisted: watchlistTickers.contains(result.ticker.uppercased()))
                            }
                            .buttonStyle(.plain)

                            if index < tickerSearchResults.count - 1 {
                                Divider().overlay(Color.clavixRule)
                            }
                        }
                    }
                }
            }
        }
    }

    private var holdingsSubtitle: String? {
        var parts: [String] = []
        if let lastRefreshedAt = viewModel.lastRefreshedAt {
            parts.append("Updated \(lastRefreshedAt.formatted(date: .abbreviated, time: .omitted))")
        }
        if let brokerageLastSyncedAt = viewModel.brokerageLastSyncedAt {
            parts.append("Brokerage sync \(brokerageLastSyncedAt.formatted(date: .abbreviated, time: .omitted))")
        }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    private var isSearchingUniverse: Bool {
        !trimmedSearchQuery.isEmpty
    }

    private var biggestMoverSummary: String {
        guard let biggestMover else { return "No day-over-day change available." }
        let delta = biggestMover.scoreDelta ?? 0
        if delta == 0 { return "No rating change from yesterday." }
        return "\(delta > 0 ? "▲" : "▼") \(abs(delta)) from yesterday · \(biggestMover.ticker)"
    }

    private func sectionHeader(_ text: String) -> some View {
        Text(text.uppercased())
            .font(ClavisTypography.clavixMono(10, weight: .bold))
            .tracking(0.7)
            .foregroundColor(.clavixInk3)
    }

    private func scheduleTickerSearch(for query: String) {
        tickerSearchTask?.cancel()
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmed.isEmpty else {
            tickerSearchResults = []
            tickerSearchError = nil
            isSearchingTickers = false
            return
        }

        tickerSearchTask = Task {
            isSearchingTickers = true
            tickerSearchError = nil

            do {
                try await Task.sleep(nanoseconds: 250_000_000)
                guard !Task.isCancelled else { return }
                let results = try await viewModel.searchTickers(query: trimmed, limit: 12)
                guard !Task.isCancelled else { return }
                tickerSearchResults = results
            } catch is CancellationError {
                return
            } catch {
                tickerSearchResults = []
                tickerSearchError = ClavisCopy.Errors.tickerSearch(error)
            }

            isSearchingTickers = false
        }
    }

    private func openAddHolding() {
        if isFreeTier && viewModel.holdings.count >= 3 {
            showUpgradeSheet = true
        } else {
            showAddHoldingSheet = true
        }
    }

}

/// VQAHoldingsLedgerRow 1:1 — 4 columns: Sym/w%, Last/day(spark+pct), P&L,
/// Grade·Δ. Highlights when the position is in a worsening trend.
private struct HoldingsRow: View {
    let position: Position
    let totalPortfolioValue: Double

    private var grade: String { position.resolvedRiskGrade ?? "—" }
    private var weightPct: Int? {
        guard totalPortfolioValue > 0, let value = position.currentValue else { return nil }
        return Int(((value / totalPortfolioValue) * 100).rounded())
    }
    private var dayPct: Double? { position.sharedAnalysis?.dayChangePct }

    var body: some View {
        HStack(spacing: 8) {
            // Sym · w%
            VStack(alignment: .leading, spacing: 3) {
                Text(position.ticker)
                    .font(ClavisTypography.clavixMono(13, weight: .bold))
                    .tracking(0.3)
                    .foregroundColor(.clavixInk)
                Text(weightPct.map { "w \($0)%" } ?? "w —")
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk3)
            }
            .frame(width: 70, alignment: .leading)

            // Last · day (spark + pct)
            VStack(alignment: .leading, spacing: 4) {
                Text(currencyDecimal(position.resolvedCurrentPrice))
                    .font(ClavisTypography.clavixMono(13, weight: .semibold))
                    .foregroundColor(.clavixInk)
                HStack(spacing: 6) {
                    ClavixMiniSpark(tone: dayTone)
                        .frame(width: 48, height: 14)
                    Text(dayText)
                        .font(ClavisTypography.clavixMono(10, weight: .semibold))
                        .foregroundColor(dayTone)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // P&L
            VStack(alignment: .trailing, spacing: 3) {
                Text(pnlText)
                    .font(ClavisTypography.clavixMono(13, weight: .semibold))
                    .foregroundColor(pnlColor)
                Text(pnlPctText)
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk3)
            }
            .frame(width: 70, alignment: .trailing)

            // Grade · Δ
            VStack(alignment: .trailing, spacing: 2) {
                ClavixGradeBadge(grade, size: 18)
                Text(deltaText)
                    .font(ClavisTypography.clavixMono(10, weight: .semibold))
                    .foregroundColor(deltaColor)
            }
            .frame(width: 60, alignment: .trailing)
        }
        .padding(.horizontal, ClavixLayout.pad)
        .padding(.vertical, 12)
        .background(highlighted ? Color.clavixAccentSoft : Color.clear)
        .overlay(alignment: .leading) {
            if highlighted { Rectangle().fill(Color.clavixAccent).frame(width: 3) }
        }
        .padding(.horizontal, -ClavixLayout.pad)
    }

    private var highlighted: Bool { position.riskTrend == .worsening }

    private var dayTone: Color {
        guard let pct = dayPct else { return .clavixInk3 }
        if pct > 0.05 { return .clavixGood }
        if pct < -0.05 { return .clavixBad }
        return .clavixInk3
    }

    private var dayText: String {
        guard let pct = dayPct else { return "—" }
        return String(format: "%@%.1f%%", pct >= 0 ? "+" : "", pct)
    }

    private var pnlText: String { currencyDecimal(position.unrealizedPL, abbreviate: false) }
    private var pnlColor: Color {
        guard let pnl = position.unrealizedPL else { return .clavixInk3 }
        return pnl >= 0 ? .clavixGood : .clavixBad
    }
    private var pnlPctText: String {
        guard let pct = position.unrealizedPLPercent else { return "—" }
        return String(format: "%@%.1f%%", pct >= 0 ? "+" : "", pct)
    }

    private var deltaText: String {
        guard let delta = position.scoreDelta, delta != 0 else { return "—" }
        return delta > 0 ? "▲ \(delta)" : "▼ \(abs(delta))"
    }

    private var deltaColor: Color {
        guard let delta = position.scoreDelta else { return .clavixInk3 }
        if delta > 0 { return .clavixGood }
        if delta < 0 { return .clavixBad }
        return .clavixInk3
    }

    private func currencyDecimal(_ value: Double?, abbreviate: Bool = false) -> String {
        guard let value else { return "—" }
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = abbreviate ? 0 : 2
        if abbreviate, abs(value) >= 10_000 { formatter.maximumFractionDigits = 0 }
        return formatter.string(from: NSNumber(value: value)) ?? "—"
    }
}

private struct WatchlistRow: View {
    let item: WatchlistItem

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            GradeBadge(grade: item.resolvedGrade ?? "—", size: .compact)

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text(item.resolvedCompanyName ?? "Tracked symbol")
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.clavixInk)
                        .lineLimit(1)
                    Text(item.ticker)
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.clavixAccent)
                }

                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text(item.price.map { currency($0) } ?? "—")
                    Text("·")
                    Text("Watching")
                }
                .font(ClavisTypography.footnote)
                .foregroundColor(.clavixInk3)
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, ClavisTheme.mediumSpacing)
        .padding(.horizontal, ClavisTheme.smallSpacing)
    }

    private func currency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "—"
    }
}

private struct SearchResultRow: View {
    let result: TickerSearchResult
    let isWatchlisted: Bool

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            GradeBadge(grade: result.resolvedGrade ?? "—", size: .compact)

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text(result.ticker)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.clavixAccent)
                    Text(result.companyName)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.clavixInk3)
                        .lineLimit(1)
                }

                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text(result.price.map { currency($0) } ?? "—")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.clavixInk3)

                    if !result.isSupported {
                        SearchTag(text: "Not in tracked universe", foreground: .warn, background: .clavixWarnSoft)
                    }

                    if isWatchlisted {
                        SearchTag(text: "Watching", foreground: .clavixAccentInk, background: .clavixAccent)
                    }
                }
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, ClavisTheme.mediumSpacing)
    }

    private func currency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "—"
    }
}

private struct SearchTag: View {
    let text: String
    let foreground: Color
    let background: Color

    var body: some View {
        Text(text)
            .font(ClavisTypography.label)
            .foregroundColor(foreground)
            .padding(.horizontal, 6)
            .padding(.vertical, 4)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

struct HoldingsEmptyState: View {
    let onAddPosition: () -> Void

    var body: some View {
        ClavixCard(fill: .clavixPaper) {
            VStack(alignment: .leading, spacing: 12) {
                Text("Add your first holding")
                    .font(ClavisTypography.clavixSerif(20, weight: .medium))
                    .foregroundColor(.clavixInk)
                Text("Start with the positions you track most closely. Clavix will build your morning briefing around them.")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk2)
                    .fixedSize(horizontal: false, vertical: true)
                Button(action: onAddPosition) {
                    Text("Add your first holding")
                        .font(ClavisTypography.clavixMono(11, weight: .bold))
                        .tracking(0.4)
                        .foregroundColor(.clavixPaper)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.clavixInk)
                        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                }
                .buttonStyle(.plain)
            }
        }
    }
}

private struct HoldingsAddSheet: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var ticker = ""
    @State private var companyName = ""
    @State private var tickerSuggestions: [TickerSearchResult] = []
    @State private var isSearchingSuggestions = false
    @State private var tickerError: String?
    @State private var isTickerSupported = false
    @State private var shares = ""
    @State private var costBasis = ""
    @State private var purchaseDate = Date()
    @State private var resolveTickerTask: Task<Void, Never>?

    private var isValid: Bool {
        isTickerSupported && (Double(shares) ?? 0) > 0 && (Double(costBasis) ?? 0) >= 0
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    fieldCard(title: "Ticker") {
                        TextField("Search ticker", text: $ticker)
                            .font(ClavisTypography.body)
                            .foregroundColor(.clavixInk)
                            .textInputAutocapitalization(.characters)
                            .autocorrectionDisabled()
                            .onChange(of: ticker) { newValue in
                                resolveTickerTask?.cancel()
                                resolveTickerTask = Task { await resolveTicker(newValue) }
                            }

                        if isSearchingSuggestions {
                            ProgressView()
                                .tint(.clavixInk)
                        }

                        if !companyName.isEmpty {
                            Text(companyName)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.clavixInk3)
                        }

                        if let tickerError {
                            Text(tickerError)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.bad)
                        }
                    }

                    if !tickerSuggestions.isEmpty {
                        ClavixCard(fill: .clavixPaper) {
                            VStack(spacing: 0) {
                                ForEach(Array(tickerSuggestions.enumerated()), id: \.element.id) { index, suggestion in
                                    Button(action: { applySuggestion(suggestion) }) {
                                        SearchResultRow(result: suggestion, isWatchlisted: false)
                                    }
                                    .buttonStyle(.plain)

                                    if index < tickerSuggestions.count - 1 {
                                        Divider().overlay(Color.clavixRule)
                                    }
                                }
                            }
                        }
                    }

                    fieldCard(title: "Shares") {
                        TextField("0", text: $shares)
                            .font(ClavisTypography.body)
                            .foregroundColor(.clavixInk)
                            .keyboardType(.decimalPad)
                    }

                    fieldCard(title: "Cost basis per share") {
                        TextField("0", text: $costBasis)
                            .font(ClavisTypography.body)
                            .foregroundColor(.clavixInk)
                            .keyboardType(.decimalPad)
                    }

                    fieldCard(title: "Purchase date") {
                        DatePicker("Purchase date", selection: $purchaseDate, displayedComponents: .date)
                            .datePickerStyle(.compact)
                            .labelsHidden()
                            .tint(.clavixAccent)
                        // TODO: backend add-holding endpoint does not yet accept purchase_date.
                        Text("Purchase date will be sent once the backend route supports it.")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.clavixInk3)
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Add Holding")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .foregroundColor(.clavixInk3)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        Task { await submit() }
                    }
                    .foregroundColor(isValid ? .clavixAccent : .clavixInk4)
                    .disabled(!isValid)
                }
            }
        }
    }

    private func fieldCard<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        ClavixCard(fill: .clavixPaper) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(title)
                    .font(ClavisTypography.label)
                    .foregroundColor(.clavixInk3)
                content()
            }
        }
    }

    private func resolveTicker(_ query: String) async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            tickerSuggestions = []
            tickerError = nil
            companyName = ""
            isTickerSupported = false
            return
        }

        isSearchingSuggestions = true
        do {
            try await Task.sleep(nanoseconds: 200_000_000)
            guard !Task.isCancelled else { return }
            let results = try await viewModel.searchTickers(query: trimmed, limit: 8)
            guard !Task.isCancelled else { return }

            let exactMatch = results.first { $0.ticker.caseInsensitiveCompare(trimmed) == .orderedSame }
            if let exactMatch, exactMatch.isSupported {
                applySuggestion(exactMatch)
                tickerSuggestions = []
            } else {
                tickerSuggestions = results
                companyName = ""
                isTickerSupported = false
                tickerError = results.isEmpty ? "Ticker not found" : nil
            }
        } catch is CancellationError {
            return
        } catch {
            tickerSuggestions = []
            companyName = ""
            isTickerSupported = false
            tickerError = "Unable to validate ticker right now."
        }
        isSearchingSuggestions = false
    }

    private func applySuggestion(_ suggestion: TickerSearchResult) {
        ticker = suggestion.ticker
        companyName = suggestion.resolvedCompanyName ?? suggestion.companyName
        isTickerSupported = suggestion.isSupported
        tickerError = suggestion.isSupported ? nil : "Ticker not found"
    }

    private func submit() async {
        guard let sharesValue = Double(shares), let costBasisValue = Double(costBasis) else { return }
        await viewModel.addHolding(ticker: ticker.uppercased(), shares: sharesValue, purchasePrice: costBasisValue)
        if viewModel.errorMessage == nil {
            dismiss()
        }
    }
}

struct AddPositionProgressView: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: ClavisTheme.extraLargeSpacing) {
                Spacer()

                ClavixCard(fill: .clavixPaper) {
                    VStack(spacing: ClavisTheme.mediumSpacing) {
                        Image(systemName: viewModel.progressValue >= 1.0 ? "checkmark" : "chart.line.uptrend.xyaxis")
                            .font(.system(size: 28, weight: .medium))
                            .foregroundColor(iconColor)

                        VStack(spacing: ClavisTheme.smallSpacing) {
                            Text(primaryProgressMessage)
                                .font(ClavisTypography.h2)
                                .foregroundColor(.clavixInk)
                                .multilineTextAlignment(.center)

                            Text(viewModel.progressMessage)
                                .font(ClavisTypography.body)
                                .foregroundColor(.clavixInk3)
                                .multilineTextAlignment(.center)
                        }

                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                Rectangle()
                                    .fill(Color.clavixRule)
                                    .frame(height: 4)
                                Rectangle()
                                    .fill(iconColor)
                                    .frame(width: geo.size.width * CGFloat(viewModel.progressValue), height: 4)
                            }
                        }
                        .frame(height: 4)

                        Text(progressStageText)
                            .font(ClavisTypography.label)
                            .foregroundColor(.clavixInk3)
                    }
                }

                Spacer()
            }
            .padding(ClavisTheme.screenPadding)
            .background(ClavisAtmosphereBackground())
            .navigationTitle(viewModel.pendingTicker ?? "New Holding")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundColor(.clavixInk3)
                }
            }
        }
    }

    private var iconColor: Color {
        if viewModel.progressValue >= 1.0 { return .good }
        if viewModel.progressMessage.lowercased().contains("failed") { return .bad }
        if viewModel.progressMessage.lowercased().contains("limited") { return .warn }
        return .clavixAccent
    }

    private var primaryProgressMessage: String {
        if viewModel.progressValue >= 1.0 { return "Holding ready" }
        return "Adding \(viewModel.pendingTicker ?? "holding")"
    }

    private var progressStageText: String {
        if viewModel.progressValue >= 1.0 { return "POSITION READY" }
        return viewModel.activeRun?.currentStageMessage?.uppercased() ?? "ANALYSIS IN PROGRESS"
    }
}

private struct HoldingsUpgradeSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    ClavixCard(fill: .clavixPaper) {
                        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                            Text("Free vs Pro")
                                .font(ClavisTypography.h2)
                                .foregroundColor(.clavixInk)
                            Text("Free includes up to 3 holdings. Upgrade to Pro for unlimited holdings, CSV import, and brokerage sync.")
                                .font(ClavisTypography.body)
                                .foregroundColor(.clavixInk3)
                                .fixedSize(horizontal: false, vertical: true)
                            ClavisPrimaryButton(title: "Pro is coming soon", action: { dismiss() })
                        }
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Upgrade")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundColor(.clavixInk3)
                }
            }
        }
    }
}
