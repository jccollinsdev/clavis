// ─────────────────────────────────────────────────────────────
// Tokens.swift
// Clavix design tokens for SwiftUI. Pasted from design_handoff_clavix/tokens/Tokens.swift
// (source of truth: tokens.json). Uses @Observable per the bundle spec
// (deployment target is iOS 17+).
//
// This is the canonical token source. The older App/ClavixDesignTokens.swift
// `clavix*` palette remains for legacy views and will be migrated over time.
// All NEW views must use Color.cxInk, CXSpace.lg, CXType.sectionTitle.font, etc.
// ─────────────────────────────────────────────────────────────

import SwiftUI

// MARK: - Color palette ----------------------------------------------------

extension Color {
    // Ink (foreground)
    static let cxInk   = Color(cxHex: 0x1A1814)
    static let cxInk2  = Color(cxHex: 0x3A342B)
    static let cxInk3  = Color(cxHex: 0x6B6357)
    static let cxInk4  = Color(cxHex: 0xA39B8D)
    static let cxInk5  = Color(cxHex: 0xC8C0B0)

    // Paper (background)
    static let cxCanvas = Color(cxHex: 0xF0EADB) // outside device
    static let cxPage   = Color(cxHex: 0xF7F2E6) // screen background
    static let cxPaper  = Color(cxHex: 0xFFFDF7) // card surface
    static let cxPaper2 = Color(cxHex: 0xF3EDE0) // sunken / row hover

    // Hairlines
    static let cxRule  = Color(cxHex: 0xD6CEBD)
    static let cxRule2 = Color(cxHex: 0xE6DFCF)

    // Accent — Ink Blue (default; runtime-swappable via `Theme.accent`)
    static let cxAccent     = Color(cxHex: 0x1D3A6E)
    static let cxAccentSoft = Color(cxHex: 0xE3E9F3)
    static let cxAccentInk  = Color(cxHex: 0x11264A)

    // Risk — bond-grade, never neon
    static let cxGood      = Color(cxHex: 0x1F6F43)
    static let cxGoodSoft  = Color(cxHex: 0xDDE9D8)
    static let cxGoodInk   = Color(cxHex: 0x0D4A2A)

    static let cxWarn      = Color(cxHex: 0x9A6B1A)
    static let cxWarnSoft  = Color(cxHex: 0xF1E3C2)
    static let cxWarnInk   = Color(cxHex: 0x5A3E0C)

    static let cxBad       = Color(cxHex: 0x8E1F1F)
    static let cxBadSoft   = Color(cxHex: 0xF0D8D4)
    static let cxBadInk    = Color(cxHex: 0x5E1313)
}

enum ClavixDark {
    static let ink   = Color(cxHex: 0xF3ECE0)
    static let ink2  = Color(cxHex: 0xCDC6B8)
    static let ink3  = Color(cxHex: 0x9A9385)
    static let ink4  = Color(cxHex: 0x6B6557)
    static let ink5  = Color(cxHex: 0x4A463E)

    static let canvas = Color(cxHex: 0x0E0D0A)
    static let page   = Color(cxHex: 0x15140F)
    static let paper  = Color(cxHex: 0x1C1A14)
    static let paper2 = Color(cxHex: 0x23201A)

    static let rule   = Color(cxHex: 0x2F2C25)
    static let rule2  = Color(cxHex: 0x23201A)

    static let accentSoft = Color(cxHex: 0x1A2540)
    static let goodSoft   = Color(cxHex: 0x173324)
    static let warnSoft   = Color(cxHex: 0x3A2C10)
    static let badSoft    = Color(cxHex: 0x3A1414)
}

enum ClavixAccent: String, CaseIterable, Identifiable {
    case inkBlue     = "Ink Blue"
    case burntOrange = "Burnt Orange"
    case forest      = "Forest"
    case bordeaux    = "Bordeaux"

    var id: String { rawValue }

