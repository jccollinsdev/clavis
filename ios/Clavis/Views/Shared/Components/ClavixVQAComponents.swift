import SwiftUI

// Production-available versions of the VisualQA atom components.
// These keep VQA naming so the design canon in ClavixVisualQA.swift (#if DEBUG)
// can continue to maintain a private mirror while live tabs adopt them.

struct ClavixScreen<Content: View>: View {
    let eyebrow: String
    let title: String
    var trailing: AnyView? = nil
    @ViewBuilder let content: Content

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) { content }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 8)
                .padding(.bottom, ClavixLayout.bottomPad)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .safeAreaInset(edge: .top, spacing: 0) {
            ClavixLargeHeader(eyebrow: eyebrow, title: title, trailing: trailing)
        }
    }
}

struct ClavixLargeHeader: View {
    let eyebrow: String
    let title: String
    var trailing: AnyView? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                ClavixEyebrow(eyebrow)
                Spacer()
                if let trailing { trailing }
            }
            Text(title)
                .font(ClavisTypography.clavixSerif(32, weight: .medium))
                .tracking(-0.6)
                .foregroundColor(.clavixInk)
        }
        .padding(.horizontal, ClavixLayout.pad)
        .padding(.top, 4)
        .padding(.bottom, 14)
        .background(Color.clavixPage.ignoresSafeArea(edges: .top))
    }
}

struct ClavixStickyBar: View {
    var trailing: AnyView? = nil

    var body: some View {
        ZStack {
            HStack(spacing: 12) {
                Image("clavix_logo")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 36, height: 36)
                    .accessibilityHidden(true)
                Spacer(minLength: 8)
                if let trailing { trailing }
            }
            Text("CLAVIX")
                .font(ClavisTypography.clavixMono(21, weight: .bold))
                .tracking(1.5)
                .foregroundColor(.clavixInk)
        }
        .padding(.horizontal, ClavixLayout.pad)
        .padding(.vertical, 10)
        .background(Color.clavixPage.ignoresSafeArea(edges: .top))
        .overlay(alignment: .bottom) { Rectangle().fill(Color.clavixRule).frame(height: 1) }
    }
}

struct ClavixEyebrow: View {
    let text: String
    init(_ text: String) { self.text = text }
    var body: some View {
        Text(text.uppercased())
            .font(ClavisTypography.clavixMono(10, weight: .bold))
            .tracking(0.7)
            .foregroundColor(.clavixInk3)
    }
}

struct ClavixCard<Content: View>: View {
    var padding: CGFloat = 16
    var fill: Color = .clavixPaper
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(fill)
            .overlay(RoundedRectangle(cornerRadius: ClavixLayout.cardRadius).stroke(Color.clavixRule, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.cardRadius))
    }
}

struct ClavixSection<Content: View>: View {
    let eyebrow: String
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ClavixEyebrow(eyebrow)
            Text(title)
                .font(ClavisTypography.clavixSerif(20, weight: .medium))
                .tracking(-0.3)
                .foregroundColor(.clavixInk)
            content
        }
        .padding(.top, 6)
    }
}

struct ClavixStatePanel: View {
    let glyph: String
    let message: String
    let cta: String
    var tone: Color = .clavixInk
    let action: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: glyph)
                .font(.system(size: 52, weight: .light))
                .foregroundColor(tone)
            Text(message)
                .font(ClavisTypography.clavixSerif(17, weight: .regular))
                .foregroundColor(.clavixInk2)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
            Button(action: action) {
                Text(cta)
                    .font(ClavisTypography.clavixMono(11, weight: .semibold))
                    .foregroundColor(.clavixPaper)
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 10)
                    .background(tone)
                    .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous))
            }
            .buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 38)
    }
}

struct ClavixInlineNoticeCard: View {
    let eyebrow: String
    let title: String
    let message: String
    var footnote: String? = nil
    var glyph: String? = nil
    var fill: Color = .clavixPaper
    var foreground: Color = .clavixInk
    var secondary: Color = .clavixInk2
    var buttonTitle: String? = nil
    var action: (() -> Void)? = nil

