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
                                .fill(toggledDimensions.contains(key) ? color : Color.clavixPaper2)
                                .frame(width: 8, height: 8)
                            Text(label)
                                .font(ClavisTypography.clavixMono(11, weight: .semibold))
                                .foregroundColor(toggledDimensions.contains(key) ? .clavixInk : .clavixInk3)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(
                            toggledDimensions.contains(key)
                                ? color.opacity(0.12)
                                : Color.clavixPaper2.opacity(0.8)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .stroke(toggledDimensions.contains(key) ? color.opacity(0.3) : Color.clavixRule2, lineWidth: 1)
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var newIndicator: some View {
        VStack(spacing: 4) {
            Text("New")
                .font(ClavisTypography.clavixMono(14, weight: .bold))
                .foregroundColor(.gradeCBBB)
            Text("Score history requires at least 2 days of data.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.clavixInk3)
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
                    .foregroundStyle(Color.clavixInk)
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
                .font(ClavisTypography.clavixMono(11, weight: .bold))
                .foregroundColor(.gradeCBBB)
                .padding(.vertical, 4)
        } else {
            Chart(snapshots) { snap in
                LineMark(
                    x: .value("Date", snap.date),
                    y: .value("Score", snap.composite)
                )
                .foregroundStyle(Color.clavixInk)
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
    var height: CGFloat = 44

    var body: some View {
        if prices.count < 2 {
            EmptyView()
        } else {
            let values = prices.map { $0.price }
            let minPrice = values.min() ?? 0
            let maxPrice = values.max() ?? 0
            let lastPrice = prices.last?.price ?? 0
            let firstPrice = prices.first?.price ?? 0
            let lineColor: Color = lastPrice >= firstPrice ? .clavixGood : .clavixBad

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
            .frame(height: height)
        }
    }
}

struct TickerPriceChart: View {
    let prices: [PricePoint]
    let tone: Color

    private var yDomain: ClosedRange<Double> {
        let values = prices.map(\.price)
        let minValue = values.min() ?? 0
        let maxValue = values.max() ?? 1
        let spread = max(maxValue - minValue, maxValue * 0.04, 0.01)
        let lower = max(0, minValue - spread * 0.35)
        let upper = maxValue + spread * 0.35
        return lower...upper
    }

    var body: some View {
        if prices.count < 2 {
            Text("Price history unavailable for the selected window.")
                .font(ClavisTypography.clavixCaption)
                .foregroundColor(.clavixInk3)
                .frame(maxWidth: .infinity, minHeight: 120)
        } else {
            Chart(prices) { point in
                LineMark(
                    x: .value("Date", point.recordedAt),
                    y: .value("Price", point.price)
                )
                .interpolationMethod(.linear)
                .foregroundStyle(tone)
                .lineStyle(StrokeStyle(lineWidth: 2.25, lineCap: .round, lineJoin: .round))
            }
            .chartYScale(domain: yDomain)
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .frame(height: 150)
        }
    }
}

struct TickerRadarDimension: Identifiable, Hashable {
    let key: String
    let label: String
    let score: Double?

    var id: String { key }
}

struct TickerRadarChart: View {
    let dimensions: [TickerRadarDimension]
    var size: CGFloat = 168

    private var availableDimensions: [TickerRadarDimension] {
        dimensions.filter { $0.score != nil }
    }

    var body: some View {
        GeometryReader { geometry in
            let frame = min(geometry.size.width, geometry.size.height)
            let center = CGPoint(x: frame / 2, y: frame / 2)
            let radius = frame * 0.34
            let labelRadius = frame * 0.45
            let axisCount = max(dimensions.count, 3)

            ZStack {
                ForEach(1..<4, id: \.self) { ring in
                    let scale = CGFloat(ring) / 3.0
                    Path { path in
                        for index in 0..<axisCount {
                            let point = polygonPoint(
                                center: center,
                                radius: radius * scale,
                                index: index,
                                count: axisCount
                            )
                            if index == 0 {
                                path.move(to: point)
                            } else {
                                path.addLine(to: point)
                            }
                        }
                        path.closeSubpath()
                    }
                    .stroke(Color.clavixRule2, lineWidth: 1)
                }

                ForEach(Array(dimensions.enumerated()), id: \.offset) { index, dimension in
                    let point = polygonPoint(center: center, radius: radius, index: index, count: axisCount)
                    Path { path in
                        path.move(to: center)
                        path.addLine(to: point)
                    }
                    .stroke(Color.clavixRule2, style: StrokeStyle(lineWidth: 1))

                    if dimension.score != nil {
                        Text(dimension.label)
                            .font(ClavisTypography.clavixMono(10, weight: .bold))
                            .foregroundColor(.clavixInk3)
                            .position(
                                polygonPoint(
                                    center: center,
                                    radius: labelRadius,
                                    index: index,
                                    count: axisCount
                                )
                            )
                    }
                }

                if availableDimensions.count >= 2 {
                    let indices = dimensions.enumerated().compactMap { offset, item in
                        item.score == nil ? nil : (offset, item)
                    }

                    Path { path in
                        for (offset, item) in indices {
                            let point = polygonPoint(
                                center: center,
                                radius: radius * CGFloat((item.score ?? 0) / 100.0),
                                index: offset,
                                count: axisCount
                            )
                            if path.isEmpty {
                                path.move(to: point)
                            } else {
                                path.addLine(to: point)
                            }
                        }
                        path.closeSubpath()
                    }
                    .fill(Color.clavixAccentSoft.opacity(0.85))

                    Path { path in
                        for (offset, item) in indices {
                            let point = polygonPoint(
                                center: center,
                                radius: radius * CGFloat((item.score ?? 0) / 100.0),
                                index: offset,
                                count: axisCount
                            )
                            if path.isEmpty {
                                path.move(to: point)
                            } else {
                                path.addLine(to: point)
                            }
                        }
                        path.closeSubpath()
                    }
                    .stroke(Color.clavixAccent, style: StrokeStyle(lineWidth: 2))
                }
            }
            .frame(width: frame, height: frame)
        }
        .frame(width: size, height: size)
    }

    private func polygonPoint(center: CGPoint, radius: CGFloat, index: Int, count: Int) -> CGPoint {
        let angle = (-CGFloat.pi / 2) + (CGFloat(index) * (2 * .pi / CGFloat(count)))
        return CGPoint(
            x: center.x + cos(angle) * radius,
            y: center.y + sin(angle) * radius
        )
    }
}
