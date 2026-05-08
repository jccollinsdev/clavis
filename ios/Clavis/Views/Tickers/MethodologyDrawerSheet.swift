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
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    headerSection
                    Divider().background(Color.border).padding(.vertical, 12)

                    DimensionAccordion(
                        key: "financial_health",
                        score: methodology.dimensions.financialHealth.score,
                        title: methodology.dimensions.financialHealth.label,
                        isExpanded: expandedDimension == "financial_health",
                        onTap: { toggle("financial_health") }
                    ) {
                        FinancialHealthDetailView(dimension: methodology.dimensions.financialHealth)
                    }

                    DimensionAccordion(
                        key: "news_sentiment",
                        score: methodology.dimensions.newsSentiment.score,
                        title: methodology.dimensions.newsSentiment.label,
                        isExpanded: expandedDimension == "news_sentiment",
                        onTap: { toggle("news_sentiment") }
                    ) {
                        NewsSentimentDetailView(
                            dimension: methodology.dimensions.newsSentiment,
                            onArticleTap: { selectedArticle = $0 }
                        )
                    }

                    DimensionAccordion(
                        key: "macro_exposure",
                        score: methodology.dimensions.macroExposure.score,
                        title: methodology.dimensions.macroExposure.label,
                        isExpanded: expandedDimension == "macro_exposure",
                        onTap: { toggle("macro_exposure") }
                    ) {
                        MacroExposureDetailView(dimension: methodology.dimensions.macroExposure)
                    }

                    DimensionAccordion(
                        key: "sector_exposure",
                        score: methodology.dimensions.sectorExposure.score,
                        title: methodology.dimensions.sectorExposure.label,
                        isExpanded: expandedDimension == "sector_exposure",
                        onTap: { toggle("sector_exposure") }
                    ) {
                        SectorExposureDetailView(dimension: methodology.dimensions.sectorExposure)
                    }

                    DimensionAccordion(
                        key: "volatility",
                        score: methodology.dimensions.volatility.score,
                        title: methodology.dimensions.volatility.label,
                        isExpanded: expandedDimension == "volatility",
                        onTap: { toggle("volatility") }
                    ) {
                        VolatilityDetailView(dimension: methodology.dimensions.volatility)
                    }

                    compositeFooter
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(Color.backgroundPrimary.ignoresSafeArea())
            .navigationTitle("\(ticker) Methodology")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundColor(.informational)
                }
            }
        }
        .sheet(item: $selectedArticle) { article in
            ArticleDetailSheet(article: article, ticker: ticker)
        }
    }

    private func toggle(_ key: String) {
        withAnimation(.easeInOut(duration: 0.2)) {
            expandedDimension = expandedDimension == key ? "" : key
        }
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let grade = methodology.composite.grade {
                HStack(spacing: 10) {
                    GradeBadge(grade: grade, size: .large)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Composite Grade")
                            .font(ClavisTypography.label)
                            .foregroundColor(.textSecondary)
                        if let score = methodology.composite.score {
                            Text("Score: \(Int(score.rounded()))")
                                .font(ClavisTypography.bodyEmphasis)
                                .foregroundColor(.textPrimary)
                        }
                    }
                }
            }

            if let version = methodology.composite.methodologyVersion {
                Text("Methodology v\(version)")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
        }
    }

    private var compositeFooter: some View {
        VStack(spacing: 12) {
            Text("All five dimensions are weighted equally (20% each) in the composite score.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
                .multilineTextAlignment(.center)
                .padding(.top, 12)

            Text("Scores reflect model output based on available data. They do not constitute financial advice.")
                .font(.system(size: 11))
                .foregroundColor(.textTertiary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, 8)
    }
}

private struct DimensionAccordion<Content: View>: View {
    let key: String
    let score: Double?
    let title: String
    let isExpanded: Bool
    let onTap: () -> Void
    @ViewBuilder let content: Content

    var body: some View {
        VStack(spacing: 0) {
            Button(action: onTap) {
                HStack(spacing: 10) {
                    if let score {
                        Text("\(Int(score.rounded()))")
                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                            .foregroundColor(ClavisGradeStyle.riskColor(for: grade(for: score)))
                            .frame(width: 32)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text(title)
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.textPrimary)
                        if score == nil {
                            LimitedDataBadge()
                        }
                    }

                    Spacer()

                    Image(systemName: isExpanded ? "chevron.down" : "chevron.right")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.textTertiary)
                }
                .padding(.vertical, 14)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if isExpanded {
                content
                    .padding(.leading, 42)
                    .padding(.bottom, 12)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }

            Divider().background(Color.border)
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

private struct FinancialHealthDetailView: View {
    let dimension: MethodologyFinancialHealth

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ValueRow(label: "Debt / Equity", value: decimal(dimension.debtToEquity))
            ValueRow(label: "FCF Margin", value: percent(dimension.fcfMargin))
            ValueRow(label: "Interest Coverage", value: decimal(dimension.interestCoverage))
            ValueRow(label: "Current Ratio", value: decimal(dimension.currentRatio))
            TextRow(label: "Revenue Growth Trend", value: dimension.revenueGrowthTrend?.humanizedTitleCasedDisplayText)
            TextRow(label: "Profitability Trend", value: dimension.profitabilityTrend?.humanizedTitleCasedDisplayText)
            TextRow(label: "As Of", value: dimension.asOfDate)
            TextRow(label: "Source", value: dimension.dataSource?.uppercased())
        }
    }

    private func decimal(_ value: Double?) -> String? {
        guard let value else { return nil }
        return String(format: "%.2f", value)
    }

    private func percent(_ value: Double?) -> String? {
        guard let value else { return nil }
        return String(format: "%.1f%%", value * 100)
    }
}

private struct NewsSentimentDetailView: View {
    let dimension: MethodologyNewsSentiment
    let onArticleTap: (MethodologyArticle) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("\(dimension.articleCount7d) articles, last 7 days")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                if dimension.volumeSignal {
                    LimitedDataBadge(title: "High Volume", tint: .gradeCF)
                }
            }

            if let weightedScore = dimension.weightedScore {
                Text("Weighted score: \(Int(weightedScore.rounded()))")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }

            if dimension.articles.isEmpty {
                LimitedDataBadge()
            } else {
                ForEach(dimension.articles.prefix(10)) { article in
                    Button(action: { onArticleTap(article) }) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(article.title ?? "")
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.textPrimary)
                                .lineLimit(2)

                            HStack(spacing: 6) {
                                if let source = article.source {
                                    Text(source)
                                        .font(.system(size: 11))
                                        .foregroundColor(.textTertiary)
                                }
                                if let date = article.publishedAt {
                                    Text("·")
                                        .foregroundColor(.textTertiary)
                                    Text(String(date.prefix(10)))
                                        .font(.system(size: 11))
                                        .foregroundColor(.textTertiary)
                                }
                                if let score = article.sentimentScore {
                                    PillText(text: "\(Int(score.rounded()))", color: sentimentColor(score))
                                }
                                if let tier = article.sourceTier {
                                    PillText(text: "T\(tier)", color: .gradeCAA)
                                }
                                if let recencyWeight = article.recencyWeight {
                                    PillText(text: "\(String(format: "%.1fx", recencyWeight))", color: .gradeCBBB)
                                }
                            }

                            if let tldr = article.tldr, !tldr.isEmpty {
                                Text(tldr)
                                    .font(.system(size: 11))
                                    .foregroundColor(.textTertiary)
                                    .lineLimit(3)
                            }
                        }
                        .padding(8)
                        .background(Color.surfaceElevated.opacity(0.6))
                        .cornerRadius(6)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func sentimentColor(_ score: Double) -> Color {
        if score >= 70 { return .gradeCAA }
        if score >= 50 { return .gradeCBB }
        return .gradeCF
    }
}

