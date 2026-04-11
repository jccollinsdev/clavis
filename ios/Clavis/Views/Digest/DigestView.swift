import SwiftUI

struct DigestView: View {
    @StateObject private var viewModel = DigestViewModel()

    private var activeRunningRun: AnalysisRun? {
        guard let run = viewModel.activeRun,
              run.status == "running" || run.status == "queued" else {
            return nil
        }
        return run
    }

    private var shouldShowIdleState: Bool {
        !viewModel.isLoading && viewModel.todayDigest == nil && activeRunningRun == nil && viewModel.errorMessage == nil
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if let activeRun = activeRunningRun {
                        AnalysisRunStatusCard(run: activeRun)
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DigestErrorCard(message: errorMessage) {
                            Task { await viewModel.loadDigest() }
                        }
                    }

                    if let timeoutMessage = viewModel.timeoutMessage {
                        DigestTimeoutCard(message: timeoutMessage)
                    }

                    if let digest = viewModel.todayDigest {
                        DigestScoreSummaryCard(digest: digest, holdings: viewModel.holdings)
                        DigestLeadCard(digest: digest)
                        WhatChangedSection(digest: digest, holdings: viewModel.holdings, alerts: viewModel.alerts)
                        WhatMattersTodaySection(digest: digest)
                        WhatToDoSection(digest: digest)
                        PositionsSection(holdings: viewModel.holdings)
                        FullNarrativeSection(digest: digest)
                    } else if shouldShowIdleState {
                        DigestEmptyStateCard {
                            Task { await viewModel.triggerAnalysis() }
                        }
                    }

                    if viewModel.isLoading && viewModel.todayDigest == nil && activeRunningRun == nil && viewModel.errorMessage == nil {
                        ClavisLoadingCard(title: "Loading digest", subtitle: "Fetching the latest morning summary.")
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.largeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Morning Digest")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        Task { await viewModel.triggerAnalysis() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(viewModel.isLoading || viewModel.activeRun?.status == "running")
                }
            }
            .onAppear {
                if viewModel.todayDigest == nil && viewModel.digestHistory.isEmpty && !viewModel.isLoading {
                    Task { await viewModel.loadDigest() }
                }
            }
        }
    }
}

struct DigestScoreSummaryCard: View {
    let digest: Digest
    let holdings: [Position]

    private var portfolioGrade: String {
        if let grade = digest.overallGrade { return grade }
        let grades = holdings.compactMap { $0.riskGrade }
        guard !grades.isEmpty else { return "C" }
        let avg = Double(grades.map(gradeRank).reduce(0, +)) / Double(grades.count)
        return gradeFromAverage(avg)
    }

