import SwiftUI

struct HoldingsListView: View {
    @Binding var selectedTab: Int
    @Binding var deepLinkTicker: String?
    @StateObject private var viewModel = HoldingsViewModel()
    @State private var showTickerSearch = false
    @State private var searchQuery = ""
    @State private var tickerSearchResults: [TickerSearchResult] = []
    @State private var isSearchingTickers = false
    @State private var tickerSearchError: String?
    @State private var tickerSearchTask: Task<Void, Never>?
    @State private var selectedSort: HoldingSort = .grade
    @State private var selectedFilter: HoldingFilter = .all
    @State private var deleteTickerCandidate: Position?
    @State private var navigationPath: [String] = []

    private var sortedHoldings: [Position] {
        selectedSort.sort(filteredHoldings)
    }

    private var filteredHoldings: [Position] {
        viewModel.holdings.filter { selectedFilter.matches(position: $0) }
    }

    private var trimmedSearchQuery: String {
        searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var isSearchingUniverse: Bool {
        !trimmedSearchQuery.isEmpty
    }

    private var watchlistTickers: Set<String> {
        Set(viewModel.watchlistItems.map { $0.ticker.uppercased() })
    }

    private var holdingsCount: Int {
        viewModel.holdings.count
    }

    private var watchlistCount: Int {
        viewModel.watchlistItems.count
    }

    private var highRiskCount: Int {
        viewModel.holdings.filter { $0.riskGrade == "D" || $0.riskGrade == "F" }.count
    }

    private var improvingCount: Int {
        viewModel.holdings.filter { $0.riskTrend == .improving }.count
    }

    var body: some View {
        NavigationStack(path: $navigationPath) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    HoldingsTopHeader(
                        onAddPosition: { viewModel.showAddSheet = true },
                        onRefresh: { Task { await viewModel.refreshHoldings() } },
                        isRefreshing: viewModel.isRefreshing,
                        isOffline: NetworkStatusMonitor.shared.isOffline
                    )

                    HoldingsSearchBar(
                        query: $searchQuery,
                        onOpenTickerSearch: { showTickerSearch = true }
                    )

                    HoldingsSummaryCard(
                        positions: viewModel.holdings,
                        lastUpdatedAt: viewModel.lastRefreshedAt,
                        brokerageLastSyncedAt: viewModel.brokerageLastSyncedAt,
                        isOffline: NetworkStatusMonitor.shared.isOffline
                    )

                    if NetworkStatusMonitor.shared.isOffline {
                        OfflineStatusBanner()
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    if viewModel.isLoading && viewModel.holdings.isEmpty {
                        ClavisLoadingCard(title: "Loading holdings", subtitle: "Pulling positions and the latest scores.")
                    } else if isSearchingUniverse {
                        HoldingsTickerSearchResultsCard(
                            query: trimmedSearchQuery,
                            results: tickerSearchResults,
                            isSearching: isSearchingTickers,
                            errorMessage: tickerSearchError,
                            watchlistedTickers: watchlistTickers,
                            onToggleWatchlist: { result in
                                Task { await toggleWatchlist(for: result) }
                            }
                        )
                    } else if viewModel.holdings.isEmpty {
                        HoldingsEmptyState(onAddPosition: { viewModel.showAddSheet = true })
                    } else {
                        HoldingsControlCard(
                            selectedFilter: $selectedFilter,
                            selectedSort: $selectedSort,
                            isRefreshing: viewModel.isRefreshing,
                            onRefresh: { Task { await viewModel.refreshHoldings() } }
                        )

                        if !viewModel.watchlistItems.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Watchlist · \(viewModel.watchlistItems.count)")
                                    .font(ClavisTypography.label)
                                    .foregroundColor(.textSecondary)

                                PrototypeHoldingsSection {
                                    ForEach(Array(viewModel.watchlistItems.enumerated()), id: \.element.id) { index, item in
                                        NavigationLink(value: item.ticker) {
                                            WatchlistCardRow(item: item, showsDivider: index < viewModel.watchlistItems.count - 1)
                                        }
                                        .buttonStyle(.plain)
                                        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                            Button(role: .destructive) {
                                                Task { _ = try? await viewModel.removeTickerFromWatchlist(item.ticker) }
                                            } label: {
                                                Label("Remove", systemImage: "star.slash")
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        if !needsReviewPositions.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Needs review · \(needsReviewPositions.count)")
                                    .font(ClavisTypography.label)
                                    .foregroundColor(.textSecondary)

                                VStack(alignment: .leading, spacing: 0) {
                                    Text("These holdings have deteriorated since last review.")
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.textSecondary)
                                        .padding(.horizontal, 14)
                                        .padding(.top, 8)
                                        .padding(.bottom, 2)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(Color.dangerSurface)

                                    PrototypeHoldingsSection {
                                        ForEach(Array(needsReviewPositions.enumerated()), id: \.element.id) { index, position in
                                            holdingRow(for: position, isLast: index == needsReviewPositions.count - 1)
                                        }
                                    }
                                }
                                .overlay(
                                    RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                                        .stroke(Color.border, lineWidth: 1)
                                )
                                .overlay(alignment: .leading) {
                                    Rectangle()
                                        .fill(Color.riskD)
                                        .frame(width: 3)
                                        .clipShape(RoundedRectangle(cornerRadius: 1.5))
                                }
                                .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
                            }
                        }

                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("All holdings")
                                    .font(ClavisTypography.label)
                                    .foregroundColor(.textSecondary)

                                Spacer()

                                Menu {
                                    ForEach(HoldingSort.allCases, id: \.self) { sort in
                                        Button(sort.rawValue) {
                                            selectedSort = sort
                                        }
                                    }
                                } label: {
                                    Text("Sort by \(selectedSort.rawValue) ▾")
                                        .font(ClavisTypography.footnoteEmphasis)
                                        .foregroundColor(.informational)
                                }
                            }

                            PrototypeHoldingsSection {
                                ForEach(Array(sortedHoldings.enumerated()), id: \.element.id) { index, position in
                                    holdingRow(for: position, isLast: index == sortedHoldings.count - 1)
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.largeSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .refreshable {
                await viewModel.refreshHoldings()
            }
            .onChange(of: searchQuery) { _, newValue in
                scheduleTickerSearch(for: newValue)
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .sheet(isPresented: $viewModel.showAddSheet) {
                AddPositionSheet(viewModel: viewModel)
            }
            .sheet(isPresented: $showTickerSearch) {
                TickerSearchSheet()
            }
            .fullScreenCover(isPresented: $viewModel.showProgressSheet) {
                AddPositionProgressView(viewModel: viewModel)
            }
            .alert("Error", isPresented: $viewModel.showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(viewModel.errorMessage ?? "Unknown error")
            }
            .alert("Delete position?", isPresented: Binding(get: { deleteTickerCandidate != nil }, set: { if !$0 { deleteTickerCandidate = nil } })) {
                Button("Delete", role: .destructive) {
                    if let candidate = deleteTickerCandidate {
                        Task { await viewModel.deleteHolding(candidate) }
                    }
                    deleteTickerCandidate = nil
                }
                Button("Cancel", role: .cancel) { deleteTickerCandidate = nil }
            } message: {
                Text("This removes the position from your holdings.")
            }
            .onAppear {
                viewModel.showError = false
                if viewModel.holdings.isEmpty && !viewModel.isLoading {
                    Task { await viewModel.loadHoldings() }
                }
            }
            .onChange(of: deepLinkTicker) { _, newValue in
                guard let newValue else { return }
                navigationPath = [newValue]
                deepLinkTicker = nil
            }
            .navigationDestination(for: String.self) { ticker in
                TickerDetailView(ticker: ticker)
            }
        }
    }

    private func scheduleTickerSearch(for rawQuery: String) {
        tickerSearchTask?.cancel()

        let trimmed = rawQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            tickerSearchResults = []
            tickerSearchError = nil
            isSearchingTickers = false
            return
        }

        tickerSearchTask = Task { [trimmed] in
            isSearchingTickers = true
            tickerSearchError = nil

            do {
                try await Task.sleep(nanoseconds: 250_000_000)
                guard !Task.isCancelled else { return }
                let results = try await viewModel.searchTickers(query: trimmed, limit: 50)
                guard !Task.isCancelled else { return }
                tickerSearchResults = prioritizedSearchResults(results, query: trimmed)
            } catch is CancellationError {
                return
            } catch {
                tickerSearchResults = []
                tickerSearchError = error.localizedDescription
            }

            isSearchingTickers = false
        }
    }

    private func prioritizedSearchResults(_ results: [TickerSearchResult], query: String) -> [TickerSearchResult] {
        let normalizedQuery = query.uppercased()

        return results.sorted { left, right in
            let leftKey = searchRank(for: left, query: normalizedQuery)
            let rightKey = searchRank(for: right, query: normalizedQuery)

            if leftKey.priority != rightKey.priority {
                return leftKey.priority < rightKey.priority
            }

            if leftKey.secondary != rightKey.secondary {
                return leftKey.secondary < rightKey.secondary
            }

            return left.ticker < right.ticker
        }
    }

    private func searchRank(for result: TickerSearchResult, query: String) -> (priority: Int, secondary: Int) {
        let ticker = result.ticker.uppercased()
        let company = result.companyName.uppercased()

        if ticker == query { return (0, 0) }
        if ticker.hasPrefix(query) { return (1, 0) }
        if company.hasPrefix(query) { return (2, 0) }
        if ticker.contains(query) { return (3, 0) }
        if company.contains(query) { return (4, 0) }
        return (5, 0)
    }

    private func toggleWatchlist(for result: TickerSearchResult) async {
        let ticker = result.ticker.uppercased()

        do {
            if watchlistTickers.contains(ticker) {
                try await viewModel.removeTickerFromWatchlist(ticker)
            } else {
                try await viewModel.addTickerToWatchlist(ticker)
            }

            tickerSearchTask?.cancel()
            searchQuery = ""
            tickerSearchResults = []
            tickerSearchError = nil
        } catch {
            tickerSearchError = "Watchlist update failed: \(error.localizedDescription)"
        }
    }

    private var needsReviewPositions: [Position] {
        sortedHoldings.filter {
            $0.riskGrade == "D" || $0.riskGrade == "F" || $0.riskTrend == .increasing
        }
    }

    @ViewBuilder
    private func holdingRow(for position: Position, isLast: Bool) -> some View {
        NavigationLink(value: position.ticker) {
            PositionCardRow(position: position, showsDivider: !isLast)
        }
        .buttonStyle(.plain)
        .contextMenu {
            Button {
                Task {
                    if watchlistTickers.contains(position.ticker.uppercased()) {
                        _ = try? await viewModel.removeTickerFromWatchlist(position.ticker)
                    } else {
                        _ = try? await viewModel.addTickerToWatchlist(position.ticker)
                    }
                }
            } label: {
                Label(watchlistTickers.contains(position.ticker.uppercased()) ? "Remove from watchlist" : "Add to watchlist", systemImage: "star")
            }

            Button(role: .destructive) {
                deleteTickerCandidate = position
            } label: {
                Label("Delete Position", systemImage: "trash")
            }
        }
        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
            Button(role: .destructive) {
                deleteTickerCandidate = position
            } label: {
                Label("Delete", systemImage: "trash")
            }
        }
        .swipeActions(edge: .leading, allowsFullSwipe: false) {
            Button {
                Task {
                    if watchlistTickers.contains(position.ticker.uppercased()) {
                        _ = try? await viewModel.removeTickerFromWatchlist(position.ticker)
                    } else {
                        _ = try? await viewModel.addTickerToWatchlist(position.ticker)
                    }
                }
            } label: {
                Label(watchlistTickers.contains(position.ticker.uppercased()) ? "Unstar" : "Star", systemImage: "star")
            }
            .tint(.informational)
        }
    }
}

private struct HoldingsTickerSearchResultsCard: View {
    let query: String
    let results: [TickerSearchResult]
    let isSearching: Bool
    let errorMessage: String?
    let watchlistedTickers: Set<String>
    let onToggleWatchlist: (TickerSearchResult) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Search results")
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)
                    Text(query.uppercased())
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)
                }

                Spacer()

                if isSearching {
                    ProgressView()
                }
            }

            if let errorMessage {
                Text(errorMessage)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.riskF)
            }

            if !isSearching && results.isEmpty && errorMessage == nil {
                Text("No tickers matched your search.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }

            ForEach(Array(results.enumerated()), id: \.element.id) { index, result in
                HoldingsTickerSearchResultRow(
                    result: result,
                    isWatchlisted: watchlistedTickers.contains(result.ticker.uppercased()),
                    showsDivider: index < results.count - 1,
                    onToggleWatchlist: { onToggleWatchlist(result) }
                )
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle()
    }
}

private struct HoldingsTickerSearchResultRow: View {
    let result: TickerSearchResult
    let isWatchlisted: Bool
    let showsDivider: Bool
    let onToggleWatchlist: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            NavigationLink(destination: TickerDetailView(ticker: result.ticker)) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(result.ticker)
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.textPrimary)
                        GradeTag(grade: result.grade ?? "C", compact: true)
                    }

                    Text(result.companyName)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)

                    if let summary = result.summary, !summary.isEmpty {
                        Text(summary.sanitizedDisplayText)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.plain)

            Button(action: onToggleWatchlist) {
                Image(systemName: isWatchlisted ? "star.fill" : "star")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(isWatchlisted ? .informational : .textSecondary)
                    .frame(width: 32, height: 32)
                    .background(Color.surface)
                    .clipShape(Circle())
                    .overlay(Circle().stroke(Color.border, lineWidth: 1))
            }
            .buttonStyle(.plain)
        }
        .padding(.vertical, 12)
        .overlay(alignment: .bottom) {
            if showsDivider {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 1)
                    .offset(x: 0, y: 8)
            }
        }
    }
}

