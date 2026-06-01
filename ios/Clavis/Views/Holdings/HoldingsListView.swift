import SwiftUI

extension Notification.Name {
    static let openAddHoldingFromOnboarding = Notification.Name("openAddHoldingFromOnboarding")
    static let holdingsDidChange = Notification.Name("holdingsDidChange")
    static let watchlistDidChange = Notification.Name("watchlistDidChange")
}

private enum HoldingsSortKey {
    case weight
    case grade
    case dayChange
    case profitLoss
}

struct HoldingsListView: View {
    @Binding var selectedTab: Int
    @Binding var deepLinkTicker: String?

    @StateObject private var viewModel = HoldingsViewModel()
    @StateObject private var brokerageViewModel = BrokerageViewModel()
    @State private var navigationPath: [String] = []
    @State private var deleteCandidate: Position?
    @State private var showUpgradeSheet = false
    @State private var showAddHoldingSheet = false
    @State private var sortKey: HoldingsSortKey = .weight

    private var totalMarketValue: Double {
        viewModel.holdings.compactMap(\.currentValue).reduce(0, +)
    }

    private var sortedHoldings: [Position] {
        viewModel.holdings.sorted { lhs, rhs in
            switch sortKey {
            case .weight:
                return (lhs.currentValue ?? 0) > (rhs.currentValue ?? 0)
            case .grade:
                return (lhs.resolvedTotalScore ?? 0) > (rhs.resolvedTotalScore ?? 0)
            case .dayChange:
                return abs(lhs.sharedAnalysis?.dayChangePct ?? 0) > abs(rhs.sharedAnalysis?.dayChangePct ?? 0)
            case .profitLoss:
                return (lhs.unrealizedPL ?? 0) > (rhs.unrealizedPL ?? 0)
            }
        }
    }

    private var weightedScore: Double? {
        PortfolioMath.weightedScore(viewModel.holdings)
    }

    private var weightedGrade: String {
        PortfolioMath.weightedGrade(viewModel.holdings)
    }

    private var biggestMover: Position? {
        sortedHoldings.max { abs($0.scoreDelta ?? 0) < abs($1.scoreDelta ?? 0) }
    }

    private var isFreeTier: Bool {
        viewModel.subscriptionTier == "free"
    }

    private var isInitialHydration: Bool {
        viewModel.isLoading && viewModel.holdings.isEmpty
    }

