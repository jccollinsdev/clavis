import SwiftUI

private enum HoldingsDetailRoute: Hashable {
    case ticker(String)
    case position(String)
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
    @State private var selectedSort: HoldingSort = .grade
    @State private var selectedFilter: HoldingFilter = .all
    @State private var deleteTickerCandidate: Position?
    @State private var navigationPath: [HoldingsDetailRoute] = []

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

    private var riskyCount: Int {
        viewModel.holdings.filter { $0.riskGrade == "D" || $0.riskGrade == "F" }.count
    }

    private var improvingCount: Int {
        viewModel.holdings.filter { $0.riskTrend == .improving }.count
    }

    var body: some View {
        NavigationStack(path: $navigationPath) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if NetworkStatusMonitor.shared.isOffline {
                        OfflineStatusBanner()
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    if viewModel.isLoading && viewModel.holdings.isEmpty {
                        ClavisLoadingCard(title: "Loading holdings", subtitle: "Pulling your holdings and the latest scores.")
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
                                HStack(spacing: 10) {
                                    Text("Watchlist")
                                        .font(ClavisTypography.inter(16, weight: .heavy))
                                        .foregroundColor(.textPrimary)
                                    Text("\(viewModel.watchlistItems.count)")
                                        .font(ClavisTypography.inter(13, weight: .semibold))
                                        .foregroundColor(.textSecondary)
                                        .frame(width: 24, height: 24)
                                        .background(Color.surfaceElevated)
                                        .clipShape(Circle())
                                }

                                PrototypeHoldingsSection {
                                    ForEach(Array(viewModel.watchlistItems.enumerated()), id: \.element.id) { index, item in
                                        NavigationLink(value: HoldingsDetailRoute.ticker(item.ticker)) {
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
                                HStack(spacing: 10) {
                                    Text("Needs Attention")
                                        .font(ClavisTypography.inter(16, weight: .heavy))
                                        .foregroundColor(.textPrimary)
                                    Text("\(needsReviewPositions.count)")
                                        .font(ClavisTypography.inter(13, weight: .semibold))
                                        .foregroundColor(.riskD)
                                        .frame(width: 24, height: 24)
                                        .background(Color.riskD.opacity(0.12))
                                        .clipShape(Circle())
                                }

                                VStack(alignment: .leading, spacing: 0) {
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
                            HStack(spacing: 10) {
                                Text("All Holdings")
                                    .font(ClavisTypography.inter(16, weight: .heavy))
                                    .foregroundColor(.textPrimary)
                                Text("\(sortedHoldings.count)")
                                    .font(ClavisTypography.inter(13, weight: .semibold))
                                    .foregroundColor(.textSecondary)
                                    .frame(width: 24, height: 24)
                                    .background(Color.surfaceElevated)
                                    .clipShape(Circle())
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
                .padding(.top, 0)
                .padding(.bottom, ClavisTheme.floatingTabHeight + ClavisTheme.floatingTabInset + ClavisTheme.extraLargeSpacing)
            }
            .safeAreaInset(edge: .top, spacing: 0) {
                VStack(spacing: 0) {
                    HoldingsTopHeader(
                        onAddPosition: { viewModel.showAddSheet = true },
                        onRefresh: { Task { await viewModel.refreshHoldings() } },
                        isRefreshing: viewModel.isRefreshing,
                        isOffline: NetworkStatusMonitor.shared.isOffline,
                        lastRefreshedAt: viewModel.lastRefreshedAt,
                        brokerageLastSyncedAt: viewModel.brokerageLastSyncedAt
                    )
                    HoldingsSearchBar(query: $searchQuery)
                }
            }
            .contentMargins(.top, 0, for: .scrollContent)
            .contentMargins(.bottom, 0, for: .scrollContent)
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
            .fullScreenCover(isPresented: $viewModel.showProgressSheet) {
                AddPositionProgressView(viewModel: viewModel)
            }
            .alert("Error", isPresented: $viewModel.showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(viewModel.errorMessage ?? "Unknown error")
            }
            .alert("Delete holding?", isPresented: Binding(get: { deleteTickerCandidate != nil }, set: { if !$0 { deleteTickerCandidate = nil } })) {
                Button("Delete", role: .destructive) {
                    if let candidate = deleteTickerCandidate {
                        Task { await viewModel.deleteHolding(candidate) }
                    }
                    deleteTickerCandidate = nil
                }
                Button("Cancel", role: .cancel) { deleteTickerCandidate = nil }
            } message: {
                Text("This removes the holding from your portfolio.")
            }
            .onAppear {
                viewModel.showError = false
                if viewModel.holdings.isEmpty && !viewModel.isLoading {
                    Task { await viewModel.loadHoldings() }
                } else if !viewModel.isLoading {
                    Task { await viewModel.refreshWatchlist() }
                }
            }
            .onChange(of: deepLinkTicker) { _, newValue in
                guard let newValue else { return }
                navigationPath = [.ticker(newValue)]
                deepLinkTicker = nil
            }
            .navigationDestination(for: HoldingsDetailRoute.self) { route in
                switch route {
                case .ticker(let ticker):
                    TickerDetailView(ticker: ticker)
                case .position(let positionId):
                    PositionDetailView(positionId: positionId)
                }
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
                let results = try await viewModel.searchTickers(query: trimmed, limit: 10)
                guard !Task.isCancelled else { return }
                tickerSearchResults = prioritizedSearchResults(results, query: trimmed)
            } catch is CancellationError {
                return
            } catch {
                tickerSearchResults = []
                tickerSearchError = ClavisCopy.Errors.tickerSearch(error)
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
            tickerSearchError = ClavisCopy.Errors.watchlistUpdate(error)
        }
    }

    private var needsReviewPositions: [Position] {
        sortedHoldings.filter {
            $0.riskGrade == "D" || $0.riskGrade == "F" || $0.riskTrend == .worsening
        }
    }

    @ViewBuilder
    private func holdingRow(for position: Position, isLast: Bool) -> some View {
        PositionCardRow(
            position: position,
            showsDivider: !isLast,
            onOpenDetail: { navigationPath.append(.position(position.id)) }
        )
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

            let supportedResults = Array(results.filter { $0.isSupported }.prefix(3))
            let exactMatch = results.first { $0.ticker.caseInsensitiveCompare(query) == .orderedSame }
            let isUnsupportedExactTicker = exactMatch != nil && exactMatch?.isSupported == false

            if let errorMessage {
                Text(errorMessage)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.riskF)
            } else if !isSearching && (results.isEmpty || isUnsupportedExactTicker) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Unsupported ticker")
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.riskF)
                    Text("No analysis available for \(query.uppercased()) yet.")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }
            }

            ForEach(Array(supportedResults.enumerated()), id: \.element.id) { index, result in
                HoldingsTickerSearchResultRow(
                    result: result,
                    isWatchlisted: watchlistedTickers.contains(result.ticker.uppercased()),
                    showsDivider: index < supportedResults.count - 1,
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
                        GradeBadge(grade: result.grade ?? "—", size: .compact)
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
    let lastRefreshedAt: Date?
    let brokerageLastSyncedAt: Date?

    var body: some View {
        ClavixPageHeader(
            title: "Holdings",
            subtitle: holdingsSubtitle
        ) {
            HStack(spacing: 6) {
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
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.top, 8)
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

    private var holdingsSubtitle: String? {
        var parts: [String] = []

        if let lastRefreshedAt {
            parts.append("Updated \(lastRefreshedAt.formatted(date: .abbreviated, time: .omitted))")
        }

        if let brokerageLastSyncedAt {
            parts.append("Brokerage sync \(brokerageLastSyncedAt.formatted(date: .abbreviated, time: .omitted))")
        }

        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }
}

private struct HoldingsHeaderButton: View {
    let systemName: String

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: 16, weight: .medium))
            .foregroundColor(.textPrimary)
            .frame(width: 32, height: 32)
    }
}

private struct HoldingsSearchBar: View {
    @Binding var query: String

    var body: some View {
        ClavisRaisedControlSurface(padding: 12) {
            HStack(spacing: 10) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 15, weight: .medium))
                    .foregroundColor(.textSecondary)

                TextField("Search ticker or company", text: $query)
                    .font(.system(size: 15, weight: .regular))
                    .foregroundColor(.textPrimary)
                    .autocorrectionDisabled()
            }
        }
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

struct HoldingsControlCard: View {
    @Binding var selectedFilter: HoldingFilter
    @Binding var selectedSort: HoldingSort
    let isRefreshing: Bool
    let onRefresh: () -> Void

    var body: some View {
        VStack(spacing: 14) {
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
                Menu {
                    ForEach(HoldingSort.allCases, id: \.self) { sort in
                        Button(sort.rawValue) {
                            selectedSort = sort
                        }
                    }
                } label: {
                    HStack(spacing: 4) {
                        Text("Sort:")
                            .font(.system(size: 13, weight: .regular))
                            .foregroundColor(Color(hex: "#9DA5B4"))
                        Text(selectedSort.rawValue)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundColor(.textPrimary)
                        Image(systemName: "chevron.down")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundColor(.textPrimary)
                    }
                }

                Spacer()

                Button(action: onRefresh) {
                    HStack(spacing: 6) {
                        Image(systemName: isRefreshing ? "hourglass" : "arrow.clockwise")
                            .font(.system(size: 12, weight: .semibold))
                        Text(isRefreshing ? "Refreshing" : "Refresh")
                            .font(.system(size: 13, weight: .bold))
                    }
                    .foregroundColor(Color(hex: "#F0C76C"))
                }
                .buttonStyle(.plain)
                .disabled(isRefreshing)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 12)
            .background(Color(hex: "#0D1119").opacity(0.62))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(Color(hex: "#242934").opacity(0.5), lineWidth: 1)
            )
        }
    }

    @ViewBuilder
    private func controlPill(title: String, isSelected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 13, weight: isSelected ? .semibold : .medium))
                .foregroundColor(isSelected ? Color(hex: "#121313") : Color(hex: "#B6BDCA"))
                .padding(.horizontal, 16)
                .padding(.vertical, 7)
                .background(isSelected ? LinearGradient(colors: [Color(hex: "#FFE8A8"), Color(hex: "#EABF57")], startPoint: .topLeading, endPoint: .bottomTrailing) : LinearGradient(colors: [Color.surfaceElevated.opacity(0.02), Color.surfaceElevated.opacity(0.02)], startPoint: .top, endPoint: .bottom))
                .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 11, style: .continuous)
                        .stroke(isSelected ? Color.clear : Color(hex: "#242934").opacity(0.5), lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
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
        ClavisStandardCard(fill: .surface) {
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
        }
    }
}