private struct HoldingsTopHeader: View {
    let onAddPosition: () -> Void
    let onRefresh: () -> Void
    let isRefreshing: Bool
    let isOffline: Bool

    var body: some View {
        ClavixWordmarkHeader(subtitle: Date().formatted(.dateTime.weekday(.wide).month(.abbreviated).day())) {
            HStack(spacing: 10) {
                Button(action: onAddPosition) {
                    HoldingsHeaderButton(systemName: "plus")
                }
                .buttonStyle(.plain)

                Button(action: onRefresh) {
                    HoldingsHeaderButton(systemName: isRefreshing ? "hourglass" : "arrow.clockwise")
                }
                .buttonStyle(.plain)
                .disabled(isRefreshing || isOffline)
                .accessibilityLabel(isRefreshing ? "Refreshing holdings" : "Refresh holdings")
            }
        }
    }
}

private struct HoldingsHeaderButton: View {
    let systemName: String

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: 15, weight: .semibold))
            .foregroundColor(.textSecondary)
            .frame(width: 40, height: 40)
            .background(Color.surface)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color.border, lineWidth: 1))
    }
}

private struct HoldingsSearchBar: View {
    @Binding var query: String
    let onOpenTickerSearch: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 15, weight: .medium))
                .foregroundColor(.textSecondary)

            TextField("Search all stocks", text: $query)
                .font(ClavisTypography.body)
                .foregroundColor(.textPrimary)
                .autocorrectionDisabled()

            Button(action: onOpenTickerSearch) {
                Image(systemName: "arrow.up.right.circle")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.textSecondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 13)
        .padding(.vertical, 11)
        .background(Color.surface)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(Color.border, lineWidth: 1)
        )
    }
}

