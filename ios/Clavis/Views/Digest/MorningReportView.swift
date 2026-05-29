import SwiftUI

/// Full Morning Report (the digest prose). Reached from the Today screen's
/// Morning Report card. Reuses the parent DigestViewModel so the data is
/// already loaded when the user opens it.
struct MorningReportView: View {
    @ObservedObject var viewModel: DigestViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ClavixScreen(
            eyebrow: "Daily risk brief",
            title: "Morning Report",
            trailing: AnyView(
                HStack(spacing: 14) {
                    NavigationLink(destination: MethodologyView()) {
                        Image(systemName: "doc")
                            .foregroundColor(.clavixInk)
                    }
                    .buttonStyle(.plain)

                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark")
                            .foregroundColor(.clavixInk)
                    }
                    .buttonStyle(.plain)
                }
            )
        ) {
            if let digest = viewModel.todayDigest {
                masthead(digest)
                macroSection(digest)
                sectorSection(digest)
                positionsSection(digest)
                watchlistSection(digest)
                whatToWatchSection(digest)
                methodologySection(digest)
            } else {
                ClavixCard {
                    Text("No digest is available yet for today.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk2)
                }
            }
        }
        .toolbar(.hidden, for: .navigationBar)
    }

    private func masthead(_ digest: Digest) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("CLAVIX · MORNING REPORT")
                    .font(ClavisTypography.clavixMono(10, weight: .bold))
                    .tracking(1.5)
                    .foregroundColor(.clavixInk3)
                Spacer()
                Text(mastheadDateLabel(digest))
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk3)
            }

            Text(generatedLine(digest))
                .font(ClavisTypography.clavixSerif(13).italic())
                .foregroundColor(.clavixInk2)

            HStack(alignment: .bottom, spacing: 14) {
                VStack(alignment: .leading, spacing: 5) {
                    ClavixEyebrow("Portfolio rating")
                    HStack(alignment: .lastTextBaseline, spacing: 10) {
                        ClavixGradeBadge(portfolioGrade(digest), size: 44)
                        Text(portfolioCompositeLine(digest))
                            .font(ClavisTypography.clavixMono(14, weight: .regular))
                            .foregroundColor(.clavixInk2)
                    }
                }

                Spacer()

                if historyScores.count >= 2 {
                    DigestSparkline(scores: historyScores)
                        .frame(width: 112, height: 40)
                } else {
                    Text("History unavailable")
                        .font(ClavisTypography.clavixMono(10, weight: .regular))
                        .foregroundColor(.clavixInk3)
                }
            }
        }
        .padding(.bottom, 14)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.clavixInk).frame(height: 2) }
    }

    private func macroSection(_ digest: Digest) -> some View {
        let section = digest.structuredSections?.overnightMacro
        return ReportRomanSection("I", "Macro overnight", tag: "Generic") {
            Text(section?.brief.sanitizedDisplayText ?? "Overnight macro section is being generated.")
                .font(ClavisTypography.clavixSerif(16))
                .foregroundColor(.clavixInk)
                .fixedSize(horizontal: false, vertical: true)

            if let readThrough = section?.themes.first?.sanitizedDisplayText, !readThrough.isEmpty {
                ClavixCard(padding: 12, fill: .clavixPaper2) {
                    Text("READ-THROUGH: \(readThrough)")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk2)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func sectorSection(_ digest: Digest) -> some View {
        let sectorHeat = digest.structuredSections?.sectorHeat ?? []
        let todaySectors = viewModel.today?.sectorExposure ?? []
        return ReportRomanSection("II", "Sector exposure", tag: "Your sectors") {
            // Opening prose: first sectorHeat brief gives the overall sector read
            if let opening = sectorHeat.first?.brief.sanitizedDisplayText, !opening.isEmpty {
                Text(opening)
                    .font(ClavisTypography.clavixSerif(16))
                    .foregroundColor(.clavixInk)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if !todaySectors.isEmpty {
                ClavixCard(padding: 0) {
                    SectorHeatmapView(
                        items: todaySectors.prefix(6).map { s in
                            SectorHeatmapItem(
                                id: s.sector,
                                symbol: s.etf ?? "—",
                                name: s.sector,
                                weight: s.portfolioWeightPct / 100.0,
                                changePct: s.etfDayChangePct
                            )
                        }
                    )
                    .frame(height: SectorHeatmapView.height(for: todaySectors.count))
                }
            } else if !sectorHeat.isEmpty {
                // Fallback: compact display from sectorHeat when Today endpoint hasn't loaded
                ClavixCard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(sectorHeat.prefix(3).enumerated()), id: \.element.id) { index, sector in
                            HStack(spacing: 0) {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("—")
                                        .font(ClavisTypography.clavixMono(12, weight: .bold))
                                        .foregroundColor(.clavixInk)
                                    Text(sector.sector.humanizedTitleCasedDisplayText)
                                        .font(ClavisTypography.clavixCaption)
                                        .foregroundColor(.clavixInk2)
                                        .lineLimit(2)
                                }
                                Spacer()
                            }
                            .padding(12)
                            if index < min(sectorHeat.count, 3) - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            } else {
                ClavixCard {
                    Text("Sector detail is being assembled for your holdings.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            }
        }
    }

    private func positionsSection(_ digest: Digest) -> some View {
        let positions = digest.structuredSections?.positions ?? []
        return ReportRomanSection("III", "Position changes", tag: "Personalised") {
            if positions.isEmpty {
                ClavixCard {
                    Text("No material position changes in this briefing.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard(padding: 0) {
                    VStack(spacing: 0) {
                        HStack(alignment: .center) {
                            ClavixColumnHeader("SYM")
                                .frame(width: 44, alignment: .leading)
                            ClavixColumnHeader("NOTE")
                            Spacer()
                            ClavixColumnHeader("GRADE", align: .center)
                                .frame(width: 40)
                            ClavixColumnHeader("DELTA", align: .trailing)
                                .frame(width: 32)
                        }
                        .padding(10)

                        Rectangle().fill(Color.clavixRule).frame(height: 1)

                        ForEach(Array(positions.enumerated()), id: \.element.id) { index, item in
                            NavigationLink(destination: TickerDetailView(ticker: item.ticker)) {
                                positionRow(item)
                            }
                            .buttonStyle(.plain)

                            if index < positions.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    private func positionRow(_ item: DigestPositionImpact) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text(item.ticker)
                .font(ClavisTypography.clavixMono(12, weight: .bold))
                .foregroundColor(.clavixInk)
                .frame(width: 44, alignment: .leading)

            VStack(alignment: .leading, spacing: 4) {
                if let urgency = item.urgency?.sanitizedDisplayText, !urgency.isEmpty {
                    Text(urgency.uppercased())
                        .font(ClavisTypography.clavixMono(9, weight: .bold))
                        .tracking(0.4)
                        .foregroundColor(urgencyTone(item.urgency))
                }

                Text(item.impactSummary.sanitizedDisplayText)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk2)
                    .lineLimit(3)
                    .multilineTextAlignment(.leading)

                if let watch = item.watchItems.first?.sanitizedDisplayText, !watch.isEmpty {
                    Text(watch)
                        .font(ClavisTypography.clavixMono(10, weight: .regular))
                        .foregroundColor(.clavixInk3)
                        .lineLimit(2)
                }
            }

            Spacer()

            ClavixGradeBadge(viewModel.grade(for: item.ticker), size: 22)

            Text(deltaText(item.ticker))
                .font(ClavisTypography.clavixMono(10, weight: .bold))
                .foregroundColor(deltaTone(item.ticker))
                .frame(width: 32, alignment: .trailing)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
    }

    private func watchlistSection(_ digest: Digest) -> some View {
        let items = trackedTickerItems(digest)
        return ReportRomanSection("IV", "Tracked tickers", tag: "\(items.count) names") {
            if items.isEmpty {
                ClavixCard {
                    Text("No tracked-ticker updates in this briefing.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                            Text(item.sanitizedDisplayText)
                                .font(ClavisTypography.clavixSerif(15))
                                .foregroundColor(.clavixInk)
                                .fixedSize(horizontal: false, vertical: true)

                            if index < items.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    private func whatToWatchSection(_ digest: Digest) -> some View {
        let items = digest.structuredSections?.whatToWatchToday?.catalysts ?? []
        return ReportRomanSection("V", "What to Watch", tag: "Catalysts") {
            if items.isEmpty {
                ClavixCard {
                    Text("No scheduled events surfaced for your portfolio today.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                            Text(cleanWatchText(item))
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixInk2)
                                .fixedSize(horizontal: false, vertical: true)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            if index < items.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    private func cleanWatchText(_ item: DigestWhatMattersItem) -> String {
        let raw = item.catalyst.sanitizedDisplayText
        let (_, _, title) = parseCalendarLine(raw, tickers: item.impactedPositions)
        let t = title.trimmingCharacters(in: .whitespacesAndNewlines)
        return t.isEmpty ? raw : t
    }

    private func methodologySection(_ digest: Digest) -> some View {
        ReportRomanSection("VI", "Sources & Methodology", tag: "Audit") {
            ClavixCard(padding: 12, fill: .clavixPaper2) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Generated by Clavix at \(digest.generatedAt.formatted(date: .omitted, time: .shortened)).")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)

                    NavigationLink(destination: MethodologyView()) {
                        Text("View full methodology →")
                            .font(ClavisTypography.clavixMono(11, weight: .semibold))
                            .foregroundColor(.clavixAccent)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: - Helpers

    private func portfolioGrade(_ digest: Digest) -> String {
        if let grade = viewModel.today?.portfolio.grade, !grade.isEmpty {
            return grade
        }
        if let weighted = PortfolioMath.weightedScore(viewModel.holdings), weighted > 0 {
            return PortfolioMath.weightedGrade(viewModel.holdings)
        }
        return digest.structuredSections?.header?.portfolioGrade ?? digest.overallGrade ?? "—"
    }

    private func portfolioScoreValue(_ digest: Digest) -> Double? {
        if let score = viewModel.today?.portfolio.compositeScore {
            return score
        }
        if let weighted = PortfolioMath.weightedScore(viewModel.holdings) {
            return weighted
        }
        return digest.overallScore
    }

    private func portfolioCompositeLine(_ digest: Digest) -> String {
        let currentText = portfolioScoreValue(digest).map { "composite \(Int($0.rounded()))" } ?? "composite —"

        if let previous = viewModel.today?.portfolio.previousScore {
            return "\(currentText) · was \(Int(previous.rounded()))"
        }

        if let delta = viewModel.today?.portfolio.scoreDelta {
            let rounded = Int(delta.rounded())
            if rounded == 0 {
                return "\(currentText) · —"
            }
            return "\(currentText) · \(rounded > 0 ? "+" : "")\(rounded)"
        }

        if historyScores.count <= 1, portfolioScoreValue(digest) != nil {
            return "\(currentText) · New"
        }

        return "\(currentText) · —"
    }

    private var historyScores: [Double] {
        let scores = viewModel.digestHistory.compactMap(\.overallScore)
        if !scores.isEmpty {
            return scores
        }
        if let digest = viewModel.todayDigest, let current = portfolioScoreValue(digest) {
            return [current]
        }
        return []
    }

    private func mastheadDateLabel(_ digest: Digest) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter.string(from: digest.generatedAt).uppercased()
    }

    private func generatedLine(_ digest: Digest) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEE, MMM d, yyyy · 'generated' h:mm a z"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = .current
        return formatter.string(from: digest.generatedAt)
    }

    private func deltaText(_ ticker: String) -> String {
        guard let delta = viewModel.scoreDelta(for: ticker) else { return "—" }
        if delta == 0 { return "—" }
        return delta > 0 ? "+\(delta)" : "\(delta)"
    }

    private func deltaTone(_ ticker: String) -> Color {
        guard let delta = viewModel.scoreDelta(for: ticker) else { return .clavixInk3 }
        if delta == 0 { return .clavixInk3 }
        return delta > 0 ? .clavixGood : .clavixBad
    }

    private func urgencyTone(_ urgency: String?) -> Color {
        switch urgency?.lowercased() {
        case "high", "elevated", "urgent":
            return .clavixBad
        case "medium", "moderate":
            return .clavixWarn
        case "low", "stable":
            return .clavixGood
        default:
            return .clavixInk3
        }
    }

    private func trackedTickerItems(_ digest: Digest) -> [String] {
        let structured = digest.structuredSections?.watchlistUpdates
        let watchList = structured?.watchList ?? []
        if !watchList.isEmpty {
            return watchList
        }
        return structured?.alerts ?? []
    }

    private func parseCalendarLine(_ raw: String, tickers: [String]) -> (String, String, String) {
        let parts = raw.split(separator: " ", maxSplits: 2, omittingEmptySubsequences: true).map(String.init)
        let timeRegex = try? NSRegularExpression(pattern: "^\\d{1,2}:\\d{2}$")
        if let first = parts.first,
           let regex = timeRegex,
           regex.firstMatch(in: first, range: NSRange(first.startIndex..., in: first)) != nil,
           parts.count >= 2 {
            let time = first
            let typeOrWord = parts[1]
            let isType = typeOrWord.uppercased() == typeOrWord && typeOrWord.count <= 6
            if isType, parts.count >= 3 {
                return (time, typeOrWord, parts[2].sanitizedDisplayText)
            }
            return (time, calendarType(tickers), parts.dropFirst().joined(separator: " ").sanitizedDisplayText)
        }
        return ("—", calendarType(tickers), raw.sanitizedDisplayText)
    }

    private func calendarType(_ tickers: [String]) -> String {
        if tickers.contains(where: { $0.uppercased() == "FED" || $0.uppercased() == "MACRO" }) {
            return "FED"
        }
        if !tickers.isEmpty {
            return "EARN"
        }
        return "DATA"
    }
}

private struct ReportRomanSection<Content: View>: View {
    let roman: String
    let title: String
    let tag: String
    @ViewBuilder let content: Content

    init(_ roman: String, _ title: String, tag: String, @ViewBuilder content: () -> Content) {
        self.roman = roman
        self.title = title
        self.tag = tag
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("§ \(roman)")
                    .font(ClavisTypography.clavixSerif(22, weight: .medium))
                    .foregroundColor(.clavixInk)
                Text(title)
                    .font(ClavisTypography.clavixSerif(22, weight: .medium))
                    .foregroundColor(.clavixInk)
                Spacer()
                ClavixEyebrow(tag)
            }
            content
        }
        .padding(.top, 8)
    }
}

private struct DigestSparkline: View {
    let scores: [Double]

    var body: some View {
        GeometryReader { geo in
            Path { path in
                let values = scores.map { min(max($0, 0), 100) }
                let minValue = values.min() ?? 0
                let maxValue = values.max() ?? 100
                let range = max(maxValue - minValue, 1)
                let stepX = values.count > 1 ? geo.size.width / CGFloat(values.count - 1) : 0

                for (index, value) in values.enumerated() {
                    let normalized = (value - minValue) / range
                    let y = geo.size.height - CGFloat(normalized) * max(geo.size.height - 2, 1) - 1
                    let point = CGPoint(x: CGFloat(index) * stepX, y: y)
                    if index == 0 {
                        path.move(to: point)
                    } else {
                        path.addLine(to: point)
                    }
                }
            }
            .stroke(Color.clavixAccent, lineWidth: 1.5)
        }
    }
}
