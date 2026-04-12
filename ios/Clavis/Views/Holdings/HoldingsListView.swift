import SwiftUI

struct HoldingsListView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = HoldingsViewModel()
    @State private var positionToDelete: Position?
    @State private var showDeleteConfirmation = false

    private var sortedHoldings: [Position] {
        viewModel.holdings.sorted { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ClavisTopBar(onLogoTap: { selectedTab = 0 }) {
                    Button {
                        Task { await viewModel.refreshHoldings() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                    .disabled(viewModel.isRefreshing)

                    Button {
                        viewModel.showAddSheet = true
                    } label: {
                        Label("Add Position", systemImage: "plus")
                    }

                    Button {
                        positionToDelete = sortedHoldings.first
                        showDeleteConfirmation = true
                    } label: {
                        Label("Delete Position", systemImage: "trash")
                    }
                    .disabled(sortedHoldings.isEmpty)

                    Divider()

                    Button {
                        selectedTab = 1
                    } label: {
                        Label("Holdings", systemImage: "briefcase.fill")
                    }

                    Button {
                        selectedTab = 2
                    } label: {
                        Label("Digest", systemImage: "newspaper.fill")
                    }

                    Button {
                        selectedTab = 3
                    } label: {
                        Label("Alerts", systemImage: "bell.fill")
                    }

                    Button {
                        selectedTab = 4
                    } label: {
                        Label("Settings", systemImage: "gearshape.fill")
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 8)
                .padding(.bottom, 12)

                ScrollView {
                    LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                        if let errorMessage = viewModel.errorMessage {
                            DashboardErrorCard(message: errorMessage)
                        }

                        if viewModel.isLoading && viewModel.holdings.isEmpty {
                            ClavisLoadingCard(title: "Loading holdings", subtitle: "Pulling positions and the latest scores.")
                        } else if viewModel.holdings.isEmpty {
                            HoldingsEmptyState(onAddPosition: { viewModel.showAddSheet = true })
                        } else {
                            HoldingsOverviewCard(
                                positions: sortedHoldings,
                                lastUpdatedAt: viewModel.lastRefreshedAt
                            )

                            if !needsReviewPositions.isEmpty {
                                HoldingsSectionCard(title: "Needs Review") {
                                    ForEach(needsReviewPositions) { position in
                                        holdingRow(for: position)
                                    }
                                }
                            }

                            HoldingsSectionCard(title: sectionSubtitle) {
                                ForEach(sortedHoldings) { position in
                                    holdingRow(for: position)
                                }
                            }
                        }
                    }
                    .padding(.horizontal, ClavisTheme.screenPadding)
                    .padding(.top, ClavisTheme.mediumSpacing)
                    .padding(.bottom, ClavisTheme.extraLargeSpacing)
                }
                .refreshable {
                    await viewModel.refreshHoldings()
                }
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
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
            .onAppear {
                viewModel.showError = false
                if viewModel.holdings.isEmpty && !viewModel.isLoading {
                    Task { await viewModel.loadHoldings() }
                }
            }
            .alert("Delete Position", isPresented: $showDeleteConfirmation) {
                Button("Cancel", role: .cancel) {
                    positionToDelete = nil
                }
                Button("Delete", role: .destructive) {
                    if let position = positionToDelete {
                        Task { await viewModel.deleteHolding(position) }
                    }
                    positionToDelete = nil
                }
            } message: {
                if let position = positionToDelete {
                    Text("Are you sure you want to delete \(position.ticker)? This action cannot be undone.")
                }
            }
        }
    }

    private var needsReviewPositions: [Position] {
        sortedHoldings.filter {
            $0.riskGrade == "D" || $0.riskGrade == "F" || $0.riskTrend == .increasing
        }
    }

    private var sectionSubtitle: String {
        let count = sortedHoldings.count
        return "\(count) position\(count == 1 ? "" : "s") ranked by current risk"
    }

    @ViewBuilder
    private func holdingRow(for position: Position) -> some View {
        NavigationLink(destination: PositionDetailView(positionId: position.id)) {
            PositionCardRow(position: position)
        }
        .buttonStyle(.plain)
        .onLongPressGesture(minimumDuration: 0.5) {
            Task { await viewModel.deleteHolding(position) }
        }
        .contextMenu {
            Button(role: .destructive) {
                Task { await viewModel.deleteHolding(position) }
            } label: {
                Label("Delete Position", systemImage: "trash")
            }
        }
    }
}

struct HoldingsOverviewCard: View {
    let positions: [Position]
    let lastUpdatedAt: Date?

    private var averageScore: Double? {
        let scores = positions.compactMap(\.totalScore)
        guard !scores.isEmpty else { return nil }
        return scores.reduce(0, +) / Double(scores.count)
    }

    private var trackedValue: Double? {
        let values = positions.compactMap(\.currentValue)
        guard !values.isEmpty else { return nil }
        return values.reduce(0, +)
    }

    private var highRiskCount: Int {
        positions.filter { $0.riskGrade == "D" || $0.riskGrade == "F" }.count
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Portfolio Overview")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            VStack(alignment: .leading, spacing: 10) {
                HoldingsOverviewMetricRow(
                    title: "Average score",
                    value: averageScore.map { "\(Int($0.rounded()))" } ?? "--",
                    valueColor: ClavisDecisionStyle.color(for: averageScore ?? 50)
                )

                HoldingsOverviewMetricRow(
                    title: "Tracked value",
                    value: trackedValue.map(formatCurrency) ?? "Updating"
                )

                HoldingsOverviewMetricRow(
                    title: "High risk",
                    value: "\(highRiskCount)",
                    valueColor: .riskF
                )
            }

            if let lastUpdatedAt {
                Text("Updated \(lastUpdatedAt.formatted(date: .abbreviated, time: .shortened))")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisHeroCardStyle(fill: .surface)
    }

    private func formatCurrency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "$0"
    }
}

