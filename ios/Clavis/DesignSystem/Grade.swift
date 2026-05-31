import SwiftUI

/// Bond-grade letter pill.
/// Bands → tier: AAA/AA = good (solid green) · A = good-soft (light green) · BBB/BB = warn (amber) · B/CCC/CC/C = bad (oxblood).
enum CXGrade: String, CaseIterable {
    case AAA, AA, A, BBB, BB, B, CCC, CC, C
}

enum CXGradeSize {
    case xs, sm, md, lg, hero

    /// (width, height, fontSize)
    var dims: (CGFloat, CGFloat, CGFloat) {
        switch self {
        case .xs:   return (30, 18, 10)
        case .sm:   return (38, 22, 11)
        case .md:   return (50, 28, 13)
        case .lg:   return (76, 44, 22)
        case .hero: return (124, 84, 42)
        }
    }
}

struct GradePill: View {
    let grade: CXGrade
    var size: CXGradeSize = .md
    var fill: Bool = true
    var delta: Int? = nil

    @Environment(\.theme) private var theme

    var body: some View {
        let (w, h, fs) = size.dims
        let t = tier(for: grade)
        HStack(spacing: 6) {
            Text(grade.rawValue)
                .font(CXFont.mono(fs, weight: .bold))
                .tracking(0.4)
                .frame(width: w, height: h)
                .foregroundStyle(fill ? t.fg : t.ink)
                .background(fill ? t.bg : Color.clear)
                .overlay(
                    Rectangle().stroke(fill ? t.bg : t.ink,
                                       lineWidth: fill ? 1 : 1.5)
                )
            if let delta { GradeDelta(value: delta, size: max(10, fs * 0.6)) }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(accessibilityDescription)
    }

    private var accessibilityDescription: String {
        var s = "Grade \(grade.rawValue)"
        if let d = delta {
            if d == 0 { s += ", unchanged" }
            else if d > 0 { s += ", up \(d)" }
            else { s += ", down \(abs(d))" }
        }
        return s
    }

    private func tier(for g: CXGrade) -> (bg: Color, fg: Color, ink: Color) {
        switch g {
        case .AAA, .AA:    return (.cxGood,     .white,      .cxGoodInk)
        case .A:           return (.cxGoodSoft, .cxGoodInk,  .cxGoodInk)
        case .BBB, .BB:    return (.cxWarn,     .white,      .cxWarnInk)
        default:           return (.cxBad,   .white,      .cxBadInk)
        }
    }
}

/// Grade delta glyph: ▲ / ▼ / —. Never use emoji arrows.
struct GradeDelta: View {
    let value: Int
    var size: CGFloat = 11

    var body: some View {
        let isZero = value == 0
        let isUp = value > 0
        let color: Color = isZero ? .cxInk3 : (isUp ? .cxGood : .cxBad)
        let arrow = isZero ? "—" : (isUp ? "▲" : "▼")
        Text(isZero ? arrow : "\(arrow) \(abs(value))")
            .font(CXFont.mono(size, weight: .semibold))
            .foregroundStyle(color)
            .accessibilityHidden(true)
    }
}

#if DEBUG
struct GradePill_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            VStack(alignment: .leading, spacing: 16) {
                HStack(spacing: 12) {
                    ForEach(CXGrade.allCases, id: \.rawValue) { g in
                        GradePill(grade: g, size: .md)
                    }
                }
                HStack(spacing: 12) {
                    GradePill(grade: .AAA, size: .xs)
                    GradePill(grade: .AAA, size: .sm)
                    GradePill(grade: .AAA, size: .md)
                    GradePill(grade: .AAA, size: .lg)
                }
                GradePill(grade: .AAA, size: .hero)
                HStack(spacing: 12) {
                    GradePill(grade: .BBB, size: .md, delta: 0)
                    GradePill(grade: .BBB, size: .md, delta: 3)
                    GradePill(grade: .BBB, size: .md, delta: -2)
                }
                HStack(spacing: 12) {
                    GradePill(grade: .AA, size: .md, fill: false)
                    GradePill(grade: .A, size: .md, fill: false)
                    GradePill(grade: .B, size: .md, fill: false)
                }
            }
            .padding(20)
            .background(Color.cxPage)
            .previewDisplayName("Light")
        }
    }
}
#endif
