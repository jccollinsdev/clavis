import Foundation

enum PortfolioMath {
    /// Value-weighted portfolio composite score per CLAVIX_TRUTH §9.
    /// Σ(market_value × score) / Σ(market_value), excluding holdings without a score or value.
    /// Returns nil when no scored, valued holdings exist.
    static func weightedScore(_ holdings: [Position]) -> Double? {
        let weightedPairs = holdings.compactMap { position -> (Double, Double)? in
            guard let value = position.currentValue, value > 0,
                  let score = position.resolvedTotalScore else { return nil }
            return (value, score)
        }
        let totalWeight = weightedPairs.reduce(0) { $0 + $1.0 }
        guard totalWeight > 0 else { return nil }
        return weightedPairs.reduce(0) { $0 + ($1.0 * $1.1) } / totalWeight
    }

    /// Grade derived from a 0-100 composite score using the CLAVIX_TRUTH §7 band table.
    static func grade(forScore score: Double) -> String {
        switch score {
        case 90...100: return "AAA"
        case 80..<90:  return "AA"
        case 70..<80:  return "A"
        case 60..<70:  return "BBB"
        case 50..<60:  return "BB"
        case 40..<50:  return "B"
        case 30..<40:  return "CCC"
        case 20..<30:  return "CC"
        case 10..<20:  return "C"
        default:       return "F"
        }
    }

    /// Convenience: value-weighted grade. Returns "—" when score is unavailable.
    static func weightedGrade(_ holdings: [Position]) -> String {
        guard let score = weightedScore(holdings) else { return "—" }
        return grade(forScore: score)
    }
}
