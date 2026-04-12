import SwiftUI
import Charts

struct PriceChartView: View {
    let ticker: String
    let prices: [PricePoint]
    var days: Int = 30
    @State private var selectedDate: Date?

    private var chartPrices: [PricePoint] {
        let sortedPrices = prices.sorted { $0.recordedAt < $1.recordedAt }
        var latestByDay: [Date: PricePoint] = [:]
        let calendar = Calendar.current

        for point in sortedPrices {
            let day = calendar.startOfDay(for: point.recordedAt)
            latestByDay[day] = point
        }

        return latestByDay.keys.sorted().compactMap { latestByDay[$0] }
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

    private var selectedPoint: PricePoint? {
        guard !chartPrices.isEmpty else { return nil }
        guard let selectedDate else { return chartPrices.last }

        return chartPrices.min(by: {
            abs($0.recordedAt.timeIntervalSince(selectedDate)) < abs($1.recordedAt.timeIntervalSince(selectedDate))
        })
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

                    if point.id == selectedPoint?.id {
                        PointMark(
                            x: .value("Date", point.recordedAt),
                            y: .value("Price", point.price)
                        )
                        .symbolSize(70)
                        .foregroundStyle(priceDirectionColor)
                    }
                }
                .chartYScale(domain: yRange ?? 0...100)
                .chartXAxis(.hidden)
                .chartYAxis(.hidden)
                .chartXSelection(value: $selectedDate)
                .frame(height: 220)
                .contentShape(Rectangle())

                Text("Drag or tap the chart to inspect a day.")
                    .font(.caption)
                    .foregroundColor(.textSecondary)

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
                        Text(selectedPoint?.id == chartPrices.last?.id ? "Current" : "Selected")
                            .font(.caption)
                            .foregroundColor(.textSecondary)
                        Text("$\(Int(selectedPoint?.price ?? chartPrices.last?.price ?? 0))")
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