struct HoldingsOverviewMetricRow: View {
    let title: String
    let value: String
    var valueColor: Color = .textPrimary

    var body: some View {
        HStack(spacing: 12) {
            Text(title)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)

            Spacer()

            Text(value)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(valueColor)
                .monospacedDigit()
        }
    }
}

struct HoldingsStatPill: View {
    let title: String
    let value: String
    var accent: Color = .textPrimary

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(ClavisTypography.label)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(accent)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
    }
}

struct HoldingsSectionCard<Content: View>: View {
    let title: String
    var subtitle: String? = nil
    @ViewBuilder let content: Content

    init(title: String, subtitle: String? = nil, @ViewBuilder content: () -> Content) {
        self.title = title
        self.subtitle = subtitle
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                if let subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }
            }

            VStack(spacing: ClavisTheme.smallSpacing) {
                content
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct PositionCardRow: View {
    let position: Position

    private var grade: String {
        position.riskGrade ?? "C"
    }

    private var scoreText: String {
        if let score = position.totalScore {
            return "\(Int(score.rounded()))"
        }
        return "--"
    }

    private var subtitleText: String {
        if let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
            return summary
        }
        if position.analysisStartedAt != nil && position.riskGrade == nil {
            return "Analysis in progress. This position will populate when scoring finishes."
        }
        return "No summary available yet."
    }

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 8) {
                    Text(position.ticker)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)

                    HoldingsSignalPill(text: position.archetype.displayName)
                }

                Text(subtitleText)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .lineLimit(2)
            }

            Spacer(minLength: 12)

            VStack(alignment: .trailing, spacing: 6) {
                Text(scoreText)
                    .font(ClavisTypography.dataNumber)
                    .foregroundColor(ClavisGradeStyle.riskColor(for: position.riskGrade))
                    .monospacedDigit()

                GradeTag(grade: grade, compact: true)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfaceElevated)
    }
}

struct HoldingsSignalPill: View {
    let text: String
    var accent: Color = .textSecondary

