import SwiftUI

struct HoldingsListView: View {
    @StateObject private var viewModel = HoldingsViewModel()
    @State private var animateContent = false

    private var groupedHoldings: [HoldingsGroup] {
        let scored = viewModel.holdings.filter { $0.riskGrade != nil }
        let reduce = scored.filter { ($0.totalScore ?? 50) < 50 }
        let watch = scored.filter { (50..<65).contains($0.totalScore ?? 50) }
        let hold = scored.filter { ($0.totalScore ?? 50) >= 65 }
        let analyzing = viewModel.holdings.filter { $0.riskGrade == nil && $0.analysisStartedAt != nil }

        return [
            HoldingsGroup(decision: .reduce, positions: reduce),
            HoldingsGroup(decision: .watch, positions: watch),
            HoldingsGroup(decision: .hold, positions: hold),
            HoldingsGroup(decision: .analyzing, positions: analyzing)
        ].filter { !$0.positions.isEmpty }
    }

    private var portfolioStats: PortfolioStats {
        let scored = viewModel.holdings.filter { $0.riskGrade != nil && $0.totalScore != nil }
        let totalValue = viewModel.holdings.compactMap { $0.currentValue }.reduce(0, +)
        let avgScore = scored.isEmpty ? nil : scored.map { $0.totalScore! }.reduce(0, +) / Double(scored.count)
        let bestGrade = scored.min(by: { gradeValue($0.riskGrade ?? "") < gradeValue($1.riskGrade ?? "") })?.riskGrade
        let worstGrade = scored.max(by: { gradeValue($0.riskGrade ?? "") < gradeValue($1.riskGrade ?? "") })?.riskGrade

        return PortfolioStats(
            positionCount: viewModel.holdings.count,
            totalValue: totalValue,
            averageScore: avgScore,
            bestGrade: bestGrade,
            worstGrade: worstGrade
        )
    }

    private func gradeValue(_ grade: String) -> Int {
        switch grade {
        case "A": return 5
        case "B": return 4
        case "C": return 3
        case "D": return 2
        case "F": return 1
        default: return 0
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                ClavisAtmosphereBackground().ignoresSafeArea()

                if viewModel.isLoading && viewModel.holdings.isEmpty {
                    VStack {
                        ClavisLoadingCard(title: "Loading holdings", subtitle: "Pulling positions and the latest scores.")
                    }
                    .padding()
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                } else if viewModel.holdings.isEmpty {
                    HoldingsEmptyState(onAddPosition: { viewModel.showAddSheet = true })
                } else {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 0) {
                            PortfolioSummaryHeader(stats: portfolioStats)
                                .padding(.horizontal, ClavisTheme.screenPadding)
                                .padding(.top, ClavisTheme.mediumSpacing)
                                .padding(.bottom, ClavisTheme.largeSpacing)
                                .opacity(animateContent ? 1 : 0)
                                .offset(y: animateContent ? 0 : -20)

                            if let errorMessage = viewModel.errorMessage {
                                DashboardErrorCard(message: errorMessage)
                                    .padding(.horizontal, ClavisTheme.screenPadding)
                                    .padding(.bottom, ClavisTheme.mediumSpacing)
                            }

                            ForEach(groupedHoldings) { group in
                                DecisionSection(group: group, viewModel: viewModel)
                                    .padding(.bottom, ClavisTheme.sectionSpacing)
                                    .opacity(animateContent ? 1 : 0)
                                    .offset(y: animateContent ? 0 : 30)
                            }
                        }
                        .padding(.bottom, ClavisTheme.floatingTabHeight + ClavisTheme.largeSpacing)
                    }
                }
            }
            .navigationTitle("Holdings")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        Task { await viewModel.refreshHoldings() }
                    } label: {
                        if viewModel.isRefreshing {
                            ProgressView()
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(viewModel.isRefreshing)
                }
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        viewModel.showAddSheet = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $viewModel.showAddSheet) {
                AddPositionSheet(viewModel: viewModel)
            }
            .fullScreenCover(isPresented: $viewModel.showProgressSheet) {
                AddPositionProgressView(viewModel: viewModel)
            }
            .alert("Error", isPresented: $viewModel.showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(viewModel.errorMessage ?? "Unknown error")
            }
            .refreshable {
                await viewModel.refreshHoldings()
            }
            .onAppear {
                viewModel.showError = false
                if viewModel.holdings.isEmpty && !viewModel.isLoading {
                    Task { await viewModel.loadHoldings() }
                }
                withAnimation(.easeOut(duration: 0.4).delay(0.1)) {
                    animateContent = true
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .positionAnalysisComplete)) { _ in
                Task { @MainActor in
                    await viewModel.loadHoldings(showLoading: false)
                    withAnimation(.easeOut(duration: 0.3)) {
                        animateContent = true
                    }
                }
            }
        }
    }
}