private struct MacroExposureDetailView: View {
    let dimension: MethodologyMacroExposure

    private let factorOrder = ["tnx", "dxy", "wti", "vix", "spy"]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if dimension.limitedData {
                LimitedDataBadge()
            }

            ValueRow(label: "R²", value: decimal(dimension.rSquared, places: 3))
            ValueRow(label: "Trading Days", value: dimension.tradingDaysUsed.map(String.init))
            TextRow(label: "As Of", value: dimension.asOfDate)

            if let coefficients = dimension.coefficients, !coefficients.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Coefficients")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textPrimary)
                    ForEach(factorOrder, id: \.self) { factor in
                        if let value = coefficients[factor] {
                            HStack {
                                Text(factor.uppercased())
                                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                                    .foregroundColor(.textPrimary)
                                Spacer()
                                Text(String(format: "%.4f", value))
                                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                                    .foregroundColor(value >= 0 ? .gradeCAA : .gradeCF)
                                Image(systemName: value >= 0 ? "arrow.up.right" : "arrow.down.right")
                                    .font(.system(size: 10))
                                    .foregroundColor(value >= 0 ? .gradeCAA : .gradeCF)
                            }
                        }
                    }
                }
            }

            if let factorLevels = dimension.currentFactorLevels, !factorLevels.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Current Factor Levels")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textPrimary)
                    ForEach(factorOrder, id: \.self) { factor in
                        if let value = factorLevels[factor] {
                            ValueRow(label: factor.uppercased(), value: decimal(value, places: 2))
                        }
                    }
                }
            }

            if let narrative = dimension.narrative, !narrative.isEmpty {
                Text(narrative)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func decimal(_ value: Double?, places: Int) -> String? {
        guard let value else { return nil }
        return String(format: "%.*f", places, value)
    }
}