private struct HoldingsSummaryCard: View {
    let positions: [Position]
    let lastUpdatedAt: Date?
    let brokerageLastSyncedAt: Date?
    let isOffline: Bool

    private var averageScore: Double {
        let scores = positions.compactMap(\.totalScore)
        guard !scores.isEmpty else { return 50 }
        return scores.reduce(0, +) / Double(scores.count)
    }

    private var averageGrade: String {
        switch averageScore {
        case 75...: return "A"
        case 55..<75: return "B"
        case 35..<55: return "C"
        case 15..<35: return "D"
        default: return "F"
        }
    }

    private var statusText: String {
        let highRisk = positions.filter { $0.riskGrade == "D" || $0.riskGrade == "F" }.count
        return highRisk > 0 ? "Overall risk elevated" : "Overall risk stable"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("\(positions.count) position\(positions.count == 1 ? "" : "s")")
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)

                    Text(statusText)
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)
                }

                Spacer()

                HStack(spacing: 10) {
                    Text("\(Int(averageScore.rounded()))")
                        .font(ClavisTypography.dataNumber)
                        .foregroundColor(.textPrimary)
                        .monospacedDigit()

                    GradeTag(grade: averageGrade, large: true)
                }
            }

            if let lastUpdatedAt {
                Text("Updated \(lastUpdatedAt.formatted(date: .abbreviated, time: .shortened))")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }

            if let brokerageLastSyncedAt {
                Text("Brokerage sync \(brokerageLastSyncedAt.formatted(date: .abbreviated, time: .shortened))")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.informational)
            }

            if isOffline {
                Text("Read-only while offline")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.riskD)
            }
        }
        .padding(14)
        .clavisCardStyle(fill: .surface)
    }
}

