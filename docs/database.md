# NutriQ Database Schema Specification

## PostgreSQL Physical Schema Blueprint (27 Relational Tables)

### 1. Identity & Profile
- **`users`**: `id` UUID PK, `email` VARCHAR(255) UNIQUE NOT NULL, `password_hash` VARCHAR(255) NOT NULL, `role` VARCHAR(50) DEFAULT 'user', `created_at` TIMESTAMPTZ, `updated_at` TIMESTAMPTZ.
- **`user_profiles`**: `id` UUID PK, `user_id` UUID FK UNIQUE NOT NULL, `name` VARCHAR(255), `age` INT, `gender` VARCHAR(50), `height_cm` FLOAT, `weight_kg` FLOAT, `activity_level` VARCHAR(50), `fitness_goal` VARCHAR(50), `dietary_preference` VARCHAR(100), `food_preferences` TEXT, `created_at` TIMESTAMPTZ, `updated_at` TIMESTAMPTZ.
- **`goals`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `goal_type` VARCHAR(50), `current_weight_kg` FLOAT, `target_weight_kg` FLOAT, `desired_rate` FLOAT, `target_date` TIMESTAMPTZ, `active` BOOLEAN, `created_at` TIMESTAMPTZ, `updated_at` TIMESTAMPTZ.

### 2. Foods & Conversions
- **`foods`**: `id` UUID PK, `name` VARCHAR(255) INDEX NOT NULL, `category` VARCHAR(100) INDEX NOT NULL, `serving_size` FLOAT DEFAULT 100.0, `unit` VARCHAR(50) DEFAULT 'g', `calories` FLOAT NOT NULL, `protein_g` FLOAT, `carbs_g` FLOAT, `fat_g` FLOAT, `fiber_g` FLOAT, `sugar_g` FLOAT, `sodium_mg` FLOAT, `source` VARCHAR(100) DEFAULT 'IFCT', `barcode` VARCHAR(100) INDEX, `updated_at` TIMESTAMPTZ.
- **`serving_conversions`**: `id` UUID PK, `food_id` UUID FK NOT NULL, `serving_label` VARCHAR(100) NOT NULL, `grams` FLOAT NOT NULL, `unit` VARCHAR(50), UNIQUE(`food_id`, `serving_label`).
- **`custom_foods`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `name` VARCHAR(255), `category` VARCHAR(100), `calories` FLOAT, `protein_g` FLOAT, `carbs_g` FLOAT, `fat_g` FLOAT, `fiber_g` FLOAT, `is_private` BOOLEAN DEFAULT TRUE, `created_at` TIMESTAMPTZ.

### 3. Meals, Recipes & Favorites
- **`meals`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `meal_type` VARCHAR(50) NOT NULL, `occurred_at` TIMESTAMPTZ NOT NULL, `source` VARCHAR(50) DEFAULT 'manual', `sync_version` INT DEFAULT 1, `created_at` TIMESTAMPTZ, `updated_at` TIMESTAMPTZ.
- **`meal_items`**: `id` UUID PK, `meal_id` UUID FK NOT NULL, `food_id` UUID FK, `food_name` VARCHAR(255), `quantity` FLOAT, `serving_unit` VARCHAR(50), `grams` FLOAT, `calories` FLOAT, `protein_g` FLOAT, `carbs_g` FLOAT, `fat_g` FLOAT, `fiber_g` FLOAT, `sugar_g` FLOAT, `sodium_mg` FLOAT.
- **`favorite_meals`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `name` VARCHAR(255), `meal_type` VARCHAR(50), `template_payload` TEXT, `created_at` TIMESTAMPTZ.
- **`recipes`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `name` VARCHAR(255), `description` TEXT, `servings` INT, `total_calories` FLOAT, `total_protein_g` FLOAT, `total_carbs_g` FLOAT, `total_fat_g` FLOAT, `created_at` TIMESTAMPTZ.
- **`recipe_ingredients`**: `id` UUID PK, `recipe_id` UUID FK NOT NULL, `food_id` UUID FK, `food_name` VARCHAR(255), `quantity` FLOAT, `unit` VARCHAR(50), `grams` FLOAT.

