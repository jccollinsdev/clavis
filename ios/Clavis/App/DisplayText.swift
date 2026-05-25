import Foundation

extension String {
    var sanitizedDisplayText: String {
        let cleaned = self
            .replacingOccurrences(of: "\u{FFFD}", with: "")
            .replacingOccurrences(of: "�", with: "")
            .replacingOccurrences(of: "\u{0000}", with: "")
            .replacingOccurrences(of: "□", with: "")
            .replacingOccurrences(of: "☐", with: "")
            .replacingOccurrences(of: "\u{2028}", with: "\n")
            .replacingOccurrences(of: "\u{2029}", with: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        let filteredScalars = cleaned.unicodeScalars.filter { scalar in
            if CharacterSet.controlCharacters.contains(scalar) {
                return scalar == "\n" || scalar == "\t"
            }
            return true
        }

        let stripped = String(String.UnicodeScalarView(filteredScalars))
            .replacingOccurrences(of: "\n\n\n", with: "\n\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        return stripped.clavixVocabSafe
    }

    /// Replaces CLAVIX_TRUTH §2 banned vocabulary with neutral observation-grade
    /// language (whole-word, case-preserving). Backend prompts try to avoid these
    /// terms, but this guard keeps any leak from reaching the user.
    fileprivate var clavixVocabSafe: String {
        var s = self
        let replacements: [(String, String)] = [
            ("Monitor", "Track"), ("monitor", "track"),
            ("Monitoring", "Tracking"), ("monitoring", "tracking"),
            ("Coverage", "Tracking"), ("coverage", "tracking"),
            ("Momentum", "Trend"), ("momentum", "trend"),
            ("Recommend", "Note"), ("recommend", "note"),
            ("Recommendation", "Observation"), ("recommendation", "observation"),
            ("Suggest", "Note"), ("suggest", "note"),
            ("Suggests", "Notes"), ("suggests", "notes"),
            ("Forecast", "Projection"), ("forecast", "projection"),
            ("Predicts", "Indicates"), ("predicts", "indicates"),
            ("Predict", "Indicate"), ("predict", "indicate"),
            ("Analyst", "Data"), ("analyst", "data"),
        ]
        for (from, to) in replacements {
            s = s.replacingWholeWord(from, with: to)
        }
        return s
    }

    fileprivate func replacingWholeWord(_ word: String, with replacement: String) -> String {
        guard !word.isEmpty, let regex = try? NSRegularExpression(pattern: "\\b\(NSRegularExpression.escapedPattern(for: word))\\b") else {
            return self
        }
        let range = NSRange(startIndex..<endIndex, in: self)
        return regex.stringByReplacingMatches(in: self, range: range, withTemplate: replacement)
    }

    var humanizedDisplayText: String {
        sanitizedDisplayText.replacingOccurrences(of: "_", with: " ")
    }

    var humanizedTitleCasedDisplayText: String {
        let cleaned = humanizedDisplayText.lowercased()
        return cleaned.isEmpty ? cleaned : cleaned.capitalized
    }

    var strippedMarkdownMarkers: String {
        sanitizedDisplayText
            .replacingOccurrences(of: "**", with: "")
            .replacingOccurrences(of: "__", with: "")
            .replacingOccurrences(of: "## ", with: "")
            .replacingOccurrences(of: "# ", with: "")
    }
}