private struct SectorExposureDetailView: View {
    let dimension: MethodologySectorExposure

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            TextRow(label: "Sector", value: dimension.sector)
            TextRow(label: "Sector ETF", value: dimension.sectorEtf)
            ValueRow(label: "Sector Beta", value: decimal(dimension.sectorBeta, places: 3))
            ValueRow(label: "Momentum vs SPY (30d)", value: percent(dimension.sectorMomentum30d))
            ValueRow(label: "Sector Breadth", value: percent(dimension.sectorBreadth))

            if let narrative = dimension.narrative, !narrative.isEmpty {
                Text(narrative)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func decimal(_ value: Double?, places: Int) -> String? {
        guard let value else { return nil }
        return String(format: "%.*f", places, value)
    }

    private func percent(_ value: Double?) -> String? {
        guard let value else { return nil }
        return String(format: "%.1f%%", value * 100)
    }
}

private struct VolatilityDetailView: View {
    let dimension: MethodologyVolatility

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ValueRow(label: "Realized Vol (30d)", value: percent(dimension.realizedVol30d))
            ValueRow(label: "Realized Vol (90d)", value: percent(dimension.realizedVol90d))

            if let volRatio = dimension.volRatio {
                HStack {
                    Text("Vol Ratio")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                    Spacer()
                    Text(String(format: "%.2f", volRatio))
                        .font(.system(size: 13, weight: .medium, design: .monospaced))
                        .foregroundColor(volRatio > 1 ? .gradeCF : .gradeCAA)
                    Image(systemName: volRatio > 1 ? "arrow.up.right" : "arrow.down.right")
                        .font(.system(size: 10))
                        .foregroundColor(volRatio > 1 ? .gradeCF : .gradeCAA)
                }
            }

            ValueRow(label: "Max Drawdown (252d)", value: percent(dimension.maxDrawdown252d))
            ValueRow(label: "Beta to SPY", value: decimal(dimension.betaToSpy, places: 3))
            TextRow(label: "As Of", value: dimension.asOfDate)
        }
    }

    private func decimal(_ value: Double?, places: Int) -> String? {
        guard let value else { return nil }
        return String(format: "%.*f", places, value)
    }

    private func percent(_ value: Double?) -> String? {
        guard let value else { return nil }
        return String(format: "%.1f%%", value * 100)
    }
}

private struct ValueRow: View {
    let label: String
    let value: String?

    var body: some View {
        if let value, !value.isEmpty {
            HStack {
                Text(label)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                Spacer()
                Text(value)
                    .font(.system(size: 13, weight: .medium, design: .monospaced))
                    .foregroundColor(.textPrimary)
            }
        }
    }
}

private struct TextRow: View {
    let label: String
    let value: String?

    var body: some View {
        if let value, !value.isEmpty {
            HStack(alignment: .top) {
                Text(label)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                Spacer(minLength: 12)
                Text(value)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textPrimary)
                    .multilineTextAlignment(.trailing)
            }
        }
    }
}

private struct PillText: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.system(size: 10, weight: .bold))
            .foregroundColor(color)
            .padding(.horizontal, 5)
            .padding(.vertical, 1)
            .background(color.opacity(0.15))
            .cornerRadius(4)
    }
}

private struct LimitedDataBadge: View {
    var title: String = "Limited Data"
    var tint: Color = .gradeCBB

    var body: some View {
        Text(title)
            .font(ClavisTypography.footnote)
            .foregroundColor(tint)
            .padding(.vertical, 2)
    }
}
