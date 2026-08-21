# NutriQ — AI-Powered Nutrition Intelligence Platform

> **Build Edition**: Version 2.0 Consolidated & Build-Ready Edition  
> **Standards Source**: *NutriQ Master Specification Version 2.0* & *NutriQ Technical Design Document (TDD)*

NutriQ is a production-grade personal nutrition, calorie tracking, and wellness platform combining **deterministic clinical nutrition formulas** with **agentic AI intelligence** powered by Anthropic Claude.

---

## Architecture Overview

```
React PWA Client
     ↓
Frontend Services (API Client & Offline Store)
     ↓
TanStack Query & Zustand State Management
     ↓
FastAPI REST API (15 Domain Routers)
     ↓
OAuth2 + JWT Auth & Security Middleware
     ↓
Deterministic Nutrition Engine / Warning Engine / AI Agent Layer
     ↓
PostgreSQL Relational Storage (27 Relational Entities)
```

---

## Key Capabilities

- **100% Deterministic Nutrition Engine**: Implements the Mifflin-St Jeor formula for Men & Women, 5-tier activity multipliers, bounded targets, and a safe minimum 1200 kcal floor with zero LLM dependence.
- **Deterministic Contextual Smart Warnings**: Real-time evaluator for excess calories, low protein lag, and repeated multi-day intake excesses.
- **Curated IFCT & International Food Database**: Pre-seeded with regional Indian items and colloquial serving unit conversions (*"1 dosa"*, *"1 katori"*, *"1 piece"*, *"1 glass"* $\rightarrow$ grams).
- **Natural Language & Multi-Mode Food Logging**: Log meals via free-text natural language (*"two boiled eggs and two chapatis for breakfast"*), catalog search, barcode lookup, plate photo recognition, and one-tap favorites.
- **7 Agentic AI State Machines**: Dedicated state-machine agents (`NutritionAgent`, `GoalAgent`, `RecommendationAgent`, `MealPlanningAgent`, `ProgressAgent`, `AlertAgent`, `ReportAgent`) operating with strict validation.
- **Offline-First PWA**: Client storage via Dexie.js (IndexedDB) with Last-Write-Wins (LWW) conflict resolution and background synchronization upon reconnection.
- **Privacy & Governance**: Mandatory onboarding consent, full JSON/CSV data export, and cascading account deletion workflows.
- **Family / Multi-Profile Management**: Isolated targets, meals, and analytics for linked dependents.

---

## Quick Start & Local Execution

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL (or automated SQLite development fallback)

### 2. Backend Setup
```bash
cd nutriq-backend
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run backend API server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup
```bash
cd nutriq-frontend
# Install dependencies
npm install

# Start Vite development server
npm run dev -- --host 127.0.0.1 --port 5173
```
- Web Application URL: `http://127.0.0.1:5173/`

### 4. Running Automated Tests
```bash
cd nutriq-backend
pytest -v
```

---

## Documentation Index
- [`docs/implementation-plan.md`](./docs/implementation-plan.md): Complete Phase 0–49 implementation roadmap.
- [`docs/architecture.md`](./docs/architecture.md): Layered system architecture.
- [`docs/feature-matrix.md`](./docs/feature-matrix.md): Master requirement mapping matrix.
- [`docs/database.md`](./docs/database.md): 27 relational tables physical schema.
- [`docs/api.md`](./docs/api.md): REST API contracts and endpoint documentation.
- [`docs/ai.md`](./docs/ai.md): Claude AI integration, rate limiting & guardrails.
- [`docs/agents.md`](./docs/agents.md): 7 Agentic state machines and orchestration.
- [`docs/offline-sync.md`](./docs/offline-sync.md): Dexie.js IndexedDB and LWW conflict resolution.
- [`docs/security.md`](./docs/security.md): Authentication, RBAC, and privacy compliance.
- [`docs/testing.md`](./docs/testing.md): Automated test matrix and acceptance criteria.
- [`docs/deployment.md`](./docs/deployment.md): Docker, staging, and production runbook.