private struct PrototypeHoldingsSection<Content: View>: View {
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

struct HoldingsTriageCard: View {
    let holdingsCount: Int
    let watchlistCount: Int
    let highRiskCount: Int
    let improvingCount: Int
    let lastUpdatedAt: Date?
    let onAddPosition: () -> Void
    let onSearch: () -> Void
    let onRefresh: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            ClavisEyebrowHeader(eyebrow: "Holdings", title: "Search, add, and review positions")

            Text("Positions are ordered by current risk, with quick access to the cached watchlist and add flow.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            HStack(spacing: ClavisTheme.smallSpacing) {
                HoldingsStatPill(title: "Tracked", value: "\(holdingsCount)")
                HoldingsStatPill(title: "Watchlist", value: "\(watchlistCount)")
                HoldingsStatPill(title: "High risk", value: "\(highRiskCount)", accent: .riskF)
                HoldingsStatPill(title: "Improving", value: "\(improvingCount)", accent: .riskA)
            }

            HStack(spacing: ClavisTheme.smallSpacing) {
                Button(action: onSearch) {
                    Label("Search tickers", systemImage: "magnifyingglass")
                        .font(ClavisTypography.bodyEmphasis)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button(action: onAddPosition) {
                    Label("Add position", systemImage: "plus")
                        .font(ClavisTypography.bodyEmphasis)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.informational)
            }

            HStack {
                Label(lastUpdatedAt.map { "Updated \($0.formatted(date: .abbreviated, time: .shortened))" } ?? "Updated pending", systemImage: "clock")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
                Spacer()
                Button(action: onRefresh) {
                    Label("Refresh", systemImage: "arrow.clockwise")
                        .font(ClavisTypography.footnoteEmphasis)
                }
                .buttonStyle(.plain)
                .foregroundColor(.informational)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisHeroCardStyle(fill: .surface)
    }
}

struct HoldingsControlCard: View {
    @Binding var selectedFilter: HoldingFilter
    @Binding var selectedSort: HoldingSort
    let isRefreshing: Bool
    let onRefresh: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            ClavisSectionHeader("Review tools", subtitle: "Filter by concern and change the sort order.") {
                Button(action: onRefresh) {
                    Label(isRefreshing ? "Refreshing" : "Refresh", systemImage: "arrow.clockwise")
                        .font(ClavisTypography.footnoteEmphasis)
                }
                .disabled(isRefreshing)
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(HoldingFilter.allCases, id: \.self) { filter in
                        controlPill(title: filter.rawValue, isSelected: selectedFilter == filter) {
                            selectedFilter = filter
                        }
                    }
                }
            }