struct PortfolioStats {
    let positionCount: Int
    let totalValue: Double
    let averageScore: Double?
    let bestGrade: String?
    let worstGrade: String?

    var formattedValue: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: totalValue)) ?? "$0"
    }
}

struct HoldingsGroup: Identifiable {
    let id = UUID()
    let decision: DecisionCategory
    let positions: [Position]

    enum DecisionCategory: String {
        case reduce = "Reduce"
        case watch = "Watch"
        case hold = "Hold"
        case analyzing = "Analyzing"

        var color: Color {
            switch self {
            case .reduce: return .criticalTone
            case .watch: return .warningTone
            case .hold: return .successTone
            case .analyzing: return .accentBlue
            }
        }

        var icon: String {
            switch self {
            case .reduce: return "exclamationmark.triangle.fill"
            case .watch: return "eye.fill"
            case .hold: return "checkmark.shield.fill"
            case .analyzing: return "waveform.path.ecg"
            }
        }

        var subtitle: String {
            switch self {
            case .reduce: return "Consider reducing exposure"
            case .watch: return "Monitor for changes"
            case .hold: return "Looking stable"
            case .analyzing: return "Analysis in progress"
            }
        }
    }
}

struct PortfolioSummaryHeader: View {
    let stats: PortfolioStats

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Portfolio Overview")
                        .font(ClavisTypography.eyebrow)
                        .kerning(1.5)
                        .foregroundColor(.textTertiary)

                    Text("\(stats.positionCount) Position\(stats.positionCount == 1 ? "" : "s")")
                        .font(ClavisTypography.pageTitle)
                        .foregroundColor(.textPrimary)
                }

                Spacer()

                if let score = stats.averageScore {
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("Avg Score")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                        Text("\(Int(score))")
                            .font(ClavisTypography.metric)
                            .foregroundColor(scoreColor(score))
                    }
                }
            }

            HStack(spacing: ClavisTheme.mediumSpacing) {
                StatBadge(label: "Value", value: stats.formattedValue, tint: .accentBlue)
                StatBadge(label: "Best", value: stats.bestGrade ?? "--", tint: .successTone)
                StatBadge(label: "Worst", value: stats.worstGrade ?? "--", tint: .criticalTone)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private func scoreColor(_ score: Double) -> Color {
        switch score {
        case 65...100: return .successTone
        case 50..<65: return .warningTone
        default: return .criticalTone
        }
    }
}

