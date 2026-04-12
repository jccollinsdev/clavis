import SwiftUI

// MARK: - Theme Constants

enum ClavisTheme {
    static let cornerRadius: CGFloat = 8          // cards
    static let innerCornerRadius: CGFloat = 4     // data elements, grade tags
    static let sectionSpacing: CGFloat = 20
    static let cardPadding: CGFloat = 16
    static let screenPadding: CGFloat = 16
    static let microSpacing: CGFloat = 4
    static let smallSpacing: CGFloat = 8
    static let mediumSpacing: CGFloat = 16
    static let largeSpacing: CGFloat = 24
    static let extraLargeSpacing: CGFloat = 48
    static let topBarSpacing: CGFloat = 30
    static let floatingTabInset: CGFloat = 16
    static let floatingTabHeight: CGFloat = 74
}

// MARK: - Typography

enum ClavisTypography {
    // Inter — UI text
    static func inter(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        Font.custom("Inter", size: size).weight(weight)
    }
    // JetBrains Mono — all data and numbers
    static func mono(_ size: CGFloat) -> Font {
        Font.custom("JetBrainsMono-Regular", size: size)
    }

    // Spec-defined styles
    static let portfolioScore = mono(52)                     // portfolio hero score
    static let h1             = inter(28, weight: .medium)   // screen title
    static let h2             = inter(20, weight: .medium)   // section header
    static let dataNumber     = mono(22)                     // data/number display
    static let gradeTag       = mono(13)                     // grade badge label
    static let label          = inter(11, weight: .medium)   // UPPERCASE labels
    static let rowTicker      = inter(13, weight: .medium)   // ticker in rows
    static let rowScore       = mono(13)                     // score in rows
    static let bodySmall      = inter(13, weight: .regular)

    // Backward-compat aliases — existing views compile without changes
    static func appFont(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        inter(size, weight: weight)
    }
    static let dashboardTitle    = h1
    static let pageTitle         = h1
    static let sectionTitle      = h2
    static let cardTitle         = inter(15, weight: .medium)
    static let body              = inter(15, weight: .regular)
    static let bodyStrong        = inter(15, weight: .medium)
    static let bodyEmphasis      = inter(15, weight: .medium)
    static let footnote          = inter(12, weight: .regular)
    static let footnoteEmphasis  = inter(12, weight: .medium)
    static let metric            = mono(32)
    static let grade             = mono(36)
    static let heroNumber        = mono(48)
    static let heroLabel         = inter(24, weight: .medium)
    static let interpretation    = inter(15, weight: .regular)
    static let action            = inter(15, weight: .medium)
    static let topBarTitle       = h1
    static let eyebrow           = label
    static let brandTitle        = inter(18, weight: .bold)
}

// MARK: - Color Palette

extension Color {
    // MARK: Surfaces (dark)
    static let backgroundPrimary = Color(hex: "#0F1117")
    static let surface           = Color(hex: "#161B24")
    static let surfaceElevated   = Color(hex: "#1E2530")
    static let border            = Color(hex: "#2A3140")

    // MARK: Text
    static let textPrimary   = Color(hex: "#E8ECF0")
    static let textSecondary = Color(hex: "#7A8799")
    static let textTertiary  = Color(hex: "#7A8799")   // alias

    // MARK: Informational (non-risk blue — never near score displays)
    static let informational = Color(hex: "#1A6494")

    // MARK: Risk Scale — 5-state closed set. Color = state, never brand.
    static let riskA = Color(hex: "#1D9E75")   // Safe      75–100
    static let riskB = Color(hex: "#639922")   // Stable    55–74
    static let riskC = Color(hex: "#BA7517")   // Watch     35–54
    static let riskD = Color(hex: "#D85A30")   // Risky     15–34
    static let riskF = Color(hex: "#C8342B")   // Critical  0–14

    // MARK: Grade Tag Surfaces
    static let gradeABg   = Color(hex: "#E1F5EE")
    static let gradeAText = Color(hex: "#085041")
    static let gradeBBg   = Color(hex: "#EAF3DE")
    static let gradeBText = Color(hex: "#27500A")
    static let gradeCBg   = Color(hex: "#FAEEDA")
    static let gradeCText = Color(hex: "#633806")
    static let gradeDBg   = Color(hex: "#FAECE7")
    static let gradeDText = Color(hex: "#712B13")
    static let gradeFBg   = Color(hex: "#FCEBEB")
    static let gradeFText = Color(hex: "#791F1F")

