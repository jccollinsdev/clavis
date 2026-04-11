import SwiftUI

struct PositionDetailView: View {
    let positionId: String
    @State private var detail: PositionDetailResponse?
    @State private var priceHistory: [PricePoint] = []
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var isRefreshingAnalysis = false
    @State private var hasLoaded = false
    @State private var selectedDays: Int = 30
    @State private var activeRun: AnalysisRun?
    @State private var animateContent = false

    var body: some View {
        ScrollView {
            contentView
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.largeSpacing)
        }
        .background(Color.appBackground)
        .navigationTitle(detail?.position.ticker ?? "Position")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    Task { await triggerFreshAnalysis() }
                } label: {
                    if isRefreshingAnalysis {
                        ProgressView()
                    } else {
                        Image(systemName: "arrow.clockwise")
                    }
                }
                .disabled(isRefreshingAnalysis)
            }
        }
        .overlay(alignment: .top) {
            if let errorMessage {
                InlineErrorBanner(message: errorMessage)
                    .padding(.horizontal)
                    .padding(.top, 8)
            }
        }
        .refreshable {
            await reloadAll()
        }
        .onAppear {
            guard !hasLoaded else { return }
            hasLoaded = true

            Task {
                await reloadAll()
            }
        }
        .onChange(of: detail?.position.id) { _, _ in
            withAnimation(.easeOut(duration: 0.5)) {
                animateContent = true
            }
        }
    }

    private func reloadAll() async {
        await loadDetail()
        await loadPriceHistory(days: selectedDays)
        withAnimation(.easeOut(duration: 0.5)) {
            animateContent = true
        }
    }

    private func loadDetail() async {
        isLoading = true
        errorMessage = nil

        do {
            detail = try await APIService.shared.fetchPositionDetail(id: positionId)
        } catch {
            errorMessage = "Failed to load position details: \(error.localizedDescription)"
        }

        isLoading = false
    }

    private func loadPriceHistory(days: Int = 30) async {
        guard let ticker = detail?.position.ticker else { return }
        do {
            let response = try await APIService.shared.fetchPriceHistory(ticker: ticker, days: days)
            withAnimation(.smooth(duration: 0.4)) {
                priceHistory = response.prices
            }
        } catch {
            errorMessage = "Failed to load price history: \(error.localizedDescription)"
        }
    }

    private func triggerFreshAnalysis() async {
        isRefreshingAnalysis = true
        errorMessage = nil
        activeRun = nil
        defer { isRefreshingAnalysis = false }

        do {
            let trigger = try await APIService.shared.triggerAnalysis(positionId: positionId)
            if let runId = trigger.analysisRunId {
                try await pollAnalysisRun(runId: runId)
            }
            await reloadAll()
            withAnimation(.easeOut(duration: 0.3)) {
                animateContent = true
            }
        } catch {
            errorMessage = "Failed to trigger analysis: \(error.localizedDescription)"
            withAnimation(.easeOut(duration: 0.3)) {
                animateContent = true
            }
        }
    }

    private func pollAnalysisRun(runId: String) async throws {
        for _ in 0..<30 {
            let run = try await APIService.shared.fetchAnalysisRun(id: runId)
            activeRun = run
            await loadDetail()

            switch run.lifecycleStatus {
            case "completed":
                activeRun = nil
                return
            case "failed":
                throw APIError.networkError(
                    NSError(
                        domain: "Clavis",
                        code: 1,
                        userInfo: [NSLocalizedDescriptionKey: run.errorMessage ?? "Analysis failed."]
                    )
                )
            default:
                break
            }

            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }

        activeRun = nil
        throw APIError.networkError(
            NSError(
                domain: "Clavis",
                code: 2,
                userInfo: [NSLocalizedDescriptionKey: "Analysis is still running. Please check back in a moment."]
            )
        )
    }

    @ViewBuilder
    private var contentView: some View {
        if isLoading && detail == nil {
            PositionDetailSkeletonView()
        } else if let detail {
            VStack(spacing: ClavisTheme.sectionSpacing) {
                if isRefreshingAnalysis {
                    RefreshingBanner()
                }

                if detail.position.riskGrade == nil && detail.position.analysisStartedAt != nil {
                    AnalysisInProgressCard(position: detail.position)
                }

                animatedContent(PositionRiskHero(position: detail.position, score: detail.currentScore))

                animatedContent(PriceAndTrendSection(
                    ticker: detail.position.ticker,
                    priceHistory: priceHistory,
                    selectedDays: $selectedDays,
                    onDaysChange: { days in
                        Task { await loadPriceHistory(days: days) }
                    }
                ))

                animatedContent(PositionSnapshotGrid(position: detail.position))

                if let analysis = detail.currentAnalysis {
                    if let watchItems = analysis.watchItems, !watchItems.isEmpty {
                        animatedContent(WhatToWatchSection(items: watchItems))
                    }

                    animatedContent(RiskDimensionsCard(score: detail.currentScore, analysis: analysis))

                    if !detail.latestEventAnalyses.isEmpty {
                        animatedContent(RelevantNewsCard(
                            events: detail.latestEventAnalyses,
                            ticker: detail.position.ticker
                        ))
                    }
                } else if detail.position.riskGrade == nil && detail.position.analysisStartedAt == nil {
                    animatedContent(NoAnalysisCard {
                        Task { await triggerFreshAnalysis() }
                    })
                }
            }
        }
    }

    @ViewBuilder
    private func animatedContent<Content: View>(_ view: Content) -> some View {
        view
            .opacity(animateContent ? 1 : 0)
            .offset(y: animateContent ? 0 : 20)
    }
}