            HStack(spacing: 8) {
                ForEach(HoldingSort.allCases, id: \.self) { sort in
                    controlPill(title: sort.rawValue, isSelected: selectedSort == sort) {
                        selectedSort = sort
                    }
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }

    @ViewBuilder
    private func controlPill(title: String, isSelected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(isSelected ? .backgroundPrimary : .textPrimary)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(isSelected ? Color.textPrimary : Color.surfaceElevated)
                .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                        .stroke(Color.border, lineWidth: isSelected ? 0 : 1)
                )
        }
        .buttonStyle(.plain)
    }
}

struct HoldingsOverviewCard: View {
    let positions: [Position]
    let lastUpdatedAt: Date?

    private var averageScore: Double? {
        let scores = positions.compactMap(\.totalScore)
        guard !scores.isEmpty else { return nil }
        return scores.reduce(0, +) / Double(scores.count)
    }

    private var trackedValue: Double? {
        let values = positions.compactMap(\.currentValue)
        guard !values.isEmpty else { return nil }
        return values.reduce(0, +)
    }

    private var highRiskCount: Int {
        positions.filter { $0.riskGrade == "D" || $0.riskGrade == "F" }.count
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Portfolio Overview")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            VStack(alignment: .leading, spacing: 10) {
                HoldingsOverviewMetricRow(
                    title: "Average score",
                    value: averageScore.map { "\(Int($0.rounded()))" } ?? "--",
                    valueColor: ClavisDecisionStyle.color(for: averageScore ?? 50)
                )

                HoldingsOverviewMetricRow(
                    title: "Tracked value",
                    value: trackedValue.map(formatCurrency) ?? "Updating"
                )

                HoldingsOverviewMetricRow(
                    title: "High risk",
                    value: "\(highRiskCount)",
                    valueColor: .riskF
                )
            }