    var body: some View {
        NavigationStack(path: $navigationPath) {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    bookHero
                    positionsSection
                    watchlistSection
                    sectorCompositionSection
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.sectionSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .safeAreaInset(edge: .top, spacing: 0) {
                ClavixStickyBar(trailing: AnyView(
                    HStack(spacing: 18) {
                        Button(action: { sortKey = sortKey == .weight ? .grade : .weight }) {
                            Image(systemName: "slider.horizontal.3")
                                .foregroundColor(.clavixInk)
                        }
                        .buttonStyle(.plain)
                        Button(action: openAddHolding) {
                            Image(systemName: "plus")
                                .foregroundColor(.clavixInk)
                        }
                        .buttonStyle(.plain)
                    }
                ))
            }
            .toolbar(.hidden, for: .navigationBar)
            .task {
                await viewModel.loadHoldings()
            }
            .onAppear {
                Task { await viewModel.refreshWatchlist() }
            }
            .refreshable {
                await viewModel.refreshHoldings()
            }
            .onChange(of: deepLinkTicker) { newValue in
                guard let ticker = newValue else { return }
                deepLinkTicker = nil
                navigationPath.append(ticker)
            }
            .sheet(isPresented: $showAddHoldingSheet) {
                HoldingsAddMethodSheet(
                    viewModel: viewModel,
                    brokerageViewModel: brokerageViewModel,
                    selectedTab: $selectedTab
                )
            }
            .sheet(
                isPresented: Binding(
                    get: { brokerageViewModel.presentedURL != nil },
                    set: { if !$0 { brokerageViewModel.presentedURL = nil } }
                )
            ) {
                if let url = brokerageViewModel.presentedURL {
                    SafariView(url: url)
                }
            }
            .fullScreenCover(isPresented: $viewModel.showProgressSheet) {
                AddPositionProgressView(viewModel: viewModel)
            }
            .sheet(isPresented: $showUpgradeSheet) {
                HoldingsUpgradeSheet()
            }
            .sheet(item: $deleteCandidate) { position in
                HoldingDeleteSheet(
                    ticker: position.ticker,
                    onDelete: {
                        Task { await viewModel.deleteHolding(position) }
                        deleteCandidate = nil
                    },
                    onKeep: {
                        deleteCandidate = nil
                    }
                )
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
            .onReceive(NotificationCenter.default.publisher(for: .watchlistDidChange)) { _ in
                Task { await viewModel.refreshWatchlist() }
            }
        }
    }

    // MARK: - Book hero

    private var bookHero: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Your Book")
                .font(ClavisTypography.clavixSerif(34, weight: .medium))
                .tracking(-0.6)
                .foregroundColor(.clavixInk)

            HStack(alignment: .bottom, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Portfolio value")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                    Text(totalMarketValue > 0 ? currencyNoCents(totalMarketValue) : "—")
                        .font(ClavisTypography.clavixMono(29, weight: .semibold))
                        .tracking(-0.6)
                        .foregroundColor(.clavixInk)
                        .lineLimit(1)
                        .minimumScaleFactor(0.76)
                    if let stamp = syncStampText {
                        Text(stamp)
                            .font(ClavisTypography.clavixMono(10, weight: .regular))
                            .tracking(0.7)
                            .foregroundColor(.clavixInk3)
                    }
                    Text(holdingsSummaryText)
                        .font(ClavisTypography.clavixMono(10, weight: .regular))
                        .tracking(0.3)
                        .foregroundColor(.clavixInk3)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    ClavixGradeBadge(weightedGrade)
                    Text(weightedScore.map { "Composite \(Int($0.rounded()))" } ?? "Composite —")
                        .font(ClavisTypography.clavixMono(11, weight: .regular))
                        .foregroundColor(.clavixInk3)
                }
            }
        }
        .padding(.bottom, 14)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.clavixRule).frame(height: 1) }
    }

    private var syncStampText: String? {
        if isInitialHydration {
            return "SYNCING LATEST BOOK"
        }
        if let ts = viewModel.brokerageLastSyncedAt {
            let stamp = ts.formatted(date: .omitted, time: .shortened)
            return "SYNCED \(stamp.uppercased()) · BROKERAGE"
        }
        if let ts = viewModel.lastRefreshedAt {
            let dateText = ts.formatted(date: .abbreviated, time: .omitted)
            return "UPDATED \(dateText.uppercased())"
        }
        return nil
    }

    private var holdingsSummaryText: String {
        if isInitialHydration {
            return "Loading positions and watchlist"
        }

        let holdingsCount = viewModel.holdings.count
        return "\(holdingsCount) position\(holdingsCount == 1 ? "" : "s") · \(viewModel.watchlistItems.count) tracked"
    }

    // MARK: - Sort toolbar

    private var holdingsToolbar: some View {
        HStack(spacing: 4) {
            toolbarPill(label: "Weight", key: .weight)
            toolbarPill(label: "Grade", key: .grade)
            toolbarPill(label: "Δ Today", key: .dayChange)
            toolbarPill(label: "P&L", key: .profitLoss)
            Spacer()
        }
    }

    @ViewBuilder
    private var holdingsSection: some View {
        if viewModel.isLoading && viewModel.holdings.isEmpty {
            ClavisLoadingCard(title: "Loading holdings", subtitle: "Pulling your latest positions and ratings.")
        } else if viewModel.holdings.isEmpty {
            HoldingsEmptyState(onAddPosition: openAddHolding)
        } else {
            ClavixCard(padding: 0) {
                VStack(spacing: 0) {
                    HStack(spacing: 8) {
                        ClavixColumnHeader("Sym · w%")
                            .frame(width: 70, alignment: .leading)
                        ClavixColumnHeader("Price · day")
                            .frame(maxWidth: .infinity, alignment: .leading)
                        ClavixColumnHeader("P&L", align: .trailing)
                            .frame(width: 70, alignment: .trailing)
                        ClavixColumnHeader("Grade · Δ", align: .trailing)
                            .frame(width: 60, alignment: .trailing)
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(Color.clavixPaper2)
                    Rectangle().fill(Color.clavixRule).frame(height: 1)
                    ForEach(Array(sortedHoldings.enumerated()), id: \.element.id) { index, position in
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
                        if index < sortedHoldings.count - 1 {
                            Rectangle().fill(Color.clavixRule2).frame(height: 1)
                        }
                    }
                }
            }
        }
    }

    private var watchlistSection: some View {
        simpleSection(
            title: "Watchlist",
            trailing: AnyView(
                Button("Add ticker →") { selectedTab = 2 }
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixAccent)
                    .buttonStyle(.plain)
            )
        ) {
            if isInitialHydration && viewModel.watchlistItems.isEmpty {
                ClavisLoadingCard(title: "Loading watchlist", subtitle: "Checking the tickers you already track.")
            } else if viewModel.watchlistItems.isEmpty {
                ClavixCard {
                    Text("Track tickers here to monitor grade and price changes alongside your positions.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                        .fixedSize(horizontal: false, vertical: true)
                }
            } else {
                ClavixCard(padding: 0) {
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
    private var sectorCompositionSection: some View {
        if !viewModel.holdings.isEmpty {
            simpleSection(title: "Grade Map") {
                ClavixCard(padding: 0) {
                    PositionHeatmapView(positions: sortedHoldings)
                        .frame(height: PositionHeatmapView.height(for: sortedHoldings.count))
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
            }
        }
    }

    // MARK: - Positions section

    private var positionsSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Your Positions")
                .font(ClavisTypography.clavixSerif(20, weight: .medium))
                .tracking(-0.3)
                .foregroundColor(.clavixInk)
                .padding(.top, 6)
                .padding(.bottom, 10)
            holdingsToolbar
                .padding(.bottom, 10)
            holdingsSection
        }
    }

    private func simpleSection<Content: View>(
        title: String,
        trailing: AnyView? = nil,
        @ViewBuilder content: @escaping () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text(title)
                    .font(ClavisTypography.clavixSerif(20, weight: .medium))
                    .tracking(-0.3)
                    .foregroundColor(.clavixInk)
                Spacer()
                if let trailing {
                    trailing
                }
            }
            content()
        }
        .padding(.top, 6)
    }

    private var sectorRows: [SectorHoldingsRow] {
        guard totalMarketValue > 0 else { return [] }

        struct Bucket {
            var positions: [Position] = []
            var value: Double = 0
        }

        var buckets: [String: Bucket] = [:]
        for position in viewModel.holdings {
            guard let value = position.currentValue, value > 0 else { continue }
            let sector = normalizedSectorName(position.sharedAnalysis?.sector)
            var bucket = buckets[sector, default: Bucket()]
            bucket.positions.append(position)
            bucket.value += value
            buckets[sector] = bucket
        }

        return buckets
            .map { sector, bucket in
                let tickers = bucket.positions
                    .map(\.ticker)
                    .sorted()
                    .joined(separator: " · ")
                let grade = PortfolioMath.weightedGrade(bucket.positions)
                return SectorHoldingsRow(
                    name: sector,
                    weightPct: Int(((bucket.value / totalMarketValue) * 100).rounded()),
                    grade: grade,
                    tickers: tickers
                )
            }
            .sorted { $0.weightPct > $1.weightPct }
    }

    private func normalizedSectorName(_ raw: String?) -> String {
        guard let value = raw?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty else {
            return "Unclassified"
        }
        switch value.lowercased() {
        case "tech":
            return "Technology"
        case "consumer discretionary":
            return "Consumer Disc."
        case "consumer staples":
            return "Consumer Staples"
        case "communication services":
            return "Communication Svcs"
        case "us total market":
            return "US Total Market"
        default:
            return value
        }
    }

    private func toolbarPill(label: String, key: HoldingsSortKey) -> some View {
        Button {
            sortKey = key
        } label: {
            ClavixPill(label: label, active: sortKey == key)
        }
        .buttonStyle(.plain)
    }

    private func openAddHolding() {
        if isFreeTier && viewModel.holdings.count >= 3 {
            showUpgradeSheet = true
        } else {
            showAddHoldingSheet = true
        }
    }

    private func currencyNoCents(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "—"
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

            // Price · day
            VStack(alignment: .leading, spacing: 3) {
                Text(currencyDecimal(position.resolvedCurrentPrice))
                    .font(ClavisTypography.clavixMono(13, weight: .semibold))
                    .foregroundColor(.clavixInk)
                Text(dayText)
                    .font(ClavisTypography.clavixMono(10, weight: .semibold))
                    .foregroundColor(dayTone)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // P&L
            VStack(alignment: .trailing, spacing: 3) {
                Text(pnlText)
                    .font(ClavisTypography.clavixMono(13, weight: .semibold))
                    .foregroundColor(pnlColor)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
                Text(pnlPctText)
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk3)
                    .lineLimit(1)
            }
            .frame(width: 82, alignment: .trailing)

            // Grade · Δ
            VStack(alignment: .trailing, spacing: 2) {
                ClavixGradeBadge(grade, size: 18)
                Text(deltaText)
                    .font(ClavisTypography.clavixMono(10, weight: .semibold))
                    .foregroundColor(deltaColor)
            }
            .frame(width: 60, alignment: .trailing)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity)
        .background(highlighted ? Color.clavixAccentSoft : Color.clear)
        .overlay(alignment: .leading) {
            if highlighted { Rectangle().fill(Color.clavixAccent).frame(width: 3) }
        }
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

private struct SectorHoldingsRow {
    let name: String
    let weightPct: Int
    let grade: String
    let tickers: String
}

private struct SectorCompositionRow: View {
    let row: SectorHoldingsRow

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .center, spacing: 10) {
                Text(row.name)
                    .font(ClavisTypography.inter(15, weight: .semibold))
                    .foregroundColor(.clavixInk)
                    .lineLimit(1)
                Spacer()
                Text("\(row.weightPct)%")
                    .font(ClavisTypography.clavixMono(11, weight: .semibold))
                    .foregroundColor(.clavixInk3)
                ClavixGradeBadge(row.grade, size: 18)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 3, style: .continuous)
                        .fill(Color.clavixRule2)
                    RoundedRectangle(cornerRadius: 3, style: .continuous)
                        .fill(barTone)
                        .frame(width: geo.size.width * CGFloat(row.weightPct) / 100.0)
                }
            }
            .frame(height: 6)

            Text(row.tickers)
                .font(ClavisTypography.clavixCaption)
                .foregroundColor(.clavixInk3)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var barTone: Color {
        switch row.grade {
        case "AAA", "AA":
            return .clavixGood
        case "A":
            return .clavixAccent
        case "BBB", "BB":
            return .clavixWarn
        case "—":
            return .clavixInk4
        default:
            return .clavixBad
        }
    }
}