struct PositionDetailSkeletonView: View {
    var body: some View {
        VStack(spacing: ClavisTheme.sectionSpacing) {
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .fill(Color.surfaceSecondary)
                .frame(height: 180)

            HStack(spacing: ClavisTheme.mediumSpacing) {
                RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                    .fill(Color.surfaceSecondary)
                    .frame(height: 80)
                RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                    .fill(Color.surfaceSecondary)
                    .frame(height: 80)
                RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                    .fill(Color.surfaceSecondary)
                    .frame(height: 80)
            }

            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .fill(Color.surfaceSecondary)
                .frame(height: 200)

            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .fill(Color.surfaceSecondary)
                .frame(height: 150)
        }
    }
}

struct PositionRiskHero: View {
    let position: Position
    let score: RiskScore?

    private var displayScoreValue: Double {
        score?.displayScore ?? 0
    }

    private var displayGradeValue: String {
        score?.displayGrade ?? position.riskGrade ?? "C"
    }

    private var isAnalyzing: Bool {
        position.riskGrade == nil && position.analysisStartedAt != nil
    }

    private var riskTrend: RiskTrend {
        position.riskTrend ?? .stable
    }

    private var actionPressure: ActionPressure {
        ActionPressure.from(score: displayScoreValue, trend: riskTrend)
    }

    private var safetyLabel: String {
        if isAnalyzing { return "Analyzing..." }
        switch displayGradeValue {
        case "A": return "Safe"
        case "B": return "Stable"
        case "C": return "Watch"
        case "D": return "Risky"
        case "F": return "Critical"
        default: return "Unknown"
        }
    }

    private var gradeColor: Color {
        ClavisGradeStyle.color(for: displayGradeValue)
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .center, spacing: ClavisTheme.largeSpacing) {
                ZStack {
                    ClavisRingGauge(
                        progress: scoreProgress,
                        lineWidth: 10,
                        tint: gradeColor
                    )
                    .frame(width: 100, height: 100)

                    VStack(spacing: 2) {
                        if isAnalyzing {
                            ProgressView()
                        } else {
                            Text("\(Int(displayScoreValue))")
                                .font(.system(size: 28, weight: .bold, design: .rounded))
                                .foregroundColor(.textPrimary)
                        }
                    }
                }

                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text("RISK SCORE")
                        .font(ClavisTypography.eyebrow)
                        .foregroundColor(.textTertiary)

                    HStack(alignment: .firstTextBaseline, spacing: ClavisTheme.smallSpacing) {
                        if isAnalyzing {
                            Text("--")
                                .font(ClavisTypography.heroNumber)
                                .foregroundColor(.textTertiary)
                        } else {
                            Text(displayGradeValue)
                                .font(.system(size: 42, weight: .bold, design: .rounded))
                                .foregroundColor(gradeColor)
                        }

                        Text(safetyLabel)
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(isAnalyzing ? .textTertiary : gradeColor)
                    }

                    if !isAnalyzing {
                        HStack(spacing: 6) {
                            Image(systemName: trendIcon)
                                .font(.system(size: 12, weight: .semibold))
                            Text(trendLabel)
                                .font(ClavisTypography.footnote)
                        }
                        .foregroundColor(trendColor)
                    }
                }

