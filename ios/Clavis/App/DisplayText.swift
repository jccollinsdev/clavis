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

        return String(String.UnicodeScalarView(filteredScalars))
            .replacingOccurrences(of: "\n\n\n", with: "\n\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var strippedMarkdownMarkers: String {
        sanitizedDisplayText
            .replacingOccurrences(of: "**", with: "")
            .replacingOccurrences(of: "__", with: "")
            .replacingOccurrences(of: "## ", with: "")
            .replacingOccurrences(of: "# ", with: "")
    }
}
