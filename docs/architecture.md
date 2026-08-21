# NutriQ System Architecture

## Architectural Blueprint

NutriQ uses a layered, offline-capable architecture designed for scale, resilience, and strict calculation integrity.

```
React PWA Client
     ↓
Frontend Services (API client & Offline Store)
     ↓
TanStack Query & Zustand State Management
     ↓
FastAPI REST API Gateway
     ↓
Authentication & Authorization Layer (OAuth2 + JWT)
     ↓
Application Services & Business Logic
     ↓
Deterministic Nutrition Engine / Warning Engine / AI Agent Layer
     ↓
PostgreSQL Relational Storage & External Service Adapters
```

## Layer Descriptions

### 1. Presentation Layer (React.js PWA)
- **Framework**: React.js with modular component architecture.
- **Styling**: Vanilla CSS Design System with obsidian dark mode, glassmorphic card containers, and responsive layouts.
- **State Management**:
  - **Zustand**: Local interactive UI state, active tabs, drawer modals, active family profile context.
  - **TanStack Query**: Server state caching, background queries, optimistic updates.
- **Offline Storage**: IndexedDB accessed through Dexie.js for offline food database querying, local meal logging, and pending sync actions.
- **Charting**: Recharts for energy balance gauges, weekly intake adherence, and weight trajectory curves.

### 2. API Gateway & Business Service Layer (Python + FastAPI)
- **Endpoints**: 15 domain routers implementing RESTful conventions with Pydantic v2 schemas.
- **Authentication**: Native OAuth2 with JWT tokens, Argon2/bcrypt password hashing, and role verification.
- **Deterministic Calculation Engines**:
  - **NutritionEngine**: Mifflin-St Jeor equation, standard 5-tier activity multipliers, bounded targets, safe 1200 kcal floor, macro distribution.
  - **WarningEngine**: Multi-condition contextual warning evaluator.
- **AI Integration & Service Adapters**:
  - **ClaudeAdapter**: Structured JSON generation via Anthropic Claude 3.7 / 3.5 Haiku.
  - **VisionAdapter & SpeechAdapter**: Decoupled third-party interfaces with confidence gates.
  - **AI Cost Controls**: Per-user daily quotas, SHA-256 request hashing, and deterministic fallback.

### 3. Persistence Layer (PostgreSQL)
- **Asynchronous SQLAlchemy**: Clean object-relational mapping with version-controlled migrations via Alembic.
- **Data Model**: 27 relational tables supporting core nutrition, tracking, AI logs, usage counters, subscriptions, family profiles, consent logs, and audit trails.