                Spacer()
            }

            if !isAnalyzing, let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
                Text(summary.singleSentence)
                    .font(ClavisTypography.interpretation)
                    .foregroundColor(.textSecondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, ClavisTheme.mediumSpacing)
            }
        }
        .padding(ClavisTheme.largeSpacing)
        .background(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .fill(Color.surfacePrimary)
                .overlay(
                    RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                        .stroke(gradeColor.opacity(0.2), lineWidth: 1)
                )
        )
    }

    private var scoreProgress: Double {
        displayScoreValue / 100.0
    }

    private var trendIcon: String {
        switch riskTrend {
        case .improving: return "arrow.up.right"
        case .increasing: return "arrow.up.right"
        case .stable: return "arrow.right"
        }
    }

    private var trendLabel: String {
        switch riskTrend {
        case .improving: return "Improving"
        case .increasing: return "Increasing"
        case .stable: return "Stable"
        }
    }

    private var trendColor: Color {
        switch riskTrend {
        case .improving: return .successTone
        case .increasing: return .criticalTone
        case .stable: return .textTertiary
        }
    }
}

struct PositionSnapshotGrid: View {
    let position: Position

    var body: some View {
        HStack(spacing: ClavisTheme.smallSpacing) {
            StatCell(label: "Shares", value: String(format: "%.2f", position.shares))
            StatCell(label: "Cost Basis", value: position.purchasePrice.formatted(.currency(code: "USD").precision(.fractionLength(2))))
            StatCell(label: "Current", value: currentPriceText)
        }
    }

    private var currentPriceText: String {
        let price = position.currentPrice ?? position.purchasePrice
        return price.formatted(.currency(code: "USD").precision(.fractionLength(2)))
    }
}

struct StatCell: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
            Text(label.uppercased())
                .font(ClavisTypography.eyebrow)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.textPrimary)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(ClavisTheme.mediumSpacing)
        .background(Color.surfacePrimary)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                .stroke(Color.borderSubtle, lineWidth: 1)
        )
    }
}

struct RiskDimensionsCard: View {
    let score: RiskScore?
    let analysis: PositionAnalysis

    struct RiskDimension: Identifiable {
        let id = UUID()
        let label: String
        let value: Double
        let icon: String
    }

    private var dimensions: [RiskDimension] {
        guard let score else { return [] }
        return [
            RiskDimension(label: "News Sentiment", value: score.newsSentiment ?? 50, icon: "newspaper"),
            RiskDimension(label: "Macro Exposure", value: score.macroExposure ?? 50, icon: "globe"),
            RiskDimension(label: "Position Sizing", value: score.positionSizing ?? 50, icon: "chart.pie"),
            RiskDimension(label: "Volatility", value: score.volatilityTrend ?? 50, icon: "waveform.path.ecg"),
            RiskDimension(label: "Structural", value: score.structuralBaseScore ?? 50, icon: "building.columns")
        ]
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Risk Dimensions")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            ForEach(dimensions) { dim in
                RiskDimensionRow(dimension: dim)
            }
        }
        .padding(ClavisTheme.largeSpacing)
        .background(Color.surfacePrimary)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .stroke(Color.borderSubtle, lineWidth: 1)
        )
    }
}

struct RiskDimensionRow: View {
    let dimension: RiskDimensionsCard.RiskDimension

    var body: some View {
        HStack(spacing: ClavisTheme.mediumSpacing) {
            Image(systemName: dimension.icon)
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(dimensionColor)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(dimension.label)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                    Spacer()
                    Text("\(Int(dimension.value))")
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(dimensionColor)
                }

                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 3)
                            .fill(Color.surfaceSecondary)
                            .frame(height: 4)
                        RoundedRectangle(cornerRadius: 3)
                            .fill(dimensionColor)
                            .frame(width: geo.size.width * (dimension.value / 100), height: 4)
                    }
                }
                .frame(height: 4)
            }
        }
    }

    private var dimensionColor: Color {
        switch dimension.value {
        case 70...100: return .successTone
        case 50..<70: return .warningTone
        default: return .criticalTone
        }
    }
}

