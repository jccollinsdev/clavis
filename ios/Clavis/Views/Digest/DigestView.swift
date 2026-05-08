import SwiftUI

struct DigestView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = DigestViewModel()
    @State private var hasLoaded = false
    @State private var showUpgradeSheet = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    lengthToggle

                    if let errorMessage = viewModel.errorMessage, viewModel.todayDigest == nil {
                        DigestMessageCard(
                            title: "Briefing unavailable — tap to retry",
                            message: errorMessage,
                            actionTitle: "Retry",
                            action: { Task { await viewModel.loadDigest() } }
                        )
                    } else if viewModel.isLoading && viewModel.todayDigest == nil && !viewModel.isGenerating {
                        loadingState
                    } else if !viewModel.hasHoldings {
                        DigestMessageCard(
                            title: "Add holdings to get your personalized morning briefing",
                            message: "Today stays empty until Clavix knows what you hold.",
                            actionTitle: "Open Holdings",
                            action: { selectedTab = 1 }
                        )
                    } else if viewModel.isGenerating && viewModel.todayDigest == nil {
                        generatingState
                    } else if let digest = viewModel.todayDigest {
                        headerCard(digest)
                        macroSection(digest)
                        sectorSection(digest)
                        positionsSection(digest)
                        watchlistSection(digest)
                        whatToWatchSection(digest)
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.sectionSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .safeAreaInset(edge: .top, spacing: 0) {
                topHeader
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
            .sheet(isPresented: $showUpgradeSheet) {
                DigestUpgradeSheet()
            }
        }
    }

    private var topHeader: some View {
        ClavixPageHeader(
            title: "Today",
            subtitle: Date().formatted(.dateTime.weekday(.abbreviated).month(.abbreviated).day())
        ) {
            Button(action: { selectedTab = 1 }) {
                Image(systemName: "briefcase")
                    .foregroundColor(.textPrimary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.top, ClavisTheme.smallSpacing)
        .padding(.bottom, 6)
        .background(
            Color.backgroundPrimary.opacity(0.9)
                .background(.ultraThinMaterial)
                .ignoresSafeArea(edges: .top)
        )
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Color.border.opacity(0.5))
                .frame(height: 0.5)
        }
    }

    private var lengthToggle: some View {
        ClavisStandardCard(fill: .surface) {
            HStack(spacing: ClavisTheme.smallSpacing) {
                ForEach(DigestLengthOption.allCases, id: \.rawValue) { option in
                    Button(action: { handleLengthTap(option) }) {
                        HStack(spacing: ClavisTheme.microSpacing) {
                            Text(option.title)
                                .font(ClavisTypography.footnoteEmphasis)
                            if option == .verbose {
                                Text("Pro")
                                    .font(ClavisTypography.label)
                            }
                        }
                        .foregroundColor(lengthForeground(option))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, ClavisTheme.smallSpacing)
                        .background(lengthBackground(option))
                        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var loadingState: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
            ClavisLoadingCard(title: "Loading briefing", subtitle: "Pulling today’s portfolio digest.")
            ClavisLoadingCard(title: "Loading macro", subtitle: "Checking the overnight market backdrop.")
            ClavisLoadingCard(title: "Loading positions", subtitle: "Ranking your biggest risk movers.")
        }
    }

    private var generatingState: some View {
                        DigestMessageCard(
                            title: "Your briefing is being prepared...",
                            message: viewModel.activeRun?.currentStageMessage ?? "Clavix is compiling the latest macro, sector, and position changes.",
                            actionTitle: nil,
                            action: nil
                        )
    }

    private func headerCard(_ digest: Digest) -> some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text(digest.structuredSections?.header?.date ?? digest.generatedAt.formatted(date: .abbreviated, time: .shortened))
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)

                HStack(alignment: .center, spacing: ClavisTheme.mediumSpacing) {
                    GradeBadge(grade: digest.structuredSections?.header?.portfolioGrade ?? digest.overallGrade ?? "—", size: .large)
                    VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                        Text("Portfolio composite")
                            .font(ClavisTypography.label)
                            .foregroundColor(.textSecondary)
                        Text(digest.overallScore.map { "\(Int($0.rounded()))" } ?? "—")
                            .font(ClavisTypography.portfolioScore)
                            .foregroundColor(.textPrimary)
                    }
                }

                Text(digest.structuredSections?.header?.summaryLine ?? digest.summary?.sanitizedDisplayText ?? "Your portfolio briefing is ready.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func macroSection(_ digest: Digest) -> some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionTitle("Overnight Macro")
            ClavisStandardCard(fill: .surface) {
                Text(digest.structuredSections?.overnightMacro?.brief.sanitizedDisplayText ?? "No overnight macro summary is available yet.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func sectorSection(_ digest: Digest) -> some View {
        let sectors = digest.structuredSections?.sectorHeat ?? []

        return VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionTitle("Sector Heat")

            if sectors.isEmpty {
                ClavisStandardCard(fill: .surface) {
                    Text("Sector detail is still being assembled for your current holdings.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            } else {
                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: 0) {
                        // TODO: backend should return ETF performance and user exposure per held sector.
                        ForEach(Array(sectors.enumerated()), id: \.element.id) { index, sector in
                            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                                Text(sector.sector.humanizedTitleCasedDisplayText)
                                    .font(ClavisTypography.bodyEmphasis)
                                    .foregroundColor(.textPrimary)
                                Text(sector.brief.sanitizedDisplayText)
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, ClavisTheme.mediumSpacing)

                            if index < sectors.count - 1 {
                                Divider().overlay(Color.border)
                            }
                        }
                    }
                }
            }
        }
    }

    private func positionsSection(_ digest: Digest) -> some View {
        let positions = digest.structuredSections?.positions ?? []

        return VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionTitle("Your Positions")

            if positions.isEmpty {
                ClavisStandardCard(fill: .surface) {
                    Text("No position updates were returned in this digest.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            } else {
                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: 0) {
                        ForEach(Array(positions.enumerated()), id: \.element.id) { index, item in
                            NavigationLink(destination: TickerDetailView(ticker: item.ticker)) {
                                DigestPositionRow(
                                    ticker: item.ticker,
                                    grade: viewModel.grade(for: item.ticker),
                                    delta: viewModel.scoreDelta(for: item.ticker),
                                    summary: item.impactSummary.sanitizedDisplayText
                                )
                            }
                            .buttonStyle(.plain)

                            if index < positions.count - 1 {
                                Divider().overlay(Color.border)
                            }
                        }
                    }
                }
            }
        }
    }

    private func watchlistSection(_ digest: Digest) -> some View {
        let items = digest.structuredSections?.watchlistUpdates?.alerts ?? []

        return VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionTitle("Watchlist Updates")

            if items.isEmpty {
                ClavisStandardCard(fill: .surface) {
                    Text("No watchlist updates in this briefing.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            } else {
                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: 0) {
                        // TODO: backend should return watchlist ticker cards with grade and delta fields.
                        ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                            Text(item.sanitizedDisplayText)
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.vertical, ClavisTheme.mediumSpacing)

                            if index < items.count - 1 {
                                Divider().overlay(Color.border)
                            }
                        }
                    }
                }
            }
        }
    }

    private func whatToWatchSection(_ digest: Digest) -> some View {
        let items = digest.structuredSections?.whatToWatchToday?.catalysts ?? []

        return VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            sectionTitle("What to Watch Today")

            if items.isEmpty {
                ClavisStandardCard(fill: .surface) {
                    Text("No calendar items are scheduled for your portfolio today.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            } else {
                ClavisStandardCard(fill: .surface) {
                    VStack(spacing: 0) {
                        ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                                Text(item.catalyst.sanitizedDisplayText)
                                    .font(ClavisTypography.bodyEmphasis)
                                    .foregroundColor(.textPrimary)
                                Text(item.impactedPositions.joined(separator: ", "))
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, ClavisTheme.mediumSpacing)

                            if index < items.count - 1 {
                                Divider().overlay(Color.border)
                            }
                        }
                    }
                }
            }
        }
    }

    private func handleLengthTap(_ option: DigestLengthOption) {
        if option == .verbose && viewModel.isFreeTier {
            showUpgradeSheet = true
            return
        }

        Task { await viewModel.saveSummaryLength(option) }
    }

    private func lengthForeground(_ option: DigestLengthOption) -> Color {
        if option == .verbose && viewModel.isFreeTier {
            return .accentInk
        }
        return viewModel.summaryLength == option ? .accentInk : .textSecondary
    }

    private func lengthBackground(_ option: DigestLengthOption) -> Color {
        if option == .verbose && viewModel.isFreeTier {
            return .accentBurnt
        }
        return viewModel.summaryLength == option ? .accentBurnt : .surfaceElevated
    }

    private func sectionTitle(_ text: String) -> some View {
        Text(text)
            .font(ClavisTypography.label)
            .foregroundColor(.textSecondary)
    }
}

