import SwiftUI

/// The Clavix mark — squared "C" bracket with an ECG pulse exiting past the
/// open right side. The exiting pulse is the signature move; never shorten it
/// to stop at the mark's right edge. Viewbox is 100×100; stroke is 11pt at
/// that scale (≈11% of mark size). See system/03-logo.md.
struct ClavixMark: View {
    var size: CGFloat = 32
    var color: Color? = nil          // defaults to theme.ink
    var animated: Bool = false       // splash draw-in
    var dim: Bool = false            // empty-state ghost (uses theme.ink4)

    @Environment(\.theme) private var theme
    @State private var bracketProgress: CGFloat = 0
    @State private var pulseProgress: CGFloat = 0

    private var strokeColor: Color {
        if let color { return color }
        return dim ? theme.ink4 : theme.ink
    }

    var body: some View {
        Canvas { ctx, sz in
            let s = sz.width / 100
            let lw = 11 * s

            // Bracket "C"
            var bracket = Path()
            bracket.move(to: CGPoint(x: 66 * s, y: 24 * s))
            bracket.addLine(to: CGPoint(x: 22 * s, y: 24 * s))
            bracket.addLine(to: CGPoint(x: 22 * s, y: 76 * s))
            bracket.addLine(to: CGPoint(x: 66 * s, y: 76 * s))

            let bracketTrim = animated ? bracketProgress : 1.0
            let bracketPath = bracket.trimmedPath(from: 0, to: bracketTrim)
            ctx.stroke(
                bracketPath,
                with: .color(strokeColor),
                style: StrokeStyle(lineWidth: lw, lineCap: .round, lineJoin: .round)
            )

            // ECG pulse
            var pulse = Path()
            pulse.move(to: CGPoint(x: 30 * s, y: 50 * s))
            pulse.addLine(to: CGPoint(x: 42 * s, y: 50 * s))
            pulse.addLine(to: CGPoint(x: 46 * s, y: 56 * s))
            pulse.addLine(to: CGPoint(x: 52 * s, y: 18 * s))
            pulse.addLine(to: CGPoint(x: 57 * s, y: 64 * s))
            pulse.addLine(to: CGPoint(x: 62 * s, y: 50 * s))
            pulse.addLine(to: CGPoint(x: 94 * s, y: 50 * s))

            let pulseTrim = animated ? pulseProgress : 1.0
            let pulsePath = pulse.trimmedPath(from: 0, to: pulseTrim)
            ctx.stroke(
                pulsePath,
                with: .color(strokeColor),
                style: StrokeStyle(lineWidth: lw, lineCap: .round, lineJoin: .round)
            )
        }
        .frame(width: size, height: size)
        .accessibilityLabel("Clavix")
        .onAppear {
            if animated {
                withAnimation(.timingCurve(0.4, 0, 0.2, 1, duration: 0.5)) {
                    bracketProgress = 1.0
                }
                withAnimation(.timingCurve(0.4, 0, 0.2, 1, duration: 0.55).delay(0.4)) {
                    pulseProgress = 1.0
                }
            } else {
                bracketProgress = 1.0
                pulseProgress = 1.0
            }
        }
    }
}

/// Small-size variant: drops the W-inflection complexity for legibility below 16pt.
struct ClavixMarkSmall: View {
    var size: CGFloat = 14
    var color: Color? = nil
    @Environment(\.theme) private var theme

    var body: some View {
        Canvas { ctx, sz in
            let s = sz.width / 100
            let lw = 11 * s
            let stroke = color ?? theme.ink

            var bracket = Path()
            bracket.move(to: CGPoint(x: 66 * s, y: 24 * s))
            bracket.addLine(to: CGPoint(x: 22 * s, y: 24 * s))
            bracket.addLine(to: CGPoint(x: 22 * s, y: 76 * s))
            bracket.addLine(to: CGPoint(x: 66 * s, y: 76 * s))
            ctx.stroke(bracket, with: .color(stroke),
                       style: StrokeStyle(lineWidth: lw, lineCap: .round, lineJoin: .round))

            var pulse = Path()
            pulse.move(to: CGPoint(x: 30 * s, y: 50 * s))
            pulse.addLine(to: CGPoint(x: 44 * s, y: 50 * s))
            pulse.addLine(to: CGPoint(x: 52 * s, y: 18 * s))
            pulse.addLine(to: CGPoint(x: 60 * s, y: 50 * s))
            pulse.addLine(to: CGPoint(x: 94 * s, y: 50 * s))
            ctx.stroke(pulse, with: .color(stroke),
                       style: StrokeStyle(lineWidth: lw, lineCap: .round, lineJoin: .round))
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

/// Wordmark lockup. Tagline is "PORTFOLIO RISK, MEASURED."
struct ClavixBrand: View {
    var markSize: CGFloat = 28
    var color: Color? = nil
    var showTagline: Bool = false
    var layout: Layout = .horizontal

    enum Layout { case horizontal, stacked }

    @Environment(\.theme) private var theme

    var body: some View {
        let c = color ?? theme.ink
        let wordSize = markSize * 0.64
        let tagSize = markSize * 0.36
        let gap = markSize * 0.4

        Group {
            if layout == .horizontal {
                HStack(spacing: gap) {
                    ClavixMark(size: markSize, color: c)
                    VStack(alignment: .leading, spacing: markSize * 0.1) {
                        Text(verbatim: "Clavix")
                            .font(CXFont.serif(wordSize, weight: .semibold))
                            .tracking(-0.04 * wordSize)
                            .foregroundStyle(c)
                        if showTagline {
                            Text(verbatim: "PORTFOLIO RISK, MEASURED.")
                                .font(CXFont.mono(tagSize))
                                .tracking(0.06 * tagSize)
                                .foregroundStyle(theme.ink3)
                        }
                    }
                }
            } else {
                VStack(spacing: gap * 0.6) {
                    ClavixMark(size: markSize, color: c)
                    VStack(spacing: markSize * 0.1) {
                        Text(verbatim: "Clavix")
                            .font(CXFont.serif(wordSize, weight: .semibold))
                            .tracking(-0.04 * wordSize)
                            .foregroundStyle(c)
                        if showTagline {
                            Text(verbatim: "PORTFOLIO RISK, MEASURED.")
                                .font(CXFont.mono(tagSize))
                                .tracking(0.06 * tagSize)
                                .foregroundStyle(theme.ink3)
                        }
                    }
                }
            }
        }
    }
}

#if DEBUG
struct ClavixMark_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            VStack(spacing: 24) {
                HStack(spacing: 16) {
                    ClavixMark(size: 22)
                    ClavixMark(size: 32)
                    ClavixMark(size: 48)
                    ClavixMark(size: 72)
                }
                ClavixMark(size: 60, dim: true)
                ClavixBrand(markSize: 28, showTagline: true)
                ClavixBrand(markSize: 36, showTagline: true, layout: .stacked)
            }
            .padding(24)
            .background(Color.cxPage)
            .previewDisplayName("Light")

            VStack(spacing: 24) {
                ClavixMark(size: 72, color: ClavixDark.ink)
                ClavixBrand(markSize: 28, color: ClavixDark.ink, showTagline: true)
            }
            .padding(24)
            .background(ClavixDark.page)
            .previewDisplayName("Dark")
        }
    }
}
#endif