struct RelevantNewsCard: View {
    let events: [EventAnalysis]
    let ticker: String

    private var majorCount: Int {
        events.filter { $0.significance == "major" }.count
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack {
                Text("Relevant Events")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                Spacer()

                if majorCount > 0 {
                    HStack(spacing: 4) {
                        Circle()
                            .fill(Color.criticalTone)
                            .frame(width: 6, height: 6)
                        Text("\(majorCount) major")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.criticalTone)
                    }
                }
            }

            if events.isEmpty {
                Text("No significant events.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textTertiary)
            } else {
                ForEach(events.prefix(5)) { event in
                    NavigationLink(destination: EventAnalysisDetailView(event: event, ticker: ticker)) {
                        NewsRow(event: event)
                    }
                    .buttonStyle(.plain)

                    if event.id != events.prefix(5).last?.id {
                        Divider()
                    }
                }
            }
        }
        .padding(ClavisTheme.largeSpacing)
        .background(Color.surfacePrimary)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .stroke(Color.borderSubtle, lineWidth: 1)
        )
    }
}

struct NewsRow: View {
    let event: EventAnalysis

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(event.title)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textPrimary)
                    .lineLimit(2)

                HStack(spacing: ClavisTheme.smallSpacing) {
                    if event.significance == "major" {
                        Text("MAJOR")
                            .font(ClavisTypography.eyebrow)
                            .foregroundColor(.criticalTone)
                    }

                    if let source = event.source {
                        Text(source)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                    }

                    if let publishedAt = event.publishedAt {
                        Text(publishedAt.formatted(date: .abbreviated, time: .omitted))
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                    }
                }
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.textTertiary)
        }
        .padding(.vertical, ClavisTheme.smallSpacing)
    }
}

struct WhatToWatchSection: View {
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("What to Watch")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            ForEach(Array(items.prefix(3).enumerated()), id: \.offset) { index, item in
                HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                    Text("\(index + 1)")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                        .frame(width: 20, height: 20)
                        .background(Color.surfaceSecondary)
                        .clipShape(Circle())

                    Text(item)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            }
        }
        .padding(ClavisTheme.largeSpacing)
        .background(Color.surfacePrimary)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .stroke(Color.borderSubtle, lineWidth: 1)
        )
    }
}

struct PriceAndTrendSection: View {
    let ticker: String
    let priceHistory: [PricePoint]
    @Binding var selectedDays: Int
    let onDaysChange: (Int) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Price and Trend")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Picker("Timeframe", selection: $selectedDays) {
                Text("7D").tag(7)
                Text("30D").tag(30)
                Text("90D").tag(90)
            }
            .pickerStyle(.segmented)
            .onChange(of: selectedDays) { _, days in
                onDaysChange(days)
            }

            PriceChartView(ticker: ticker, prices: priceHistory, days: selectedDays)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct EventAnalysisDetailView: View {
    let event: EventAnalysis
    let ticker: String

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                EventAnalysisHeader(event: event, ticker: ticker)

                EventRiskBriefCard(event: event, ticker: ticker)
            }
            .padding(ClavisTheme.cardPadding)
        }
        .background(Color.appBackground)
        .navigationTitle("Event Analysis")
        .navigationBarTitleDisplayMode(.inline)
    }
}

extension String {
    var singleSentence: String {
        let trimmed = sanitizedDisplayText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return trimmed }

        var endIndex: String.Index?
        var chars = Array(trimmed.dropFirst())
        var prevWasPeriod = false

        for (i, char) in chars.enumerated() {
            if ".!?".contains(char) {
                if prevWasPeriod {
                    let nextIdx = chars.index(chars.startIndex, offsetBy: i + 1, limitedBy: chars.endIndex)
                    if let ni = nextIdx, ni < chars.endIndex {
                        let next = chars[ni]
                        if next.isWhitespace || next.isUppercase {
                            endIndex = trimmed.index(trimmed.startIndex, offsetBy: i + 1)
                            break
                        }
                    }
                    prevWasPeriod = false
                } else {
                    let nextIdx = chars.index(chars.startIndex, offsetBy: i + 1, limitedBy: chars.endIndex)
                    if let ni = nextIdx, ni < chars.endIndex {
                        let next = chars[ni]
                        if next.isWhitespace || i == chars.count - 1 {
                            endIndex = trimmed.index(trimmed.startIndex, offsetBy: i + 1)
                            break
                        }
                    }
                    prevWasPeriod = true
                }
            } else {
                prevWasPeriod = false
            }
        }