    var body: some View {
        Text(text)
            .font(ClavisTypography.footnote)
            .foregroundColor(accent)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .clavisSecondaryCardStyle(fill: .surface)
    }
}

// MARK: - Holdings Empty State

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
                    .tint(Color.informational)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle()
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.vertical, ClavisTheme.largeSpacing)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }
}

// MARK: - Backward compat: keep HoldingRow as alias
typealias HoldingRow = PositionCardRow

// MARK: - Add Position Sheet

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

// MARK: - Add Position Progress View

struct AddPositionProgressView: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Spacer()

                VStack(spacing: 20) {
                    // Status icon
                    ZStack {
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.surface)
                            .frame(width: 80, height: 80)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))

                        Image(systemName: viewModel.progressValue >= 1.0 ? "checkmark" : "chart.line.uptrend.xyaxis")
                            .font(.system(size: 28, weight: .medium))
                            .foregroundColor(viewModel.progressValue >= 1.0 ? .riskA : .textSecondary)
                            .animation(.linear(duration: 0.3), value: viewModel.progressValue)
                    }

                    VStack(spacing: 6) {
                        Text(primaryProgressMessage)
                            .font(ClavisTypography.h2)
                            .foregroundColor(.textPrimary)
                            .multilineTextAlignment(.center)

                        Text(progressDescription)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                            .multilineTextAlignment(.center)
                    }

                    // Progress bar — flat, no capsule
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Rectangle()
                                .fill(Color.border)
                                .frame(height: 4)
                            Rectangle()
                                .fill(ClavisGradeStyle.riskColor(for: progressGrade))
                                .frame(width: geo.size.width * CGFloat(viewModel.progressValue), height: 4)
                                .animation(.spring(response: 0.5, dampingFraction: 0.82), value: viewModel.progressValue)
                        }
                    }
                    .frame(height: 4)

                    Text(progressStageText)
                        .font(ClavisTypography.label)
                        .kerning(0.88)
                        .foregroundColor(.textSecondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 28)
                .background(Color.surface)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
                .clipShape(RoundedRectangle(cornerRadius: 8))

                Spacer()
            }
            .padding(24)
            .background(Color.backgroundPrimary.ignoresSafeArea())
            .navigationTitle(viewModel.pendingTicker ?? "New Position")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private var primaryProgressMessage: String {
        viewModel.progressValue >= 1.0 ? "Analysis complete" : viewModel.progressMessage
    }

    private var progressDescription: String {
        if let pendingTicker = viewModel.pendingTicker {
            return "\(pendingTicker) was added. Clavix is now analyzing this holding."
        }
        return "Preparing your new holding."
    }

    private var progressGrade: String {
        if viewModel.progressValue >= 1.0 { return "A" }
        if viewModel.progressValue >= 0.6 { return "B" }
        if viewModel.progressValue >= 0.3 { return "C" }
        return "D"
    }

    private var progressStageText: String {
        if viewModel.progressValue >= 1.0 { return "POSITION READY" }
        switch viewModel.progressMessage {
        case let m where m.contains("Adding"):      return "CREATING POSITION"
        case let m where m.contains("Queueing"):    return "SCHEDULING ANALYSIS"
        case let m where m.contains("Fetching"):    return "COLLECTING CONTEXT"
        case let m where m.contains("Classifying"): return "MATCHING HEADLINES"
        case let m where m.contains("Analyzing"):   return "SCORING POSITION"
        case let m where m.contains("Building"):    return "WRITING REPORT"
        default:                                     return "RUNNING ANALYSIS"
        }
    }
}

// Keep AnimatedProgressBar defined for any remaining references
struct AnimatedProgressBar: View {
    let progress: Double
    let shimmerPhase: CGFloat

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(Color.border).frame(height: 4)
                Rectangle()
                    .fill(Color.riskB)
                    .frame(width: geo.size.width * CGFloat(min(max(progress, 0), 1)), height: 4)
                    .animation(.spring(response: 0.5, dampingFraction: 0.82), value: progress)
            }
        }
        .frame(height: 4)
    }
}
