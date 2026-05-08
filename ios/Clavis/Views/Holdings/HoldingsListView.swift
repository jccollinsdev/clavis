import SwiftUI

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
        let weightedPairs = viewModel.holdings.compactMap { position -> (Double, Double)? in
            guard let value = position.currentValue, value > 0, let score = position.resolvedTotalScore else { return nil }
            return (value, score)
        }

        let totalWeight = weightedPairs.reduce(0) { $0 + $1.0 }
        guard totalWeight > 0 else { return nil }
        return weightedPairs.reduce(0) { $0 + ($1.0 * $1.1) } / totalWeight
    }

    private var weightedGrade: String {
        guard let score = weightedScore else { return "—" }
        return grade(for: score)
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

                    portfolioHeader
                    searchBar

                    if isSearchingUniverse {
                        searchResultsSection
                    }

                    holdingsSection
                    watchlistSection
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
        }
    }

    private var topHeader: some View {
        ClavixPageHeader(title: "Holdings", subtitle: holdingsSubtitle) {
            HStack(spacing: ClavisTheme.smallSpacing) {
                Button(action: openAddHolding) {
                    Image(systemName: "plus")
                        .foregroundColor(.textPrimary)
                }
                .buttonStyle(.plain)

                Button(action: { Task { await viewModel.refreshHoldings() } }) {
                    Image(systemName: viewModel.isRefreshing ? "hourglass" : "arrow.clockwise")
                        .foregroundColor(.textPrimary)
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
                .fill(Color.border.opacity(0.5))
                .frame(height: 0.5)
        }
    }

    private var portfolioHeader: some View {
        ClavisStandardCard(fill: .surface) {
            HStack(alignment: .center, spacing: ClavisTheme.mediumSpacing) {
                GradeBadge(grade: weightedGrade, size: .large)

                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text("Portfolio composite · weighted")
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)
                    Text(weightedScore.map { "\(Int($0.rounded()))/100" } ?? "—")
                        .font(ClavisTypography.metric)
                        .foregroundColor(.textPrimary)
                    Text(biggestMoverSummary)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }

                Spacer()
            }
        }
    }

    private var searchBar: some View {
        ClavisStandardCard(fill: .surface) {
            HStack(spacing: ClavisTheme.smallSpacing) {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.textSecondary)
                TextField("Search ticker or company", text: $searchQuery)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textPrimary)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.characters)
                if !trimmedSearchQuery.isEmpty {
                    Button("Clear") {
                        searchQuery = ""
                        tickerSearchResults = []
                        tickerSearchError = nil
                    }
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.accentBurnt)
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
                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: 0) {
                        ForEach(Array(viewModel.holdings.enumerated()), id: \.element.id) { index, position in
                            NavigationLink(value: position.ticker) {
                                HoldingsRow(position: position)
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
                                Divider().overlay(Color.border)
                            }
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
                .foregroundColor(.accentBurnt)
                .buttonStyle(.plain)
            }

            if viewModel.watchlistItems.isEmpty {
                ClavisStandardCard(fill: .surface) {
                    Button(action: { selectedTab = 2 }) {
                        Text("Add tickers to watch")
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.accentBurnt)
                    }
                    .buttonStyle(.plain)
                }
            } else {
                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: 0) {
                        ForEach(Array(viewModel.watchlistItems.enumerated()), id: \.element.id) { index, item in
                            NavigationLink(value: item.ticker) {
                                WatchlistRow(item: item)
                            }
                            .buttonStyle(.plain)

                            if index < viewModel.watchlistItems.count - 1 {
                                Divider().overlay(Color.border)
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
                ClavisStandardCard(fill: .surface) {
                    Text("No search results yet.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            } else {
                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: 0) {
                        ForEach(Array(tickerSearchResults.enumerated()), id: \.element.id) { index, result in
                            NavigationLink(value: result) {
                                SearchResultRow(result: result, isWatchlisted: watchlistTickers.contains(result.ticker.uppercased()))
                            }
                            .buttonStyle(.plain)

                            if index < tickerSearchResults.count - 1 {
                                Divider().overlay(Color.border)
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
        Text(text)
            .font(ClavisTypography.label)
            .foregroundColor(.textSecondary)
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

    private func grade(for score: Double) -> String {
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

private struct HoldingsRow: View {
    let position: Position

    private var grade: String { position.resolvedRiskGrade ?? "—" }
    private var companyName: String { position.resolvedCompanyName ?? "Unknown company" }

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            GradeBadge(grade: grade, size: .compact)

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text(companyName)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)
                        .lineLimit(1)
                    Text(position.ticker)
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.accentBurnt)
                }

                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text("\(position.shares.formatted()) sh")
                    Text("·")
                    Text(currency(position.currentValue))
                    Text("·")
                    // TODO: backend holdings payload should return real day-change values per position.
                    Text("Day —")
                }
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)

                Text(unrealizedText)
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(unrealizedColor)
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, ClavisTheme.mediumSpacing)
        .padding(.horizontal, ClavisTheme.smallSpacing)
        .background(backgroundTint)
    }

    private var backgroundTint: Color {
        position.riskTrend == .worsening ? .warnSoft : .clear
    }

    private var unrealizedText: String {
        let value = currency(position.unrealizedPL)
        let pct = position.unrealizedPLPercent.map { String(format: "%@%.1f%%", $0 >= 0 ? "+" : "", $0) } ?? "—"
        return "Unrealized \(value) · \(pct)"
    }

    private var unrealizedColor: Color {
        guard let pnl = position.unrealizedPL else { return .textSecondary }
        return pnl >= 0 ? .good : .bad
    }

    private func currency(_ value: Double?) -> String {
        guard let value else { return "—" }
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 0
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
                        .foregroundColor(.textPrimary)
                        .lineLimit(1)
                    Text(item.ticker)
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.accentBurnt)
                }

                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text(item.price.map { currency($0) } ?? "—")
                    Text("·")
                    Text("Watching")
                }
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
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
                        .foregroundColor(.accentBurnt)
                    Text(result.companyName)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .lineLimit(1)
                }

                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text(result.price.map { currency($0) } ?? "—")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)

                    if !result.isSupported {
                        SearchTag(text: "Not in tracked universe", foreground: .warn, background: .warnSoft)
                    }

                    if isWatchlisted {
                        SearchTag(text: "Watching", foreground: .accentInk, background: .accentBurnt)
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
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("Add your first holding")
                    .font(ClavisTypography.h2)
                    .foregroundColor(.textPrimary)
                Text("Start with the positions you track most closely. Clavix will build your morning briefing around them.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
                ClavisPrimaryButton(title: "Add your first holding", action: onAddPosition)
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
                            .foregroundColor(.textPrimary)
                            .textInputAutocapitalization(.characters)
                            .autocorrectionDisabled()
                            .onChange(of: ticker) { newValue in
                                resolveTickerTask?.cancel()
                                resolveTickerTask = Task { await resolveTicker(newValue) }
                            }

                        if isSearchingSuggestions {
                            ProgressView()
                                .tint(.textPrimary)
                        }

                        if !companyName.isEmpty {
                            Text(companyName)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                        }

                        if let tickerError {
                            Text(tickerError)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.bad)
                        }
                    }

                    if !tickerSuggestions.isEmpty {
                        ClavisStandardCard(fill: .surface) {
                            VStack(spacing: 0) {
                                ForEach(Array(tickerSuggestions.enumerated()), id: \.element.id) { index, suggestion in
                                    Button(action: { applySuggestion(suggestion) }) {
                                        SearchResultRow(result: suggestion, isWatchlisted: false)
                                    }
                                    .buttonStyle(.plain)

                                    if index < tickerSuggestions.count - 1 {
                                        Divider().overlay(Color.border)
                                    }
                                }
                            }
                        }
                    }

                    fieldCard(title: "Shares") {
                        TextField("0", text: $shares)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textPrimary)
                            .keyboardType(.decimalPad)
                    }

                    fieldCard(title: "Cost basis per share") {
                        TextField("0", text: $costBasis)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textPrimary)
                            .keyboardType(.decimalPad)
                    }

                    fieldCard(title: "Purchase date") {
                        DatePicker("Purchase date", selection: $purchaseDate, displayedComponents: .date)
                            .datePickerStyle(.compact)
                            .labelsHidden()
                            .tint(.accentBurnt)
                        // TODO: backend add-holding endpoint does not yet accept purchase_date.
                        Text("Purchase date will be sent once the backend route supports it.")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
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
                        .foregroundColor(.textSecondary)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        Task { await submit() }
                    }
                    .foregroundColor(isValid ? .accentBurnt : .textTertiary)
                    .disabled(!isValid)
                }
            }
        }
    }

    private func fieldCard<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(title)
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)
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

                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: ClavisTheme.mediumSpacing) {
                        Image(systemName: viewModel.progressValue >= 1.0 ? "checkmark" : "chart.line.uptrend.xyaxis")
                            .font(.system(size: 28, weight: .medium))
                            .foregroundColor(iconColor)

                        VStack(spacing: ClavisTheme.smallSpacing) {
                            Text(primaryProgressMessage)
                                .font(ClavisTypography.h2)
                                .foregroundColor(.textPrimary)
                                .multilineTextAlignment(.center)

                            Text(viewModel.progressMessage)
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
                                .multilineTextAlignment(.center)
                        }

                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                Rectangle()
                                    .fill(Color.border)
                                    .frame(height: 4)
                                Rectangle()
                                    .fill(iconColor)
                                    .frame(width: geo.size.width * CGFloat(viewModel.progressValue), height: 4)
                            }
                        }
                        .frame(height: 4)

                        Text(progressStageText)
                            .font(ClavisTypography.label)
                            .foregroundColor(.textSecondary)
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
                        .foregroundColor(.textSecondary)
                }
            }
        }
    }

    private var iconColor: Color {
        if viewModel.progressValue >= 1.0 { return .good }
        if viewModel.progressMessage.lowercased().contains("failed") { return .bad }
        if viewModel.progressMessage.lowercased().contains("limited") { return .warn }
        return .accentBurnt
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
                    ClavisStandardCard(fill: .surface) {
                        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                            Text("Free vs Pro")
                                .font(ClavisTypography.h2)
                                .foregroundColor(.textPrimary)
                            Text("Free includes up to 3 holdings. Upgrade to Pro for unlimited holdings, CSV import, and brokerage sync.")
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                            ClavisPrimaryButton(title: "Start 14-day trial", action: {})
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
                        .foregroundColor(.textSecondary)
                }
            }
        }
    }
}
