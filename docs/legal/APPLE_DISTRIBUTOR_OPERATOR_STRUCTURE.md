# Apple Distributor / Legal Operator Structure

**Created:** 2026-06-01
**Status:** NEEDS PARENT AND LEGAL REVIEW — DO NOT RELY ON THIS AS LEGAL ADVICE

---

## Current Structure

| Role | Entity |
|---|---|
| Apple Developer Account Type | Individual |
| Apple Account Holder | [Individual Apple Developer Account Holder] (user's mom / legal name) |
| App Store Seller / Distributor Name | [Individual Apple Developer Account Holder]'s legal name (as displayed in App Store) |
| App Store Payment Recipient | [Individual Apple Developer Account Holder]'s bank account |
| Service Operator / Data Controller | Andover Digital LLC |
| Product Brand | Clavix |
| App Operator / Backend / Support | Andover Digital LLC |
| iOS Bundle ID | `com.clavisdev.portfolioassistant` |

---

## Current App & Docs Analysis

### 1. What does the app display as company/operator?

- **Login screen:** Links to `getclavix.com/terms` and `getclavix.com/privacy`. No explicit "operated by" text visible in the app screens examined.
- **Settings > Support & Legal:** Links to `getclavix.com/terms` and `getclavix.com/privacy`. No "operated by" text.
- **Disclaimer copy (`ClavisCopy`):** Mentions "Clavix" only. No company name.
- **No in-app legal screen** displays "Andover Digital LLC" or the individual Apple account holder's name.
- **Risk disclaimer:** "Clavix is informational only."

### 2. What does the Privacy Policy say?

The current live Privacy Policy at `getclavix.com/privacy` states:

> "Clavix is operated by Andover Digital LLC."

It does NOT mention:
- The individual Apple Developer account holder
- The App Store distributor/seller role
- That the App Store seller name may differ from Andover Digital LLC

### 3. What do the Terms say?

The current live Terms at `getclavix.com/terms` state:

> "These Terms constitute a legally binding agreement between you and Andover Digital LLC."

Plus:

> "Andover Digital LLC - operator of Clavix"
> "Commonwealth of Massachusetts, United States"

They do NOT mention:
- The individual Apple Developer account holder
- The App Store distributor role
- Any Apple-specific terms

### 4. What will users likely see on the App Store as seller/developer name?

Under an **Individual Apple Developer account**, the seller name displayed on the App Store is typically the individual account holder's **legal name** (the name on the Apple Developer account).

Users will see **"Clavix"** as the app name and **[Individual Apple Developer Account Holder]** as the seller/developer.

This creates a visible mismatch: the app's Privacy Policy and Terms of Service refer to "Andover Digital LLC" as the operator, but the App Store listing shows an individual name as the seller.

### 5. Does the Privacy Policy need to mention the individual Apple seller/distributor role?

**YES.** To avoid confusing users about the relationship between:
- The App Store seller name (individual name)
- The service operator (Andover Digital LLC)

A sentence should explain:
- The iOS app is distributed through an Individual Apple Developer account
- The App Store seller name reflects that individual
- Andover Digital LLC operates the Clavix service and handles data
- The individual does not receive or access user personal data solely through their App Store seller role

### 6. Do the Terms need to mention the individual Apple seller/distributor role?

**YES.** For the same reason. Plus:
- App Store proceeds may be paid to the individual's bank account
- This may create tax/accounting obligations for the individual
- Users should understand the contractual relationship

### 7. Does the website need a disclosure?

The website does not currently have a dedicated privacy/terms page for the app (the `getclavix.com/privacy` and `/terms` pages are the app's legal pages). The website itself (landing page at `getclavix.com`) has a footer with Privacy and Terms links that point to the same pages. **The website footer currently shows:**
> `© 2026 Clavix. All rights reserved.`

It does not show Andover Digital LLC in the footer. The privacy/terms pages themselves identify Andover Digital LLC. **The footer should include Andover Digital LLC.**

### 8. Does the in-app legal screen need a disclosure?

**YES.** The in-app Settings > Support & Legal screen should include a brief "About" or "Operating company" section that explains:
- Clavix is operated by Andover Digital LLC
- The app is distributed through the Apple App Store by an authorized individual account holder
- Links to Privacy Policy and Terms (already exist)

### 9. Is the mismatch a blocker for TestFlight?

**PROBABLY NOT.** TestFlight typically shows the developer name based on the Apple Developer account. For individual accounts, it shows the individual's name. TestFlight testers are a small, trusted group. The mismatch is less concerning for TestFlight.

However, **TestFlight still requires basic compliance**. If a tester complained to Apple about misleading legal docs, Apple might investigate.

### 10. Is the mismatch a blocker for public App Store launch?

**POTENTIALLY.** Issues to consider:
- **Apple Developer Program Agreement** §3.2 requires that the seller name in the App Store accurately identify the entity offering the app
- If users see [Individual Name] as seller but Terms say "Andover Digital LLC," there's a disclosure gap
- Apple's guidelines require clear identification of the seller/developer
- For paid apps (subscriptions), the seller name has additional significance because it identifies who processes payments
- For IAP revenue, Apple pays the individual account holder, not Andover Digital LLC
- This may create tax discrepancies: Apple issues 1099-K/1042 to the individual, not the LLC
- The individual may have personal liability exposure since they are the App Store contracting party

### 11. What must be reviewed by the parent/account holder/lawyer?

| Item | Reviewer |
|---|---|
| Whether the individual Apple account holder is comfortable with their name being the App Store seller | Account holder |
| Whether the individual understands their tax/payment obligations from App Store proceeds | Account holder + tax professional |
| Whether the operator/distributor language accurately protects the individual from liability | Lawyer |
| Whether the individual should be a named party in the Terms | Lawyer |
| Whether Andover Digital LLC has the necessary agreements with the individual | Lawyer |
| Whether the structure complies with Apple Developer Program Agreement | Lawyer |
| Whether the structure violates any state/ federal regulations about App Store sellers | Lawyer |

### 12. Language for TestFlight

Suggested temporary disclosure for TestFlight:

> "Clavix is operated by Andover Digital LLC. The Clavix iOS app is distributed through an Individual Apple Developer account. The App Store may display an individual name as the seller for Apple distribution purposes. Andover Digital LLC operates the Clavix service and is responsible for the app experience, data handling, and support."

### 13. Language for public launch (if this structure remains)

Required disclosure additions:

**Privacy Policy:**
> "Clavix is operated by Andover Digital LLC. The Clavix iOS app is distributed on the Apple App Store through an Individual Apple Developer account held by [Individual Apple Developer Account Holder], who acts as the App Store seller for Apple distribution purposes. [Individual Apple Developer Account Holder] does not receive or access user personal data through their role as App Store seller. Andover Digital LLC is solely responsible for the operation of the Clavix service, data handling, support, and all aspects of the product experience. [TODO: PARENT/LAWYER REVIEW OF THIS LANGUAGE]"

**Terms of Service:**
> "These Terms are between you and Andover Digital LLC, the operator of Clavix. The Clavix iOS app is distributed on the Apple App Store by [Individual Apple Developer Account Holder], who serves as the App Store seller for Apple distribution purposes. Andover Digital LLC is solely responsible for the Clavix service, support, and the terms governing your use of the app. [TODO: PARENT/LAWYER REVIEW OF THIS LANGUAGE]"

### 14. Language if Apple account moves to Organization account

If the Apple Developer account is upgraded to an Organization account under Andover Digital LLC:

> "Clavix is operated and distributed by Andover Digital LLC."

This simplifies everything. The App Store seller name would be "Andover Digital LLC" (verified by Apple with D&B), matching the Privacy Policy and Terms. No individual name appears.

### 15. Docs with TODO to revisit

| Document | TODO |
|---|---|
| Privacy Policy | "Revisit when Apple account transitions from individual to organization — the App Store distributor disclosure may no longer be needed." |
| Terms of Service | "Revisit when Apple account transitions from individual to organization — the App Store seller/clause may no longer be needed." |
| In-app legal screen | "Update operator display once organization account is established." |
| Marketing website footer | "Update © notice and operator display once organization account is established." |

---

## Risk Table

| Issue | Risk | Severity | Practical Fix | Owner |
|---|---|---|---|---|
| App Store shows individual name as seller; legal docs say Andover Digital LLC | User confusion about contracting party; potential Apple Developer Program compliance issue | HIGH | Add distributor/seller disclosure to Privacy Policy and Terms | Coding agent + Lawyer review |
| App Store subscription revenue paid to individual's bank account | Individual may owe taxes on app revenue; legal/financial exposure | HIGH | Ensure individual is aware; consult tax professional; consider moving to organization account | Parent/account holder + Tax professional |
| No in-app "operated by" disclosure | App Review may reject for unclear developer identity | MEDIUM | Add "Operated by Andover Digital LLC" to Settings > Legal or app footer | Coding agent |
| Individual account holder's name appears on App Store as developer | Privacy concern for the individual (their name is publicly visible) | MEDIUM | Individual should be aware and consent; move to organization account eventually | Parent/account holder |
| Terms bind user to Andover Digital LLC but App Store seller is individual | Legal question: who is the counterparty for the app transaction? | MEDIUM | Ask lawyer whether individual needs to be mentioned in Terms | Lawyer |
| Apple Developer Program Agreement requires seller name accuracy | If Apple investigates, they may require disclosure or conversion to organization | LOW | Preemptively include disclosure language | Coding agent + Lawyer |
| No PrivacyInfo.xcprivacy in iOS app | App Review may reject (required for APIs accessing user data) | MEDIUM | Create PrivacyInfo.xcprivacy | Coding agent |
| User can't easily identify operating company in app | Transparency concern; some users may not trust anonymous "Clavix" | LOW | Add "Operated by Andover Digital LLC" to Settings footer | Coding agent |