    var body: some View {
        ClavixCard(fill: fill) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 12) {
                    if let glyph {
                        Image(systemName: glyph)
                            .font(.system(size: 17, weight: .semibold))
                            .foregroundColor(foreground)
                            .frame(width: 24, alignment: .leading)
                            .padding(.top, 2)
                    }

                    VStack(alignment: .leading, spacing: 6) {
                        ClavixEyebrow(eyebrow)
                        Text(title)
                            .font(ClavisTypography.clavixSerif(18, weight: .medium))
                            .foregroundColor(foreground)
                            .fixedSize(horizontal: false, vertical: true)
                        Text(message)
                            .font(ClavisTypography.clavixCaption)
                            .foregroundColor(secondary)
                            .fixedSize(horizontal: false, vertical: true)
                        if let footnote, !footnote.isEmpty {
                            Text(footnote)
                                .font(ClavisTypography.clavixMono(10, weight: .regular))
                                .tracking(0.3)
                                .foregroundColor(secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                if let buttonTitle, let action {
                    Button(action: action) {
                        Text(buttonTitle)
                            .font(ClavisTypography.clavixMono(11, weight: .semibold))
                            .foregroundColor(.clavixPaper)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 11)
                            .background(foreground)
                            .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}

/// AAA/AA/A/BBB/BB/B/CCC/CC/C/F grade badge in the bond-rating-agency visual style.
struct ClavixGradeBadge: View {
    let grade: String
    var size: CGFloat = 44

    init(_ grade: String, size: CGFloat = 44) {
        self.grade = grade
        self.size = size
    }

    var body: some View {
        let metrics = gradeMetrics
        Text(grade)
            .font(ClavisTypography.clavixMono(metrics.font, weight: .bold))
            .tracking(0.4)
            .foregroundColor(foreground)
            .frame(width: metrics.width, height: metrics.height)
            .background(color)
    }

    private var gradeMetrics: (width: CGFloat, height: CGFloat, font: CGFloat) {
        switch size {
        case 80...: return (124, 84, 42)
        case 40...: return (76, 44, 22)
        case 28...: return (50, 28, 13)
        case 22...: return (38, 22, 11)
        default: return (30, 18, 10)
        }
    }

    private var color: Color {
        switch grade {
        case "AAA", "AA": return .clavixGood
        case "A":         return .clavixGoodSoft
        case "BBB", "BB": return .clavixWarn
        case "—":         return .clavixInk4
        default:           return .clavixBad
        }
    }

    private var foreground: Color {
        switch grade {
        case "AAA", "AA", "BBB", "BB": return .white
        case "A":                       return .clavixGoodInk
        default:                        return .white
        }
    }
}

struct ClavixTabBar: View {
    @Binding var selectedTab: Int

    private let tabs: [(title: String, icon: String)] = [
        ("Today", "doc.text"),
        ("Holdings", "rectangle.grid.1x2"),
        ("Search", "magnifyingglass"),
        ("Alerts", "bell"),
        ("Settings", "gearshape")
    ]

    var body: some View {
        VStack(spacing: 0) {
            Rectangle().fill(Color.clavixRule).frame(height: 1)
            HStack(spacing: 0) {
                ForEach(tabs.indices, id: \.self) { index in
                    Button { selectedTab = index } label: {
                        VStack(spacing: 3) {
                            Image(systemName: tabs[index].icon)
                                .font(.system(size: 17, weight: .regular))
                            Text(tabs[index].title)
                                .font(ClavisTypography.inter(10, weight: selectedTab == index ? .semibold : .medium))
                                .tracking(0.1)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, 8)
                        .padding(.bottom, 6)
                        .foregroundColor(selectedTab == index ? .clavixAccent : .clavixInk4)
                    }
                    .buttonStyle(.plain)
                }
            }
            .background(Color.clavixPaper)
        }
        .background(Color.clavixPaper.ignoresSafeArea(edges: .bottom))
    }
}

struct ClavixScoreBar: View {
    let score: Int

    /// Interpolate a solid color: red (0) → amber (50) → green (100).
    private var scoreColor: Color {
        let t = CGFloat(min(max(score, 0), 100)) / 100.0
        let red   = (r: 0.88 as CGFloat, g: 0.14 as CGFloat, b: 0.14 as CGFloat)
        let amber = (r: 1.00 as CGFloat, g: 0.70 as CGFloat, b: 0.00 as CGFloat)
        let green = (r: 0.08 as CGFloat, g: 0.74 as CGFloat, b: 0.30 as CGFloat)
        let from = t <= 0.5 ? red   : amber
        let to   = t <= 0.5 ? amber : green
        let u    = t <= 0.5 ? t / 0.5 : (t - 0.5) / 0.5
        return Color(
            red:   Double(from.r + u * (to.r - from.r)),
            green: Double(from.g + u * (to.g - from.g)),
            blue:  Double(from.b + u * (to.b - from.b))
        )
    }

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 3)
                    .fill(Color.clavixRule2)
                RoundedRectangle(cornerRadius: 3)
                    .fill(scoreColor)
                    .frame(width: geo.size.width * CGFloat(min(max(score, 0), 100)) / 100)
            }
        }
    }
}

/// VQAPill 1:1: small mono chip used for toolbars and quick filters.
/// Active variant fills with `clavixInk`, inactive uses paper2 + rule.
struct ClavixPill: View {
    let label: String
    var active: Bool = false

    var body: some View {
        Text(label)
            .font(ClavisTypography.clavixMono(10, weight: .bold))
            .tracking(0.4)
            .foregroundColor(active ? .clavixPaper : .clavixInk2)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(active ? Color.clavixInk : Color.clavixPaper2)
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.clavixRule, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
    }
}

/// VQAColumnHeader: ALL CAPS mono label used in the Holdings ledger header.
struct ClavixColumnHeader: View {
    let text: String
    var align: TextAlignment = .leading

    init(_ text: String, align: TextAlignment = .leading) {
        self.text = text
        self.align = align
    }

    var body: some View {
        Text(text.uppercased())
            .font(ClavisTypography.clavixMono(9, weight: .bold))
            .tracking(0.7)
            .foregroundColor(.clavixInk3)
            .multilineTextAlignment(align)
            .lineLimit(1)
            .minimumScaleFactor(0.75)
    }
}

/// VQAMiniSpark 1:1: tiny inline sparkline used in ledger rows. Renders a
/// deterministic-but-cheap zigzag so the column has a visual rhythm even
/// before real per-position price history is wired in.
struct ClavixMiniSpark: View {
    let tone: Color
    var seed: Int = 0

    var body: some View {
        GeometryReader { geo in
            Path { path in
                let count = 12
                let stepX = geo.size.width / CGFloat(count - 1)
                let baseline = geo.size.height / 2
                // Deterministic shape until real per-position price history is wired in.
                for i in 0..<count {
                    let phase = sin(Double(i + seed) * 0.9) * 0.4
                    let y = baseline + CGFloat(phase) * (geo.size.height / 2)
                    let pt = CGPoint(x: stepX * CGFloat(i), y: y)
                    if i == 0 { path.move(to: pt) } else { path.addLine(to: pt) }
                }
            }
            .stroke(tone, lineWidth: 1)
        }
    }
}
