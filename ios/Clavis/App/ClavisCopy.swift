import Foundation

/// Launch-scope feature flags.
///
/// `brokerageEnabled` is OFF for v1: Clavix launches manual-entry only.
/// Brokerage / automatic position sync is deferred to a post-v1 release for
/// legal/admin reasons (see `docs/CLAVIX_LAUNCH_SCOPE_v1.md` and CLAVIX_TRUTH §11).
/// While this is `false`, no brokerage CTA may be reachable in the shipping app.
/// `BrokerageViewModel` and `/brokerage/*` stay in the codebase (dormant) so the
/// feature can be re-enabled later without a rewrite.
enum FeatureFlags {
    static let brokerageEnabled = false
}

enum ClavisCopy {
    static let informationalDisclosure = "Clavix is informational only. It is not financial advice."
    static let riskAcknowledgment = "Clavix is informational only. Risk grades and scores reflect risk signals derived from public data and model outputs. They are not recommendations to buy, sell, or hold any security."
    static let settingsDisclaimer = "Clavix provides risk intelligence for informational purposes only. Scores reflect model output based on available data and do not constitute investment advice."

    static var appVersionString: String {
        let shortVersion = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String
        let buildVersion = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String

        switch (shortVersion, buildVersion) {
        case let (short?, build?) where !build.isEmpty && build != short:
            return "v\(short) (\(build))"
        case let (short?, _):
            return "v\(short)"
        case let (_, build?) where !build.isEmpty:
            return "Build \(build)"
        default:
            return "Version unavailable"
        }
    }

    enum Status {
        static let updating = "Updating"

        static func label(for rawStatus: String) -> String {
            switch normalize(rawStatus) {
            case "queued", "running", "starting":
                return "Updating"
            case "failed":
                return "Needs attention"
            case "ready", "fresh", "completed", "skipped_ai_scored":
                return "Current"
            case "thin":
                return "Limited data"
            case "provisional":
                return "Early data"
            case "substantive":
                return "Strong data"
            case "stale":
                return "Refreshing"
            case "cached":
                return "Up to date"
            case "partial":
                return "Partially updated"
            default:
                return titleCase(rawStatus)
            }
        }

        static func sourceLabel(for rawSource: String) -> String {
            switch normalize(rawSource) {
            case "shared", "snapshot":
                return "Market view"
            case "position", "holding", "user":
                return "In portfolio"
            case "watchlist":
                return "Watchlist"
            default:
                return titleCase(rawSource)
            }
        }

        static func reviewStatusLine(for rawStatus: String) -> String {
            "Review status: \(label(for: rawStatus))"
        }

        static func refreshStatusLine(for rawStatus: String) -> String {
            "Data refresh: \(label(for: rawStatus))"
        }

        static func newsStatusLine(for rawStatus: String) -> String {
            "News data: \(label(for: rawStatus))"
        }

        static func timestamp(_ date: Date?) -> String {
            guard let date else { return updating }
            return date.formatted(date: .abbreviated, time: .shortened)
        }
    }

    enum Errors {
        static let networkIssue = "Check your connection and try again."
        static let sessionExpired = "Your session expired. Please sign in again."
        static let analysisRefreshFailed = "This refresh didn't finish. Please try again in a moment."

        static func dashboardLoad(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't load your portfolio right now.")
        }

        static func dashboardRefresh(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't refresh your portfolio right now.")
        }

        static func digestLoad(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't load your Morning Rating right now.")
        }

        static func digestRefresh(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't generate a new Morning Rating right now.")
        }

        static func holdingsLoad(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't load your holdings right now.")
        }

        static func holdingAdd(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't add this holding right now.")
        }

        static func holdingDelete(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't delete this holding right now.")
        }

        static func holdingRefresh(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't refresh this holding right now.")
        }

        static func watchlistUpdate(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't update your watchlist right now.")
        }

        static func tickerLoad(ticker: String, error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't load \(ticker) right now.")
        }

        static func tickerRefresh(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't refresh this ticker right now.")
        }

        static func tickerSearch(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't search tickers right now.")
        }

        static func positionLoad(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't open this holding right now.")
        }

        static func alertsLoad(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't load your alerts right now.")
        }

        static func brokerageStatus(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't load your brokerage connection right now.")
        }

        static func brokerageConnect(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't open brokerage connection right now.")
        }

        static func brokerageSettings(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't update your brokerage settings right now.")
        }

        static func brokerageSync(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't sync your brokerage holdings right now.")
        }

        static func brokerageDisconnect(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't disconnect your brokerage right now.")
        }

        static func accountExport(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't prepare your account export right now.")
        }

        static func accountDelete(_ error: Error) -> String {
            userMessage(for: error, fallback: "Couldn't delete your account right now.")
        }

        private static func userMessage(for error: Error, fallback: String) -> String {
            if let apiError = error as? APIError {
                switch apiError {
                case .invalidURL, .invalidResponse:
                    return fallback
                case .unauthorized:
                    return sessionExpired
                case .networkError:
                    return networkIssue
                case .serverError, .decodingError:
                    return fallback
                }
            }

            let nsError = error as NSError
            if nsError.domain == NSURLErrorDomain {
                return networkIssue
            }

            let message = nsError.localizedDescription.lowercased()
            if message.contains("offline") || message.contains("internet") || message.contains("network") || message.contains("timed out") {
                return networkIssue
            }

            return fallback
        }
    }

    private static func normalize(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }

    // CLAVIX_TRUTH §2 bans raw .capitalized backend status strings in UI.
    // When no explicit copy mapping exists, return a neutral "Updating"
    // rather than surfacing the internal status token.
    private static func titleCase(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? Status.updating : Status.updating
    }
}
