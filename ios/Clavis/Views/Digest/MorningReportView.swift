import SwiftUI

struct MorningReportView: View {
    @ObservedObject var viewModel: DigestViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Today's Morning Digest")
                    .font(ClavisTypography.clavixSerif(28, weight: .medium))
                    .tracking(-0.5)
                    .foregroundColor(.clavixInk)
                    .padding(.top, 4)

                if let digest = viewModel.todayDigest {
                    masthead(digest)
                    macroSection(digest)
                    sectorSection(digest)
                    positionsSection(digest)
                    watchlistSection(digest)
                    whatToWatchSection(digest)
                    methodologyCard(digest)
                } else {
                    ClavixCard {
                        Text("No digest is available yet for today.")
                            .font(ClavisTypography.clavixCaption)
                            .foregroundColor(.clavixInk2)
                    }
                }
            }
            .padding(.horizontal, ClavixLayout.pad)
            .padding(.top, 8)
            .padding(.bottom, ClavixLayout.bottomPad)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .safeAreaInset(edge: .top, spacing: 0) {
            morningReportBar
        }
        .toolbar(.hidden, for: .navigationBar)
    }

    private var morningReportBar: some View {
        ZStack {
            HStack(spacing: 12) {
                Button(action: { dismiss() }) {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundColor(.clavixInk)
                }
                .buttonStyle(.plain)
                Spacer(minLength: 8)
                NavigationLink(destination: MethodologyView()) {
                    Image(systemName: "doc")
                        .foregroundColor(.clavixInk)
                }
                .buttonStyle(.plain)
            }
            Text("CLAVIX")
                .font(ClavisTypography.clavixMono(21, weight: .bold))
                .tracking(1.5)
                .foregroundColor(.clavixInk)
        }
        .padding(.horizontal, ClavixLayout.pad)
        .padding(.vertical, 10)
        .background(Color.clavixPage.ignoresSafeArea(edges: .top))
        .overlay(alignment: .bottom) { Rectangle().fill(Color.clavixRule).frame(height: 1) }
    }

    // MARK: - Portfolio rating hero

    private func masthead(_ digest: Digest) -> some View {
        HStack(alignment: .bottom, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                ClavixEyebrow("Portfolio rating")
                ClavixGradeBadge(portfolioGrade(digest), size: 44)
                Text(mastheadDateLabel(digest))
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .tracking(0.7)
                    .foregroundColor(.clavixInk3)
                Text("Composite score \(compositeScoreDisplay(digest))")
                    .font(ClavisTypography.clavixMono(12, weight: .regular))
                    .foregroundColor(.clavixInk2)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(portfolioDeltaText(digest))
                    .font(ClavisTypography.clavixMono(30, weight: .semibold))
                    .foregroundColor(portfolioDeltaColor(digest))
                    .lineLimit(1)
                Text("day delta")
                    .font(ClavisTypography.clavixMono(9, weight: .regular))
                    .foregroundColor(.clavixInk3)
            }
        }
        .padding(.bottom, 14)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.clavixRule).frame(height: 1) }
    }

    // MARK: - Macro overnight

    private func macroSection(_ digest: Digest) -> some View {
        let section = digest.structuredSections?.overnightMacro
        return ReportRomanSection("I", "Macro overnight") {
            Text(section?.brief.sanitizedDisplayText ?? "Overnight macro section is being generated.")
                .font(ClavisTypography.clavixSerif(16))
                .foregroundColor(.clavixInk)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - Your sectors

    private func sectorSection(_ digest: Digest) -> some View {
        let sectorHeat = digest.structuredSections?.sectorHeat ?? []
        let todaySectors = viewModel.today?.sectorExposure ?? []
        return ReportRomanSection("II", "Your sectors") {
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

    // MARK: - Position changes

    private func positionsSection(_ digest: Digest) -> some View {
        let positions = digest.structuredSections?.positions ?? []
        return ReportRomanSection("III", "Position changes") {
            if positions.isEmpty {
                ClavixCard {
                    Text("No material position changes in this briefing.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ForEach(positions, id: \.id) { item in
                    NavigationLink(destination: TickerDetailView(ticker: item.ticker)) {
                        positionCard(item)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func positionCard(_ item: DigestPositionImpact) -> some View {
        ClavixCard(padding: 14) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .center) {
                    HStack(spacing: 8) {
                        Text(item.ticker)
                            .font(ClavisTypography.clavixMono(14, weight: .bold))
                            .foregroundColor(.clavixInk)
                        if let urgency = item.urgency?.sanitizedDisplayText, !urgency.isEmpty {
                            Text(urgency.uppercased())
                                .font(ClavisTypography.clavixMono(9, weight: .bold))
                                .tracking(0.4)
                                .foregroundColor(urgencyTone(item.urgency))
                        }
                    }
                    Spacer()
                    HStack(spacing: 8) {
                        ClavixGradeBadge(viewModel.grade(for: item.ticker), size: 22)
                        Text(deltaText(item.ticker))
                            .font(ClavisTypography.clavixMono(10, weight: .bold))
                            .foregroundColor(deltaTone(item.ticker))
                            .frame(width: 32, alignment: .trailing)
                    }
                }
                Text(fullBlurb(item))
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk2)
                    .fixedSize(horizontal: false, vertical: true)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private func fullBlurb(_ item: DigestPositionImpact) -> String {
        let main = item.impactSummary.sanitizedDisplayText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let watch = item.watchItems.first?.sanitizedDisplayText.trimmingCharacters(in: .whitespacesAndNewlines),
              !watch.isEmpty else { return main }
        if main.hasSuffix(".") || main.hasSuffix("?") || main.hasSuffix("!") {
            return "\(main) \(watch)"
        }
        return "\(main). \(watch)"
    }

    // MARK: - Watchlist alerts

    private func watchlistSection(_ digest: Digest) -> some View {
        let items = trackedTickerItems(digest)
        return ReportRomanSection("IV", "Watchlist alerts") {
            if items.isEmpty {
                ClavixCard {
                    Text("No watchlist updates in this briefing.")
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

    // MARK: - What to Watch

    private func whatToWatchSection(_ digest: Digest) -> some View {
        let items = digest.structuredSections?.whatToWatchToday?.catalysts ?? []
        return ReportRomanSection("V", "What to Watch") {
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

    // MARK: - Generated by card (no section header)

    private func methodologyCard(_ digest: Digest) -> some View {
        ClavixCard(padding: 12, fill: .clavixPaper2) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Generated by Clavix at \(digest.generatedAt.formatted(date: .omitted, time: .shortened)).")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
                NavigationLink(destination: MethodologyView()) {
                    Text("View methodology →")
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(.clavixAccent)
                }
                .buttonStyle(.plain)
            }
        }
    }

    // MARK: - Helpers

    private func portfolioGrade(_ digest: Digest) -> String {
        if let grade = viewModel.today?.portfolio.grade, !grade.isEmpty { return grade }
        if let weighted = PortfolioMath.weightedScore(viewModel.holdings), weighted > 0 {
            return PortfolioMath.weightedGrade(viewModel.holdings)
        }
        return digest.structuredSections?.header?.portfolioGrade ?? digest.overallGrade ?? "—"
    }

    private func portfolioScoreValue(_ digest: Digest) -> Double? {
        if let score = viewModel.today?.portfolio.compositeScore { return score }
        if let weighted = PortfolioMath.weightedScore(viewModel.holdings) { return weighted }
        return digest.overallScore
    }

    private func compositeScoreDisplay(_ digest: Digest) -> String {
        guard let score = portfolioScoreValue(digest) else { return "—" }
        return "\(Int(score.rounded()))"
    }

    private func portfolioDeltaText(_ digest: Digest) -> String {
        if let delta = viewModel.today?.portfolio.scoreDelta {
            let rounded = Int(delta.rounded())
            if rounded == 0 { return "—" }
            return rounded > 0 ? "+\(rounded)" : "\(rounded)"
        }
        if let previous = viewModel.today?.portfolio.previousScore,
           let current = portfolioScoreValue(digest) {
            let delta = Int((current - previous).rounded())
            if delta == 0 { return "—" }
            return delta > 0 ? "+\(delta)" : "\(delta)"
        }
        return "—"
    }

    private func portfolioDeltaColor(_ digest: Digest) -> Color {
        if let delta = viewModel.today?.portfolio.scoreDelta {
            if delta > 0 { return .clavixGood }
            if delta < 0 { return .clavixBad }
        }
        if let previous = viewModel.today?.portfolio.previousScore,
           let current = portfolioScoreValue(digest) {
            let diff = current - previous
            if diff > 0 { return .clavixGood }
            if diff < 0 { return .clavixBad }
        }
        return .clavixInk3
    }

    private func mastheadDateLabel(_ digest: Digest) -> String {
        let f = DateFormatter()
        f.dateFormat = "MMM d, yyyy"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f.string(from: digest.generatedAt).uppercased()
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
        case "high", "elevated", "urgent": return .clavixBad
        case "medium", "moderate": return .clavixWarn
        case "low", "stable": return .clavixGood
        default: return .clavixInk3
        }
    }

    private func trackedTickerItems(_ digest: Digest) -> [String] {
        let structured = digest.structuredSections?.watchlistUpdates
        let watchList = structured?.watchList ?? []
        if !watchList.isEmpty { return watchList }
        return structured?.alerts ?? []
    }

    private func cleanWatchText(_ item: DigestWhatMattersItem) -> String {
        let raw = item.catalyst.sanitizedDisplayText
        let (_, _, title) = parseCalendarLine(raw, tickers: item.impactedPositions)
        let t = title.trimmingCharacters(in: .whitespacesAndNewlines)
        return t.isEmpty ? raw : t
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
        if tickers.contains(where: { $0.uppercased() == "FED" || $0.uppercased() == "MACRO" }) { return "FED" }
        if !tickers.isEmpty { return "EARN" }
        return "DATA"
    }
}

private struct ReportRomanSection<Content: View>: View {
    let roman: String
    let title: String
    @ViewBuilder let content: Content

    init(_ roman: String, _ title: String, @ViewBuilder content: () -> Content) {
        self.roman = roman
        self.title = title
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
            }
            content
        }
        .padding(.top, 8)
    }
}