            if let lastUpdatedAt {
                Text("Updated \(lastUpdatedAt.formatted(date: .abbreviated, time: .shortened))")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisHeroCardStyle(fill: .surface)
    }

    private func formatCurrency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "$0"
    }
}

struct HoldingsOverviewMetricRow: View {
    let title: String
    let value: String
    var valueColor: Color = .textPrimary

    var body: some View {
        HStack(spacing: 12) {
            Text(title)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)

            Spacer()

            Text(value)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(valueColor)
                .monospacedDigit()
        }
    }
}

struct HoldingsStatPill: View {
    let title: String
    let value: String
    var accent: Color = .textPrimary

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(ClavisTypography.label)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(accent)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
    }
}

struct HoldingsSectionCard<Content: View>: View {
    let title: String
    var subtitle: String? = nil
    @ViewBuilder let content: Content

    init(title: String, subtitle: String? = nil, @ViewBuilder content: () -> Content) {
        self.title = title
        self.subtitle = subtitle
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                if let subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }
            }

            VStack(spacing: ClavisTheme.smallSpacing) {
                content
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct PositionCardRow: View {
    let position: Position
    var showsDivider: Bool = false

    private var grade: String {
        position.riskGrade ?? "C"
    }

    private var scoreText: String {
        if let score = position.totalScore {
            return "\(Int(score.rounded()))"
        }
        return "--"
    }

    private var subtitleText: String {
        if let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
            return summary
        }
        if position.analysisStartedAt != nil && position.riskGrade == nil {
            return "Analysis in progress. This position will populate when scoring finishes."
        }
        return "No summary available yet."
    }

    private var trendSymbol: String {
        switch position.riskTrend {
        case .improving:
            return "▲"
        case .increasing:
            return "▼"
        default:
            return "—"
        }
    }

    private var trendColor: Color {
        switch position.riskTrend {
        case .improving:
            return .riskA
        case .increasing:
            return .riskD
        default:
            return .textSecondary
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .center, spacing: 12) {
                GradeTag(grade: grade)

                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 8) {
                        Text(position.ticker)
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundColor(.textPrimary)

                        Text(position.archetype.displayName)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .lineLimit(1)

                        if position.isBrokerageSynced {
                            Text("Synced")
                                .font(ClavisTypography.label)
                                .foregroundColor(.informational)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 3)
                                .background(Color.informational.opacity(0.12))
                                .clipShape(Capsule())
                        }
                    }

                    Text(subtitleText)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .lineLimit(2)
                }

                Spacer(minLength: 12)

                VStack(alignment: .trailing, spacing: 4) {
                    Text(scoreText)
                        .font(.system(size: 15, weight: .semibold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                        .monospacedDigit()

                    Text(trendSymbol)
                        .font(.system(size: 15, weight: .semibold, design: .monospaced))
                        .foregroundColor(trendColor)
                }
            }

            if showsDivider {
                Divider()
                    .overlay(Color.border)
            }
        }
        .padding(.vertical, 13)
    }
}