struct StatBadge: View {
    let label: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(tint)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(tint.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

struct DecisionSection: View {
    let group: HoldingsGroup
    @ObservedObject var viewModel: HoldingsViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            DecisionSectionHeader(
                category: group.decision,
                count: group.positions.count
            )
            .padding(.horizontal, ClavisTheme.screenPadding)

            VStack(spacing: ClavisTheme.smallSpacing) {
                ForEach(Array(group.positions.enumerated()), id: \.element.id) { index, position in
                    NavigationLink(destination: PositionDetailView(positionId: position.id)) {
                        EnhancedHoldingRow(position: position, delay: Double(index) * 0.05)
                    }
                    .buttonStyle(.plain)
                    .contextMenu {
                        Button(role: .destructive) {
                            Task { await viewModel.deleteHolding(position) }
                        } label: {
                            Label("Delete Position", systemImage: "trash")
                        }
                    }
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
        }
    }
}

struct DecisionSectionHeader: View {
    let category: HoldingsGroup.DecisionCategory
    let count: Int

    var body: some View {
        HStack(spacing: ClavisTheme.smallSpacing) {
            Image(systemName: category.icon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(category.color)

            Text(category.rawValue)
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Text("(\(count))")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)

            Spacer()

            Text(category.subtitle)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
        }
        .padding(.vertical, ClavisTheme.smallSpacing)
    }
}

struct EnhancedHoldingRow: View {
    let position: Position
    let delay: Double
    @State private var isVisible = false

    var body: some View {
        HStack(alignment: .center, spacing: ClavisTheme.mediumSpacing) {
            RingGradeBadge(grade: position.riskGrade, size: 52)
                .opacity(isVisible ? 1 : 0)
                .scaleEffect(isVisible ? 1 : 0.7)

            VStack(alignment: .leading, spacing: 5) {
                HStack(spacing: 8) {
                    Text(position.ticker)
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)
                        .lineLimit(1)

                    if let archetype = position.archetype.displayName.first, position.archetype != .growth {
                        Text(String(archetype))
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(.textTertiary)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.surfaceSecondary)
                            .clipShape(Capsule())
                    }

                    if let trend = position.riskTrend, trend != .stable {
                        TrendBadge(trend: trend)
                    }
                }

                HStack(spacing: ClavisTheme.smallSpacing) {
                    if let value = position.currentValue {
                        Text(formatCurrency(value))
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }

                    if let plPercent = position.unrealizedPLPercent {
                        PLBadge(percent: plPercent)
                    }

                    if let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
                        Text("·")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                        Text(summary)
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .lineLimit(1)
                    }
                }
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 5) {
                if let score = position.totalScore {
                    Text("\(Int(score))")
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)
                }

                if let state = position.riskState {
                    Text(state.displayName)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textTertiary)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .background(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .fill(Color.surfacePrimary)
                .shadow(color: Color.clavisShadow, radius: 0, x: 0, y: 0)
                .overlay(
                    RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                        .stroke(gradeBorderColor, lineWidth: position.riskGrade == "F" || position.riskGrade == "D" ? 1.5 : 0.5)
                )
        )
        .onAppear {
            withAnimation(.easeOut(duration: 0.35).delay(delay)) {
                isVisible = true
            }
        }
    }

    private var gradeBorderColor: Color {
        switch position.riskGrade {
        case "F": return .criticalTone.opacity(0.4)
        case "D": return .warningTone.opacity(0.3)
        default: return .borderSubtle
        }
    }

    private func formatCurrency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "$0"
    }
}

struct RingGradeBadge: View {
    let grade: String?
    let size: CGFloat
    private let lineWidth: CGFloat = 4

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.borderSubtle, lineWidth: lineWidth)
                .frame(width: size, height: size)

            if let grade {
                Circle()
                    .trim(from: 0, to: gradeProgress)
                    .stroke(gradeColor, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                    .frame(width: size, height: size)
                    .rotationEffect(.degrees(-90))

                Text(grade)
                    .font(.system(size: size * 0.36, weight: .bold))
                    .foregroundColor(.textPrimary)
            } else {
                ProgressView()
                    .progressViewStyle(.circular)
                    .scaleEffect(0.7)
            }
        }
        .frame(width: size, height: size)
    }

    private var gradeProgress: CGFloat {
        switch grade {
        case "A": return 0.9
        case "B": return 0.75
        case "C": return 0.58
        case "D": return 0.4
        case "F": return 0.22
        default: return 0.5
        }
    }

    private var gradeColor: Color {
        ClavisGradeStyle.color(for: grade)
    }
}

struct TrendBadge: View {
    let trend: RiskTrend

