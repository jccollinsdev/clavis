import SwiftUI

struct TickerDriverCardsSection: View {
    let analysis: PositionAnalysis?

    private var driverCards: [DriverCard] {
        analysis?.driverCards ?? []
    }

    private var driverState: DriverCardsState {
        let cards = driverCards
        return analysis?.driverCardsState ?? (cards.isEmpty ? .pending : .ready)
    }

    private var shouldShowKeyDrivers: Bool {
        !driverCards.isEmpty && (driverState == .ready || driverState == .limited)
    }

    var body: some View {
        if shouldShowKeyDrivers {
            keyDriversCard
        } else if driverState == .limited && driverCards.isEmpty {
            limitedEvidenceCard
        }
    }

    private var keyDriversCard: some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                CX2SectionLabel(text: "Key Drivers")

                VStack(alignment: .leading, spacing: 12) {
                    ForEach(driverCards) { card in
                        DriverCardView(card: card)
                    }
                }
            }
        }
    }

    private var limitedEvidenceCard: some View {
        ClavisStandardCard(fill: .surface) {
            VStack(alignment: .leading, spacing: 8) {
                CX2SectionLabel(text: "Key Drivers")

                Text("Limited evidence")
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.clavixInk)

                Text("The backend returned a limited structured signal set for this holding.")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.clavixInk3)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

private struct DriverCardView: View {
    let card: DriverCard

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 10) {
                rankBadge

                VStack(alignment: .leading, spacing: 4) {
                    Text(card.title)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.clavixInk)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(card.theme.displayName)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.clavixInk3)
                }

                Spacer(minLength: 8)

                HStack(spacing: 6) {
                    driverDirectionBadge
                    driverStrengthBadge
                }
            }

            Text(card.summary)
                .font(ClavisTypography.body)
                .foregroundColor(.clavixInk3)
                .lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)

            if !card.sourceChips.isEmpty {
                sourceChips
            }

            if !card.supportingEvidence.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(card.supportingEvidence) { item in
                        SupportingEvidenceRow(item: item)
                    }
                }
            }
        }
        .padding(12)
        .background(Color.clavixPaper2)
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .stroke(Color.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }

    private var rankBadge: some View {
        Text("#\(card.rank)")
            .font(ClavisTypography.footnoteEmphasis)
            .foregroundColor(.clavixInk)
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(Color.surface)
            .clipShape(Capsule())
            .overlay(Capsule().stroke(Color.border, lineWidth: 1))
    }

    private var driverDirectionBadge: some View {
        HStack(spacing: 4) {
            Image(systemName: card.direction.iconName)
                .font(.system(size: 10, weight: .semibold))
            Text(card.direction.displayName)
                .font(ClavisTypography.label)
        }
        .foregroundColor(directionColor)
        .padding(.horizontal, 8)
        .padding(.vertical, 5)
        .background(directionColor.opacity(0.12))
        .clipShape(Capsule())
    }

    private var driverStrengthBadge: some View {
        Text(card.strength.displayName)
            .font(ClavisTypography.label)
            .foregroundColor(strengthColor)
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(strengthColor.opacity(0.12))
            .clipShape(Capsule())
    }

    private var sourceChips: some View {
        HStack(spacing: 6) {
            ForEach(Array(card.sourceChips.prefix(3)), id: \.self) { source in
                Text(source)
                    .font(ClavisTypography.label)
                    .foregroundColor(.clavixInk3)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 5)
                    .background(Color.surface)
                    .clipShape(Capsule())
                    .overlay(Capsule().stroke(Color.border, lineWidth: 1))
            }
        }
    }

    private var directionColor: Color {
        switch card.direction {
        case .positive: return .riskA
        case .negative: return .riskD
        case .neutral: return .clavixInk3
        }
    }

    private var strengthColor: Color {
        switch card.strength {
        case .strong: return .riskA
        case .moderate: return .informational
        case .limited: return .clavixInk3
        }
    }
}

private struct SupportingEvidenceRow: View {
    let item: SupportingEvidenceItem

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(item.kind.displayName)
                    .font(ClavisTypography.label)
                    .foregroundColor(.clavixInk3)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.surface)
                    .clipShape(Capsule())

                Spacer()

                if let publishedAt = item.publishedAt {
                    Text(publishedAt.formatted(date: .abbreviated, time: .omitted))
                        .font(ClavisTypography.label)
                        .foregroundColor(.clavixInk4)
                }
            }

            Text(item.title)
                .font(ClavisTypography.footnoteEmphasis)
                .foregroundColor(.clavixInk)
                .fixedSize(horizontal: false, vertical: true)

            if !item.summary.isEmpty {
                Text(item.summary)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.clavixInk3)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 6) {
                if !item.source.isEmpty {
                    Text(item.source)
                        .font(ClavisTypography.label)
                        .foregroundColor(.clavixInk4)
                }
            }
        }
        .padding(10)
        .background(Color.surface)
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius - 4, style: .continuous)
                .stroke(Color.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius - 4, style: .continuous))
    }
}