struct HoldingsSignalPill: View {
    let text: String
    var accent: Color = .textSecondary

    var body: some View {
        Text(text)
            .font(ClavisTypography.footnote)
            .foregroundColor(accent)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .clavisSecondaryCardStyle(fill: .surface)
    }
}

// MARK: - Holdings Empty State

struct HoldingsEmptyState: View {
    let onAddPosition: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.largeSpacing) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("No holdings yet")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text("Add your first position to start tracking downside risk and portfolio updates.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)

                Button("Add Position", action: onAddPosition)
                    .buttonStyle(.borderedProminent)
                    .tint(Color.informational)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle()
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.vertical, ClavisTheme.largeSpacing)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }
}

// MARK: - Backward compat: keep HoldingRow as alias
typealias HoldingRow = PositionCardRow

// MARK: - Add Position Sheet

struct AddPositionSheet: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var ticker = ""
    @State private var companyName = ""
    @State private var shares = ""
    @State private var purchasePrice = ""
    @State private var archetype: Archetype = .growth
    @State private var showError = false
    @State private var errorMessage = ""

    private var isFormValid: Bool {
        !ticker.isEmpty && !shares.isEmpty && Double(shares) != nil && !purchasePrice.isEmpty && Double(purchasePrice) != nil
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Position") {
                    TextField("Ticker (e.g., AAPL)", text: $ticker)
                        .textCase(.uppercase)
                        .autocapitalization(.allCharacters)
                        .onChange(of: ticker) { _, newValue in
                            Task { await resolveTicker(newValue) }
                        }

                    if !companyName.isEmpty {
                        Text(companyName)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }

                    Text("Enter an exact ticker symbol. Search suggestions are available in the dedicated ticker search screen.")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)

                    TextField("Shares", text: $shares)
                        .keyboardType(.decimalPad)

                    TextField("Purchase Price", text: $purchasePrice)
                        .keyboardType(.decimalPad)
                }

                Section("Archetype") {
                    Picker("Archetype", selection: $archetype) {
                        ForEach(Archetype.allCases, id: \.self) { arch in
                            Text(arch.displayName).tag(arch)
                        }
                    }
                    .pickerStyle(.menu)
                }
            }
            .navigationTitle("Add Position")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        Task { await addPosition() }
                    }
                    .disabled(!isFormValid)
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage)
            }
        }
    }

    private func addPosition() async {
        guard let sharesVal = Double(shares), let priceVal = Double(purchasePrice) else {
            errorMessage = "Invalid number format"
            showError = true
            return
        }

        await viewModel.addHolding(
            ticker: ticker.uppercased(),
            shares: sharesVal,
            purchasePrice: priceVal,
            archetype: archetype
        )

        if viewModel.errorMessage == nil {
            dismiss()
        } else {
            errorMessage = viewModel.errorMessage ?? "Unable to add position."
            showError = true
        }
    }

    private func resolveTicker(_ query: String) async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 1 else {
            companyName = ""
            return
        }

        do {
            let results = try await viewModel.searchTickers(query: trimmed)
            companyName = results.first(where: { $0.ticker == trimmed.uppercased() })?.companyName ?? ""
        } catch {
            companyName = ""
        }
    }
}

// MARK: - Add Position Progress View