### 4. Tracking & Telemetry
- **`exercise`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `type` VARCHAR(100), `duration_min` INT, `calories_burned_est` FLOAT, `recorded_at` TIMESTAMPTZ.
- **`water`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `amount_ml` FLOAT, `recorded_at` TIMESTAMPTZ.
- **`weight_history`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `weight_kg` FLOAT, `recorded_at` TIMESTAMPTZ.

### 5. AI, Warnings & Orchestration
- **`ai_recommendations`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `recommendation_type` VARCHAR(50), `title` VARCHAR(255), `content` TEXT, `metadata_json` TEXT, `status` VARCHAR(50), `created_at` TIMESTAMPTZ.
- **`ai_warnings`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `warning_id` VARCHAR(100), `type` VARCHAR(50), `severity` VARCHAR(50), `message` TEXT, `evidence` TEXT, `created_at` TIMESTAMPTZ, `expires_at` TIMESTAMPTZ, `dismissed_at` TIMESTAMPTZ.
- **`meal_plans`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `title` VARCHAR(255), `plan_payload` TEXT, `active` BOOLEAN, `created_at` TIMESTAMPTZ.
- **`ai_interaction_logs`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `endpoint` VARCHAR(100), `model` VARCHAR(100), `input_hash` VARCHAR(64) INDEX, `request_metadata` TEXT, `response_metadata` TEXT, `latency_ms` INT, `token_usage` INT, `created_at` TIMESTAMPTZ.
- **`ai_usage_counters`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `endpoint` VARCHAR(100), `usage_date` VARCHAR(10), `count` INT DEFAULT 1, UNIQUE(`user_id`, `endpoint`, `usage_date`).

### 6. Subscriptions, Sync, Privacy & Administration
- **`subscriptions`**: `id` UUID PK, `user_id` UUID FK UNIQUE NOT NULL, `plan_tier` VARCHAR(50) DEFAULT 'free', `billing_status` VARCHAR(50) DEFAULT 'active', `current_period_end` TIMESTAMPTZ, `created_at` TIMESTAMPTZ, `updated_at` TIMESTAMPTZ.
- **`entitlements`**: `id` UUID PK, `subscription_id` UUID FK NOT NULL, `feature_key` VARCHAR(100), `daily_quota` INT, `is_enabled` INT.
- **`device_sync_state`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `device_id` VARCHAR(100), `last_sync_at` TIMESTAMPTZ, `cursor` VARCHAR(100), `status` VARCHAR(50), UNIQUE(`user_id`, `device_id`).
- **`sync_records`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `device_id` VARCHAR(100), `entity_type` VARCHAR(50), `entity_id` UUID, `operation` VARCHAR(20), `payload` TEXT, `client_timestamp` TIMESTAMPTZ, `server_timestamp` TIMESTAMPTZ, `status` VARCHAR(50).
- **`family_profiles`**: `id` UUID PK, `primary_user_id` UUID FK NOT NULL, `name` VARCHAR(255), `relationship` VARCHAR(50), `age` INT, `gender` VARCHAR(50), `height_cm` FLOAT, `weight_kg` FLOAT, `activity_level` VARCHAR(50), `fitness_goal` VARCHAR(50), `dietary_preference` VARCHAR(100), `created_at` TIMESTAMPTZ.
- **`allergies`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `allergen_type` VARCHAR(100), `severity` VARCHAR(50), `notes` TEXT, `created_at` TIMESTAMPTZ.
- **`consent_records`**: `id` UUID PK, `user_id` UUID FK NOT NULL, `consent_type` VARCHAR(100), `version` VARCHAR(50), `accepted_at` TIMESTAMPTZ, `revoked_at` TIMESTAMPTZ.
- **`audit_logs`**: `id` UUID PK, `admin_user_id` UUID FK, `action` VARCHAR(100), `entity_type` VARCHAR(50), `entity_id` UUID, `metadata_json` TEXT, `created_at` TIMESTAMPTZ.
