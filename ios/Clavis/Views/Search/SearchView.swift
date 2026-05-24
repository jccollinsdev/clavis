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
                VStack(alignment: .leading, spacing: 16) {
                    searchField

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
                            Text("Searching tickers…")
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixInk3)
                        }
                    } else if trimmedQuery.isEmpty {
                        emptyState
                    } else if results.isEmpty {
                        ClavixCard {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("No results for \(trimmedQuery.uppercased())")
                                    .font(ClavisTypography.clavixSerif(15, weight: .medium))
                                    .foregroundColor(.clavixInk)
                                Text("Try a different ticker or company name. Outside-universe tickers are not yet searchable here.")
                                    .font(ClavisTypography.clavixCaption)
                                    .foregroundColor(.clavixInk2)
                            }
                        }
                    } else {
                        ClavixCard(padding: 0) {
                            VStack(spacing: 0) {
                                ForEach(Array(results.enumerated()), id: \.element.id) { index, result in
                                    NavigationLink(destination: TickerDetailView(ticker: result.ticker)) {
                                        SearchResultRow(result: result)
                                    }
                                    .buttonStyle(.plain)
                                    if index < results.count - 1 {
                                        Rectangle().fill(Color.clavixRule).frame(height: 1)
                                    }
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 8)
                .padding(.bottom, ClavixLayout.bottomPad)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .toolbar(.hidden, for: .navigationBar)
            .safeAreaInset(edge: .top, spacing: 0) {
                ClavixLargeHeader(eyebrow: "Tracked universe", title: "Search")
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
        ClavixCard(padding: 12) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.clavixInk3)
                TextField("Ticker or company name…", text: $query)
                    .font(ClavisTypography.clavixSerif(15))
                    .foregroundColor(.clavixInk)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                if !trimmedQuery.isEmpty {
                    Button("Clear") {
                        query = ""
                        results = []
                        errorMessage = nil
                    }
                    .font(ClavisTypography.clavixMono(11, weight: .semibold))
                    .foregroundColor(.clavixAccent)
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var emptyState: some View {
        ClavixCard {
            VStack(alignment: .leading, spacing: 6) {
                ClavixEyebrow("Tracked universe")
                Text("Search the tracked universe")
                    .font(ClavisTypography.clavixSerif(18, weight: .medium))
                    .foregroundColor(.clavixInk)
                Text("Enter a ticker or company name to open a rating, inspect recent news, or add to your holdings.")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
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

private struct SearchResultRow: View {
    let result: TickerSearchResult

    private var grade: String { result.resolvedGrade ?? "—" }
    private var scoreText: String {
        guard let score = result.resolvedSafetyScore else { return "—" }
        return "\(Int(score.rounded()))"
    }

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            ClavixGradeBadge(grade, size: 28)

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(result.ticker)
                        .font(ClavisTypography.clavixMono(13, weight: .bold))
                        .foregroundColor(.clavixInk)
                    Text(result.companyName)
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk2)
                        .lineLimit(1)
                }

                HStack(spacing: 6) {
                    if let price = result.price {
                        Text(currency(price))
                            .font(ClavisTypography.clavixMono(11, weight: .semibold))
                            .foregroundColor(.clavixInk)
                    }
                    if let overlay = result.portfolioOverlay, overlay.isHeld {
                        TagChip(text: "In holdings", foreground: .clavixAccentInk, background: .clavixAccentSoft)
                    }
                    if !result.isSupported {
                        TagChip(text: "Not in tracked universe", foreground: .clavixWarnInk, background: .clavixWarnSoft)
                    }
                }
            }

            Spacer(minLength: 12)

            Text(scoreText)
                .font(ClavisTypography.clavixMono(15, weight: .semibold))
                .foregroundColor(.clavixInk3)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 13)
    }

    private func currency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "$0.00"
    }
}

private struct TagChip: View {
    let text: String
    let foreground: Color
    let background: Color

    var body: some View {
        Text(text)
            .font(ClavisTypography.clavixMono(9, weight: .bold))
            .tracking(0.4)
            .foregroundColor(foreground)
            .padding(.horizontal, 6)
            .padding(.vertical, 3)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
    }
}
