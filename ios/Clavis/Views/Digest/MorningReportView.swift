import SwiftUI

/// Full Morning Report (the digest prose). Reached from the Today screen's
/// Morning Report card. Reuses the parent DigestViewModel so the data is
/// already loaded when the user opens it.
struct MorningReportView: View {
    @ObservedObject var viewModel: DigestViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let digest = viewModel.todayDigest {
                    masthead(digest)
                    macroSection(digest)
                    sectorSection(digest)
                    positionsSection(digest)
                    watchlistSection(digest)
                    whatToWatchSection(digest)
                    footer(digest)
                } else {
                    ClavixCard(fill: .clavixPaper) {
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
            ClavixLargeHeader(
                eyebrow: "Daily risk brief",
                title: "Morning Report",
                trailing: AnyView(
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark")
                            .foregroundColor(.clavixInk)
                    }
                )
            )
        }
    }

    private func masthead(_ digest: Digest) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                Text("CLAVIX · MORNING REPORT")
                    .font(ClavisTypography.clavixMono(10, weight: .bold))
                    .tracking(1.5)
                    .foregroundColor(.clavixInk3)
                Spacer()
                Text(digest.structuredSections?.header?.date ?? digest.generatedAt.formatted(date: .abbreviated, time: .shortened))
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk3)
            }
            Rectangle().fill(Color.clavixRule).frame(height: 1)
            HStack(alignment: .center, spacing: 12) {
                ClavixGradeBadge(portfolioGrade(digest), size: 44)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Portfolio composite")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                    Text(portfolioScoreText(digest))
                        .font(ClavisTypography.clavixMono(22, weight: .semibold))
                        .foregroundColor(.clavixInk)
                }
                Spacer()
            }
            Text(digest.structuredSections?.header?.summaryLine ?? digest.summary?.sanitizedDisplayText ?? "Your portfolio briefing is ready.")
                .font(ClavisTypography.clavixSerif(15))
                .foregroundColor(.clavixInk2)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func macroSection(_ digest: Digest) -> some View {
        ClavixSection(eyebrow: "Overnight macro", title: "What moved overnight") {
            ClavixCard {
                Text(digest.structuredSections?.overnightMacro?.brief.sanitizedDisplayText ?? "Overnight macro section is being generated.")
                    .font(ClavisTypography.clavixSerif(14))
                    .foregroundColor(.clavixInk2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func sectorSection(_ digest: Digest) -> some View {
        let sectors = digest.structuredSections?.sectorHeat ?? []
        return ClavixSection(eyebrow: "Sector heat", title: "Your sectors") {
            if sectors.isEmpty {
                ClavixCard {
                    Text("Sector detail is being assembled for your holdings.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(sectors.enumerated()), id: \.element.id) { index, sector in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(sector.sector.humanizedTitleCasedDisplayText)
                                    .font(ClavisTypography.clavixMono(11, weight: .bold))
                                    .foregroundColor(.clavixInk)
                                Text(sector.brief.sanitizedDisplayText)
                                    .font(ClavisTypography.clavixCaption)
                                    .foregroundColor(.clavixInk2)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(14)
                            if index < sectors.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    private func positionsSection(_ digest: Digest) -> some View {
        let positions = digest.structuredSections?.positions ?? []
        return ClavixSection(eyebrow: "Your positions", title: "Position changes") {
            if positions.isEmpty {
                ClavixCard {
                    Text("No material position changes in this briefing.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(positions.enumerated()), id: \.element.id) { index, item in
                            NavigationLink(destination: TickerDetailView(ticker: item.ticker)) {
                                positionRow(item)
                            }
                            .buttonStyle(.plain)
                            if index < positions.count - 1 {
                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                            }
                        }
                    }
                }
            }
        }
    }

    private func positionRow(_ item: DigestPositionImpact) -> some View {
        HStack(alignment: .top, spacing: 12) {
            ClavixGradeBadge(viewModel.grade(for: item.ticker), size: 28)
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(item.ticker)
                        .font(ClavisTypography.clavixMono(13, weight: .bold))
                        .foregroundColor(.clavixInk)
                    if let delta = viewModel.scoreDelta(for: item.ticker), delta != 0 {
                        Text(delta > 0 ? "+\(delta)" : "\(delta)")
                            .font(ClavisTypography.clavixMono(11, weight: .semibold))
                            .foregroundColor(delta > 0 ? .clavixGood : .clavixBad)
                    }
                }
                Text(item.impactSummary.sanitizedDisplayText)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk2)
                    .lineLimit(3)
                    .multilineTextAlignment(.leading)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
    }

    private func watchlistSection(_ digest: Digest) -> some View {
        let items = digest.structuredSections?.watchlistUpdates?.alerts ?? []
        return ClavixSection(eyebrow: "Tracked tickers", title: "Tracked updates") {
            if items.isEmpty {
                ClavixCard {
                    Text("No tracked-ticker updates in this briefing.")
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            } else {
                ClavixCard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                            Text(item.sanitizedDisplayText)
                                .font(ClavisTypography.clavixSerif(14))
                                .foregroundColor(.clavixInk2)
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

    private func whatToWatchSection(_ digest: Digest) -> some View {
        let items = digest.structuredSections?.whatToWatchToday?.catalysts ?? []
        return ClavixSection(eyebrow: "Today", title: "What to watch") {
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

    private func footer(_ digest: Digest) -> some View {
        Text("Generated by Clavix at \(digest.generatedAt.formatted(date: .omitted, time: .shortened)). View full methodology →")
            .font(ClavisTypography.clavixCaption)
            .foregroundColor(.clavixInk3)
            .padding(.top, 8)
    }

    // MARK: - Helpers

    private func portfolioGrade(_ digest: Digest) -> String {
        if !viewModel.holdings.isEmpty,
           PortfolioMath.weightedScore(viewModel.holdings) != nil {
            return PortfolioMath.weightedGrade(viewModel.holdings)
        }
        return digest.structuredSections?.header?.portfolioGrade ?? digest.overallGrade ?? "—"
    }

    private func portfolioScoreText(_ digest: Digest) -> String {
        if let weighted = PortfolioMath.weightedScore(viewModel.holdings) {
            return "\(Int(weighted.rounded()))"
        }
        return digest.overallScore.map { "\(Int($0.rounded()))" } ?? "—"
    }
}