        guard let end = endIndex else { return trimmed }
        return String(trimmed[..<end]).trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct EventAnalysisHeader: View {
    let event: EventAnalysis
    let ticker: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text(event.title)
                    .font(ClavisTypography.sectionTitle)
                    .foregroundColor(.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                if let significance = event.significance, !significance.isEmpty {
                    Text(significance.uppercased())
                        .font(ClavisTypography.footnote)
                        .foregroundColor(significance == "major" ? .criticalTone : .textTertiary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.surfaceSecondary)
                        .clipShape(Capsule())
                }
            }

            HStack(spacing: 8) {
                Text(ticker)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)

                if let source = event.source, !source.isEmpty {
                    Text("•")
                        .foregroundColor(.textTertiary)
                    Text(source)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }

                if let publishedAt = event.publishedAt {
                    Text("•")
                        .foregroundColor(.textTertiary)
                    Text(publishedAt.formatted(date: .abbreviated, time: .omitted))
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }
            }
        }
    }
}

struct EventRiskBriefCard: View {
    let event: EventAnalysis
    let ticker: String

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            BriefSection(
                title: "EVENT SUMMARY",
                content: fullAnalysisText,
                bullets: nil,
                accent: .textPrimary
            )

            Divider().overlay(Color.borderSubtle)

            BriefSection(
                title: "MARKET INTERPRETATION",
                content: marketInterpretationText,
                bullets: nil,
                accent: .textSecondary
            )

            Divider().overlay(Color.borderSubtle)

            BriefSection(
                title: "POSITION IMPACT",
                content: nil,
                bullets: positionImpactBullets,
                accent: .textSecondary
            )

            Divider().overlay(Color.borderSubtle)

            ActionSignalSection(actionText: actionSignalText, confidenceText: confidenceText)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private var fullAnalysisText: String {
        if let longAnalysis = normalizedLongAnalysis {
            return longAnalysis
        }

        if let summary = firstMeaningfulLine(event.summary) {
            return summary
        }

        return event.title
    }

    private var marketInterpretationText: String {
        if let scenario = firstMeaningfulLine(event.scenarioSummary) {
            return scenario
        }

        if let analysis = firstMeaningfulSentence(event.longAnalysis) {
            return analysis
        }

        return "The market is reacting to a new information set with mixed near-term implications."
    }

    private var positionImpactBullets: [String] {
        var bullets = event.keyImplications?.compactMap { firstMeaningfulLine($0) } ?? []

        if bullets.isEmpty, let followups = event.recommendedFollowups?.compactMap({ firstMeaningfulLine($0) }), !followups.isEmpty {
            bullets = followups
        }

        if bullets.isEmpty {
            bullets = ["For \(ticker), this changes the risk profile but not necessarily the core thesis."]
        }

        return Array(bullets.prefix(2))
    }

    private var actionSignalText: String {
        let direction = normalizedDirection
        let confidence = event.confidence ?? 0.5

        switch direction {
        case let value where value.contains("bull"):
            return confidence >= 0.7 ? "Add" : "Monitor"
        case let value where value.contains("bear"):
            return confidence >= 0.8 && significanceIsMajor ? "Exit" : "Reduce"
        case let value where value.contains("neutral"):
            return "Monitor"
        default:
            return "Monitor"
        }
    }

    private var confidenceText: String? {
        guard let confidence = event.confidence else { return nil }

        switch confidence {
        case 0.8...:
            return "High"
        case 0.6..<0.8:
            return "Medium"
        default:
            return "Low"
        }
    }

    private var significanceIsMajor: Bool {
        event.significance?.lowercased() == "major"
    }

    private var normalizedDirection: String {
        event.riskDirection?.lowercased().replacingOccurrences(of: "_", with: "-") ?? ""
    }

    private func cleanText(_ text: String) -> String {
        text.sanitizedDisplayText
    }

    private var normalizedLongAnalysis: String? {
        guard let longAnalysis = event.longAnalysis else { return nil }
        let cleaned = cleanText(longAnalysis)
        return cleaned.isEmpty ? nil : cleaned
    }

