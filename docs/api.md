# NutriQ API Specification & Contracts

## Base URL
`/api`

## Authentication Endpoints (`/api/auth`)
- `POST /api/auth/register`: Create user account with terms & AI consent.
- `POST /api/auth/login`: Authenticate and obtain JWT bearer token.
- `POST /api/auth/logout`: Revoke active session.

## Profile Endpoints (`/api/profile`)
- `GET /api/profile`: Retrieve active user profile.
- `PUT /api/profile`: Update demographics & dietary preferences.

## Goals & Targets (`/api/goals`, `/api/calories`, `/api/nutrition/targets`)
- `GET /api/goals`: List user goals.
- `POST /api/goals`: Create/activate a new fitness goal.
- `PUT /api/goals/{id}`: Update existing goal.
- `POST /api/calculate/calories`: Calculate BMR, TDEE, bounded targets.
- `GET /api/nutrition/targets`: Retrieve active user's calculated targets.

## Foods & Catalog (`/api/foods`)
- `GET /api/foods`: Search curated IFCT food database.
- `GET /api/foods/{id}`: Get food details with serving conversions.
- `POST /api/foods`: Admin food creation (Admin only).
- `POST /api/foods/custom`: Create user custom food item.
- `GET /api/foods/barcode/{code}`: Look up verified packaged food by barcode.

## Meals & Recipes (`/api/meals`, `/api/favorites`, `/api/recipes`)
- `POST /api/meals`: Log new meal with multiple items & servings.
- `GET /api/meals`: List historical meals by date range.
- `GET /api/meals/{id}`: Get specific meal details.
- `DELETE /api/meals/{id}`: Delete meal entry.
- `POST /api/favorites`: Save meal as reusable template.
- `GET /api/favorites`: List user favorite meal templates.
- `POST /api/recipes`: Create multi-ingredient composite recipe.
- `GET /api/recipes`: List user recipes with calculated totals.

## Tracking Endpoints (`/api/exercise`, `/api/water`, `/api/weight`)
- `GET /api/exercise`: List workout logs.
- `POST /api/exercise`: Log activity & duration with calorie burn estimate.
- `DELETE /api/exercise/{id}`: Delete workout log.
- `GET /api/water`: List hydration logs.
- `POST /api/water`: Log water consumption in ml.
- `GET /api/weight/history`: List periodic weigh-ins.
- `POST /api/weight`: Log new weight in kg.

## AI & Intelligence Endpoints (`/api/ai`)
- `POST /api/ai/analyze-food`: Natural language food item extraction.
- `POST /api/ai/recommend`: Context-aware food & portion recommendations.
- `POST /api/ai/meal-plan`: Multi-day personalized meal planner.
- `POST /api/ai/chat`: Conversational nutrition companion with guardrails.
- `POST /api/ai/analyze-image`: Food plate image recognition adapter.
- `POST /api/ai/analyze-habits`: Multi-day habit & pattern detector.

## Analytics & Reports (`/api/analytics`)
- `GET /api/analytics/daily`: Real-time daily energy balance & smart warnings.
- `GET /api/analytics/weekly`: 7-day intake averages & Weekly AI Intelligence Report.
- `GET /api/analytics/monthly`: 30-day adherence & milestone progress.

## Billing & Entitlements (`/api/billing`)
- `GET /api/billing/plan`: Retrieve subscription status and daily AI quota.
- `POST /api/billing/subscribe`: Upgrade or change plan tier.
- `POST /api/billing/cancel`: Downgrade to Free tier.

## Privacy, Consent & Governance (`/api/privacy`)
- `POST /api/privacy/consent`: Record timestamped consent.
- `GET /api/privacy/export`: Complete JSON/CSV archive export.
- `DELETE /api/privacy/account`: Cascading account deletion workflow.

## Family & Allergies (`/api/family`, `/api/allergies`)
- `GET /api/family/profiles`: List linked dependent profiles.
- `POST /api/family/profiles`: Create linked profile.
- `PUT /api/family/profiles/{id}`: Update dependent profile.
- `GET /api/allergies`: List declared allergens.
- `POST /api/allergies`: Add allergen preference flag.

## Offline Synchronization (`/api/sync`)
- `POST /api/sync`: Process batch of offline pending mutations with LWW conflict resolution.