    // MARK: Backward-compat aliases
    static let accentBlue         = informational
    static let canvasBackground   = backgroundPrimary
    static let cardBackground     = surface
    static let elevatedBackground = surfaceElevated
    static let appBackground      = backgroundPrimary
    static let surfacePrimary     = surface
    static let surfaceSecondary   = surfaceElevated
    static let borderSubtle       = border
    static let borderStrong       = border
    static let successTone        = riskA
    static let warningTone        = riskC
    static let criticalTone       = riskF
    static let mint               = riskB
    static let trustNavy          = informational
    static let neutralSurface     = surfaceElevated
    static let clavisCardBorder   = border
    static let clavisShadow       = Color.clear
    static let clavisAlertText    = riskF
    static let clavisAlertBg      = Color(hex: "#C8342B").opacity(0.12)
    static let successSurface     = Color(hex: "#1D9E75").opacity(0.12)
    static let warningSurface     = Color(hex: "#BA7517").opacity(0.12)
    static let dangerSurface      = Color(hex: "#C8342B").opacity(0.12)
    static let decisionSafe       = riskA
    static let decisionWatch      = riskC
    static let decisionReduce     = riskF
    static let decisionInfo       = textSecondary
    static let semanticGreen      = riskA
    static let semanticAmber      = riskC
    static let semanticRed        = riskF
    static let semanticBlue       = informational
    static let semanticGray       = textSecondary

    // Slate scale (backward compat — mapped to dark equivalents)
    static let slate900 = Color(hex: "#E8ECF0")
    static let slate700 = Color(hex: "#7A8799")
    static let slate500 = Color(hex: "#7A8799")
    static let slate300 = Color(hex: "#2A3140")
    static let slate200 = Color(hex: "#2A3140")
    static let slate100 = Color(hex: "#1E2530")

    // MARK: Hex initializer
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Grade Style

enum ClavisGradeStyle {
    static func riskColor(for grade: String?) -> Color {
        switch grade {
        case "A": return .riskA
        case "B": return .riskB
        case "C": return .riskC
        case "D": return .riskD
        case "F": return .riskF
        default:  return .textSecondary
        }
    }

    /// Backward-compat alias
    static func color(for grade: String?) -> Color { riskColor(for: grade) }

    static func gradeBandBg(for grade: String?) -> Color {
        switch grade {
        case "A": return .gradeABg
        case "B": return .gradeBBg
        case "C": return .gradeCBg
        case "D": return .gradeDBg
        case "F": return .gradeFBg
        default:  return .surfaceElevated
        }
    }

    static func gradeBandText(for grade: String?) -> Color {
        switch grade {
        case "A": return .gradeAText
        case "B": return .gradeBText
        case "C": return .gradeCText
        case "D": return .gradeDText
        case "F": return .gradeFText
        default:  return .textSecondary
        }
    }

    static func gradeBandLabel(for grade: String?) -> String {
        switch grade {
        case "A": return "Safe (75–100)"
        case "B": return "Stable (55–74)"
        case "C": return "Watch (35–54)"
        case "D": return "Risky (15–34)"
        case "F": return "Critical (0–14)"
        default:  return "—"
        }
    }
}

// MARK: - Decision Style (backward compat)

enum ClavisDecisionStyle {
    static func color(for score: Double) -> Color {
        switch score {
        case 75...100: return .riskA
        case 55..<75:  return .riskB
        case 35..<55:  return .riskC
        case 15..<35:  return .riskD
        default:       return .riskF
        }
    }

    static func label(for score: Double) -> String {
        switch score {
        case 75...100: return "Safe"
        case 55..<75:  return "Stable"
        case 35..<55:  return "Watch"
        case 15..<35:  return "Risky"
        default:       return "Critical"
        }
    }

    static func tint(for pressure: ActionPressure?) -> Color {
        switch pressure {
        case .low:    return .riskA
        case .medium: return .riskC
        case .high:   return .riskF
        case .none:   return .textSecondary
        }
    }
}

// MARK: - View Modifiers

extension View {
    func clavisCardStyle(fill: Color = .surface) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.border, lineWidth: 1)
            )
    }

    func clavisHeroCardStyle(fill: Color = .surface) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.border, lineWidth: 1.5)
            )
    }

    func clavisSecondaryCardStyle(fill: Color = .surfaceElevated) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

// MARK: - Atmosphere Background (flat dark — no gradient)

struct ClavisAtmosphereBackground: View {
    var body: some View {
        Color.backgroundPrimary
            .ignoresSafeArea()
    }
}

// MARK: - Grade Tag

/// Filled grade badge. 32×32 standard, 32×24 compact, 56×56 large. 4px radius. JetBrains Mono 13px.
struct GradeTag: View {
    let grade: String
    var compact: Bool = false
    var large: Bool = false