    var body: some View {
        HStack(spacing: 2) {
            Image(systemName: trend.iconName)
                .font(.system(size: 9, weight: .bold))
            Text(trend.displayName)
                .font(.system(size: 9, weight: .semibold))
        }
        .foregroundColor(trendColor)
        .padding(.horizontal, 6)
        .padding(.vertical, 3)
        .background(trendColor.opacity(0.12))
        .clipShape(Capsule())
    }

    private var trendColor: Color {
        switch trend {
        case .increasing: return .criticalTone
        case .stable: return .textTertiary
        case .improving: return .successTone
        }
    }
}

struct PLBadge: View {
    let percent: Double

    var body: some View {
        Text("\(percent >= 0 ? "+" : "")\(String(format: "%.1f", percent))%")
            .font(ClavisTypography.footnoteEmphasis)
            .foregroundColor(plColor)
    }

    private var plColor: Color {
        if percent >= 0 { return .successTone }
        return .criticalTone
    }
}

struct HoldingsSectionHeader: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(ClavisTypography.sectionTitle)
                .foregroundColor(.textPrimary)
            Text(subtitle)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
        }
        .padding(.top, 8)
        .padding(.bottom, 4)
    }
}

struct HoldingsEmptyState: View {
    let onAddPosition: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.largeSpacing) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("No holdings yet")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text("Add your first position to start tracking downside risk and portfolio updates.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)

                Button("Add Position", action: onAddPosition)
                    .buttonStyle(.borderedProminent)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.vertical, ClavisTheme.largeSpacing)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(Color.appBackground)
    }
}

struct HoldingRow: View {
    let position: Position

    private var isAnalyzing: Bool {
        position.riskGrade == nil && position.analysisStartedAt != nil
    }

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            ZStack {
                if isAnalyzing {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(Color.slate200)
                        .frame(width: 44, height: 52)
                    ProgressView()
                        .progressViewStyle(.circular)
                        .scaleEffect(0.8)
                } else {
                    Text(position.riskGrade ?? "--")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(.white)
                        .frame(width: 44, height: 52)
                        .background(ClavisGradeStyle.color(for: position.riskGrade))
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(position.ticker)
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)
                        .lineLimit(1)

                    if isAnalyzing {
                        Text("Analyzing")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundColor(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.accentBlue)
                            .clipShape(Capsule())
                    }
                }

                if isAnalyzing {
                    Text("Analysis in progress")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .lineLimit(1)
                } else if let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
                    Text(summary)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .lineLimit(1)
                }
            }

            Spacer()

            if isAnalyzing {
                VStack(alignment: .trailing, spacing: 4) {
                    AnalyzingProgressBadge(startedAt: position.analysisStartedAt)
                }
            } else {
                VStack(alignment: .trailing, spacing: 4) {
                    Text("\(Int(position.totalScore ?? 0))")
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)

                    if let trend = position.riskTrend {
                        Image(systemName: trend.iconName)
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(trendColor(trend))
                    }
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private func trendColor(_ trend: RiskTrend) -> Color {
        switch trend {
        case .increasing: return .criticalTone
        case .stable: return .textTertiary
        case .improving: return .successTone
        }
    }
}

struct AnalyzingPositionCard: View {
    let position: Position

    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { context in
            let started = position.analysisStartedAt ?? context.date
            let elapsed = context.date.timeIntervalSince(started)
            let progress = min(elapsed / 180.0, 1.0)
            let remaining = max(0, 180 - Int(elapsed))
            let timeText = remaining == 0
                ? "Finalizing..."
                : remaining >= 60
                    ? "\(remaining / 60)m \(remaining % 60)s remaining"
                    : "\(remaining)s remaining"

            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                HStack(alignment: .center) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(position.ticker)
                            .font(ClavisTypography.cardTitle)
                            .foregroundColor(.textPrimary)

                        Text("Analysis is running in the background")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                    }

                    Spacer()

                    Text(timeText)
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textTertiary)
                }

                ProgressView(value: progress)
                    .progressViewStyle(LinearProgressViewStyle(tint: .accentBlue))

                HStack {
                    Text("Waiting for news, event analysis, and scoring")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                    Spacer()
                    Text("\(Int(progress * 100))%")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textSecondary)
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
    }
}

