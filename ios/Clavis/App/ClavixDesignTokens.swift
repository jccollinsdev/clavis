import SwiftUI

// Cream/paper design tokens. These are the production-available versions of
// the private vqa* tokens that live inside the (debug-only) ClavixVisualQA.swift.
// New live-tab views consume `Clavix*` tokens; the debug VisualQA file keeps
// its private mirror so it can be edited without touching production.

// Canonical Clavix Hi-Fi v2 palette, extracted from
// docs/design/clavix-hifi-v2.html (the design source of truth).
// Editorial ink-on-cream, bond-rating fills, mono numerics.
extension Color {
    // Ink ramp (text & primary fills)
    static let clavixInk    = Color(hex: "#1A1814")
    static let clavixInk2   = Color(hex: "#3A342B")
    static let clavixInk3   = Color(hex: "#777777")  // muted body/meta (HTML cx.ink3)
    static let clavixInk4   = Color(hex: "#999999")  // ghost / icon disabled
    static let clavixInk5   = Color(hex: "#C8C0B0")

    // Cream paper system
    static let clavixCanvas = Color(hex: "#F0EADB")  // canvas / background scroll
    static let clavixPage   = Color(hex: "#F0EADB")  // page surface (= canvas in v2)
    static let clavixPaper  = Color(hex: "#F3ECE0")  // card surface (warmer)
    static let clavixPaper2 = Color(hex: "#E8E0CC")  // ledger header / inset row

    // Rules / dividers
    static let clavixRule   = Color(hex: "#D6CEBD")
    static let clavixRule2  = Color(hex: "#E6DFCF")

    // Accent: Ink Blue (cx.accent)
    static let clavixAccent     = Color(hex: "#1D3A6E")
    static let clavixAccentSoft = Color(hex: "#E3E9F3")
    static let clavixAccentInk  = Color(hex: "#11264A")

    // Good: Forest (cx.good)
    static let clavixGood     = Color(hex: "#1F5B3A")
    static let clavixGoodSoft = Color(hex: "#DDE9D8")
    static let clavixGoodInk  = Color(hex: "#0D3A22")

    // Warn: Burnt orange (cx.warn — used for Pro accent / pressure)
    static let clavixWarn     = Color(hex: "#B34A14")
    static let clavixWarnSoft = Color(hex: "#F4DCC4")
    static let clavixWarnInk  = Color(hex: "#6E2C09")

    // Bad: Bordeaux (cx.bad)
    static let clavixBad     = Color(hex: "#7A1E2C")
    static let clavixBadSoft = Color(hex: "#F0D8D4")
    static let clavixBadInk  = Color(hex: "#5C2B2E")
}

extension ClavisTypography {
    /// JetBrainsMono Regular at the requested size and weight. Used for ledger
    /// rows, numeric values, timestamps, and eyebrow chips.
    static func clavixMono(_ size: CGFloat, weight: Font.Weight) -> Font {
        Font.custom("JetBrainsMono-Regular", size: size).weight(weight)
    }

    /// System serif at the requested size. Used for headlines and editorial copy.
    static func clavixSerif(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        Font.system(size: size, weight: weight, design: .serif)
    }

    static var clavixCaption: Font { inter(12, weight: .regular) }
}

enum ClavixLayout {
    static let pad: CGFloat = 20
    static let bottomPad: CGFloat = 28
    static let cardRadius: CGFloat = 10
    static let controlRadius: CGFloat = 7
}
