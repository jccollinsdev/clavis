import SwiftUI

// Cream/paper design tokens. These are the production-available versions of
// the private vqa* tokens that live inside the (debug-only) ClavixVisualQA.swift.
// New live-tab views consume `Clavix*` tokens; the debug VisualQA file keeps
// its private mirror so it can be edited without touching production.

extension Color {
    static let clavixInk    = Color(hex: "#1A1814")
    static let clavixInk2   = Color(hex: "#3A342B")
    static let clavixInk3   = Color(hex: "#6B6357")
    static let clavixInk4   = Color(hex: "#A39B8D")
    static let clavixInk5   = Color(hex: "#C8C0B0")
    static let clavixCanvas = Color(hex: "#F0EADB")
    static let clavixPage   = Color(hex: "#F7F2E6")
    static let clavixPaper  = Color(hex: "#FFFDF7")
    static let clavixPaper2 = Color(hex: "#F3EDE0")
    static let clavixRule   = Color(hex: "#D6CEBD")
    static let clavixRule2  = Color(hex: "#E6DFCF")
    static let clavixAccent     = Color(hex: "#1D3A6E")
    static let clavixAccentSoft = Color(hex: "#E3E9F3")
    static let clavixAccentInk  = Color(hex: "#11264A")
    static let clavixGood     = Color(hex: "#1F6F43")
    static let clavixGoodSoft = Color(hex: "#DDE9D8")
    static let clavixGoodInk  = Color(hex: "#0D4A2A")
    static let clavixWarn     = Color(hex: "#9A6B1A")
    static let clavixWarnSoft = Color(hex: "#F1E3C2")
    static let clavixWarnInk  = Color(hex: "#5A3E0C")
    static let clavixBad     = Color(hex: "#8E1F1F")
    static let clavixBadSoft = Color(hex: "#F0D8D4")
    static let clavixBadInk  = Color(hex: "#5E1313")
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
