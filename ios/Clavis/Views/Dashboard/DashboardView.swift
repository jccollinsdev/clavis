import SwiftUI

struct DashboardView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if viewModel.isLoading && viewModel.holdings.isEmpty {
                        DashboardLoadingCard()
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    PortfolioStatusCard(
                        grade: viewModel.portfolioGrade,
                        score: viewModel.portfolioScore,
                        summary: viewModel.portfolioSummary,
                        lastUpdatedAt: viewModel.lastUpdatedAt
                    )

                    NeedsAttentionSection(positions: viewModel.needsAttentionPositions)

                    SinceLastReviewRow(
                        worseningCount: viewModel.deterioratingCount,
                        improvingCount: viewModel.improvingCount,
                        majorEventCount: viewModel.majorEventCount
                    )

                    DigestPreviewCard(digest: viewModel.todayDigest) {
                        selectedTab = 2
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.largeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Dashboard")
            .navigationBarTitleDisplayMode(.large)
            .refreshable {
                await viewModel.loadData()
            }
            .onAppear {
                if viewModel.holdings.isEmpty && viewModel.todayDigest == nil && !viewModel.isLoading {
                    Task { await viewModel.loadData() }
                }
            }
        }
    }
}

struct DashboardLoadingCard: View {
    var body: some View {
        ClavisLoadingCard(title: "Loading dashboard", subtitle: "Fetching holdings and digest data.")
    }
}

struct PortfolioStatusCard: View {
    let grade: String
    let score: Double
    let summary: String
    let lastUpdatedAt: Date?

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Portfolio Risk")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)

                    Text("\(Int(score.rounded()))")
                        .font(ClavisTypography.metric)
                        .foregroundColor(.textPrimary)
                }

                Spacer()

                Text(grade)
                    .font(ClavisTypography.grade)
                    .foregroundColor(ClavisGradeStyle.color(for: grade))
            }

            Text(summary)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)

            if let lastUpdatedAt {
                Text("Updated \(lastUpdatedAt.formatted(date: .abbreviated, time: .shortened))")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct NeedsAttentionSection: View {
    let positions: [Position]

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Needs Attention")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            if positions.isEmpty {
                Text("No positions currently need attention.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            } else {
                ForEach(positions) { position in
                    NavigationLink(destination: PositionDetailView(positionId: position.id)) {
                        HStack(spacing: ClavisTheme.mediumSpacing) {
                            Text(position.riskGrade ?? "--")
                                .font(.system(size: 22, weight: .bold))
                                .foregroundColor(ClavisGradeStyle.color(for: position.riskGrade))
                                .frame(width: 36)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(position.ticker)
                                    .font(ClavisTypography.bodyEmphasis)
                                    .foregroundColor(.textPrimary)

                                Text(position.summary?.sanitizedDisplayText ?? "Monitoring this position for changes.")
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                                    .lineLimit(2)
                            }

                            Spacer()
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

struct SinceLastReviewRow: View {
    let worseningCount: Int
    let improvingCount: Int
    let majorEventCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Since Last Review")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            HStack(spacing: ClavisTheme.mediumSpacing) {
                CompactMetricReadout(value: worseningCount, label: "Worsening", tint: .criticalTone)
                CompactMetricReadout(value: improvingCount, label: "Improving", tint: .successTone)
                CompactMetricReadout(value: majorEventCount, label: "Events", tint: .warningTone)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

struct CompactMetricReadout: View {
    let value: Int
    let label: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("\(value)")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(tint)
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct DigestPreviewCard: View {
    let digest: Digest?
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Today's Digest")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.textPrimary)

                    Text(previewText)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .lineLimit(2)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.textTertiary)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
        .buttonStyle(.plain)
    }

    private var previewText: String {
        digest?.summary?.sanitizedDisplayText ?? "Open the latest digest summary."
    }
}

struct DashboardErrorCard: View {
    let message: String

    var body: some View {
        Text(message)
            .font(ClavisTypography.footnote)
            .foregroundColor(.criticalTone)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(ClavisTheme.cardPadding)
            .background(Color.warningSurface)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }
}
