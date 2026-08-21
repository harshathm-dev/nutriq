# NutriQ Agentic AI Architecture

## 7 Specialized State-Machine Agents

NutriQ utilizes a lightweight, auditable state machine per agent (`IDLE` → `ANALYZING` → `DECIDING` → `COMPLETED` / `FAILED`).

### 1. Nutrition Agent
- **Role**: Monitors daily intake, macronutrient ratios (Protein/Carb/Fat), and micro-nutrients in real-time.
- **State Flow**: Analyzes intake vs. targets → evaluates macro balance → outputs nutritional status telemetry.

### 2. Goal Agent
- **Role**: Compares caloric trajectory and weight history against the user's active goal.
- **State Flow**: Evaluates surplus/deficit velocity → assesses milestone alignment.

### 3. Recommendation Agent
- **Role**: Contextually identifies optimal foods, portion adjustments, and high-protein swaps based on remaining daily balances.

### 4. Meal Planning Agent
- **Role**: Generates multi-day personalized meal schedules respecting calorie targets, dietary preferences, and budget constraints.

### 5. Progress Agent
- **Role**: Computes logging consistency scores, streak achievements, and milestones.

### 6. Alert Agent
- **Role**: Evaluates health and threshold breaches (excess calories, protein deficit) to trigger non-intrusive warnings.

### 7. Report Agent
- **Role**: Compiles multi-day telemetry into comprehensive weekly intelligence summaries with actionable takeaways.

### Critical Safety Guardrail
Agents **never directly mutate database records**. All state modifications occur strictly through validated application services.
