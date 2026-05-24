#if DEBUG
import SwiftUI
import WebKit

/// Loads the bundled Clavix Hi-Fi v2 HTML in a WKWebView so the live app and
/// the canonical mock can be compared side-by-side during the parity build.
/// Enable via `CLAVIX_USE_HIFI_REFERENCE=1` in the scheme env vars.
struct ClavixHiFiReferenceView: View {
    var body: some View {
        if let url = Bundle.main.url(forResource: "clavix-hifi-v2", withExtension: "html") {
            ClavixHiFiWebView(url: url)
                .ignoresSafeArea()
        } else {
            VStack(spacing: 12) {
                Image(systemName: "doc.text.magnifyingglass")
                    .font(.system(size: 40))
                    .foregroundColor(.clavixInk3)
                Text("Hi-Fi reference HTML missing")
                    .font(ClavisTypography.clavixSerif(18, weight: .medium))
                    .foregroundColor(.clavixInk)
                Text("ios/Clavis/Resources/Design/clavix-hifi-v2.html should be bundled.")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color.clavixPage.ignoresSafeArea())
        }
    }
}

private struct ClavixHiFiWebView: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView(frame: .zero)
        webView.isOpaque = false
        webView.backgroundColor = UIColor(Color.clavixPage)
        webView.scrollView.backgroundColor = UIColor(Color.clavixPage)
        webView.scrollView.bounces = true
        webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}
}
#endif
