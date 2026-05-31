import SwiftUI

struct SearchView: View {
    @State private var query = ""
    @State private var results: [TickerSearchResult] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var hasLoadedInitialState = false
    @State private var searchTask: Task<Void, Never>?
    @State private var recents: [String] = []

    private var trimmedQuery: String {
        query.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private let recentsKey = "clavix.search.recents"
    // v1: ETFs are not in the tracked universe, so the "ETFs" and "S&P 500"
    // (seeded "SPY") chips were dead-ends and have been removed. "Recently
    // downgraded" seeded an empty query (no-op) and is removed until backend
    // filter params exist. Remaining chips seed real, in-universe results.
    private let browseChips: [[String]] = [
        ["Mega caps", "Dividend aristocrats"],
        ["High-grade only"]
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if !trimmedQuery.isEmpty {
                        queryResultsSection
                    } else {
                        recentSection
                        trendingSection
                        browseSection
                    }
                }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 14)
                .padding(.bottom, ClavixLayout.bottomPad)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .safeAreaInset(edge: .top, spacing: 0) {
                VStack(spacing: 0) {
                    ClavixStickyBar()
                    searchHeader
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                hasLoadedInitialState = true
                loadRecents()
            }
            .onChange(of: query) { _ in
                runSearch()
            }
            .navigationDestination(for: String.self) { ticker in
                TickerDetailView(ticker: ticker)
                    .onAppear { rememberRecent(ticker) }
            }
        }
    }

    // MARK: - Header (VQASearchHeader 1:1)

    private var searchHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                ClavixEyebrow("Search")
                Spacer()
                if !trimmedQuery.isEmpty {
                    Button("Cancel") {
                        query = ""
                        results = []
                        errorMessage = nil
                    }
                    .font(ClavisTypography.inter(13, weight: .medium))
                    .foregroundColor(.clavixAccent)
                }
            }
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14, weight: .regular))
                    .foregroundColor(.clavixInk3)
                TextField("Ticker or company name…", text: $query)
                    .font(ClavisTypography.clavixMono(14, weight: .regular))
                    .tracking(0.2)
                    .foregroundColor(.clavixInk)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                Spacer()
                if !trimmedQuery.isEmpty {
                    Button(action: { query = "" }) {
                        Image(systemName: "xmark")
                            .font(.system(size: 12))
                            .foregroundColor(.clavixInk3)
                    }
                }
            }
            .padding(.horizontal, 12)
            .frame(height: 42)
            .background(Color.clavixPaper)
            .overlay(
                RoundedRectangle(cornerRadius: ClavixLayout.cardRadius)
                    .stroke(trimmedQuery.isEmpty ? Color.clavixRule : Color.clavixInk,
                            lineWidth: trimmedQuery.isEmpty ? 1 : 1.5)
            )
            .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.cardRadius))
        }
        .padding(.horizontal, 16)
        .padding(.top, 4)
        .padding(.bottom, 12)
        .background(Color.clavixPage)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.clavixRule).frame(height: 1) }
    }

    // MARK: - Sections

    @ViewBuilder
    private var queryResultsSection: some View {
        if let errorMessage {
            ClavixCard {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Search unavailable")
                        .font(ClavisTypography.clavixSerif(15, weight: .medium))
                        .foregroundColor(.clavixInk)
                    Text(errorMessage)
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk2)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        } else if isLoading {
            ClavixCard {
                Text("Searching tracked universe…")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
            }
        } else if results.isEmpty {
            ClavixCard {
                VStack(alignment: .leading, spacing: 6) {
                    Text("No supported ticker matched \"\(trimmedQuery)\"")
                        .font(ClavisTypography.clavixSerif(15, weight: .medium))
                        .foregroundColor(.clavixInk)
                    Text("Try a different ticker symbol or company name.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk2)
                }
            }
        } else {
            ClavixSection(eyebrow: "Results · \(results.count)", title: "Tracked universe") {
                ClavixCard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(results.enumerated()), id: \.element.id) { index, result in
                            NavigationLink(value: result.ticker) {
                                SearchResultRow(result: result)
                            }
                            .buttonStyle(.plain)
                            .simultaneousGesture(TapGesture().onEnded { rememberRecent(result.ticker) })
                            if index < results.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var recentSection: some View {
        ClavixSection(eyebrow: "Recent", title: "Last viewed") {
            if !recents.isEmpty {
                HStack {
                    Spacer()
                    Button("Clear →") { clearRecents() }
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixAccent)
                }
                .offset(y: -48)
                .padding(.bottom, -38)

                ClavixCard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(recents.enumerated()), id: \.element) { index, ticker in
                            NavigationLink(value: ticker) {
                                RecentTickerRow(symbol: ticker)
                            }
                            .buttonStyle(.plain)
                            if index < recents.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            } else {
                ClavixCard {
                    Text("Tickers you open will appear here.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            }
        }
    }

    private var trendingSection: some View {
        ClavixSection(eyebrow: "What others are looking at", title: "Trending") {
            ClavixCard {
                Text("Trending tickers will appear here once enough activity is captured.")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
            }
        }
    }

    private var browseSection: some View {
        ClavixSection(eyebrow: "Quick filters", title: "Browse") {
            VStack(alignment: .leading, spacing: 8) {
                ForEach(Array(browseChips.enumerated()), id: \.offset) { _, row in
                    HStack(spacing: 6) {
                        ForEach(row, id: \.self) { label in
                            Button(action: { applyBrowseFilter(label) }) {
                                ClavixPill(label: label)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
    }

    // MARK: - Actions

    private func runSearch() {
        searchTask?.cancel()

        guard !trimmedQuery.isEmpty else {
            isLoading = false
            errorMessage = nil
            results = []
            return
        }

        searchTask = Task {
            try? await Task.sleep(nanoseconds: 250_000_000)
            guard !Task.isCancelled else { return }

            await MainActor.run {
                isLoading = true
                errorMessage = nil
            }

            do {
                let fetched = try await APIService.shared.searchTickers(query: trimmedQuery, limit: 25)
                guard !Task.isCancelled else { return }
                await MainActor.run {
                    results = fetched
                    isLoading = false
                }
            } catch {
                guard !Task.isCancelled else { return }
                await MainActor.run {
                    results = []
                    errorMessage = error.localizedDescription
                    isLoading = false
                }
            }
        }
    }

    private func applyBrowseFilter(_ label: String) {
        // Quick filters become a search seed today; backend filter params come later (P1).
        switch label {
        case "Mega caps":           query = "AAPL"
        case "Dividend aristocrats":query = "JNJ"
        case "High-grade only":     query = "MSFT"
        default: query = label
        }
    }

    // MARK: - Recents (UserDefaults)

    private func loadRecents() {
        recents = UserDefaults.standard.stringArray(forKey: recentsKey) ?? []
    }

    private func rememberRecent(_ ticker: String) {
        let upper = ticker.uppercased()
        var next = recents.filter { $0 != upper }
        next.insert(upper, at: 0)
        if next.count > 6 { next = Array(next.prefix(6)) }
        recents = next
        UserDefaults.standard.set(next, forKey: recentsKey)
    }

    private func clearRecents() {
        recents = []
        UserDefaults.standard.removeObject(forKey: recentsKey)
    }
}

// MARK: - Rows

private struct SearchResultRow: View {
    let result: TickerSearchResult

    private var grade: String { result.resolvedGrade ?? "—" }
    private var scoreText: String {
        guard let score = result.resolvedSafetyScore else { return "—" }
        return "\(Int(score.rounded()))"
    }

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 8) {
                    Text(result.ticker)
                        .font(ClavisTypography.clavixMono(13, weight: .bold))
                        .tracking(0.3)
                        .foregroundColor(.clavixInk)
                    Text(result.companyName)
                        .font(ClavisTypography.inter(12, weight: .regular))
                        .foregroundColor(.clavixInk3)
                        .lineLimit(1)
                    if !result.isSupported {
                        Text("· OUTSIDE")
                            .font(ClavisTypography.clavixMono(9, weight: .bold))
                            .foregroundColor(.clavixWarn)
                    }
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                if let price = result.price {
                    Text(currency(price))
                        .font(ClavisTypography.clavixMono(12, weight: .semibold))
                        .foregroundColor(.clavixInk)
                }
                Text(scoreText)
                    .font(ClavisTypography.clavixMono(10, weight: .semibold))
                    .foregroundColor(.clavixInk3)
            }
            .frame(width: 70, alignment: .trailing)
            ClavixGradeBadge(grade, size: 18)
            Image(systemName: "chevron.right")
                .font(.system(size: 10))
                .foregroundColor(.clavixInk4)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .opacity(result.isSupported ? 1 : 0.85)
    }

    private func currency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "$0.00"
    }
}

private struct RecentTickerRow: View {
    let symbol: String
    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "arrow.clockwise")
                .font(.system(size: 13, weight: .regular))
                .foregroundColor(.clavixInk4)
            Text(symbol)
                .font(ClavisTypography.clavixMono(13, weight: .bold))
                .tracking(0.3)
                .foregroundColor(.clavixInk)
            Spacer()
            Image(systemName: "chevron.right")
                .font(.system(size: 10))
                .foregroundColor(.clavixInk4)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
    }
}
