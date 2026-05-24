import SwiftUI
import Charts

struct ScoreHistoryChart: View {
    let snapshots: [ScoreSnapshot]
    let showAllDimensions: Bool
    @Binding var toggledDimensions: Set<String>

    private let dimensionKeys: [(String, String, Color)] = [
        ("financial_health", "Financial Health", .gradeCAA),
        ("news_sentiment", "News Sentiment", .gradeCBBB),
        ("macro_exposure", "Macro Exposure", .gradeCCC),
        ("sector_exposure", "Sector Exposure", .gradeCCCC),
        ("volatility", "Volatility", .gradeCF),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if showAllDimensions {
                dimensionToggles
            }

            if snapshots.count < 2 {
                newIndicator
            } else {
                chartView
            }
        }
    }

    private var dimensionToggles: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(dimensionKeys, id: \.0) { key, label, color in
                    Button(action: {
                        if toggledDimensions.contains(key) {
                            toggledDimensions.remove(key)
                        } else {
                            toggledDimensions.insert(key)
                        }
                    }) {
                        HStack(spacing: 4) {
                            Circle()
                                .fill(toggledDimensions.contains(key) ? color : Color.surfaceElevated)
                                .frame(width: 8, height: 8)
                            Text(label)
                                .font(.system(size: 11, weight: .medium))
                                .foregroundColor(toggledDimensions.contains(key) ? .textPrimary : .textTertiary)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(
                            toggledDimensions.contains(key)
                                ? color.opacity(0.12)
                                : Color.surfaceElevated.opacity(0.6)
                        )
                        .cornerRadius(6)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var newIndicator: some View {
        VStack(spacing: 4) {
            Text("New")
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.gradeCBBB)
            Text("Score history requires at least 2 days of data.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 40)
    }

    private var chartView: some View {
        guard let first = snapshots.first, let lastSnap = snapshots.last else {
            return AnyView(newIndicator)
        }
        return AnyView(
            Chart {
                RectangleMark(
                    xStart: .value("date", first.date),
                    xEnd: .value("date", lastSnap.date),
                    yStart: .value("score", 90),
                    yEnd: .value("score", 100)
                )
                .foregroundStyle(Color.gradeCAAA.opacity(0.08))

                RectangleMark(
                    xStart: .value("date", first.date),
                    xEnd: .value("date", lastSnap.date),
                    yStart: .value("score", 80),
                    yEnd: .value("score", 89)
                )
                .foregroundStyle(Color.gradeCAA.opacity(0.06))

                RectangleMark(
                    xStart: .value("date", first.date),
                    xEnd: .value("date", lastSnap.date),
                    yStart: .value("score", 70),
                    yEnd: .value("score", 79)
                )
                .foregroundStyle(Color.gradeCA.opacity(0.05))

                RectangleMark(
                    xStart: .value("date", first.date),
                    xEnd: .value("date", lastSnap.date),
                    yStart: .value("score", 0),
                    yEnd: .value("score", 59)
                )
                .foregroundStyle(Color.gradeCF.opacity(0.04))

                ForEach(snapshots) { snap in
                    LineMark(
                        x: .value("Date", snap.date),
                        y: .value("Composite", snap.composite)
                    )
                    .foregroundStyle(Color.textPrimary)
                    .lineStyle(StrokeStyle(lineWidth: 2))
                }

                ForEach(dimensionKeys, id: \.0) { key, label, color in
                    if toggledDimensions.contains(key) {
                        ForEach(snapshots) { snap in
                            if let value = snap.dimensionValue(for: key) {
                                LineMark(
                                    x: .value("Date", snap.date),
                                    y: .value(label, value)
                                )
                                .foregroundStyle(color)
                                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 2]))
                            }
                        }
                    }
                }
            }
            .chartYScale(domain: 0...100)
            .chartXAxis {
                AxisMarks(values: .automatic(desiredCount: 5))
            }
            .chartYAxis {
                AxisMarks(values: [0, 25, 50, 75, 100])
            }
            .frame(height: 220)
        )
    }
}

struct ScoreSnapshot: Identifiable, Hashable {
    let id: String
    let date: Date
    let composite: Double
    let financialHealth: Double?
    let newsSentiment: Double?
    let macroExposure: Double?
    let sectorExposure: Double?
    let volatility: Double?

    func dimensionValue(for key: String) -> Double? {
        switch key {
        case "financial_health": return financialHealth
        case "news_sentiment":   return newsSentiment
        case "macro_exposure":   return macroExposure
        case "sector_exposure":  return sectorExposure
        case "volatility":       return volatility
        default:                 return nil
        }
    }
}

struct HeroScoreSparkline: View {
    let snapshots: [ScoreSnapshot]

    var body: some View {
        if snapshots.count < 2 {
            Text("New")
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.gradeCBBB)
                .padding(.vertical, 4)
        } else {
            Chart(snapshots) { snap in
                LineMark(
                    x: .value("Date", snap.date),
                    y: .value("Score", snap.composite)
                )
                .foregroundStyle(Color.textPrimary)
                .lineStyle(StrokeStyle(lineWidth: 1.5))
            }
            .chartYScale(domain: 0...100)
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .frame(height: 40)
        }
    }
}

struct HeroPriceSparkline: View {
    let prices: [PricePoint]

    var body: some View {
        if prices.count < 2 {
            EmptyView()
        } else {
            let values = prices.map { $0.price }
            let minPrice = values.min() ?? 0
            let maxPrice = values.max() ?? 0
            let lastPrice = prices.last?.price ?? 0
            let firstPrice = prices.first?.price ?? 0
            let lineColor: Color = lastPrice >= firstPrice ? .good : .bad

            Chart(prices) { point in
                LineMark(
                    x: .value("Date", point.recordedAt),
                    y: .value("Price", point.price)
                )
                .foregroundStyle(lineColor)
                .lineStyle(StrokeStyle(lineWidth: 1.5))
            }
            .chartYScale(domain: minPrice...max(maxPrice, minPrice + 0.01))
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .frame(height: 44)
        }
    }
}