private struct WatchlistRow: View {
    let item: WatchlistItem

    private var dayPct: Double? { item.sharedAnalysis?.dayChangePct }

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

    private var deltaText: String {
        guard let delta = item.sharedAnalysis?.scoreDelta, delta != 0 else { return "—" }
        return delta > 0 ? "▲ \(delta)" : "▼ \(abs(delta))"
    }

    private var deltaColor: Color {
        guard let delta = item.sharedAnalysis?.scoreDelta else { return .clavixInk3 }
        if delta > 0 { return .clavixGood }
        if delta < 0 { return .clavixBad }
        return .clavixInk3
    }

    var body: some View {
        HStack(spacing: 8) {
            VStack(alignment: .leading, spacing: 3) {
                Text(item.ticker)
                    .font(ClavisTypography.clavixMono(13, weight: .bold))
                    .foregroundColor(.clavixInk)
                Text(item.resolvedCompanyName ?? "Tracked symbol")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
                    .lineLimit(1)
            }
            .frame(width: 84, alignment: .leading)

            VStack(alignment: .leading, spacing: 3) {
                Text(item.price.map { currency($0) } ?? "—")
                    .font(ClavisTypography.clavixMono(13, weight: .semibold))
                    .foregroundColor(.clavixInk)
                Text(dayText)
                    .font(ClavisTypography.clavixMono(10, weight: .semibold))
                    .foregroundColor(dayTone)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .trailing, spacing: 2) {
                ClavixGradeBadge(item.resolvedGrade ?? "—", size: 18)
                Text(deltaText)
                    .font(ClavisTypography.clavixMono(10, weight: .semibold))
                    .foregroundColor(deltaColor)
            }
            .frame(width: 60, alignment: .trailing)
        }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
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
        HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(result.ticker)
                    .font(ClavisTypography.clavixMono(13, weight: .bold))
                    .foregroundColor(.clavixInk)
                Text(result.resolvedCompanyName ?? result.companyName)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
                    .lineLimit(1)
            }

