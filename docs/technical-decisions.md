# NutriQ Technical Decisions & Rationale

This document logs the major technical choices made for NutriQ in accordance with the Master Specification v2.0 and TDD.

## 1. AI Provider & Model Strategy
- **Decision**: Anthropic Claude API as primary AI provider (`claude-3-7-sonnet` for agentic workflows & chat, `claude-3-5-haiku` for fast food extraction).
- **Rationale**: Strong reasoning capability, reliable tool use / function calling for structured JSON schemas, predictable token billing.

## 2. Deterministic vs. AI Separation
- **Decision**: BMR, TDEE, bounded targets, macro/water targets, and meal energy summation are 100% deterministic (Python service layer).
- **Rationale**: LLMs are non-deterministic and can hallucinate numerical quantities. Core clinical formulas must produce exact, reproducible values.

## 3. Database & ORM
- **Decision**: PostgreSQL with Asynchronous SQLAlchemy 2.0 and Alembic for schema migrations.
- **Rationale**: Relational integrity with foreign keys, cascading deletions for privacy compliance, unique constraints on serving conversions and daily usage counters, and native JSONB support.

## 4. Frontend State & Caching
- **Decision**: React.js with Zustand for local UI state and TanStack Query for server state caching and optimistic UI updates.
- **Rationale**: Clean separation between server data and client state, minimizing boilerplate while optimizing rendering performance.

## 5. Offline Storage & Conflict Resolution
- **Decision**: IndexedDB via Dexie.js with an Outbox queue pattern. Conflict resolution strategy is **Last-Write-Wins (LWW) by timestamp at record level** with field-level merge for non-conflicting fields.
- **Rationale**: Provides robust, structured storage on mobile and web PWAs and ensures user edits offline synchronize reliably without data loss.

## 6. Authentication & Security
- **Decision**: OAuth2 with JWT tokens, PBKDF2-SHA256 / bcrypt password hashing, and server-enforced resource ownership checks.
- **Rationale**: Zero reliance on client-side security assertions. Secrets and third-party API keys are never exposed to the frontend bundle.
