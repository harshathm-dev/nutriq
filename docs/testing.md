# NutriQ Testing Strategy & Critical Acceptance Tests

## Testing Levels

### 1. Unit Tests (`pytest`)
- **Deterministic Formulas**: Verified Mifflin-St Jeor formula across boundary ages, heights, weights, and genders.
- **TDEE & Safe Floor**: Verified 1200 kcal floor clamping and activity multipliers.
- **Warning Engine**: Evaluates excess calorie, low protein, and multi-day trend alerts.
- **Serving Conversions**: Verified colloquial units to grams calculation accuracy.

### 2. Integration Tests
- **Auth & Lifecycle**: Registration → Consent → Login → Token Refresh → Logout.
- **Meal Logging**: Create meal → Compute totals → Fetch daily analytics.
- **Sync Idempotency**: Verify duplicate sync payloads are ignored safely.
- **Multi-Profile Isolation**: Verify primary user cannot access unauthorized family profile data.

### 3. Critical Acceptance Test Matrix (TDD Section 28)
1. [x] Valid profile generates configured calorie estimate.
2. [x] Meal logging updates daily totals without AI dependency.
3. [x] Excess-calorie warning appears only under configured contextual rule.
4. [x] Low-protein recommendation uses user's target.
5. [x] Natural-language food logging asks for confirmation when uncertain.
6. [x] Barcode logging uses verified packaged-food data or falls back to search.
7. [x] Low-confidence image results are never silently logged.
8. [x] Voice results are editable before final logging.
9. [x] Offline meals synchronize exactly once.
10. [x] Conflicting edits follow timestamp/merge rule.
11. [x] AI quotas prevent unauthorized calls.
12. [x] AI failure does not break core tracking.
13. [x] Export contains required user-owned data.
14. [x] Deletion removes/anonymizes data according to policy.
15. [x] Family-profile requests cannot access another profile's data.
16. [x] Admin changes create audit records.
