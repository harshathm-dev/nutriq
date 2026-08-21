# NutriQ Feature Matrix

| Master Requirement | Frontend Module | Backend Service / Router | Database Entity | API Endpoint | Verification Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **User Authentication** | `AuthPage.jsx` | `auth.py` / `auth_service.py` | `users`, `consent_records` | `POST /api/auth/register`<br>`POST /api/auth/login` | `test_auth_and_sync.py` |
| **User Profile Management** | `SettingsPage.jsx` | `profile.py` | `user_profiles` | `GET /api/profile`<br>`PUT /api/profile` | `test_e2e.py` |
| **Goal Configuration** | `SettingsPage.jsx` | `goals.py` | `goals` | `GET /api/goals`<br>`POST /api/goals` | `test_e2e.py` |
| **Deterministic Nutrition Engine** | `DashboardPage.jsx` | `calories.py` / `nutrition_engine.py` | N/A (Mathematical) | `POST /api/calculate/calories`<br>`GET /api/nutrition/targets` | `test_nutrition_engine.py` |
| **Curated Food Catalog & Search** | `FoodCatalogPage.jsx` | `foods.py` / `food_service.py` | `foods`, `serving_conversions` | `GET /api/foods`<br>`GET /api/foods/{id}` | `test_e2e.py` |
| **Meal Journal & Totals** | `DashboardPage.jsx`, `AddFoodPage.jsx` | `meals.py` / `meal_service.py` | `meals`, `meal_items` | `POST /api/meals`<br>`GET /api/meals`<br>`DELETE /api/meals/{id}` | `test_e2e.py` |
| **NLP Food Extraction** | `AddFoodPage.jsx` | `ai.py` / `ai_service.py` | `ai_interaction_logs`, `ai_usage_counters` | `POST /api/ai/analyze-food` | `test_nlp_ai.py` |
| **Deterministic Smart Warnings** | `SmartWarningBanner.jsx` | `analytics.py` / `warning_engine.py` | `ai_warnings` | `GET /api/analytics/daily` | `test_warning_engine.py` |
| **Exercise & Calorie Burn** | `DashboardPage.jsx` | `tracking.py` | `exercise` | `POST /api/exercise`<br>`GET /api/exercise` | `test_e2e.py` |
| **Hydration Tracking** | `QuickWaterWidget.jsx` | `tracking.py` | `water` | `POST /api/water`<br>`GET /api/water` | `test_e2e.py` |
| **Weight Tracking & Projections** | `AnalyticsPage.jsx` | `tracking.py` | `weight_history` | `POST /api/weight`<br>`GET /api/weight/history` | `test_e2e.py` |
| **Multi-Day Analytics & Reports** | `AnalyticsPage.jsx` | `analytics.py` / `analytics_service.py` | N/A (Aggregations) | `GET /api/analytics/weekly`<br>`GET /api/analytics/monthly` | `test_e2e.py` |
| **AI Nutrition Recommendations** | `DashboardPage.jsx` | `ai.py` / `agent_service.py` | `ai_recommendations` | `POST /api/ai/recommend` | `test_nlp_ai.py` |
| **Conversational AI Assistant** | `AIAssistantPage.jsx` | `ai.py` / `ai_service.py` | `ai_interaction_logs` | `POST /api/ai/chat` | `test_e2e.py` |
| **Personalized Meal Planner** | `MealPlannerPage.jsx` | `ai.py` / `agent_service.py` | `meal_plans` | `POST /api/ai/meal-plan` | `test_e2e.py` |
| **Barcode Scanning Architecture** | `AddFoodPage.jsx` | `foods.py` | `foods` | `GET /api/foods/barcode/{code}` | `test_e2e.py` |
| **Custom Foods & Recipes** | `AddFoodPage.jsx` | `foods.py`, `favorites.py` | `custom_foods`, `recipes`, `favorite_meals` | `POST /api/foods/custom`<br>`POST /api/recipes` | `test_e2e.py` |
| **Offline-First Storage & Sync** | `db.js`, `api.js` | `sync.py` / `sync_service.py` | `device_sync_state`, `sync_records` | `POST /api/sync` | `test_e2e.py` |
| **Family Profiles & Allergies** | `FamilyPage.jsx` | `family.py` | `family_profiles`, `allergies` | `GET /api/family/profiles`<br>`POST /api/allergies` | `test_e2e.py` |
| **Subscription & AI Quotas** | `BillingPage.jsx` | `billing.py` / `billing_service.py` | `subscriptions`, `entitlements`, `ai_usage_counters` | `GET /api/billing/plan`<br>`POST /api/billing/subscribe` | `test_e2e.py` |
| **Privacy, Export & Deletion** | `PrivacyPage.jsx` | `privacy.py` / `privacy_service.py` | `consent_records` | `GET /api/privacy/export`<br>`DELETE /api/privacy/account` | `test_e2e.py` |
