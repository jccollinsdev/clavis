import SwiftUI
import Charts

struct PriceChartView: View {
    let ticker: String
    let prices: [PricePoint]
    var days: Int = 30

    private var chartPrices: [PricePoint] {
        Array(prices.sorted { $0.recordedAt < $1.recordedAt }.suffix(days))
    }

    private var yRange: ClosedRange<Double>? {
        guard !chartPrices.isEmpty else { return nil }
        let low = chartPrices.map { $0.price }.min() ?? 0
        let high = chartPrices.map { $0.price }.max() ?? 0
        let padding = (high - low) * 0.1
        let lowerBound = Swift.max(0, low - padding)
        let upperBound = Swift.max(high, low + padding)
        return lowerBound...upperBound
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Price History")
                        .font(.headline)
                        .foregroundColor(.textPrimary)
                    Text("\(ticker) · last \(days) days")
                        .font(.caption)
                        .foregroundColor(.textSecondary)
                }
                Spacer()
                if !chartPrices.isEmpty {
                    Text(priceDirectionLabel)
                        .font(.caption.weight(.semibold))
                        .foregroundColor(priceDirectionColor)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(priceDirectionColor.opacity(0.12))
                        .clipShape(Capsule())
                }
            }

            if chartPrices.isEmpty {
                Text("No price data available")
                    .font(.subheadline)
                    .foregroundColor(.textSecondary)
                    .frame(height: 200)
            } else {
                Chart(chartPrices) { point in
                    LineMark(
                        x: .value("Date", point.recordedAt),
                        y: .value("Price", point.price)
                    )
                    .interpolationMethod(.linear)
                    .lineStyle(StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))
                    .foregroundStyle(priceDirectionColor.gradient)
                }
                .chartYScale(domain: yRange ?? 0...100)
                .chartXAxis(.hidden)
                .chartYAxis(.hidden)
                .frame(height: 220)

                HStack {
                    VStack(alignment: .leading) {
                        Text("Low")
                            .font(.caption)
                            .foregroundColor(.textSecondary)
                        Text("$\(Int(chartPrices.map { $0.price }.min() ?? 0))")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.textPrimary)
                    }
                    Spacer()
                    VStack {
                        Text("High")
                            .font(.caption)
                            .foregroundColor(.textSecondary)
                        Text("$\(Int(chartPrices.map { $0.price }.max() ?? 0))")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.textPrimary)
                    }
                    Spacer()
                    VStack {
                        Text("Current")
                            .font(.caption)
                            .foregroundColor(.textSecondary)
                        Text("$\(Int(chartPrices.last?.price ?? 0))")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.textPrimary)
                    }
                }
            }
        }
        .padding()
        .clavisCardStyle()
    }

    private var priceDirectionColor: Color {
        guard let first = chartPrices.first?.price, let last = chartPrices.last?.price else {
            return .accentBlue
        }
        return last >= first ? .successTone : .criticalTone
    }

    private var priceDirectionLabel: String {
        guard let first = chartPrices.first?.price, let last = chartPrices.last?.price, first > 0 else {
            return "Flat"
        }
        let change = ((last - first) / first) * 100
        let prefix = change >= 0 ? "+" : ""
        return "\(prefix)\(String(format: "%.1f", change))%"
    }
}