    private func firstMeaningfulLine(_ text: String?) -> String? {
        guard let text else { return nil }
        let cleaned = cleanText(text)
        return cleaned.isEmpty ? nil : cleaned
    }

    private func firstMeaningfulSentence(_ text: String?) -> String? {
        guard let text else { return nil }
        let cleaned = cleanText(text)
        guard !cleaned.isEmpty else { return nil }

        let sentence = cleaned.split(whereSeparator: { ".!?".contains($0) }).first.map(String.init)
        return sentence?.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct BriefSection: View {
    let title: String
    let content: String?
    let bullets: [String]?
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(ClavisTypography.footnote.weight(.bold))
                .foregroundColor(.textTertiary)

            if let content {
                Text(content)
                    .font(ClavisTypography.body)
                    .foregroundColor(accent)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if let bullets, !bullets.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(Array(bullets.prefix(2).enumerated()), id: \.offset) { _, bullet in
                        HStack(alignment: .top, spacing: 8) {
                            Circle()
                                .fill(Color.textTertiary)
                                .frame(width: 5, height: 5)
                                .padding(.top, 7)
                            Text(bullet)
                                .font(ClavisTypography.body)
                                .foregroundColor(accent)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
        }
    }
}

struct ActionSignalSection: View {
    let actionText: String
    let confidenceText: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("ACTION SIGNAL")
                .font(ClavisTypography.footnote.weight(.bold))
                .foregroundColor(.textTertiary)

            Text("Action: \(actionText)")
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.textPrimary)

            if let confidenceText {
                Text("Confidence: \(confidenceText)")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
        }
    }
}

struct NoAnalysisCard: View {
    let onRunAnalysis: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("No Analysis Yet")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Text("Run a fresh analysis to generate a detailed report for this holding.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            Button("Run Fresh Analysis") {
                onRunAnalysis()
            }
            .buttonStyle(.borderedProminent)
            .tint(.trustNavy)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct AnalysisProgressCard: View {
    let run: AnalysisRun

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack {
                Label("Analysis in progress", systemImage: "waveform.path.ecg")
                    .font(ClavisTypography.cardTitle)
                Spacer()
                if let positions = run.positionsProcessed {
                    Text("\(positions) positions")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }
            }

            Text(run.currentStageMessage ?? "Processing...")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .background(Color.warningSurface)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }
}

struct RefreshingBanner: View {
    var body: some View {
        HStack(spacing: ClavisTheme.smallSpacing) {
            ProgressView()
                .progressViewStyle(.circular)
                .scaleEffect(0.8)

            Text("Refreshing analysis...")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)

            Spacer()
        }
        .padding(.horizontal, ClavisTheme.mediumSpacing)
        .padding(.vertical, ClavisTheme.smallSpacing)
        .background(Color.surfaceSecondary)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

struct AnalysisInProgressCard: View {
    let position: Position
    private let maxSeconds: Int = 180

    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { context in
            let started = position.analysisStartedAt ?? context.date
            let elapsed = context.date.timeIntervalSince(started)
            let progress = min(elapsed / Double(maxSeconds), 1.0)
            let remaining = max(0, maxSeconds - Int(elapsed))
            let timeLabel = remaining == 0 ? "Finalizing..." : "\(remaining)s remaining"

            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                HStack {
                    Label("Analyzing \(position.ticker)", systemImage: "waveform.path.ecg")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)
                    Spacer()
                    Text(timeLabel)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }

                GeometryReader { geometry in
                    ZStack(alignment: .leading) {
                        Capsule()
                            .fill(Color.slate200)
                            .frame(height: 8)

                        Capsule()
                            .fill(
                                LinearGradient(
                                    colors: [.accentBlue, .accentBlue.opacity(0.8)],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: geometry.size.width * progress, height: 8)
                            .animation(.linear(duration: 1), value: progress)
                    }
                }
                .frame(height: 8)

                Text("This usually takes under 3 minutes. You'll be notified when it's ready.")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }
            .padding(ClavisTheme.cardPadding)
            .background(Color.surfacePrimary)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.borderSubtle, lineWidth: 1)
            )
        }
    }
}

struct InlineErrorBanner: View {
    let message: String

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(.orange)
            Text(message)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
            Spacer()
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}
