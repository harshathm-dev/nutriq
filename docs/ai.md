# NutriQ AI Integration & Guardrails

## AI Strategy & Models
- **Primary AI Provider**: Anthropic Claude API (`claude-3-7-sonnet` for agentic planning & chat, `claude-3-5-haiku` for fast extraction).
- **Core Principle**: AI serves as an intelligence, extraction, and reasoning layer, **never** as the canonical source of truth for numerical calculations.

## AI Guardrails & Medical Disclaimers
1. **No Medical Diagnoses**: NutriQ AI explicitly disclaims medical authority and provides nutritional estimates, not clinical prescriptions or treatment.
2. **Deterministic Validation**: Every AI response must pass through strict Pydantic models before being presented or stored.
3. **Canonical Food Grounding**: Extracted food items from unstructured natural language are mapped against the verified IFCT database.
4. **Editable User Confirmations**: Low-confidence plate recognitions or voice inputs are editable by the user before creating records.

## AI Cost & Usage Controls
- **Rate Limiting**: Enforced via `ai_usage_counters` per user per endpoint per day (15 requests/day for Free, 200/day for Pro).
- **Response Caching**: SHA-256 hash caching of queries to avoid duplicate external API calls.
- **Graceful Degradation**: If AI limits are reached, the system falls back to rule-based recommendations without disrupting core tracking.