struct AddPositionProgressView: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Spacer()

                VStack(spacing: 20) {
                    // Status icon
                    ZStack {
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.surface)
                            .frame(width: 80, height: 80)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))

                        Image(systemName: viewModel.progressValue >= 1.0 ? "checkmark" : "chart.line.uptrend.xyaxis")
                            .font(.system(size: 28, weight: .medium))
                            .foregroundColor(viewModel.progressValue >= 1.0 ? .riskA : .textSecondary)
                            .animation(.linear(duration: 0.3), value: viewModel.progressValue)
                    }

                    VStack(spacing: 6) {
                        Text(primaryProgressMessage)
                            .font(ClavisTypography.h2)
                            .foregroundColor(.textPrimary)
                            .multilineTextAlignment(.center)

                        Text(progressDescription)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                            .multilineTextAlignment(.center)
                    }

                    // Progress bar — flat, no capsule
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Rectangle()
                                .fill(Color.border)
                                .frame(height: 4)
                            Rectangle()
                                .fill(ClavisGradeStyle.riskColor(for: progressGrade))
                                .frame(width: geo.size.width * CGFloat(viewModel.progressValue), height: 4)
                                .animation(.spring(response: 0.5, dampingFraction: 0.82), value: viewModel.progressValue)
                        }
                    }
                    .frame(height: 4)

                    Text(progressStageText)
                        .font(ClavisTypography.label)
                        .kerning(0.88)
                        .foregroundColor(.textSecondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 28)
                .background(Color.surface)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
                .clipShape(RoundedRectangle(cornerRadius: 8))

                Spacer()
            }
            .padding(24)
            .background(Color.backgroundPrimary.ignoresSafeArea())
            .navigationTitle(viewModel.pendingTicker ?? "New Position")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private var primaryProgressMessage: String {
        viewModel.progressValue >= 1.0 ? "Analysis complete" : viewModel.progressMessage
    }

    private var progressDescription: String {
        if let pendingTicker = viewModel.pendingTicker {
            return "\(pendingTicker) was added. Clavix is loading the latest cached ticker snapshot."
        }
        return "Preparing your new holding."
    }

    private var progressGrade: String {
        if viewModel.progressValue >= 1.0 { return "A" }
        if viewModel.progressValue >= 0.6 { return "B" }
        if viewModel.progressValue >= 0.3 { return "C" }
        return "D"
    }

    private var progressStageText: String {
        if viewModel.progressValue >= 1.0 { return "POSITION READY" }
        switch viewModel.progressMessage {
        case let m where m.contains("Adding"):      return "CREATING POSITION"
        case let m where m.contains("cached ticker snapshot"): return "LOADING SHARED CACHE"
        case let m where m.contains("ready"):       return "POSITION READY"
        default:                                     return "UPDATING POSITION"
        }
    }
}

struct WatchlistCardRow: View {
    let item: WatchlistItem
    var showsDivider: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .center, spacing: 12) {
                GradeTag(grade: item.grade ?? "C")

                VStack(alignment: .leading, spacing: 3) {
                    Text(item.ticker)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(.textPrimary)

                    Text(item.companyName ?? "Cached S&P ticker")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .lineLimit(2)
                }

                Spacer(minLength: 12)

                Text(item.safetyScore.map { "\(Int($0.rounded()))" } ?? "--")
                    .font(.system(size: 15, weight: .semibold, design: .monospaced))
                    .foregroundColor(.textPrimary)
                    .monospacedDigit()
            }

            if showsDivider {
                Divider()
                    .overlay(Color.border)
            }
        }
        .padding(.vertical, 10)
    }
}

// Keep AnimatedProgressBar defined for any remaining references
struct AnimatedProgressBar: View {
    let progress: Double
    let shimmerPhase: CGFloat

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(Color.border).frame(height: 4)
                Rectangle()
                    .fill(Color.riskB)
                    .frame(width: geo.size.width * CGFloat(min(max(progress, 0), 1)), height: 4)
                    .animation(.spring(response: 0.5, dampingFraction: 0.82), value: progress)
            }
        }
        .frame(height: 4)
    }
}
