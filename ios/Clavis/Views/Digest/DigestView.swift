import SwiftUI

/// Today tab. Cream/paper VisualQA design ported to live data.
/// Heavy editorial content lives in `MorningReportView`, presented from the
/// Morning Report card.
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
                    ClavixLargeHeader(
                        eyebrow: "Morning Report",
                        title: "Today",
                        trailing: AnyView(
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
                        )
                    )
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
                stateCard(
                    title: "Briefing unavailable",
                    body: errorMessage,
                    cta: "Retry"
                ) {
                    Task { await viewModel.loadDigest() }
                }
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
                stateCard(
                    title: "No positions yet",
                    body: "Add positions to generate a Morning Report and portfolio risk grade.",
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
            HStack {
                Text(headerDateText)
                Spacer()
                Text(freshnessLabel)
            }
            .font(ClavisTypography.clavixMono(10, weight: .regular))
            .tracking(0.7)
            .foregroundColor(.clavixInk3)

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
                    // Day-change line intentionally absent until backend exposes
                    // per-position previous_close on /holdings (P1-2).
                    Text("Today —")
                        .font(ClavisTypography.clavixMono(12, weight: .regular))
                        .foregroundColor(.clavixInk3)
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

    // MARK: - Five-axis snapshot

    private var dimensionSnapshot: some View {
        ClavixSection(eyebrow: "Portfolio risk by dimension", title: "Five-axis snapshot") {
            HStack(spacing: 1) {
                ForEach(dimensionTuples, id: \.0) { code, score in
                    VStack(spacing: 8) {
                        Text(code)
                            .font(ClavisTypography.clavixMono(10, weight: .bold))
                            .foregroundColor(.clavixInk3)
                        Text(score)
                            .font(ClavisTypography.clavixMono(22, weight: .semibold))
                            .foregroundColor(.clavixInk)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(Color.clavixPaper)
                }
            }
            .overlay(Rectangle().stroke(Color.clavixRule, lineWidth: 1))
        }
    }

    // MARK: - Sector exposure

    private var sectorExposure: some View {
        ClavixSection(eyebrow: "Portfolio sectors", title: "Sector exposure") {
            if sectorRows.isEmpty {
                ClavixCard {
                    Text("Sector breakdown will appear once positions have analysis data.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 1), count: 3), spacing: 1) {
                    ForEach(sectorRows, id: \.sector) { row in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(row.sector)
                                .font(ClavisTypography.clavixMono(11, weight: .bold))
                                .foregroundColor(.clavixInk)
                            Text("w\(row.weightInt)%")
                                .font(ClavisTypography.clavixMono(11, weight: .regular))
                                .foregroundColor(.clavixInk3)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .background(Color.clavixPaper)
                    }
                }
                .overlay(Rectangle().stroke(Color.clavixRule, lineWidth: 1))
            }
        }
    }

    // MARK: - Attention (alerts preview)

    private var attention: some View {
        ClavixSection(eyebrow: attentionEyebrow, title: "Attention") {
            HStack {
                Spacer()
                Button("See all →") { selectedTab = 3 }
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixAccent)
            }
            .offset(y: -48)
            .padding(.bottom, -38)

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

    private func alertRow(_ alert: Alert) -> some View {
        ClavixCard(padding: 12) {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(alertCategoryLabel(alert).uppercased())
                        .font(ClavisTypography.clavixMono(10, weight: .bold))
                        .tracking(0.7)
                        .foregroundColor(.clavixInk3)
                    Spacer()
                    Text(alert.createdAt.formatted(date: .omitted, time: .shortened))
                        .font(ClavisTypography.clavixMono(10, weight: .regular))
                        .foregroundColor(.clavixInk3)
                }
                Text(alert.message.sanitizedDisplayText)
                    .font(ClavisTypography.clavixSerif(14, weight: .medium))
                    .foregroundColor(.clavixInk)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
            }
        }
    }

    // MARK: - Top movers

    private var bookPreview: some View {
        ClavixSection(eyebrow: bookEyebrow, title: "Your book") {
            HStack {
                Spacer()
                Button("Holdings →") { selectedTab = 1 }
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixAccent)
            }
            .offset(y: -48)
            .padding(.bottom, -38)

            ClavixCard(padding: 0) {
                VStack(spacing: 0) {
                    HStack {
                        Text("SYM")
                        Spacer()
                        Text("GRADE · DELTA")
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

    private func bookRow(_ position: Position) -> some View {
        HStack {
            Text(position.ticker)
                .font(ClavisTypography.clavixMono(13, weight: .bold))
                .foregroundColor(.clavixInk)
            Spacer()
            HStack(spacing: 8) {
                ClavixGradeBadge(position.resolvedRiskGrade ?? "—", size: 22)
                if let delta = position.scoreDelta, delta != 0 {
                    Text(delta > 0 ? "+\(delta)" : "\(delta)")
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(delta > 0 ? .clavixGood : .clavixBad)
                } else {
                    Text("—")
                        .font(ClavisTypography.clavixMono(11, weight: .regular))
                        .foregroundColor(.clavixInk3)
                }
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
    }

    // MARK: - Calendar

    private var calendar: some View {
        ClavixSection(eyebrow: "Today", title: "Calendar") {
            let items = viewModel.todayDigest?.structuredSections?.whatToWatchToday?.catalysts ?? []
            if items.isEmpty {
                ClavixCard {
                    Text("No scheduled events surfaced for your portfolio today.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.catalyst.sanitizedDisplayText)
                                    .font(ClavisTypography.clavixSerif(14, weight: .medium))
                                    .foregroundColor(.clavixInk)
                                if !item.impactedPositions.isEmpty {
                                    Text(item.impactedPositions.joined(separator: ", "))
                                        .font(ClavisTypography.clavixMono(10, weight: .regular))
                                        .foregroundColor(.clavixInk3)
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(14)
                            if index < items.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    // MARK: - State card

    private func stateCard(title: String, body: String, cta: String, action: @escaping () -> Void) -> some View {
        ClavixCard {
            VStack(alignment: .leading, spacing: 12) {
                Text(title)
                    .font(ClavisTypography.clavixSerif(18, weight: .medium))
                    .foregroundColor(.clavixInk)
                Text(body)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk2)
                    .fixedSize(horizontal: false, vertical: true)
                Button(action: action) {
                    Text(cta + " →")
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(.clavixAccent)
                }
            }
        }
    }

    // MARK: - Computed values

    private var headerDateText: String {
        Date().formatted(.dateTime.weekday(.wide).month(.abbreviated).day().hour().minute()).uppercased()
    }

    private var freshnessLabel: String {
        guard let digest = viewModel.todayDigest else { return "Updating" }
        let interval = Date().timeIntervalSince(digest.generatedAt)
        if interval < 60 * 60 { return "Updated" }
        if interval < 60 * 60 * 24 { return "Today" }
        return "Stale"
    }

    private var portfolioValueText: String {
        let total = viewModel.holdings.compactMap(\.currentValue).reduce(0, +)
        guard total > 0 else { return "—" }
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: total)) ?? "—"
    }

    private var portfolioGradeText: String {
        if !viewModel.holdings.isEmpty,
           PortfolioMath.weightedScore(viewModel.holdings) != nil {
            return PortfolioMath.weightedGrade(viewModel.holdings)
        }
        return viewModel.todayDigest?.structuredSections?.header?.portfolioGrade
            ?? viewModel.todayDigest?.overallGrade
            ?? "—"
    }

    private var compositeLine: String {
        if let weighted = PortfolioMath.weightedScore(viewModel.holdings) {
            return "Composite \(Int(weighted.rounded())) · —"
        }
        if let overall = viewModel.todayDigest?.overallScore {
            return "Composite \(Int(overall.rounded())) · —"
        }
        return "Composite —"
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
    private var dimensionTuples: [(String, String)] {
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
                return (label, "—")
            }
            return (label, "\(Int((num / denom).rounded()))")
        }
    }

    private struct SectorRow {
        let sector: String
        let weight: Double
        var weightInt: Int { Int((weight * 100).rounded()) }
    }

    private var sectorRows: [SectorRow] {
        let totalValue = viewModel.holdings.compactMap(\.currentValue).reduce(0, +)
        guard totalValue > 0 else { return [] }
        var bySector: [String: Double] = [:]
        for position in viewModel.holdings {
            guard let value = position.currentValue, value > 0 else { continue }
            let sector = position.sharedAnalysis?.sector ?? "Unclassified"
            bySector[sector, default: 0] += value
        }
        return bySector
            .map { SectorRow(sector: $0.key, weight: $0.value / totalValue) }
            .sorted { $0.weight > $1.weight }
            .prefix(6)
            .map { $0 }
    }

    private var attentionEyebrow: String {
        let n = viewModel.alerts.count
        if n == 0 { return "No new alerts" }
        return "\(n) alert\(n == 1 ? "" : "s")"
    }

    private var bookEyebrow: String {
        let n = viewModel.holdings.count
        return "Top movers · \(n) position\(n == 1 ? "" : "s")"
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
                                         return "Portfolio"
        case .macroShock:               return "Macro"
        case .safetyDeterioration,
             .concentrationDanger,
             .clusterRisk,
             .structuralFragility:      return "Risk"
        case .ratingReady, .digestReady:return "Update"
        }
    }
}
