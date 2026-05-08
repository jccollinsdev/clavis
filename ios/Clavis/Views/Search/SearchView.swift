import SwiftUI

struct SearchView: View {
    @State private var query = ""
    @State private var results: [TickerSearchResult] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var hasLoadedInitialState = false
    @State private var searchTask: Task<Void, Never>?

    private var trimmedQuery: String {
        query.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    searchField

                    if let errorMessage {
                        SearchErrorCard(message: errorMessage)
                    } else if isLoading {
                        ClavisLoadingCard(
                            title: "Searching tickers",
                            subtitle: "Pulling the latest tracked names and current ratings."
                        )
                    } else if trimmedQuery.isEmpty {
                        SearchEmptyStateCard()
                    } else if results.isEmpty {
                        SearchNoResultsCard(query: trimmedQuery)
                    } else {
                        SearchResultsCard(results: results)
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.sectionSpacing)
                .padding(.bottom, ClavisTheme.largeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .safeAreaInset(edge: .top, spacing: 0) {
                SearchTopHeader()
            }
            .onAppear {
                hasLoadedInitialState = true
            }
            .onChange(of: query) { _ in
                runSearch()
            }
        }
    }

    private var searchField: some View {
        HStack(spacing: ClavisTheme.smallSpacing) {
            Image(systemName: "magnifyingglass")
                .foregroundColor(.textSecondary)
            TextField("Search ticker or company", text: $query)
                .font(ClavisTypography.body)
                .foregroundColor(.textPrimary)
                .textInputAutocapitalization(.characters)
                .autocorrectionDisabled()
            if !trimmedQuery.isEmpty {
                Button("Clear") {
                    query = ""
                    results = []
                    errorMessage = nil
                }
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.accentBurnt)
                .buttonStyle(.plain)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }

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
}

private struct SearchTopHeader: View {
    var body: some View {
        ClavixPageHeader(title: "Search", subtitle: "Tracked universe")
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
}

private struct SearchEmptyStateCard: View {
    var body: some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("Search the tracked universe")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text("Enter a ticker or company name to open a rating, inspect recent news, or add the ticker to your holdings or watchlist.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

private struct SearchNoResultsCard: View {
    let query: String

    var body: some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("No results for \(query.uppercased())")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text("Try a different ticker symbol or company name.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
        }
    }
}

private struct SearchResultsCard: View {
    let results: [TickerSearchResult]

    var body: some View {
        ClavisFlushListCard(fill: .surface, padding: ClavisTheme.cardPadding) {
            ForEach(Array(results.enumerated()), id: \.element.id) { index, result in
                NavigationLink(destination: TickerDetailView(ticker: result.ticker)) {
                    SearchResultRow(result: result, showsDivider: index < results.count - 1)
                }
                .buttonStyle(.plain)
            }
        }
    }
}

private struct SearchErrorCard: View {
    let message: String

    var body: some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("Search unavailable")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text(message)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

private struct SearchResultRow: View {
    let result: TickerSearchResult
    let showsDivider: Bool

    private var grade: String {
        result.resolvedGrade ?? "—"
    }

    private var scoreText: String {
        guard let score = result.resolvedSafetyScore else { return "--" }
        return "\(Int(score.rounded()))"
    }

    private var subtitle: String {
        if let summary = result.resolvedSummary?.sanitizedDisplayText, !summary.isEmpty {
            return summary
        }
        return result.companyName
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .center, spacing: 12) {
                GradeBadge(grade: grade)

                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(result.ticker)
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.accentBurnt)
                        Text(result.companyName)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .lineLimit(1)
                    }

                    Text(subtitle)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .lineLimit(2)

                    HStack(spacing: 8) {
                        if let price = result.price {
                            Text(currency(price))
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.textPrimary)
                        }

                        if let overlay = result.portfolioOverlay, overlay.isHeld {
                            SearchTag(text: "In holdings", foreground: .accentInk, background: .accentBurnt)
                        }

                        if !result.isSupported {
                            SearchTag(text: "Not in tracked universe", foreground: .warn, background: .warnSoft)
                        }
                    }
                }

                Spacer(minLength: 12)

                Text(scoreText)
                    .font(ClavisTypography.rowScore)
                    .foregroundColor(.textSecondary)
            }
            .padding(.vertical, 13)

            if showsDivider {
                Divider().overlay(Color.border)
            }
        }
    }

    private func currency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "$0.00"
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
