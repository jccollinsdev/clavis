import SwiftUI

struct FinancialHealthAuditView: View {
    let ticker: String
    let methodology: MethodologyResponse?

    private var dimension: MethodologyFinancialHealth? { methodology?.dimensions.financialHealth }
    private var isReferenceMode: Bool { methodology == nil }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                if isReferenceMode {
                    AuditReferenceContextView(
                        dimensionName: "Financial Health",
                        message: "Open a ticker from Search, Holdings, Alerts, or the Morning Report to inspect live balance-sheet and cash-flow inputs for that company."
                    )
                } else {
                    AuditHeaderCard(
                        title: "Financial Health",
                        ticker: ticker,
                        score: dimension?.score,
                        subtitle: "Source: Finnhub, updated \(AuditSupport.formattedAsOfDate(dimension?.asOfDate))"
                    )

                    AuditSectionCard(title: "Ratio Table") {
                        AuditValueRow(label: "D/E", value: decimal(dimension?.debtToEquity), status: status(for: dimension?.debtToEquity, lowIsGood: true))
                        AuditValueRow(label: "FCF Margin", value: percent(dimension?.fcfMargin), status: status(for: dimension?.fcfMargin, lowIsGood: false))
                        AuditValueRow(label: "Interest Coverage", value: decimal(dimension?.interestCoverage), status: status(for: dimension?.interestCoverage, lowIsGood: false))
                        AuditValueRow(label: "Current Ratio", value: decimal(dimension?.currentRatio), status: status(for: dimension?.currentRatio, lowIsGood: false))
                        AuditValueRow(label: "Revenue Growth Trend", value: dimension?.revenueGrowthTrend?.humanizedTitleCasedDisplayText ?? "Unavailable", status: "Trend")
                        AuditValueRow(label: "Profitability Trend", value: dimension?.profitabilityTrend?.humanizedTitleCasedDisplayText ?? "Unavailable", status: "Trend")
                    }

                    AuditSectionCard(title: "Industry Comparison") {
                        Text("Your ticker is shown against its sector median when comparative data is available.")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.clavixInk3)
                        let medians = dimension?.sectorMedianComparison ?? [:]
                        if medians.isEmpty {
                            Text("Sector median comparison unavailable.")
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.clavixInk)
                        } else {
                            ForEach(medians.keys.sorted(), id: \.self) { metric in
                                if let row = medians[metric] {
                                    AuditValueRow(
                                        label: metric.humanizedTitleCasedDisplayText,
                                        value: decimal(row.median),
                                        status: row.nTickers.map { "\($0) tickers" } ?? "Median"
                                    )
                                }
                            }
                        }
                        let peers = dimension?.peerComparisons ?? []
                        if !peers.isEmpty {
                            Text("Peers: " + peers.prefix(5).compactMap(\.ticker).joined(separator: ", "))
                                .font(ClavisTypography.footnoteEmphasis)
                                .foregroundColor(.clavixInk)
                        }
                    }
                }

                AuditSectionCard(title: "Methodology") {
                    Text("Financial Health measures the structural strength of the company. It uses balance-sheet and cash-flow inputs such as debt-to-equity ratio, free cash flow margin, interest coverage, current ratio, revenue growth trend, and profitability trend.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.clavixInk3)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.sectionSpacing)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .navigationTitle("Financial Health")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func decimal(_ value: Double?) -> String {
        guard let value else { return "Unavailable" }
        return String(format: "%.2f", value)
    }

    private func percent(_ value: Double?) -> String {
        guard let value else { return "Unavailable" }
        return String(format: "%.1f%%", value * 100)
    }

    private func status(for value: Double?, lowIsGood: Bool) -> String {
        guard let value else { return "Unavailable" }
        if lowIsGood {
            return value < 1 ? "Healthy" : value < 2 ? "Watch" : "Stressed"
        }
        return value > 1 ? "Healthy" : value > 0.5 ? "Watch" : "Stressed"
    }
}

struct AuditHeaderCard: View {
    let title: String
    let ticker: String
    let score: Double?
    let subtitle: String

    var body: some View {
        ClavixCard(fill: .clavixPaper) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(title)
                    .font(ClavisTypography.h2)
                    .foregroundColor(.clavixInk)
                Text(ticker)
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.clavixAccent)
                HStack(alignment: .center, spacing: ClavisTheme.smallSpacing) {
                    Text(score.map { "\(Int($0.rounded()))" } ?? "—")
                        .font(ClavisTypography.portfolioScore)
                        .foregroundColor(.clavixInk)
                    GradeBadge(grade: grade(for: score), size: .standard)
                }
                Text(subtitle)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.clavixInk3)
            }
        }
    }

    private func grade(for score: Double?) -> String {
        guard let score else { return "—" }
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

struct AuditSectionCard<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        ClavixCard(fill: .clavixPaper) {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text(title)
                    .font(ClavisTypography.label)
                    .foregroundColor(.clavixInk3)
                content
            }
        }
    }
}

struct AuditValueRow: View {
    let label: String
    let value: String
    let status: String

    var body: some View {
        HStack(alignment: .center, spacing: ClavisTheme.smallSpacing) {
            Text(label)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.clavixInk)
            Spacer()
            Text(value)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.clavixInk3)
            Text(status)
                .font(ClavisTypography.label)
                .foregroundColor(.clavixAccent)
        }
    }
}

struct AuditLimitedDataView: View {
    let message: String

    var body: some View {
        ClavixCard(fill: .clavixPaper) {
            Text(message)
                .font(ClavisTypography.body)
                .foregroundColor(.clavixInk3)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

struct AuditReferenceContextView: View {
    let dimensionName: String
    let message: String

    var body: some View {
        ClavixInlineNoticeCard(
            eyebrow: "Reference Mode",
            title: "\(dimensionName) needs a live ticker",
            message: message,
            footnote: "Reference pages explain the framework. Live inputs appear when you open this audit from a stock.",
            glyph: "scope",
            fill: .clavixPaper2,
            secondary: .clavixInk3
        )
    }
}

enum AuditSupport {
    private static let isoFormatters: [ISO8601DateFormatter] = {
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        let standard = ISO8601DateFormatter()
        standard.formatOptions = [.withInternetDateTime]

        return [fractional, standard]
    }()

    private static let fallbackFormatters: [DateFormatter] = {
        let formats = [
            "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
            "yyyy-MM-dd'T'HH:mm:ss.SSS",
            "yyyy-MM-dd'T'HH:mm:ss"
        ]

        return formats.map { format in
            let formatter = DateFormatter()
            formatter.dateFormat = format
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.timeZone = TimeZone(secondsFromGMT: 0)
            return formatter
        }
    }()

    private static let displayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter
    }()

    static func formattedAsOfDate(_ rawValue: String?) -> String {
        guard let rawValue, !rawValue.isEmpty else { return "Date unavailable" }
        if let parsedDate = isoFormatters.lazy.compactMap({ $0.date(from: rawValue) }).first {
            return displayFormatter.string(from: parsedDate)
        }
        if let parsedDate = fallbackFormatters.lazy.compactMap({ $0.date(from: rawValue) }).first {
            return displayFormatter.string(from: parsedDate)
        }
        return rawValue
    }
}