    var body: some View {
        Text(grade)
            .font(large ? .system(size: 40, weight: .bold, design: .monospaced) : ClavisTypography.gradeTag)
            .fontWeight(.medium)
            .foregroundColor(ClavisGradeStyle.gradeBandText(for: grade))
            .frame(width: large ? 56 : (compact ? 24 : 32), height: large ? 56 : (compact ? 24 : 32))
            .background(ClavisGradeStyle.gradeBandBg(for: grade))
            .cornerRadius(4)
    }
}

// MARK: - Risk Bar

/// 4px-height data bar. Filled to score% in risk color. No pill ends.
struct RiskBar: View {
    let score: Double
    let grade: String

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 4)
                Rectangle()
                    .fill(ClavisGradeStyle.riskColor(for: grade))
                    .frame(width: geo.size.width * CGFloat(max(0, min(score, 100)) / 100), height: 4)
            }
        }
        .frame(height: 4)
    }
}

// MARK: - Brand Mark

struct ClavisBrandMark: View {
    var body: some View {
        Image("AppLogo")
            .resizable()
            .scaledToFit()
            .accessibilityHidden(true)
    }
}

// MARK: - Top Bar

struct ClavisTopBar<MenuContent: View>: View {
    let title: String
    let onLogoTap: () -> Void
    @ViewBuilder let menuContent: () -> MenuContent

    init(
        title: String = "CLAVIS",
        onLogoTap: @escaping () -> Void,
        @ViewBuilder menuContent: @escaping () -> MenuContent
    ) {
        self.title = title
        self.onLogoTap = onLogoTap
        self.menuContent = menuContent
    }

    var body: some View {
        ZStack {
            HStack {
                Button(action: onLogoTap) {
                    ClavisBrandMark()
                        .frame(width: 62, height: 62)
                        .frame(width: 70, height: 62, alignment: .leading)
                        .scaleEffect(1.15)
                }
                .buttonStyle(.plain)

                Spacer()

                Menu {
                    menuContent()
                } label: {
                    Image(systemName: "line.3.horizontal")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.textPrimary)
                        .frame(width: 40, height: 40)
                        .scaleEffect(1.15)
                }
                .menuStyle(.borderlessButton)
            }

            Text(title)
                .font(ClavisTypography.brandTitle)
                .foregroundColor(.textPrimary)
                .kerning(2.1)
                .scaleEffect(1.15)
        }
    }
}

// MARK: - Circle Button

struct ClavisCircleButton<Content: View>: View {
    let size: CGFloat
    let action: () -> Void
    @ViewBuilder let content: Content

    init(size: CGFloat = 52, action: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.size = size
        self.action = action
        self.content = content()
    }

    var body: some View {
        Button(action: action) {
            content
                .frame(width: size, height: size)
                .background(Color.surface)
                .clipShape(Circle())
                .overlay(Circle().stroke(Color.border, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Capsule Button (deprecated — violates spec R-07)

@available(*, deprecated, message: "Use clavisCardStyle instead. Capsule shapes violate spec R-07.")
struct ClavisCapsuleButton<Content: View>: View {
    let action: () -> Void
    @ViewBuilder let content: Content

    init(action: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.action = action
        self.content = content()
    }

    var body: some View {
        Button(action: action) {
            content
                .padding(.horizontal, 24)
                .padding(.vertical, 16)
                .background(Color.surface)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Eyebrow Header

struct ClavisEyebrowHeader: View {
    let eyebrow: String
    let title: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(eyebrow.uppercased())
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)
            Text(title)
                .font(ClavisTypography.dashboardTitle)
                .foregroundColor(.textPrimary)
        }
    }
}

// MARK: - Clavix Mark

struct ClavynxMark: View {
    var body: some View {
        if let uiImage = UIImage(named: "clavix_logo") {
            Image(uiImage: uiImage)
                .resizable()
                .scaledToFit()
                .frame(height: 48)
        } else {
            // Fallback: three sharp risk-colored bars
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.surface)
                    .frame(width: 88, height: 88)
                VStack(spacing: 0) {
                    HStack(alignment: .bottom, spacing: 6) {
                        Rectangle().fill(Color.riskA).frame(width: 18, height: 36)
                        Rectangle().fill(Color.riskC).frame(width: 18, height: 52)
                        Rectangle().fill(Color.riskF).frame(width: 18, height: 68)
                    }
                    Rectangle().fill(Color.textPrimary).frame(width: 70, height: 1.5)
                }
            }
        }
    }
}

// MARK: - Screen Header

struct ClavisScreenHeader: View {
    let title: String
    let subtitle: String?

    init(title: String, subtitle: String? = nil) {
        self.title = title
        self.subtitle = subtitle
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(ClavisTypography.pageTitle)
                .foregroundColor(.textPrimary)
            if let subtitle, !subtitle.isEmpty {
                Text(subtitle)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }
        }
    }
}

// MARK: - Glass Header

struct ClavisGlassHeader: View {
    let eyebrow: String
    let title: String
    let subtitle: String
    let grade: String?

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text(eyebrow.uppercased())
                        .font(ClavisTypography.label)
                        .kerning(0.88)
                        .foregroundColor(.textSecondary)
                    Text(title)
                        .font(ClavisTypography.dashboardTitle)
                        .foregroundColor(.textPrimary)
                    Text(subtitle)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 16)
                if let grade {
                    GradeTag(grade: grade)
                }
            }
        }
        .padding(ClavisTheme.largeSpacing)
        .clavisCardStyle()
    }
}