struct PositionCardRow: View {
    let position: Position
    var showsDivider: Bool = false
    let onOpenDetail: () -> Void

    private var grade: String {
        position.riskGrade ?? "—"
    }

    private var scoreText: String {
        if let score = position.totalScore {
            return "\(Int(score.rounded()))"
        }
        return "--"
    }

    private var subtitleText: String {
        if let state = position.analysisState {
            switch state {
            case "queued", "running":
                return position.coverageNote ?? "Updating this holding now."
            case "failed":
                return position.coverageNote ?? "Analysis incomplete. Showing the latest available data."
            case "stale":
                return position.coverageNote ?? "Refreshing with newer market data."
            case "thin":
                return position.coverageNote ?? "Limited recent data available."
            default:
                break
            }
        }
        if let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
            return Self.previewSummary(summary)
        }
        if position.analysisStartedAt != nil && position.riskGrade == nil {
            return "Updating this holding now. Scores will appear shortly."
        }
        return "Analysis pending."
    }

    var body: some View {
        VStack(spacing: 0) {
            Button(action: onOpenDetail) {
                HStack(alignment: .center, spacing: 12) {
                    GradeBadge(grade: grade)

                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 8) {
                            Text(position.ticker)
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundColor(.textPrimary)

                            Text(position.archetype.displayName)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)
                                .lineLimit(1)
                                .minimumScaleFactor(0.85)

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
                            .fixedSize(horizontal: false, vertical: true)

                        HStack(spacing: 6) {
                            if let evidence = position.evidenceStrength {
                                EvidenceDots(evidence: evidence, grade: grade)
                            }
                            ScoreSourceChip(source: position.scoreSource)
                            FreshnessChip(date: position.scoreAsOf ?? position.analysisAsOf)
                        }
                    }

                    Spacer(minLength: 12)

                    VStack(alignment: .trailing, spacing: 4) {
                        if let trend = position.riskTrend {
                            RiskDirectionLabel(trend: trend)
                        }

                        Text(scoreText)
                            .font(.system(size: 15, weight: .semibold, design: .monospaced))
                            .foregroundColor(.textSecondary)
                            .monospacedDigit()
                    }
                }
            }
            .buttonStyle(.plain)

            if showsDivider {
                Divider()
                    .overlay(Color.border)
            }
        }
        .padding(.vertical, 13)
    }

    private static func previewSummary(_ summary: String, wordLimit: Int = 15) -> String {
        let words = summary.split { $0.isWhitespace }
        guard words.count > wordLimit else { return summary }
        return words.prefix(wordLimit).joined(separator: " ") + "..."
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
                Text("Add your first holding to start tracking downside risk and portfolio updates.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)

                ClavisPrimaryButton(title: "Add holding", action: onAddPosition)
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
    @State private var tickerSuggestions: [TickerSearchResult] = []
    @State private var isSearchingSuggestions = false
    @State private var isTickerSupported = false
    @State private var supportMessage: String?
    @State private var shares = ""
    @State private var purchasePrice = ""
    @State private var archetype: Archetype = .growth
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var resolveTickerTask: Task<Void, Never>?

    private var isFormValid: Bool {
        isTickerSupported && !shares.isEmpty && Double(shares) != nil && !purchasePrice.isEmpty && Double(purchasePrice) != nil
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Position") {
                    TextField("Ticker (e.g., AAPL)", text: $ticker)
                        .textCase(.uppercase)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                        .onChange(of: ticker) { _, newValue in
                            resolveTickerTask?.cancel()
                            resolveTickerTask = Task { await resolveTicker(newValue) }
                        }

                    if isSearchingSuggestions {
                        ProgressView()
                    }

                    if !companyName.isEmpty {
                        Text(companyName)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }

                    if let supportMessage {
                        Text(supportMessage)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.riskF)
                    }

                    if !tickerSuggestions.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Top matches")
                                .font(ClavisTypography.label)
                                .foregroundColor(.textSecondary)

                            ForEach(Array(tickerSuggestions.prefix(3)), id: \.ticker) { suggestion in
                                Button {
                                    resolveTickerTask?.cancel()
                                    ticker = suggestion.ticker
                                    companyName = suggestion.companyName
                                    tickerSuggestions = []
                                    supportMessage = nil
                                    isTickerSupported = suggestion.isSupported
                                } label: {
                                    HStack(spacing: 10) {
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(suggestion.ticker)
                                                .font(ClavisTypography.bodyEmphasis)
                                                .foregroundColor(.textPrimary)
                                            Text(suggestion.companyName)
                                                .font(ClavisTypography.footnote)
                                                .foregroundColor(.textSecondary)
                                        }

                                        Spacer()

                                        GradeBadge(grade: suggestion.grade ?? "—", size: .compact)
                                    }
                                    .padding(.vertical, 8)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }

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
            errorMessage = viewModel.errorMessage ?? "Unable to add holding."
            showError = true
        }
    }

    private func resolveTicker(_ query: String) async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 1 else {
            companyName = ""
            tickerSuggestions = []
            supportMessage = nil
            isTickerSupported = false
            isSearchingSuggestions = false
            return
        }

        isSearchingSuggestions = true

        do {
            // Debounce: wait before hitting the network, matching the main search behaviour.
            try await Task.sleep(nanoseconds: 200_000_000)
            guard !Task.isCancelled else { isSearchingSuggestions = false; return }

            let results = try await viewModel.searchTickers(query: trimmed, limit: 10)
            guard !Task.isCancelled else { isSearchingSuggestions = false; return }

            let exactMatch = results.first { $0.ticker.caseInsensitiveCompare(trimmed) == .orderedSame }

            if let exactMatch, exactMatch.isSupported {
                // Exact supported match — resolve immediately, no need to show suggestions.
                companyName = exactMatch.companyName
                tickerSuggestions = []
                supportMessage = nil
                isTickerSupported = true
            } else {
                companyName = ""
                isTickerSupported = false
                tickerSuggestions = Array(results.filter { $0.isSupported }.prefix(3))
                supportMessage = (results.isEmpty || exactMatch?.isSupported == false)
                    ? "This ticker is not supported yet."
                    : nil
            }
        } catch is CancellationError {
            // A newer keystroke cancelled this task — leave state as-is.
        } catch {
            companyName = ""
            tickerSuggestions = []
            supportMessage = "Unable to check ticker support right now."
            isTickerSupported = false
        }

        isSearchingSuggestions = false
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
                    ZStack {
                        RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                            .fill(Color.surface)
                            .frame(width: 80, height: 80)
                            .overlay(
                                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                                    .stroke(Color.border, lineWidth: 1)
                            )

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
                .overlay(
                    RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                        .stroke(Color.border, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))

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
        if viewModel.progressValue >= 1.0 {
            let lower = viewModel.progressMessage.lowercased()
            if lower.contains("failed") || lower.contains("limited") {
                return viewModel.progressMessage
            }
            return "Analysis complete"
        }
        return viewModel.progressMessage
    }

    private var progressDescription: String {
        if let pendingTicker = viewModel.pendingTicker {
            let lower = viewModel.progressMessage.lowercased()
            if lower.contains("failed") || lower.contains("limited") {
                return viewModel.progressMessage
            }
            if viewModel.progressValue >= 1.0 {
                return "\(pendingTicker) now has the latest available analysis."
            }
            return viewModel.progressMessage
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
        case let m where m.contains("limited"):     return "LIMITED DATA"
        case let m where m.contains("running"):     return "ANALYSIS RUNNING"
        case let m where m.contains("ready"):       return "POSITION READY"
        case let m where m.contains("failed"):      return "ANALYSIS FAILED"
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
                GradeBadge(grade: item.grade ?? "—")

                VStack(alignment: .leading, spacing: 3) {
                    Text(item.ticker)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(.textPrimary)

                    Text(item.companyName ?? "Tracked symbol")
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