            Spacer(minLength: 12)

            VStack(alignment: .trailing, spacing: 6) {
                HStack(spacing: 6) {
                    if !result.isSupported {
                        SearchTag(text: "OUTSIDE", foreground: .clavixWarnInk, background: .clavixWarnSoft)
                    }

                    if isWatchlisted {
                        SearchTag(text: "WATCHING", foreground: .clavixAccentInk, background: .clavixAccentSoft)
                    }
                }

                HStack(spacing: 8) {
                    Text(result.price.map { currency($0) } ?? "—")
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(.clavixInk3)
                    ClavixGradeBadge(result.resolvedGrade ?? "—", size: 18)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
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
            .font(ClavisTypography.clavixMono(9, weight: .bold))
            .foregroundColor(foreground)
            .padding(.horizontal, 6)
            .padding(.vertical, 3)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
    }
}

private struct HoldingDeleteSheet: View {
    let ticker: String
    let onDelete: () -> Void
    let onKeep: () -> Void

    var body: some View {
        ClavixScreen(eyebrow: ticker, title: "Remove position") {
            ClavixCard(fill: .clavixBadSoft) {
                Text("Removing this position removes portfolio context for \(ticker). Ticker-level risk data remains available through Search.")
                    .font(ClavisTypography.inter(14, weight: .regular))
                    .foregroundColor(.clavixInk2)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HoldingsSheetButton(
                title: "Remove position",
                fill: .clavixBad,
                action: onDelete
            )

            HoldingsSheetButton(
                title: "Keep position",
                fill: .clavixPaper,
                foreground: .clavixInk,
                bordered: true,
                action: onKeep
            )
        }
    }
}

struct HoldingsEmptyState: View {
    let onAddPosition: () -> Void

