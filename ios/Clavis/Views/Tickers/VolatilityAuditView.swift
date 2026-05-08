import SwiftUI

struct VolatilityAuditView: View {
    let ticker: String
    let methodology: MethodologyResponse?
    let scoreHistory: [ScoreSnapshot]

    private var dimension: MethodologyVolatility? { methodology?.dimensions.volatility }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                AuditHeaderCard(
                    title: "Volatility",
                    ticker: ticker,
                    score: dimension?.score,
                    subtitle: "Updated \(dimension?.asOfDate ?? "Date unavailable")"
                )

                AuditSectionCard(title: "Metrics") {
                    AuditValueRow(label: "Realized Vol 30d", value: percent(dimension?.realizedVol30d), status: "Metric")
                    AuditValueRow(label: "Realized Vol 90d", value: percent(dimension?.realizedVol90d), status: "Metric")
                    AuditValueRow(label: "Vol Ratio", value: format(dimension?.volRatio), status: (dimension?.volRatio ?? 1) > 1 ? "Rising" : "Falling")
                    AuditValueRow(label: "Max Drawdown 252d", value: percent(dimension?.maxDrawdown252d), status: "Metric")
                    AuditValueRow(label: "Beta to SPY", value: format(dimension?.betaToSpy), status: "Metric")
                }

                AuditSectionCard(title: "Vol Trend") {
                    // TODO: backend expose volatility-specific history for the full audit screen.
                    ScoreHistoryChart(snapshots: scoreHistory, showAllDimensions: false, toggledDimensions: .constant([]))
                }

                AuditSectionCard(title: "Methodology") {
                    Text("Volatility measures price instability and whether it is rising or falling. Inputs include 30-day realized volatility, 90-day realized volatility, the 30-day/90-day volatility ratio, maximum drawdown from the trailing 252-day high, and beta to the S&P 500.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.sectionSpacing)
        }
        .background(ClavisAtmosphereBackground())
        .navigationTitle("Volatility")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func format(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.2f", value)
    }

    private func percent(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.1f%%", value * 100)
    }
}