    private var portfolioScore: Double {
        digest.overallScore ?? 50
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 6) {
                Text("Portfolio Risk")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text("\(Int(portfolioScore.rounded()))")
                    .font(ClavisTypography.metric)
                    .foregroundColor(.textPrimary)
                Text(digest.summary?.sanitizedDisplayText ?? "Latest portfolio summary.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }

            Spacer()

            Text(portfolioGrade)
                .font(ClavisTypography.grade)
                .foregroundColor(ClavisGradeStyle.color(for: portfolioGrade))
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private func gradeRank(_ grade: String) -> Int {
        switch grade {
        case "A": return 5
        case "B": return 4
        case "C": return 3
        case "D": return 2
        case "F": return 1
        default: return 3
        }
    }

    private func gradeFromAverage(_ value: Double) -> String {
        if value >= 4.5 { return "A" }
        if value >= 3.5 { return "B" }
        if value >= 2.5 { return "C" }
        if value >= 1.5 { return "D" }
        return "F"
    }
}

struct DigestLeadCard: View {
    let digest: Digest

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text("Generated \(digest.generatedAt.formatted(date: .abbreviated, time: .shortened))")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)

            Text(digest.summary?.sanitizedDisplayText ?? digest.content.sanitizedDisplayText.firstParagraph ?? "")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct WhatChangedSection: View {
    let digest: Digest
    let holdings: [Position]
    let alerts: [Alert]

    private var gradeChanges: [Alert] { alerts.filter { $0.type == .gradeChange } }
    private var majorEvents: [String] { digest.structuredSections?.majorEvents ?? [] }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("What Changed")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            if !gradeChanges.isEmpty {
                ChangedRow(title: "Grade Changes", detail: "\(gradeChanges.count) position\(gradeChanges.count == 1 ? "" : "s") changed")
            }

            if let firstEvent = majorEvents.first {
                ChangedRow(title: "Major Events", detail: firstEvent)
            }

            if gradeChanges.isEmpty && majorEvents.isEmpty {
                Text("No major changes detected.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct ChangedRow: View {
    let title: String
    let detail: String

    var body: some View {
        HStack(alignment: .top) {
            Text(title)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.textPrimary)
            Spacer()
            Text(detail)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
                .multilineTextAlignment(.trailing)
        }
    }
}

struct WhatMattersTodaySection: View {
    let digest: Digest

    private var matters: [String] {
        Array(((digest.structuredSections?.watchList ?? []) + (digest.structuredSections?.majorEvents ?? [])).prefix(3))
    }

    var body: some View {
        if !matters.isEmpty {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("What Matters Today")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                ForEach(Array(matters.enumerated()), id: \.offset) { index, item in
                    HStack(alignment: .top, spacing: ClavisTheme.smallSpacing) {
                        Text("\(index + 1).")
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(.textTertiary)
                        Text(item)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                    }
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
    }
}

struct WhatToDoSection: View {
    let digest: Digest

    private var actions: [String] {
        Array(digest.structuredSections?.portfolioAdvice.prefix(3) ?? [])
    }

    var body: some View {
        if !actions.isEmpty {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("What To Do")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                ForEach(Array(actions.enumerated()), id: \.offset) { _, action in
                    Text(action)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
    }
}

struct PositionsSection: View {
    let holdings: [Position]

    private var sortedHoldings: [Position] {
        holdings.sorted { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
    }

    var body: some View {
        if !holdings.isEmpty {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("Positions")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)

                ForEach(sortedHoldings) { holding in
                    NavigationLink(destination: PositionDetailView(positionId: holding.id)) {
                        HStack(spacing: ClavisTheme.mediumSpacing) {
                            Text(holding.riskGrade ?? "--")
                                .font(.system(size: 18, weight: .bold))
                                .foregroundColor(ClavisGradeStyle.color(for: holding.riskGrade))
                                .frame(width: 32)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(holding.ticker)
                                    .font(ClavisTypography.bodyEmphasis)
                                    .foregroundColor(.textPrimary)
                                Text(holding.summary?.sanitizedDisplayText ?? "")
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                                    .lineLimit(1)
                            }

                            Spacer()

                            Text("\(Int(holding.totalScore ?? 0))")
                                .font(ClavisTypography.bodyEmphasis)
                                .foregroundColor(.textPrimary)
                        }
                        .padding(ClavisTheme.cardPadding)
                        .clavisCardStyle(fill: .surfacePrimary)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}

struct FullNarrativeSection: View {
    let digest: Digest
    @State private var isExpanded = false

    var body: some View {
        if !digest.content.isEmpty {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) { isExpanded.toggle() }
                } label: {
                    HStack {
                        Text("Full Narrative")
                            .font(ClavisTypography.cardTitle)
                            .foregroundColor(.textPrimary)
                        Spacer()
                        Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(.textTertiary)
                    }
                }

                if isExpanded {
                    MarkdownText(digest.content.sanitizedDisplayText, font: ClavisTypography.body, color: .textSecondary)
                }
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfaceSecondary)
        }
    }
}

struct AnalysisRunStatusCard: View {
    let run: AnalysisRun

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack {
                Text(run.status == "failed" ? "Analysis interrupted" : "Analysis in progress")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Spacer()
                Text(run.status.capitalized)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }

            ProgressView(value: progressValue)
                .tint(.accentBlue)

            Text(statusMessage)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private var progressValue: Double {
        switch run.status {
        case "queued": return 0.12
        case "running": return min(0.95, 0.2 + Double(run.positionsProcessed ?? 0) * 0.18)
        default: return 1
        }
    }

    private var statusMessage: String {
        if run.status == "failed" { return run.displayErrorMessage }
        return "\(run.positionsProcessed ?? 0) positions processed, \(run.eventsProcessed ?? 0) events analyzed."
    }
}

struct DigestErrorCard: View {
    let message: String
    var onRetry: (() -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text(message.sanitizedDisplayText)
                .font(ClavisTypography.body)
                .foregroundColor(.criticalTone)

            if let onRetry {
                Button("Retry", action: onRetry)
                    .buttonStyle(.bordered)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfaceSecondary)
    }
}

struct DigestTimeoutCard: View {
    let message: String

    var body: some View {
        Text(message)
            .font(ClavisTypography.body)
            .foregroundColor(.textSecondary)
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfaceSecondary)
    }
}

struct DigestEmptyStateCard: View {
    let onRunFreshReview: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("No Digest Yet")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Text("Run a fresh review to generate the first digest.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            Button("Run Fresh Review", action: onRunFreshReview)
                .buttonStyle(.borderedProminent)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

private extension String {
    var firstParagraph: String? {
        let paragraphs = components(separatedBy: "\n\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        return paragraphs.first
    }
}