private struct DigestPositionRow: View {
    let ticker: String
    let grade: String
    let delta: Int?
    let summary: String

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            GradeBadge(grade: grade, size: .compact)

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                HStack(spacing: ClavisTheme.smallSpacing) {
                    Text(ticker)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.accentBurnt)
                    if let delta {
                        Text(deltaText(delta))
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(deltaColor(delta))
                    }
                }

                Text(summary)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .multilineTextAlignment(.leading)
                    .lineLimit(3)
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, ClavisTheme.mediumSpacing)
    }

    private func deltaText(_ value: Int) -> String {
        if value == 0 { return "—" }
        return value > 0 ? "↑ +\(value)" : "↓ \(value)"
    }

    private func deltaColor(_ value: Int) -> Color {
        if value == 0 { return .textSecondary }
        return value > 0 ? .good : .bad
    }
}

private struct DigestMessageCard: View {
    let title: String
    let message: String
    let actionTitle: String?
    let action: (() -> Void)?

    var body: some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text(title)
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text(message)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
                if let actionTitle, let action {
                    ClavisPrimaryButton(title: actionTitle, action: action)
                }
            }
        }
    }
}

private struct DigestUpgradeSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    ClavisStandardCard(fill: .surface) {
                        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                            Text("Verbose briefing is a Pro feature")
                                .font(ClavisTypography.h2)
                                .foregroundColor(.textPrimary)
                            Text("Unlock the full morning memo, including deeper position context and longer-form briefing detail.")
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                            ClavisPrimaryButton(title: "Start 14-day trial", action: {})
                        }
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Upgrade")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundColor(.textSecondary)
                }
            }
        }
    }
}
