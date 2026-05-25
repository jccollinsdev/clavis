import SwiftUI

struct MacroExposureAuditView: View {
    let ticker: String
    let methodology: MethodologyResponse?

    private var dimension: MethodologyMacroExposure? { methodology?.dimensions.macroExposure }
    private let factors = ["tnx", "dxy", "wti", "vix", "spy"]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                AuditHeaderCard(
                    title: "Macro Exposure",
                    ticker: ticker,
                    score: dimension?.score,
                    subtitle: "R² \(format(dimension?.rSquared, places: 3)) · days \(dimension?.tradingDaysUsed.map(String.init) ?? "—")"
                )

                if dimension?.limitedData == true {
                    AuditLimitedDataView(message: "Limited Data — the regression did not have enough clean history to support a full macro read.")
                }

                AuditSectionCard(title: "Factor Sensitivity") {
                    ForEach(factors, id: \.self) { factor in
                        AuditValueRow(
                            label: factor.uppercased(),
                            value: format(dimension?.coefficients?[factor], places: 4),
                            status: format(dimension?.currentFactorLevels?[factor], places: 2)
                        )
                    }
                }

                AuditSectionCard(title: "Methodology") {
                    Text("Macro Exposure measures how sensitive a ticker is to broad macro factors. Clavix evaluates historical relationships between the ticker's returns and factors such as 10-year Treasury yields, the U.S. dollar, crude oil, VIX, and S&P 500 returns.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.clavixInk3)
                        .fixedSize(horizontal: false, vertical: true)
                    if let narrative = dimension?.narrative, !narrative.isEmpty {
                        Text(narrative)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.clavixInk3)
                    }
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.sectionSpacing)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .navigationTitle("Macro Exposure")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func format(_ value: Double?, places: Int) -> String {
        guard let value else { return "—" }
        return String(format: "%.*f", places, value)
    }
}
