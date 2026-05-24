import SwiftUI

struct SectorExposureAuditView: View {
    let ticker: String
    let methodology: MethodologyResponse?

    private var dimension: MethodologySectorExposure? { methodology?.dimensions.sectorExposure }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                AuditHeaderCard(
                    title: "Sector Exposure",
                    ticker: ticker,
                    score: dimension?.score,
                    subtitle: "\(dimension?.sector ?? "Sector unavailable") · \(dimension?.sectorEtf ?? "ETF unavailable")"
                )

                AuditSectionCard(title: "Metrics") {
                    AuditValueRow(label: "Sector Beta", value: format(dimension?.sectorBeta), status: "Metric")
                    AuditValueRow(label: "Sector Momentum (30d)", value: percent(dimension?.sectorMomentum30d), status: "Metric")
                    AuditValueRow(label: "Sector Breadth", value: percent(dimension?.sectorBreadth), status: "Metric")
                    // TODO: backend expose sector metric sparklines for the full audit screen.
                    Text("Sparklines will appear once historical sector metric series are returned.")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }

                AuditSectionCard(title: "Narrative") {
                    Text(dimension?.narrative ?? "Sector narrative unavailable.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                AuditSectionCard(title: "Methodology") {
                    Text("Sector Exposure measures how vulnerable a ticker is to its sector's current state. It considers sector beta, sector momentum versus the S&P 500, sector breadth, and sector-specific news.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.sectionSpacing)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .navigationTitle("Sector Exposure")
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
