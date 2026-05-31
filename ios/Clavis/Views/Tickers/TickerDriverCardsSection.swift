import SwiftUI

/// Hi-Fi v2 "Key drivers" cards. Each driver renders as a tone-tinted card
/// (TAILWIND / PRESSURE / HEADWIND) with a serif title and a strength badge.
struct TickerDriverCardsSection: View {
    let analysis: PositionAnalysis?

    private var driverCards: [DriverCard] {
        analysis?.driverCards ?? []
    }

    private var driverState: DriverCardsState {
        analysis?.driverCardsState ?? (driverCards.isEmpty ? .pending : .ready)
    }

    var body: some View {
        if !driverCards.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                ForEach(driverCards) { card in
                    HiFiDriverCard(card: card)
                }
            }
        } else if driverState == .limited {
            HiFiDriverPlaceholder(
                tone: .warn,
                title: "Limited evidence",
                bodyText: "The backend returned a limited structured signal set for this holding."
            )
        }
    }
}

private struct HiFiDriverCard: View {
    let card: DriverCard

    private var tone: HiFiDriverTone {
        switch card.direction {
        case .negative: return .risk
        case .neutral:  return .warn
        case .positive: return .good
        }
    }

    private var tag: String {
        switch card.direction {
        case .negative: return "HEADWIND"
        case .neutral:  return "PRESSURE"
        case .positive: return "TAILWIND"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text(tag)
                    .font(ClavisTypography.clavixMono(9, weight: .bold))
                    .tracking(0.5)
                    .foregroundColor(.white)
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3)
                    .background(tone.border)
                    .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
                    .fixedSize()

                Text("via \(card.theme.displayName)")
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(tone.ink.opacity(0.75))
                    .lineLimit(1)
            }

            Text(card.title)
                .font(ClavisTypography.clavixSerif(16, weight: .medium))
                .foregroundColor(tone.ink)
                .fixedSize(horizontal: false, vertical: true)

            if !card.summary.isEmpty {
                Text(card.summary)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(tone.ink.opacity(0.85))
                    .lineSpacing(2)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if !card.sourceChips.isEmpty {
                HStack(spacing: 6) {
                    ForEach(Array(card.sourceChips.prefix(3)), id: \.self) { source in
                        Text(source)
                            .font(ClavisTypography.clavixMono(9, weight: .semibold))
                            .tracking(0.3)
                            .foregroundColor(tone.ink.opacity(0.85))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .overlay(
                                RoundedRectangle(cornerRadius: 3, style: .continuous)
                                    .stroke(tone.border.opacity(0.55), lineWidth: 1)
                            )
                            .fixedSize()
                    }
                }
            }
        }
        .padding(14)
        .padding(.trailing, 88)  // leave room for pinned strength badge
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(tone.bg)
        .overlay(
            RoundedRectangle(cornerRadius: ClavixLayout.cardRadius, style: .continuous)
                .stroke(tone.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.cardRadius, style: .continuous))
        .overlay(alignment: .topTrailing) {
            VStack(alignment: .trailing, spacing: 1) {
                Text("STRENGTH")
                    .font(ClavisTypography.clavixMono(9, weight: .bold))
                    .tracking(0.4)
                    .foregroundColor(tone.ink.opacity(0.7))
                Text(card.strength.displayName.uppercased())
                    .font(ClavisTypography.clavixMono(12, weight: .bold))
                    .foregroundColor(tone.ink)
                    .lineLimit(1)
                    .fixedSize()
            }
            .padding(.top, 14)
            .padding(.trailing, 14)
        }
    }
}

private struct HiFiDriverPlaceholder: View {
    let tone: HiFiDriverTone
    let title: String
    let bodyText: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(ClavisTypography.clavixSerif(16, weight: .medium))
                .foregroundColor(tone.ink)
            Text(bodyText)
                .font(ClavisTypography.clavixCaption)
                .foregroundColor(tone.ink.opacity(0.85))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(tone.bg)
        .overlay(
            RoundedRectangle(cornerRadius: ClavixLayout.cardRadius, style: .continuous)
                .stroke(tone.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.cardRadius, style: .continuous))
    }
}

private enum HiFiDriverTone {
    case good, warn, risk

    var ink: Color {
        switch self {
        case .good: return .clavixGoodInk
        case .warn: return .clavixWarnInk
        case .risk: return .clavixBadInk
        }
    }

    var bg: Color {
        switch self {
        case .good: return .clavixGoodSoft
        case .warn: return .clavixWarnSoft
        case .risk: return .clavixBadSoft
        }
    }

    var border: Color {
        switch self {
        case .good: return .clavixGood
        case .warn: return .clavixWarn
        case .risk: return .clavixBad
        }
    }
}
