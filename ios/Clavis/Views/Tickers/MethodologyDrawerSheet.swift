import SwiftUI

struct MethodologyDrawerSheet: View {
    let ticker: String
    let methodology: MethodologyResponse
    let tappedDimension: String

    @Environment(\.dismiss) private var dismiss
    @State private var expandedDimension: String
    @State private var selectedArticle: MethodologyArticle?

    init(ticker: String, methodology: MethodologyResponse, tappedDimension: String) {
        self.ticker = ticker
        self.methodology = methodology
        self.tappedDimension = tappedDimension
        _expandedDimension = State(initialValue: tappedDimension)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    AuditHeaderCard(
                        title: "Methodology",
                        ticker: ticker,
                        score: methodology.composite.score,
                        subtitle: "Methodology v\(methodology.composite.methodologyVersion ?? "—")"
                    )

                    drawerDimension(
                        key: "financial_health",
                        title: methodology.dimensions.financialHealth.label,
                        score: methodology.dimensions.financialHealth.score,
                        destination: AnyView(FinancialHealthAuditView(ticker: ticker, methodology: methodology))
                    ) {
                        AuditValueRow(label: "Debt / Equity", value: decimal(methodology.dimensions.financialHealth.debtToEquity), status: methodology.dimensions.financialHealth.asOfDate ?? "Updated")
                        AuditValueRow(label: "FCF Margin", value: percent(methodology.dimensions.financialHealth.fcfMargin), status: methodology.dimensions.financialHealth.dataSource ?? "Source")
                    }

                    drawerDimension(
                        key: "news_sentiment",
                        title: methodology.dimensions.newsSentiment.label,
                        score: methodology.dimensions.newsSentiment.score,
                        destination: AnyView(NewsSentimentAuditView(ticker: ticker, methodology: methodology))
                    ) {
                        Text("\(methodology.dimensions.newsSentiment.articleCount7d) articles · weighted score \(methodology.dimensions.newsSentiment.weightedScore.map { String(Int($0.rounded())) } ?? "—")")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                        miniDistribution(count: methodology.dimensions.newsSentiment.articleCount7d)
                    }

                    drawerDimension(
                        key: "macro_exposure",
                        title: methodology.dimensions.macroExposure.label,
                        score: methodology.dimensions.macroExposure.score,
                        destination: AnyView(MacroExposureAuditView(ticker: ticker, methodology: methodology))
                    ) {
                        Text("R² \(String(format: "%.3f", methodology.dimensions.macroExposure.rSquared ?? 0)) · \(methodology.dimensions.macroExposure.tradingDaysUsed ?? 0) days used")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }

                    drawerDimension(
                        key: "sector_exposure",
                        title: methodology.dimensions.sectorExposure.label,
                        score: methodology.dimensions.sectorExposure.score,
                        destination: AnyView(SectorExposureAuditView(ticker: ticker, methodology: methodology))
                    ) {
                        Text(methodology.dimensions.sectorExposure.sector ?? "Sector unavailable")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }

                    drawerDimension(
                        key: "volatility",
                        title: methodology.dimensions.volatility.label,
                        score: methodology.dimensions.volatility.score,
                        destination: AnyView(VolatilityAuditView(ticker: ticker, methodology: methodology, scoreHistory: []))
                    ) {
                        Text("30d \(percent(methodology.dimensions.volatility.realizedVol30d)) · 90d \(percent(methodology.dimensions.volatility.realizedVol90d))")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Methodology")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                        .foregroundColor(.textSecondary)
                }
            }
        }
        .sheet(item: $selectedArticle) { article in
            ArticleDetailSheet(article: article, ticker: ticker)
        }
    }

    private func drawerDimension(key: String, title: String, score: Double?, destination: AnyView, @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Button(action: { toggle(key) }) {
                HStack {
                    Text(title)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)
                    Spacer()
                    Text(score.map { String(Int($0.rounded())) } ?? "—")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textSecondary)
                    Image(systemName: expandedDimension == key ? "chevron.down" : "chevron.right")
                        .foregroundColor(.textSecondary)
                }
            }
            .buttonStyle(.plain)

            if expandedDimension == key {
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    content()
                    NavigationLink(destination: destination) {
                        HStack {
                            Text("Full audit")
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.accentBurnt)
                            Image(systemName: "arrow.up.right")
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.accentBurnt)
                        }
                    }
                    .buttonStyle(.plain)
                }
                .padding(.leading, ClavisTheme.smallSpacing)
            }
        }
        .padding(.vertical, ClavisTheme.smallSpacing)
    }

    private func toggle(_ key: String) {
        withAnimation(.easeInOut(duration: 0.2)) {
            expandedDimension = expandedDimension == key ? "" : key
        }
    }

    private func miniDistribution(count: Int) -> some View {
        HStack(alignment: .bottom, spacing: 4) {
            ForEach(0..<5, id: \.self) { index in
                Rectangle()
                    .fill(index == 2 ? Color.accentBurnt : Color.surfaceElevated)
                    .frame(width: 18, height: CGFloat(max(8, count - abs(2 - index) * 2)))
            }
        }
        .frame(height: 40, alignment: .bottom)
    }

    private func decimal(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.2f", value)
    }

    private func percent(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.1f%%", value * 100)
    }
}