    var accent: Color {
        switch self {
        case .inkBlue:     return Color(cxHex: 0x1D3A6E)
        case .burntOrange: return Color(cxHex: 0xB34A14)
        case .forest:      return Color(cxHex: 0x1F5B3A)
        case .bordeaux:    return Color(cxHex: 0x7A1E2C)
        }
    }
    var accentSoft: Color {
        switch self {
        case .inkBlue:     return Color(cxHex: 0xE3E9F3)
        case .burntOrange: return Color(cxHex: 0xF5E2D2)
        case .forest:      return Color(cxHex: 0xDDE9D8)
        case .bordeaux:    return Color(cxHex: 0xEFD9DD)
        }
    }
    var accentInk: Color {
        switch self {
        case .inkBlue:     return Color(cxHex: 0x11264A)
        case .burntOrange: return Color(cxHex: 0x7A3208)
        case .forest:      return Color(cxHex: 0x0D3A22)
        case .bordeaux:    return Color(cxHex: 0x4A0F1C)
        }
    }
}

extension Color {
    /// `Color(cxHex: 0x1D3A6E)` — 6-digit RGB literal. Named `cxHex:` to avoid
    /// colliding with the existing `Color(hex: "#...")` initializer that takes
    /// a string and lives in App/ClavixDesignTokens.swift.
    init(cxHex: UInt32, alpha: Double = 1.0) {
        let r = Double((cxHex >> 16) & 0xFF) / 255
        let g = Double((cxHex >>  8) & 0xFF) / 255
        let b = Double( cxHex        & 0xFF) / 255
        self.init(.sRGB, red: r, green: g, blue: b, opacity: alpha)
    }
}

// MARK: - Typography -------------------------------------------------------

/// Source Serif 4 / Inter / JetBrains Mono are registered via
/// `Info.plist > UIAppFonts`. Existing ClavisTypography helpers register the
/// same files; these enums simply offer the bundle's canonical naming.
enum CXFont {
    static func serif(_ size: CGFloat, weight: Font.Weight = .medium) -> Font {
        .custom("SourceSerif4-\(weight.serifSuffix)", size: size)
    }
    static func sans(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .custom("Inter-\(weight.sansSuffix)", size: size)
    }
    static func mono(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .custom("JetBrainsMono-\(weight.monoSuffix)", size: size)
    }
}

private extension Font.Weight {
    var serifSuffix: String {
        switch self {
        case .regular:  return "Regular"
        case .medium:   return "Medium"
        case .semibold: return "Semibold"
        case .bold:     return "Bold"
        default:        return "Regular"
        }
    }
    var sansSuffix: String {
        switch self {
        case .regular:  return "Regular"
        case .medium:   return "Medium"
        case .semibold: return "SemiBold"
        case .bold:     return "Bold"
        default:        return "Regular"
        }
    }
    var monoSuffix: String {
        switch self {
        case .regular:  return "Regular"
        case .medium:   return "Medium"
        case .semibold: return "SemiBold"
        default:        return "Regular"
        }
    }
}

struct TypeStyle {
    enum Family { case serif, sans, mono }
    let family: Family
    let size: CGFloat
    let weight: Font.Weight
    let tracking: CGFloat
    let lineHeight: CGFloat
    var uppercase: Bool = false

    var font: Font {
        switch family {
        case .serif: return CXFont.serif(size, weight: weight)
        case .sans:  return CXFont.sans(size, weight: weight)
        case .mono:  return CXFont.mono(size, weight: weight)
        }
    }
}

/// Named type styles. Sizes are in points and match the design source 1:1.
enum CXType {
    static let display         = TypeStyle(family: .serif, size: 36, weight: .medium, tracking: -0.8, lineHeight: 1.05)
    static let screenTitleLg   = TypeStyle(family: .serif, size: 32, weight: .medium, tracking: -0.6, lineHeight: 1.05)
    static let sectionTitle    = TypeStyle(family: .serif, size: 26, weight: .medium, tracking: -0.3, lineHeight: 1.10)
    static let cardHeadline    = TypeStyle(family: .serif, size: 22, weight: .medium, tracking: -0.3, lineHeight: 1.10)
    static let cardSubheadline = TypeStyle(family: .serif, size: 20, weight: .medium, tracking: -0.2, lineHeight: 1.20)
    static let bodyLarge       = TypeStyle(family: .sans,  size: 15, weight: .regular, tracking: 0,   lineHeight: 1.50)
    static let body            = TypeStyle(family: .sans,  size: 14, weight: .regular, tracking: 0,   lineHeight: 1.40)
    static let bodySmall       = TypeStyle(family: .sans,  size: 13, weight: .regular, tracking: 0,   lineHeight: 1.55)
    static let caption         = TypeStyle(family: .sans,  size: 12, weight: .regular, tracking: 0,   lineHeight: 1.45)
    static let eyebrow         = TypeStyle(family: .mono,  size: 10, weight: .bold,    tracking: 0.7, lineHeight: 1.20, uppercase: true)
    static let microCaption    = TypeStyle(family: .mono,  size: 9,  weight: .semibold, tracking: 0.5, lineHeight: 1.20)
    static let numericStat     = TypeStyle(family: .mono,  size: 26, weight: .semibold, tracking: -0.4, lineHeight: 1.00)
    static let inlineNumber    = TypeStyle(family: .mono,  size: 11, weight: .regular,  tracking: 0,   lineHeight: 1.00)
}

