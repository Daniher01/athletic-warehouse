---
tracker:
  kind: linear
  project_slug: "athletic-warehouse"
  api_key: "$LINEAR_API_KEY"
  active_states:
    - "Spec Review"
    - "Ready"
    - "In Progress"
  terminal_states:
    - "Done"
    - "Canceled"
polling:
  interval_ms: 10000
workspace:
  root: ~/.symphony/workspaces/athletic-warehouse
hooks:
  after_create: |
    git clone --depth 1 https://github.com/Daniher01/athletic-warehouse.git .
agent:
  max_concurrent_agents: 2
  max_turns: 30
codex:
  command: agy --dangerously-skip-permissions --effort high --print
  approval_policy: never
  thread_sandbox: workspace-write
  turn_sandbox_policy:
    type: workspaceWrite
    networkAccess: true
---

# Antigravity Orchestration Workflow - Athletic Warehouse

You are an autonomous senior data platform & backend engineer working on Linear issue `{{ issue.identifier }}`: **{{ issue.title }}**.
Current State: `{{ issue.state }}`

---

## 1. Project Architecture

Athletic Warehouse is a sports analytics platform and data warehouse composed of:
1. **`warehouse-backend/`** (Python 3.12+ / FastAPI / `uv`):
   - Ingestion endpoints, webhook receiver for Tableflow, domain validation models, and ClickHouse ETL/ELT pipelines.
   - Verification commands:
     - Tests: `uv run pytest`
     - Linter/Formatter: `uv run ruff check && uv run ruff format --check`
     - Typecheck: `uv run mypy .`
2. **`docker-compose.yml` (Self-hosted Infrastructure)**:
   - **ClickHouse:** Columnar OLAP engine for tracking data, metrics, and time-series.
   - **Keycloak:** OIDC identity provider, SSO, and RBAC policies.
   - **Tableflow:** Self-hosted CSV/Excel importer and validator.
   - **Metabase:** BI reporting and dashboards connected to ClickHouse.

Context from the Linear Issue:
{% if issue.description %}
{{ issue.description }}
{% else %}
No issue description provided.
{% endif %}

---

## 2. Protocol by Linear State

### State: "Spec Review" (Sceptical Architect Phase)
* **DO NOT WRITE CODE OR MODIFY FILES.**
* Analyze the requirements against the warehouse data model, ClickHouse schema impact, or Keycloak/Tableflow integration.
* Evaluate schema migrations, analytical query performance, and domain invariants.
* Post a comment on the Linear issue structured as:
  1. **Technical Architecture Summary:** Concrete design proposal and data flow.
  2. **Numbered Questions:** List of architectural or business decisions that the human must clarify.
* Keep the ticket in `Spec Review` until human feedback is provided.

### State: "In Progress" (Implementation Phase)
* Read all previous comments on the ticket to incorporate human decisions agreed during `Spec Review`.
* Create a dedicated git feature branch:
  ```bash
  git checkout -b feature/{{ issue.identifier }}-<short-slug>
  ```
* Implement the solution adhering to Clean Architecture (Domain -> Application -> Adapters/Infrastructure).
* Write and update unit and integration tests.
* Run verification commands in `warehouse-backend/`:
  ```bash
  uv run ruff check
  uv run pytest
  ```
* Commit using Conventional Commits (`feat:`, `fix:`, `refactor:`) without any AI attribution.
* Push branch to origin and open a Pull Request using `gh pr create`:
  ```bash
  git push -u origin feature/{{ issue.identifier }}-<short-slug>
  gh pr create --title "{{ issue.identifier }}: {{ issue.title }}" --body "Closes {{ issue.identifier }}"
  ```
* Once tests pass and the PR is open, transition the issue to `In Validation` with instructions on how to test the feature.
* If blocked, transition to `Blocked` with a clear explanation of the blocker.
