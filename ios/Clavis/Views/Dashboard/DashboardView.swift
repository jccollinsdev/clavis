import SwiftUI

struct DashboardView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 24) {
                    if viewModel.isLoading && viewModel.holdings.isEmpty {
                        DashboardLoadingCard()
                    }

                    if let errorMessage = viewModel.errorMessage {
                        DashboardErrorCard(message: errorMessage)
                    }

                    // Score is always the first thing seen — spec R-02
                    PortfolioScoreHero(
                        grade: viewModel.portfolioGrade,
                        score: viewModel.portfolioScore,
                        lastUpdatedAt: viewModel.lastUpdatedAt
                    )

                    if !viewModel.needsAttentionPositions.isEmpty {
                        NeedsAttentionSection(positions: viewModel.needsAttentionPositions)
                    }

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
            .background(Color.backgroundPrimary.ignoresSafeArea())
            .navigationTitle("Clavix")
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

// MARK: - Portfolio Score Hero
// The score is the primary visual object. Always first. Always dominant. — spec R-02

struct PortfolioScoreHero: View {
    let grade: String
    let score: Double
    let lastUpdatedAt: Date?

    private var riskColor: Color { ClavisGradeStyle.riskColor(for: grade) }

    var body: some View {
        VStack(spacing: 0) {
            // Score row: large mono number + grade tag
            HStack(alignment: .center) {
                Text("\(Int(score.rounded()))")
                    .font(ClavisTypography.portfolioScore)
                    .foregroundColor(riskColor)
                    .contentTransition(.numericText())
                    .animation(.linear(duration: 0.3), value: score)
                    .monospacedDigit()

                Spacer()

                GradeTag(grade: grade)
            }
            .padding(.bottom, 8)

            // Grade band label
            HStack {
                Text(ClavisGradeStyle.gradeBandLabel(for: grade))
                    .font(ClavisTypography.h2)
                    .foregroundColor(riskColor)
                Spacer()
                if let lastUpdatedAt {
                    Text("Updated \(lastUpdatedAt.formatted(date: .abbreviated, time: .shortened))")
                        .font(ClavisTypography.label)
                        .kerning(0.88)
                        .foregroundColor(.textSecondary)
                }
            }
        }
        .padding(.horizontal, ClavisTheme.cardPadding)
        .padding(.vertical, ClavisTheme.largeSpacing)
        // No card border — score floats on backgroundPrimary for maximum visual dominance
    }
}

// MARK: - Needs Attention

struct NeedsAttentionSection: View {
    let positions: [Position]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("NEEDS ATTENTION")
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)
                .padding(.bottom, 8)

            VStack(spacing: 0) {
                ForEach(positions) { position in
                    NavigationLink(destination: PositionDetailView(positionId: position.id)) {
                        AttentionRow(position: position)
                    }
                    .buttonStyle(.plain)

                    if position.id != positions.last?.id {
                        Rectangle()
                            .fill(Color.border)
                            .frame(height: 1)
                    }
                }
            }
            .background(Color.surface)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }
}

struct AttentionRow: View {
    let position: Position

    private var severityColor: Color {
        switch position.riskGrade {
        case "F": return .riskF
        case "D": return .riskD
        default:  return .riskC
        }
    }

    var body: some View {
        HStack(spacing: 0) {
            // Left severity border — 2.5px
            Rectangle()
                .fill(severityColor)
                .frame(width: 2.5)

            HStack(spacing: 12) {
                Text(position.ticker)
                    .font(ClavisTypography.rowTicker)
                    .foregroundColor(.textPrimary)
                    .frame(minWidth: 44, alignment: .leading)

                RiskBar(
                    score: position.totalScore ?? 50,
                    grade: position.riskGrade ?? "C"
                )
                .frame(maxWidth: .infinity)

                HStack(spacing: 6) {
                    Text("\(Int((position.totalScore ?? 0).rounded()))")
                        .font(ClavisTypography.rowScore)
                        .foregroundColor(ClavisGradeStyle.riskColor(for: position.riskGrade))
                        .frame(width: 28, alignment: .trailing)
                        .monospacedDigit()

                    GradeTag(grade: position.riskGrade ?? "C", compact: true)
                }
            }
            .padding(.vertical, 10)
            .padding(.horizontal, 12)
        }
        .contentShape(Rectangle())
    }
}

// MARK: - Since Last Review

struct SinceLastReviewRow: View {
    let worseningCount: Int
    let improvingCount: Int
    let majorEventCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("SINCE LAST REVIEW")
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)

            HStack(spacing: 0) {
                ReviewMetric(value: worseningCount, label: "Worsening", tint: .riskF)
                Spacer()
                Rectangle().fill(Color.border).frame(width: 1, height: 32)
                Spacer()
                ReviewMetric(value: improvingCount, label: "Improving", tint: .riskA)
                Spacer()
                Rectangle().fill(Color.border).frame(width: 1, height: 32)
                Spacer()
                ReviewMetric(value: majorEventCount, label: "Events", tint: .riskC)
            }
            .padding(.vertical, 12)
            .padding(.horizontal, 16)
            .background(Color.surface)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }
}

struct ReviewMetric: View {
    let value: Int
    let label: String
    let tint: Color

    var body: some View {
        VStack(alignment: .center, spacing: 4) {
            Text("\(value)")
                .font(ClavisTypography.dataNumber)
                .foregroundColor(tint)
                .monospacedDigit()
            Text(label.uppercased())
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)
        }
    }
}

// MARK: - Digest Preview

struct DigestPreviewCard: View {
    let digest: Digest?
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 8) {
                Text("TODAY'S DIGEST")
                    .font(ClavisTypography.label)
                    .kerning(0.88)
                    .foregroundColor(.textSecondary)

                Text(previewText)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textPrimary)
                    .lineLimit(2)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle()
        }
        .buttonStyle(.plain)
    }

    private var previewText: String {
        digest?.summary?.sanitizedDisplayText ?? "Open the latest digest summary."
    }
}

// MARK: - Loading / Error

struct DashboardLoadingCard: View {
    var body: some View {
        ClavisLoadingCard(title: "Loading dashboard", subtitle: "Fetching holdings and digest data.")
    }
}

struct DashboardErrorCard: View {
    let message: String

    var body: some View {
        HStack(spacing: 0) {
            Rectangle().fill(Color.riskF).frame(width: 2.5)
            Text(message)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textPrimary)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
        }
        .background(Color.surface)
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

// MARK: - Backward compat alias used by other files
typealias CompactMetricReadout = ReviewMetric