// MARK: - Stat Pill (deprecated — violates spec R-07)

@available(*, deprecated, message: "Use ClavisMetricLabel. Pill shapes violate spec R-07.")
struct ClavisStatPill: View {
    let label: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
            Text(value)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.textPrimary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(Color.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(tint.opacity(0.18), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 4))
    }
}

// MARK: - Section Header

struct ClavisSectionHeader<Accessory: View>: View {
    let title: String
    let subtitle: String?
    @ViewBuilder let accessory: Accessory

    init(
        _ title: String,
        subtitle: String? = nil,
        @ViewBuilder accessory: () -> Accessory = { EmptyView() }
    ) {
        self.title = title
        self.subtitle = subtitle
        self.accessory = accessory()
    }

    var body: some View {
        HStack(alignment: .bottom, spacing: 16) {
            VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
                Text(title.uppercased())
                    .font(ClavisTypography.label)
                    .kerning(0.88)
                    .foregroundColor(.textSecondary)
                if let subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            }
            Spacer(minLength: 0)
            accessory
        }
    }
}

// MARK: - Loading Card

struct ClavisLoadingCard: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(spacing: ClavisTheme.mediumSpacing) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color.surfaceElevated)
                    .frame(width: 44, height: 44)
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.surfaceElevated)
                        .frame(width: 140, height: 14)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.surfaceElevated)
                        .frame(maxWidth: .infinity).frame(height: 12)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.surfaceElevated)
                        .frame(width: 180, height: 12)
                }
            }
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(title).font(ClavisTypography.cardTitle).foregroundColor(.textPrimary)
                Text(subtitle).font(ClavisTypography.footnote).foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle()
    }
}

// MARK: - Ring Gauge (deprecated — violates spec R-02 and R-03)

@available(*, deprecated, message: "Ring gauges violate spec R-02/R-03. Score is the primary visual object.")
struct ClavisRingGauge: View {
    let progress: Double
    let lineWidth: CGFloat
    let tint: Color
    let icon: String?

    init(progress: Double, lineWidth: CGFloat = 10, tint: Color, icon: String? = nil) {
        self.progress = min(max(progress, 0), 1)
        self.lineWidth = lineWidth
        self.tint = tint
        self.icon = icon
    }

    var body: some View {
        ZStack {
            Circle().stroke(Color.border, lineWidth: lineWidth)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(tint, style: StrokeStyle(lineWidth: lineWidth, lineCap: .butt))
                .rotationEffect(.degrees(-90))
            if let icon {
                Image(systemName: icon)
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundColor(tint)
            }
        }
    }
}

// MARK: - Metric Label

struct ClavisMetricLabel: View {
    let label: String
    let value: String
    let tone: Color?

    init(label: String, value: String, tone: Color? = nil) {
        self.label = label
        self.value = value
        self.tone = tone
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
            Text(label.uppercased())
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)
            Text(value)
                .font(ClavisTypography.dataNumber)
                .foregroundColor(tone ?? .textPrimary)
        }
    }
}

// MARK: - Markdown Text

struct MarkdownText: View {
    let text: String
    var font: Font = ClavisTypography.body
    var color: Color = .textPrimary

    init(_ text: String, font: Font = ClavisTypography.body, color: Color = .textPrimary) {
        self.text = text
        self.font = font
        self.color = color
    }

    var body: some View {
        if let attributed = try? AttributedString(
            markdown: text,
            options: AttributedString.MarkdownParsingOptions(
                interpretedSyntax: .inlineOnlyPreservingWhitespace
            )
        ) {
            Text(attributed).font(font).foregroundColor(color).lineSpacing(5)
        } else {
            Text(text).font(font).foregroundColor(color).lineSpacing(5)
        }
    }
}