extension View {
    func cxType(_ style: TypeStyle) -> some View {
        font(style.font)
            .tracking(style.tracking)
            .lineSpacing((style.lineHeight - 1) * style.size)
            .textCase(style.uppercase ? .uppercase : nil)
    }
}

// MARK: - Spacing & layout -------------------------------------------------

enum CXSpace {
    static let xxs:  CGFloat = 2
    static let xs:   CGFloat = 4
    static let sm:   CGFloat = 8
    static let md:   CGFloat = 12
    static let lg:   CGFloat = 16
    static let xl:   CGFloat = 20
    static let xxl:  CGFloat = 24
    static let huge: CGFloat = 32

    /// Standard screen horizontal padding. Use these instead of magic numbers.
    static let screenH:      CGFloat = 20  // Today, Holdings, Ticker
    static let screenHTight: CGFloat = 16  // tab-bar adjacent
    static let screenHAuth:  CGFloat = 24  // auth / onboarding hero
}

enum CXRadius {
    static let micro: CGFloat = 2
    static let xs:    CGFloat = 3
    static let sm:    CGFloat = 4   // grade pills
    static let md:    CGFloat = 7
    static let lg:    CGFloat = 10  // cards, buttons
    static let xl:    CGFloat = 14
    static let huge:  CGFloat = 44  // phone bezel (mock only)
}

enum CXLine {
    static let hair:     CGFloat = 1
    static let rule:     CGFloat = 1
    static let emphasis: CGFloat = 1.5
}

// MARK: - Motion -----------------------------------------------------------

enum CXMotion {
    static let microTap:     Animation = .easeOut(duration: 0.12)
    static let snap:         Animation = .interactiveSpring(response: 0.28, dampingFraction: 0.86)
    static let stateChange:  Animation = .easeInOut(duration: 0.22)
    static let splashDrawIn: Animation = .timingCurve(0.4, 0, 0.2, 1, duration: 0.5)
    static let splashEcgIn:  Animation = .timingCurve(0.4, 0, 0.2, 1, duration: 0.55).delay(0.4)
}

// MARK: - Theme environment ------------------------------------------------

/// Runtime-swappable theme: accent palette + dark mode + density multiplier.
/// Reachable via `@Environment(\.theme)`; views automatically re-render when
/// `accent`/`isDark`/`density` change thanks to `@Observable`.
@Observable
final class Theme {
    var accent: ClavixAccent = .inkBlue
    var isDark: Bool = false
    var density: Double = 1.0   // 0.9 … 1.1

    // Resolved colors — prefer these in views over raw `Color.cx*`.
    var ink: Color    { isDark ? ClavixDark.ink   : .cxInk }
    var ink2: Color   { isDark ? ClavixDark.ink2  : .cxInk2 }
    var ink3: Color   { isDark ? ClavixDark.ink3  : .cxInk3 }
    var ink4: Color   { isDark ? ClavixDark.ink4  : .cxInk4 }
    var page: Color   { isDark ? ClavixDark.page  : .cxPage }
    var paper: Color  { isDark ? ClavixDark.paper : .cxPaper }
    var paper2: Color { isDark ? ClavixDark.paper2 : .cxPaper2 }
    var rule: Color   { isDark ? ClavixDark.rule  : .cxRule }
    var rule2: Color  { isDark ? ClavixDark.rule2 : .cxRule2 }
    var accentColor:  Color { accent.accent }
    var accentSoft:   Color { isDark ? ClavixDark.accentSoft : accent.accentSoft }
    var accentInk:    Color { accent.accentInk }
}

private struct ThemeKey: EnvironmentKey {
    static let defaultValue: Theme = Theme()
}
extension EnvironmentValues {
    var theme: Theme {
        get { self[ThemeKey.self] }
        set { self[ThemeKey.self] = newValue }
    }
}
