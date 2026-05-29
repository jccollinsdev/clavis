import SwiftUI

/// Today tab. Cream/paper VisualQA design ported to live data.
struct DigestView: View {
    @Binding var selectedTab: Int
    @StateObject var viewModel = DigestViewModel()
    @State private var hasLoaded = false
    @State private var showMorningReport = false

    var body: some View {
        NavigationStack {
            content
                .background(Color.clavixPage.ignoresSafeArea())
                .safeAreaInset(edge: .top, spacing: 0) {
                    todayStickyBar
                }
                .toolbar(.hidden, for: .navigationBar)
                .task {
                    guard !hasLoaded else { return }
                    hasLoaded = true
                    await viewModel.loadDigest()
                }
                .refreshable {
                    await viewModel.loadDigest(showLoading: false)
                }
                .navigationDestination(isPresented: $showMorningReport) {
                    MorningReportView(viewModel: viewModel)
                }
                .navigationDestination(for: String.self) { ticker in
                    TickerDetailView(ticker: ticker)
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        if let errorMessage = viewModel.errorMessage, viewModel.todayDigest == nil {
            ScrollView {
                statePanel(
                    glyph: "exclamationmark.triangle",
                    body: digestErrorBody(errorMessage),
                    cta: "Try again",
                    tone: .clavixBad
                ) { Task { await viewModel.loadDigest() } }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 8)
            }
        } else if viewModel.isLoading && viewModel.todayDigest == nil {
            ScrollView {
                VStack(spacing: 16) {
                    ForEach(0..<3, id: \.self) { _ in
                        ClavixCard {
                            VStack(alignment: .leading, spacing: 8) {
                                Rectangle().fill(Color.clavixRule2).frame(height: 10).cornerRadius(2)
                                Rectangle().fill(Color.clavixRule2).frame(height: 10).cornerRadius(2)
                                Rectangle().fill(Color.clavixRule2).frame(width: 120, height: 10).cornerRadius(2)
                            }
                        }
                    }
                }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 8)
            }
        } else if !viewModel.hasHoldings {
            ScrollView {
                statePanel(
                    glyph: "briefcase",
                    body: "Add positions to generate a Today digest and portfolio risk grade.",
                    cta: "Add positions"
                ) { selectedTab = 1 }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 8)
            }
        } else {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    portfolioHero
                    morningReportCard
                    dimensionSnapshot
                    sectorExposure
                    attention
                    bookPreview
                    calendar
                }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 8)
                .padding(.bottom, ClavixLayout.bottomPad)
            }
        }
    }

    // MARK: - Portfolio hero

    private var portfolioHero: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Today's Digest")
                .font(ClavisTypography.clavixSerif(34, weight: .medium))
                .tracking(-0.6)
                .foregroundColor(.clavixInk)

            HStack(alignment: .bottom, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Portfolio value")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                    Text(portfolioValueText)
                        .font(ClavisTypography.clavixMono(29, weight: .semibold))
                        .tracking(-0.6)
                        .foregroundColor(.clavixInk)
                        .lineLimit(1)
                        .minimumScaleFactor(0.76)
                    Text(headerDateText)
                        .font(ClavisTypography.clavixMono(10, weight: .regular))
                        .tracking(0.7)
                        .foregroundColor(.clavixInk3)
                    Text(portfolioDayChangeText)
                        .font(ClavisTypography.clavixMono(12, weight: .regular))
                        .foregroundColor(portfolioDayChangeColor)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    ClavixGradeBadge(portfolioGradeText)
                    Text(compositeLine)
                        .font(ClavisTypography.clavixMono(11, weight: .regular))
                        .foregroundColor(.clavixInk3)
                }
            }
        }
        .padding(.bottom, 14)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.clavixRule).frame(height: 1) }
    }

    // MARK: - Five-axis snapshot

    private var dimensionSnapshot: some View {
        simpleSection(title: "Five-axis snapshot") {
            HStack(spacing: 8) {
                ForEach(dimensionTuples, id: \.0) { code, score in
                    AxisSnapshotCard(code: code, score: score)
                }
            }
        }
    }

    // MARK: - Sector exposure (1:1 VQA sector cell: symbol + name + change/weight)

    private var sectorExposure: some View {
        ClavixSection(eyebrow: "Portfolio sectors", title: "Your sectors") {
            if sectorRows.isEmpty {
                ClavixCard {
                    Text("Sector breakdown will appear once positions have analysis data.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                VStack(spacing: 0) {
                    SectorHeatmapView(
                        items: sectorRows.map {
                            SectorHeatmapItem(
                                id: $0.sector,
                                symbol: $0.etfSymbol,
                                name: $0.shortName,
                                weight: $0.weight,
                                changePct: $0.etfDayChangePct
                            )
                        }
                    )
                    .frame(height: SectorHeatmapView.height(for: sectorRows.count))
                }
                .background(Color.clavixPaper)
                .overlay(RoundedRectangle(cornerRadius: 2, style: .continuous).stroke(Color.clavixRule, lineWidth: 1))
                .clipShape(RoundedRectangle(cornerRadius: 2, style: .continuous))
            }
        }
    }

    // MARK: - Morning Report card

    private var morningReportCard: some View {
        Button { showMorningReport = true } label: {
            ClavixCard {
                HStack(alignment: .top, spacing: 14) {
                    VStack(alignment: .leading, spacing: 5) {
                        ClavixEyebrow("Morning Report")
                        Text(morningReportTitle)
                            .font(ClavisTypography.clavixSerif(18, weight: .medium))
                            .foregroundColor(.clavixInk)
                        Text(morningReportPreview)
                            .font(ClavisTypography.clavixCaption)
                            .foregroundColor(.clavixInk2)
                            .lineLimit(3)
                            .multilineTextAlignment(.leading)
                            .truncationMode(.tail)
                    }
                    Spacer()
                    Text("Open →")
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(.clavixAccent)
                }
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - Attention (alerts preview)

    private var attention: some View {
        simpleSection(title: "Key Alerts", trailing: AnyView(Button("See all →") { selectedTab = 3 }
            .font(ClavisTypography.clavixCaption)
            .foregroundColor(.clavixAccent)
        )) {
            if viewModel.alerts.isEmpty {
                ClavixCard {
                    Text("All quiet.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ForEach(viewModel.alerts.prefix(2), id: \.id) { alert in
                    alertRow(alert)
                }
            }
        }
    }

    /// VQAAlertRow 1:1 — colored bullet dot, category eyebrow, time, headline,
    /// truncated body, trailing meta pill.
    private func alertRow(_ alert: Alert) -> some View {
        let tone = alertTone(alert)
        return ClavixCard(padding: 12) {
            HStack(alignment: .top, spacing: 12) {
                Circle()
                    .fill(tone)
                    .frame(width: 8, height: 8)
                    .padding(.top, 6)
                VStack(alignment: .leading, spacing: 5) {
                    HStack {
                        Text(alertCategoryLabel(alert).uppercased())
                            .font(ClavisTypography.clavixMono(9, weight: .bold))
                            .tracking(0.7)
                            .foregroundColor(tone)
                        Text(alert.createdAt.formatted(date: .omitted, time: .shortened))
                            .font(ClavisTypography.clavixMono(10, weight: .regular))
                            .foregroundColor(.clavixInk3)
                    }
                    Text(alertHeadline(alert))
                        .font(ClavisTypography.clavixSerif(15, weight: .medium))
                        .foregroundColor(.clavixInk)
                        .lineLimit(2)
                        .multilineTextAlignment(.leading)
                    if let body = alertBody(alert) {
                        Text(body)
                            .font(ClavisTypography.clavixCaption)
                            .foregroundColor(.clavixInk2)
                            .lineLimit(2)
                    }
                }
                Spacer()
                if let meta = alertMeta(alert) {
                    Text(meta)
                        .font(ClavisTypography.clavixMono(10, weight: .bold))
                        .foregroundColor(.clavixInk3)
                }
            }
        }
    }

    private func alertTone(_ alert: Alert) -> Color {
        switch alert.type {
        case .gradeChange, .safetyDeterioration: return .clavixBad
        case .majorEvent, .macroShock:            return .clavixWarn
        case .portfolioGradeChange, .portfolioSafetyThresholdBreach: return .clavixInk
        case .digestReady, .ratingReady:          return .clavixAccent
        case .concentrationDanger, .clusterRisk, .structuralFragility: return .clavixBad
        }
    }

    private func alertHeadline(_ alert: Alert) -> String {
        let text = alert.message.sanitizedDisplayText
        // Headlines are typically the first sentence of the message.
        if let dot = text.firstIndex(of: ".") {
            return String(text[..<dot]).trimmingCharacters(in: .whitespaces)
        }
        return text
    }

    private func alertBody(_ alert: Alert) -> String? {
        let text = alert.message.sanitizedDisplayText
        guard let dot = text.firstIndex(of: ".") else { return nil }
        let after = text[text.index(after: dot)...].trimmingCharacters(in: .whitespaces)
        return after.isEmpty ? nil : String(after)
    }

    private func alertMeta(_ alert: Alert) -> String? {
        if let new = alert.newGrade, !new.isEmpty {
            if let delta = alert.changeDetails?["score_delta"]?.sanitizedDisplayText, !delta.isEmpty {
                return "\(new) \(delta)"
            }
            return new
        }
        if let ticker = alert.positionTicker, !ticker.isEmpty {
            return ticker
        }
        return nil
    }

    // MARK: - Your Positions

    private var bookPreview: some View {
        simpleSection(title: "Your Positions", trailing: AnyView(Button("Holdings →") { selectedTab = 1 }
            .font(ClavisTypography.clavixCaption)
            .foregroundColor(.clavixAccent)
        )) {
            ClavixCard(padding: 0) {
                VStack(spacing: 0) {
                    HStack {
                        Text("SYM")
                        Spacer()
                        Text("GRADE · DELTA · TODAY")
                    }
                    .font(ClavisTypography.clavixMono(9, weight: .bold))
                    .foregroundColor(.clavixInk3)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    Rectangle().fill(Color.clavixRule).frame(height: 1)

                    let movers = topMovers
                    if movers.isEmpty {
                        Text("Holdings load once analysis completes.")
                            .font(ClavisTypography.clavixCaption)
                            .foregroundColor(.clavixInk3)
                            .padding(14)
                    } else {
                        ForEach(Array(movers.enumerated()), id: \.element.id) { index, position in
                            NavigationLink(value: position.ticker) {
                                bookRow(position)
                            }
                            .buttonStyle(.plain)
                            if index < movers.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    /// VQABookRow 1:1 — ticker + grade + delta + today%.
    private func bookRow(_ position: Position) -> some View {
        HStack(alignment: .center, spacing: 10) {
            Text(position.ticker)
                .font(ClavisTypography.clavixMono(13, weight: .bold))
                .foregroundColor(.clavixInk)
            Spacer()
            ClavixGradeBadge(position.resolvedRiskGrade ?? "—", size: 24)
            Text(deltaText(for: position.scoreDelta))
                .font(ClavisTypography.clavixMono(11, weight: .semibold))
                .foregroundColor(deltaColor(for: position.scoreDelta))
                .frame(width: 32, alignment: .trailing)
            Text(todayText(for: position))
                .font(ClavisTypography.clavixMono(11, weight: .semibold))
                .foregroundColor(todayColor(for: position))
                .frame(width: 56, alignment: .trailing)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
    }

    private func deltaText(for delta: Int?) -> String {
        guard let delta else { return "—" }
        if delta == 0 { return "—" }
        return delta > 0 ? "+\(delta)" : "\(delta)"
    }

    private func deltaColor(for delta: Int?) -> Color {
        guard let delta else { return .clavixInk3 }
        if delta > 0 { return .clavixGood }
        if delta < 0 { return .clavixBad }
        return .clavixInk3
    }

    private func todayText(for position: Position) -> String {
        guard let pct = position.sharedAnalysis?.dayChangePct else { return "—" }
        return String(format: "%@%.1f%%", pct >= 0 ? "+" : "", pct)
    }

    private func todayColor(for position: Position) -> Color {
        guard let pct = position.sharedAnalysis?.dayChangePct else { return .clavixInk3 }
        if pct > 0.05 { return .clavixGood }
        if pct < -0.05 { return .clavixBad }
        return .clavixInk3
    }

    // MARK: - Calendar

    private var calendar: some View {
        simpleSection(title: "What to Watch") {
            let todayItems = viewModel.today?.calendar ?? []
            let items = viewModel.todayDigest?.structuredSections?.whatToWatchToday?.catalysts ?? []
            if !items.isEmpty {
                ClavixCard {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                            Text(whatToWatchText(for: item))
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
            } else if !todayItems.isEmpty {
                ClavixCard {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(Array(todayItems.enumerated()), id: \.element.id) { index, item in
                            Text(item.title?.sanitizedDisplayText ?? "Scheduled event")
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixInk2)
                                .fixedSize(horizontal: false, vertical: true)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            if index < todayItems.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            } else {
                ClavixCard {
                    Text("No scheduled events surfaced for your portfolio today.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func whatToWatchText(for item: DigestWhatMattersItem) -> String {
        let raw = item.catalyst.sanitizedDisplayText
        let (_, _, title) = parseCalendarLine(raw, tickers: item.impactedPositions)
        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? raw : trimmed
    }

    /// Parse "HH:MM TYPE rest…" out of a digest catalyst string. When the
    /// digest doesn't provide structured time/type, fall back to leaving the
    /// time slot empty and inferring a type from the impacted-tickers list.
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
                return (time, typeOrWord, parts[2])
            }
            return (time, typeForTicker(tickers), parts.dropFirst().joined(separator: " "))
        }
        return ("—", typeForTicker(tickers), raw)
    }

    private func typeForTicker(_ tickers: [String]) -> String {
        if tickers.contains(where: { $0.uppercased() == "FED" || $0.uppercased() == "MACRO" }) { return "FED" }
        if !tickers.isEmpty { return "EARN" }
        return "DATA"
    }

    // MARK: - State card

    private func statePanel(
        glyph: String,
        body: String,
        cta: String,
        tone: Color = .clavixInk,
        action: @escaping () -> Void
    ) -> some View {
        ClavixStatePanel(
            glyph: glyph,
            message: body,
            cta: cta,
            tone: tone,
            action: action
        )
    }

    // MARK: - Computed values

    private var headerDateText: String {
        // VQA spec: "FRIDAY · MAY 9 · 7:02 ET" — bullet-separated, dot-style.
        let now = Date()
        let weekday = now.formatted(.dateTime.weekday(.wide)).uppercased()
        let day = now.formatted(.dateTime.month(.abbreviated).day())
        let time = now.formatted(.dateTime.hour(.defaultDigits(amPM: .omitted)).minute())
        let tz = TimeZone.current.abbreviation() ?? ""
        return "\(weekday) · \(day) · \(time) \(tz)"
    }

    private var portfolioValueText: String {
        if let value = viewModel.today?.portfolio.value, value > 0 {
            return formatCurrency(value)
        }
        let total = viewModel.holdings.compactMap(\.currentValue).reduce(0, +)
        guard total > 0 else { return "—" }
        return formatCurrency(total)
    }

    private var portfolioGradeText: String {
        if let grade = viewModel.today?.portfolio.grade, !grade.isEmpty {
            return grade
        }
        if !viewModel.holdings.isEmpty,
           PortfolioMath.weightedScore(viewModel.holdings) != nil {
            return PortfolioMath.weightedGrade(viewModel.holdings)
        }
        return viewModel.todayDigest?.structuredSections?.header?.portfolioGrade
            ?? viewModel.todayDigest?.overallGrade
            ?? "—"
    }

    private var compositeLine: String {
        if let score = viewModel.today?.portfolio.compositeScore {
            return "Composite \(Int(score.rounded()))"
        }
        if let weighted = PortfolioMath.weightedScore(viewModel.holdings) {
            return "Composite \(Int(weighted.rounded()))"
        }
        if let overall = viewModel.todayDigest?.overallScore {
            return "Composite \(Int(overall.rounded()))"
        }
        return "Composite —"
    }

    /// Sum of (shares × day_change_amount) across holdings whose backend payload
    /// includes a previous-close price. Returns "—" when no positions report it.
    private var portfolioDayChangeText: String {
        // VQA format: "-$5,438 today" — dollar amount + "today", no percentage
        if let amount = viewModel.today?.portfolio.dayChangeAmount {
            let sign = amount >= 0 ? "+" : "−"
            return "\(sign)\(formatCurrency(abs(amount))) today"
        }
        let positions = viewModel.holdings
        var totalDelta: Double = 0
        var totalPrev: Double = 0
        var anyReported = false
        for position in positions {
            guard let dayChange = position.sharedAnalysis?.dayChangeAmount,
                  let prevClose = position.sharedAnalysis?.previousClose else { continue }
            anyReported = true
            totalDelta += dayChange * position.shares
            totalPrev += prevClose * position.shares
        }
        guard anyReported, totalPrev > 0 else { return "—" }
        let sign = totalDelta >= 0 ? "+" : "−"
        return "\(sign)\(formatCurrency(abs(totalDelta))) today"
    }

    private var portfolioDayChangeColor: Color {
        if let amount = viewModel.today?.portfolio.dayChangeAmount {
            if amount > 0 { return .clavixGood }
            if amount < 0 { return .clavixBad }
            return .clavixInk3
        }
        let positions = viewModel.holdings
        var totalDelta: Double = 0
        var anyReported = false
        for position in positions {
            guard let dayChange = position.sharedAnalysis?.dayChangeAmount else { continue }
            anyReported = true
            totalDelta += dayChange * position.shares
        }
        guard anyReported else { return .clavixInk3 }
        if totalDelta > 0 { return .clavixGood }
        if totalDelta < 0 { return .clavixBad }
        return .clavixInk3
    }

    private func formatCurrency(_ value: Double) -> String {
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.maximumFractionDigits = value >= 1000 ? 0 : 2
        return f.string(from: NSNumber(value: value)) ?? "$0"
    }

    private var morningReportTitle: String {
        if viewModel.todayDigest != nil {
            return "Your daily risk brief is ready"
        }
        return "Briefing not generated yet"
    }

    private var morningReportPreview: String {
        if let line = viewModel.todayDigest?.structuredSections?.header?.summaryLine,
           !line.isEmpty {
            return line.sanitizedDisplayText
        }
        if let text = viewModel.todayDigest?.summary?.sanitizedDisplayText, !text.isEmpty {
            return text
        }
        return "Open to see overnight macro, sector heat, and per-position changes."
    }

    /// Portfolio per-dimension snapshot. Each cell is the value-weighted average
    /// of the dimension across held tickers; "—" when no ticker exposes that
    /// dimension yet (CLAVIX_TRUTH §6 limited-data rule).
    private var dimensionTuples: [(String, Int?)] {
        if let dimensions = viewModel.today?.dimensions, !dimensions.isEmpty {
            return dimensions.map { item in
                (item.code, item.score.map { Int($0.rounded()) })
            }
        }
        let entries: [(String, (SharedRiskDimensions) -> Double?)] = [
            ("FIN",  { $0.financialHealth }),
            ("NEWS", { $0.newsSentiment }),
            ("MAC",  { $0.macroExposure }),
            ("SEC",  { $0.sectorExposure }),
            ("VOL",  { $0.volatility }),
        ]
        return entries.map { label, extract in
            var num = 0.0
            var denom = 0.0
            for position in viewModel.holdings {
                guard let dims = position.sharedAnalysis?.riskDimensions,
                      let score = extract(dims),
                      let value = position.currentValue,
                      value > 0 else { continue }
                num += score * value
                denom += value
            }
            if denom == 0 {
                return (label, nil)
            }
            return (label, Int((num / denom).rounded()))
        }
    }

    private struct SectorRow {
        let sector: String
        let weight: Double
        let etf: String?
        let etfDayChangePct: Double?

        private var normalizedSector: String {
            switch sector.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
            case "sem", "semis", "semiconductors", "semiconductor": return "Semiconductors"
            case "information technology", "technology": return "Technology"
            default: return sector
            }
        }

        /// Canonical ETF for the sector when known; falls back to the first two
        /// letters of the sector for unmapped industries.
        var etfSymbol: String {
            if let etf, !etf.isEmpty { return etf }
            switch normalizedSector.lowercased() {
            case "tech", "technology", "information technology": return "XLK"
            case "semiconductors", "semis":                      return "SOXX"
            case "health care", "healthcare":                    return "XLV"
            case "financials", "financial services":     return "XLF"
            case "energy":                                return "XLE"
            case "consumer discretionary":                return "XLY"
            case "consumer staples":                      return "XLP"
            case "industrials":                           return "XLI"
            case "utilities":                             return "XLU"
            case "materials":                             return "XLB"
            case "real estate":                           return "XLRE"
            case "communication services":                return "XLC"
            case "us total market":                       return "VTI"
            default:
                return String(normalizedSector.prefix(3)).uppercased()
            }
        }

        var shortName: String {
            switch normalizedSector.lowercased() {
            case "tech", "technology":                       return "Technology"
            case "information technology":                   return "Tech"
            case "semiconductors", "semis":                  return "Semis"
            case "health care", "healthcare":                return "Health"
            case "financials", "financial services":         return "Financials"
            case "consumer discretionary":                   return "Consumer D"
            case "consumer staples":                         return "Consumer S"
            case "communication services":                   return "Comm Svcs"
            case "us total market":                          return "US Total"
            default: return normalizedSector
            }
        }

        var changeText: String {
            guard let pct = etfDayChangePct else { return "—" }
            return String(format: "%@%.1f%%", pct >= 0 ? "+" : "", pct)
        }
    }

    private var sectorRows: [SectorRow] {
        if let sectors = viewModel.today?.sectorExposure, !sectors.isEmpty {
            return sectors.prefix(6).map {
                SectorRow(
                    sector: $0.sector,
                    weight: $0.portfolioWeightPct / 100.0,
                    etf: $0.etf,
                    etfDayChangePct: $0.etfDayChangePct
                )
            }
        }
        let totalValue = viewModel.holdings.compactMap(\.currentValue).reduce(0, +)
        guard totalValue > 0 else { return [] }
        var bySector: [String: Double] = [:]
        for position in viewModel.holdings {
            guard let value = position.currentValue, value > 0 else { continue }
            let sector = position.sharedAnalysis?.sector ?? "Unclassified"
            bySector[sector, default: 0] += value
        }
        return bySector
            .map { SectorRow(sector: $0.key, weight: $0.value / totalValue, etf: nil, etfDayChangePct: nil) }
            .sorted { $0.weight > $1.weight }
            .prefix(6)
            .map { $0 }
    }

    private var todayStickyBar: some View {
        ClavixStickyBar(trailing: AnyView(
            HStack(spacing: 18) {
                Button(action: { selectedTab = 2 }) {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.clavixInk)
                }
                Button(action: { selectedTab = 3 }) {
                    Image(systemName: "bell")
                        .foregroundColor(.clavixInk)
                }
            }
        ))
    }

    private func simpleSection<Content: View>(
        title: String,
        trailing: AnyView? = nil,
        @ViewBuilder content: @escaping () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text(title)
                    .font(ClavisTypography.clavixSerif(20, weight: .medium))
                    .tracking(-0.3)
                    .foregroundColor(.clavixInk)
                Spacer()
                if let trailing {
                    trailing
                }
            }
            content()
        }
        .padding(.top, 6)
    }

    private func digestErrorBody(_ errorMessage: String) -> String {
        "Clavix could not refresh this view. Your last saved portfolio is unchanged."
    }

    private var topMovers: [Position] {
        viewModel.holdings
            .sorted { abs($0.scoreDelta ?? 0) > abs($1.scoreDelta ?? 0) }
            .prefix(5)
            .map { $0 }
    }

    private func alertCategoryLabel(_ alert: Alert) -> String {
        // Map known internal types to user-facing categories without exposing raw status.
        switch alert.type {
        case .gradeChange:              return "Grade"
        case .majorEvent:               return "News"
        case .portfolioGradeChange,
             .portfolioSafetyThresholdBreach:
                                         return "Port"
        case .macroShock:               return "Macro"
        case .safetyDeterioration,
             .concentrationDanger,
             .clusterRisk,
             .structuralFragility:      return "Risk"
        case .ratingReady, .digestReady:return "Update"
        }
    }
}

private struct AxisSnapshotCard: View {
    let code: String
    let score: Int?

    private var tone: Color {
        axisTone(for: score)
    }

    private var scoreText: String {
        score.map(String.init) ?? "—"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(code)
                .font(ClavisTypography.clavixMono(10, weight: .bold))
                .tracking(0.5)
                .foregroundColor(.clavixInk3)
            Text(scoreText)
                .font(ClavisTypography.clavixMono(22, weight: .semibold))
                .foregroundColor(score == nil ? .clavixInk3 : tone)
            AxisScorePill(score: score, tone: tone)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(score == nil ? Color.clavixPaper : tone.opacity(0.13))
        .overlay(Rectangle().stroke(score == nil ? Color.clavixRule : tone.opacity(0.42), lineWidth: 1))
    }
}

    private struct AxisScorePill: View {
    let score: Int?
    let tone: Color

    private var fillCount: Int {
        guard let score else { return 0 }
        return min(max(score, 0), 100)
    }

    var body: some View {
        HStack(spacing: 0) {
            segmentView(index: 0)
            separator
            segmentView(index: 1)
            separator
            segmentView(index: 2)
            separator
            segmentView(index: 3)
            separator
            segmentView(index: 4)
        }
        .padding(2)
        .background(Color.clavixPaper)
        .overlay(Rectangle().stroke(score == nil ? Color.clavixRule : tone.opacity(0.40), lineWidth: 1))
    }

    private func segmentView(index: Int) -> some View {
        let lower = index * 20
        let upper = lower + 20
        let segmentFill: CGFloat
        if fillCount <= lower {
            segmentFill = 0
        } else if fillCount >= upper {
            segmentFill = 1
        } else {
            segmentFill = CGFloat(fillCount - lower) / 20.0
        }

        return GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(tone.opacity(score == nil ? 0.08 : 0.15))
                Rectangle()
                    .fill(tone.opacity(0.90))
                    .frame(width: geo.size.width * segmentFill)
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: 14)
    }

    private var separator: some View {
        Rectangle()
            .fill(Color.clavixPaper)
            .frame(width: 2, height: 14)
    }
}

private func axisTone(for score: Int?) -> Color {
    guard let score else { return .clavixInk3 }
    return score >= 50 ? .clavixGood : .clavixBad
}