struct AnalyzingProgressBadge: View {
    let startedAt: Date?
    @State private var progress: Double = 0
    private let maxDuration: TimeInterval = 180

    var body: some View {
        if let started = startedAt {
            let elapsed = Date().timeIntervalSince(started)
            let fraction = min(elapsed / maxDuration, 1.0)

            VStack(alignment: .trailing, spacing: 2) {
                Text("\(Int(fraction * 100))%")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.textSecondary)

                GeometryReader { geometry in
                    ZStack(alignment: .leading) {
                        Capsule()
                            .fill(Color.slate200)
                            .frame(height: 4)

                        Capsule()
                            .fill(Color.accentBlue)
                            .frame(width: geometry.size.width * fraction, height: 4)
                    }
                }
                .frame(width: 44, height: 4)
            }
            .onAppear {
                withAnimation(.linear(duration: 1).repeatForever(autoreverses: false)) {
                    progress = 1
                }
            }
        }
    }
}

struct AddPositionSheet: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var ticker = ""
    @State private var shares = ""
    @State private var purchasePrice = ""
    @State private var archetype: Archetype = .growth
    @State private var showError = false
    @State private var errorMessage = ""

    private var isFormValid: Bool {
        !ticker.isEmpty && !shares.isEmpty && Double(shares) != nil && !purchasePrice.isEmpty && Double(purchasePrice) != nil
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Position") {
                    TextField("Ticker (e.g., AAPL)", text: $ticker)
                        .textCase(.uppercase)
                        .autocapitalization(.allCharacters)

                    TextField("Shares", text: $shares)
                        .keyboardType(.decimalPad)

                    TextField("Purchase Price", text: $purchasePrice)
                        .keyboardType(.decimalPad)
                }

                Section("Archetype") {
                    Picker("Archetype", selection: $archetype) {
                        ForEach(Archetype.allCases, id: \.self) { arch in
                            Text(arch.displayName).tag(arch)
                        }
                    }
                    .pickerStyle(.menu)
                }
            }
            .navigationTitle("Add Position")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        Task { await addPosition() }
                    }
                    .disabled(!isFormValid)
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage)
            }
        }
    }

    private func addPosition() async {
        guard let sharesVal = Double(shares), let priceVal = Double(purchasePrice) else {
            errorMessage = "Invalid number format"
            showError = true
            return
        }

        await viewModel.addHolding(
            ticker: ticker.uppercased(),
            shares: sharesVal,
            purchasePrice: priceVal,
            archetype: archetype
        )

        if viewModel.errorMessage == nil {
            dismiss()
        } else {
            errorMessage = viewModel.errorMessage ?? "Unable to add position."
            showError = true
        }
    }
}

struct AddPositionProgressView: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                Color.appBackground.ignoresSafeArea()

                VStack(spacing: ClavisTheme.largeSpacing) {
                    Spacer()

                    VStack(spacing: ClavisTheme.mediumSpacing) {
                        Text(viewModel.pendingTicker ?? "New Position")
                            .font(ClavisTypography.pageTitle)
                            .foregroundColor(.textPrimary)

                        Text(viewModel.progressMessage)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                            .multilineTextAlignment(.center)

                        ProgressView(value: Double(viewModel.progressValue))
                            .progressViewStyle(ClavisProgressStyle())
                            .frame(maxWidth: 280)
                    }
                    .padding(ClavisTheme.cardPadding)
                    .clavisCardStyle(fill: .surfacePrimary)

                    Spacer()
                }
                .padding(ClavisTheme.screenPadding)
            }
            .navigationTitle(viewModel.pendingTicker ?? "New Position")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }
}

struct ClavisProgressStyle: ProgressViewStyle {
    func makeBody(configuration: Configuration) -> some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(Color.slate200)

                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [.accentBlue, .accentBlue.opacity(0.8)],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: geometry.size.width * (configuration.fractionCompleted ?? 0))
                    .animation(.easeInOut(duration: 0.3), value: configuration.fractionCompleted)
            }
        }
        .frame(height: 12)
    }
}
