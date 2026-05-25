import SwiftUI

/// Inline mini chart. ~72×22 default. `dotEnd` adds an end-cap dot.
struct Sparkline: View {
    let data: [Double]
    var size: CGSize = CGSize(width: 72, height: 22)
    var stroke: Color? = nil
    var dotEnd: Bool = false

    @Environment(\.theme) private var theme

    var body: some View {
        Canvas { ctx, sz in
            guard let mn = data.min(), let mx = data.max(), data.count > 1 else { return }
            let range = max(mx - mn, 0.0001)
            let pts: [CGPoint] = data.enumerated().map { (i, v) in
                let x = CGFloat(i) / CGFloat(data.count - 1) * sz.width
                let y = sz.height - CGFloat((v - mn) / range) * (sz.height - 2) - 1
                return CGPoint(x: x, y: y)
            }
            var path = Path()
            path.move(to: pts[0])
            pts.dropFirst().forEach { path.addLine(to: $0) }
            ctx.stroke(
                path,
                with: .color(stroke ?? theme.ink),
                style: StrokeStyle(lineWidth: 1.4, lineCap: .round, lineJoin: .round)
            )
            if dotEnd, let last = pts.last {
                ctx.fill(
                    Path(ellipseIn: CGRect(x: last.x - 2.2, y: last.y - 2.2, width: 4.4, height: 4.4)),
                    with: .color(stroke ?? theme.ink)
                )
            }
        }
        .frame(width: size.width, height: size.height)
        .accessibilityHidden(true)
    }
}

#if DEBUG
struct Sparkline_Previews: PreviewProvider {
    static var previews: some View {
        VStack(alignment: .leading, spacing: 12) {
            Sparkline(data: [72, 74, 71, 70, 68, 66, 64], dotEnd: true)
            Sparkline(data: [40, 41, 45, 51, 58, 62, 68], stroke: .cxGood, dotEnd: true)
            Sparkline(data: [80, 78, 76, 70, 66, 60, 55], stroke: .cxBad, dotEnd: true)
        }
        .padding(20)
        .background(Color.cxPage)
    }
}
#endif