    var body: some View {
        ClavixInlineNoticeCard(
            eyebrow: "Portfolio",
            title: "Add your first holding",
            message: "Start with the positions you follow most closely. Clavix builds the Morning Report around what actually sits in your book.",
            footnote: "If you are not ready to add a holding yet, you can still track names from Search and the Watchlist.",
            glyph: "briefcase",
            buttonTitle: "Add your first holding",
            action: onAddPosition
        )
    }
}

private struct HoldingsAddMethodSheet: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @ObservedObject var brokerageViewModel: BrokerageViewModel
    @Binding var selectedTab: Int
    @Environment(\.dismiss) private var dismiss
    @State private var showManualSheet = false
    @State private var showCSVSheet = false

    var body: some View {
        ClavixScreen(eyebrow: "Choose a method", title: "Add position") {
            HoldingsMethodCard(
                title: "Search the universe",
                description: "Type a ticker or company name. Available for tracked names.",
                icon: "magnifyingglass"
            ) {
                selectedTab = 2
                dismiss()
            }

            if FeatureFlags.brokerageEnabled {
                HoldingsMethodCard(
                    title: "Refresh from your brokerage",
                    description: brokerageViewModel.isConnected
                        ? "Connected brokerage can update share counts and cost data."
                        : "Connect your brokerage to pull positions read-only.",
                    icon: "arrow.clockwise",
                    badge: brokerageViewModel.isConnected ? "LIVE" : nil
                ) {
                    Task {
                        if brokerageViewModel.isConnected {
                            await brokerageViewModel.syncNow(refreshRemote: true)
                            await viewModel.refreshHoldings()
                        } else {
                            await brokerageViewModel.startConnect()
                        }
                    }
                }
            }

            HoldingsMethodCard(
                title: "Enter manually",
                description: "Ticker, shares, and cost basis.",
                icon: "plus"
            ) {
                showManualSheet = true
            }

            HoldingsMethodCard(
                title: "Upload CSV",
                description: "Map exported rows from major brokerages.",
                icon: "doc",
                badge: "PRO"
            ) {
                showCSVSheet = true
            }
        }
        .sheet(isPresented: $showManualSheet) {
            HoldingsAddSheet(viewModel: viewModel)
        }
        .sheet(isPresented: $showCSVSheet) {
            HoldingsCSVComingSoonSheet()
        }
    }
}

private struct HoldingsMethodCard: View {
    let title: String
    let description: String
    let icon: String
    var badge: String? = nil
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ClavixCard {
                HStack(spacing: 12) {
                    Image(systemName: icon)
                        .frame(width: 28)
                        .foregroundColor(.clavixAccent)

                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 8) {
                            Text(title)
                                .font(ClavisTypography.inter(15, weight: .semibold))
                                .foregroundColor(.clavixInk)
                            if let badge {
                                Text(badge)
                                    .font(ClavisTypography.clavixMono(9, weight: .bold))
                                    .foregroundColor(.clavixAccentInk)
                                    .padding(.horizontal, 5)
                                    .padding(.vertical, 2)
                                    .background(Color.clavixAccentSoft)
                                    .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
                            }
                        }

                        Text(description)
                            .font(ClavisTypography.clavixCaption)
                            .foregroundColor(.clavixInk2)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer()

                    Image(systemName: "chevron.right")
                        .font(.system(size: 11, weight: .regular))
                        .foregroundColor(.clavixInk4)
                }
            }
        }
        .buttonStyle(.plain)
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
    @State private var selectedTickerResult: TickerSearchResult?
    @State private var shares = ""
    @State private var costBasis = ""
    @State private var purchaseDate = Date()
    @State private var resolveTickerTask: Task<Void, Never>?

    private var isValid: Bool {
        selectedTickerResult != nil
            && !isDuplicateHeld
            && (Double(shares) ?? 0) > 0
            && (Double(costBasis) ?? 0) >= 0
    }

    private var isOutsideUniverseSelection: Bool {
        selectedTickerResult?.isSupported == false
    }

    private var isDuplicateHeld: Bool {
        viewModel.holdings.contains { $0.ticker.caseInsensitiveCompare(ticker) == .orderedSame }
    }

    var body: some View {
        ClavixScreen(
            eyebrow: isOutsideUniverseSelection ? "Outside universe" : "Manual entry",
            title: isOutsideUniverseSelection ? "Limited data" : "Add position",
            trailing: AnyView(
                Button("Close") { dismiss() }
                    .font(ClavisTypography.clavixMono(10, weight: .semibold))
                    .foregroundColor(.clavixAccent)
                    .buttonStyle(.plain)
            )
        ) {
            ClavixCard {
                VStack(spacing: 12) {
                    entryField(title: "Ticker", text: $ticker, keyboard: .default, autocapitalized: true)
                        .onChange(of: ticker) { newValue in
                            resolveTickerTask?.cancel()
                            selectedTickerResult = nil
                            resolveTickerTask = Task { await resolveTicker(newValue) }
                        }

                    entryField(title: "Shares", text: $shares, keyboard: .decimalPad)
                    entryField(title: "Cost basis", text: $costBasis, keyboard: .decimalPad)
                }
            }

            if isSearchingSuggestions {
                ProgressView()
                    .tint(.clavixInk)
                    .frame(maxWidth: .infinity, alignment: .center)
            }

            if !tickerSuggestions.isEmpty {
                ClavixCard(padding: 0, fill: .clavixPaper) {
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

            if !companyName.isEmpty {
                Text(companyName)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
            }

            if let tickerError {
                ClavixCard(fill: .clavixBadSoft) {
                    Text(tickerError.sanitizedDisplayText)
                        .font(ClavisTypography.inter(14, weight: .regular))
                        .foregroundColor(.clavixInk2)
                }
            }

            if isDuplicateHeld {
                ClavixCard(fill: .clavixAccentSoft) {
                    Text("\(ticker.uppercased()) is already in your portfolio.")
                        .font(ClavisTypography.inter(14, weight: .regular))
                        .foregroundColor(.clavixAccentInk)
                }
            }

            if isOutsideUniverseSelection {
                ClavixCard(fill: .clavixWarnSoft) {
                    Text("This ticker can be saved as portfolio metadata, but full risk data requires tracked-universe support.")
                        .font(ClavisTypography.inter(14, weight: .regular))
                        .foregroundColor(.clavixInk2)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            ClavixCard(fill: .clavixPaper2) {
                VStack(alignment: .leading, spacing: 8) {
                    ClavixEyebrow("Purchase date")
                    DatePicker("Purchase date", selection: $purchaseDate, displayedComponents: .date)
                        .datePickerStyle(.compact)
                        .labelsHidden()
                        .tint(.clavixAccent)
                    Text("Purchase date will be sent once the backend route supports it.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            }

            HoldingsSheetButton(
                title: isOutsideUniverseSelection ? "Save anyway as outside-universe" : "Save position",
                isEnabled: isValid,
                action: {
                    Task { await submit() }
                }
            )
        }
    }

    private func entryField(
        title: String,
        text: Binding<String>,
        keyboard: UIKeyboardType,
        autocapitalized: Bool = false
    ) -> some View {
        TextField(title, text: text)
            .font(ClavisTypography.inter(15, weight: .regular))
            .foregroundColor(.clavixInk)
            .textInputAutocapitalization(autocapitalized ? .characters : .never)
            .autocorrectionDisabled()
            .keyboardType(keyboard)
            .padding(.horizontal, 12)
            .frame(height: 48)
            .background(Color.clavixPaper2)
            .overlay(
                RoundedRectangle(cornerRadius: ClavixLayout.controlRadius)
                    .stroke(Color.clavixRule, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous))
    }

    private func resolveTicker(_ query: String) async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            tickerSuggestions = []
            tickerError = nil
            companyName = ""
            selectedTickerResult = nil
            return
        }

        isSearchingSuggestions = true
        do {
            try await Task.sleep(nanoseconds: 200_000_000)
            guard !Task.isCancelled else { return }
            let results = try await viewModel.searchTickers(query: trimmed, limit: 8)
            guard !Task.isCancelled else { return }

            let exactMatch = results.first { $0.ticker.caseInsensitiveCompare(trimmed) == .orderedSame }
            if let exactMatch {
                applySuggestion(exactMatch)
                tickerSuggestions = []
            } else {
                tickerSuggestions = results
                companyName = ""
                selectedTickerResult = nil
                tickerError = results.isEmpty ? "Ticker not found" : nil
            }
        } catch is CancellationError {
            return
        } catch {
            tickerSuggestions = []
            companyName = ""
            selectedTickerResult = nil
            tickerError = "Unable to validate ticker right now."
        }
        isSearchingSuggestions = false
    }

    private func applySuggestion(_ suggestion: TickerSearchResult) {
        ticker = suggestion.ticker
        companyName = suggestion.resolvedCompanyName ?? suggestion.companyName
        selectedTickerResult = suggestion
        tickerError = nil
    }

    private func submit() async {
        guard let sharesValue = Double(shares) else { return }
        let costBasisValue = Double(costBasis.trimmingCharacters(in: .whitespacesAndNewlines)) ?? 0
        await viewModel.addHolding(
            ticker: ticker.uppercased(),
            shares: sharesValue,
            purchasePrice: costBasisValue,
            allowOutsideUniverse: isOutsideUniverseSelection
        )
        if viewModel.errorMessage == nil {
            // Close the entire sheet rather than just popping the nav stack page.
            // dismiss() only goes back to the method picker; setting showAddSheet
            // directly closes the parent .sheet presentation.
            viewModel.showAddSheet = false
        }
    }
}

private struct HoldingsSheetButton: View {
    let title: String
    var isEnabled: Bool = true
    var fill: Color = .clavixInk
    var foreground: Color? = nil
    var bordered: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(ClavisTypography.inter(15, weight: .semibold))
                .foregroundColor(isEnabled ? (foreground ?? .clavixPaper) : .clavixInk4)
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(fill)
                .overlay(
                    RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous)
                        .stroke(bordered ? Color.clavixRule : Color.clear, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous))
                .opacity(isEnabled ? 1 : 0.7)
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled)
    }
}

private struct HoldingsCSVComingSoonSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    ClavixCard(fill: .clavixAccentSoft) {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("CSV import is coming soon.")
                                .font(ClavisTypography.clavixSerif(20, weight: .medium))
                                .foregroundColor(.clavixInk)
                            Text("When the importer is ready, Clavix will let you map exported columns before saving positions.")
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixAccentInk)
                                .fixedSize(horizontal: false, vertical: true)
                            HoldingsSheetButton(title: "Close", action: { dismiss() })
                        }
                    }
                }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.vertical, 20)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .navigationTitle("Upload CSV")
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
        ClavixScreen(eyebrow: "Free plan", title: "Position limit reached") {
            ClavixCard(fill: .clavixAccentSoft) {
                Text("Free accounts can track three positions. Upgrade for unlimited positions, the verbose morning brief, and full history.")
                    .font(ClavisTypography.inter(14, weight: .regular))
                    .foregroundColor(.clavixAccentInk)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HoldingsSheetButton(
                title: "View Pro",
                fill: .clavixAccent,
                action: { dismiss() }
            )

            HoldingsSheetButton(
                title: "Manage positions",
                fill: .clavixPaper,
                foreground: .clavixInk,
                bordered: true,
                action: { dismiss() }
            )
        }
    }
}
