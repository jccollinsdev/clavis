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
        case "A":         return .clavixInk
        case "BBB", "BB": return .clavixWarn
        case "—":         return .clavixInk4
        default:           return .clavixBad
        }
    }

    private var foreground: Color {
        grade == "A" ? .clavixPaper : .white
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
    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(Color.clavixRule2)
                Rectangle()
                    .fill(scoreTone(score))
                    .frame(width: geo.size.width * CGFloat(min(max(score, 0), 100)) / 100)
            }
        }
        .frame(height: 4)
    }

    private func scoreTone(_ score: Int) -> Color {
        switch score {
        case 80...100: return .clavixGood
        case 60..<80:  return .clavixAccent
        case 40..<60:  return .clavixWarn
        default:        return .clavixBad
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
