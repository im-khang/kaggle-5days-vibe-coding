# M5 Build Sprint — Phase 1 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.
> **Tactical approach:** Parallelize independent tasks using delegate_task, max 3 concurrent. After all Phase 1 tasks complete, run integration check before Phase 2.

**Goal:** Lock capstone direction + set up foundation (public repo, spec file, rules.py) to enable Phase 2 verifier/worker build.

**Architecture:** Council pattern (Orchestrator + Workers + Verifier) per D4. This plan builds the components in dependency order: decision → repo → spec → KB rules → verifier → worker → orchestrator → aggregate → full loop.

**Tech Stack:** Python 3.12, pandas, openpyxl, Google ADK 2.0, Gemini 2.5 (Flash for workers, Pro for orchestrator), pytest for evals.

---

## Task List (Phase 1: Foundation)

### Task 1: Lock Capstone Decision D1

**Objective:** Update decisions.md to lock direction #1 with one-line problem statement and measurable success metrics.

**Files:**
- Modify: `02-PROJECTS/Vibe Coding Capstone Kaggle/decisions.md`
- Obsidian vault path: `/Users/nguyenduykhang/Library/Mobile Documents/iCloud~md~obsidian/Documents/my-obsidian-vaults/02-PROJECTS/Vibe Coding Capstone Kaggle/decisions.md`

**Changes needed:**
1. Under D1 section, change "Status: **OPEN — decide at the Day 5 gate.**" to "Status: **LOCKED — confirmed June 19, 2026.**"
2. Ensure bullet points under "Decision" show:
   - Chosen direction: #1 — AI-assisted 3PL/logistics ops report agent
   - Date decided: 2026-06-19
   - One-line problem statement: "Given raw 3PL shipment rows, the agent enriches each order (Area, Route, SLA, leadtime, on-time flags) per the case rules, computes per-3PL on-time and cost/leadtime KPIs, and produces a cited carrier-performance report — with a verifier loop that recomputes derived fields and blocks any output that fails the rules."
   - Success metrics (4 bullet points as already written)
3. In Decision log, add entry: "2026-06-19: Direction #1 locked at Day 5 gate. Problem statement + success metric defined. Build sprint M5 begins."

**Verification:**
- Read decisions.md back
- Confirm D1 status shows "LOCKED"
- Confirm problem statement and metrics present
- Run: `grep -A2 "Status:" decisions.md | head -3`

**Commit:**
- This is Obsidian vault file, not in git repo yet. After edit, note in receipt later.

---

### Task 2: Create Public GitHub Repo and Push Code

**Objective:** Create public GitHub repository `3pl-ops-agent` and push current codebase.

**Files:**
- Repo: `/Users/nguyenduykhang/kaggle-5days-vibe-coding/3pl-ops-agent/`

**Steps:**
1. Ensure `.gitignore` exists in `3pl-ops-agent/` with entries:
   ```
   .venv/
   .adk/
   __pycache__/
   *.pyc
   .pytest_cache/
   uv.lock
   harness.db
   ```
   If file doesn't exist, create it.

2. Initialize git (if not already): `cd 3pl-ops-agent && git init`

3. Add remote and push:
   ```bash
   cd 3pl-ops-agent
   git add .
   git commit -m "feat: initial 3PL ops agent prototype"
   gh repo create 3pl-ops-agent --public --source=. --remote=origin --push
   ```

4. Verify: `gh repo view im-khang/3pl-ops-agent --web` should open public repo.

**Verification:**
- Run: `git remote -v` shows origin pointing to GitHub
- Run: `gh repo view im-khang/3pl-ops-agent` shows repo details
- Confirm README renders on GitHub

**Notes:**
- User's GitHub username is `im-khang` (from memory)
- If `gh` not authenticated, run `gh auth login` first (already configured per memory)
- Repo must be public for Kaggle submission

---

### Task 3: Write Spec File (BDD/Gherkin Style)

**Objective:** Create `3pl-ops-agent/specs/3pl_ops_report.md` following Day 5 spec-driven principles.

**Files:**
- Create: `3pl-ops-agent/specs/3pl_ops_report.md`

**Content structure:**
```markdown
# 3PL Ops Report Agent Spec

## One-Line Problem Statement
Given raw 3PL shipment rows, the agent enriches each order (Area, Route, SLA, leadtime, on-time flags) per the case rules, computes per-3PL on-time and cost/leadtime KPIs, and produces a cited carrier-performance report — with a verifier loop that recomputes derived fields and blocks any output that fails the rules.

## Input Contract
- Source: Excel workbook `e13_excel_case_on_3pl_performance_management.xlsx`, sheet "Raw data"
- Required columns: order_id, shipment_type, logistic_status, seller_state, buyer_state, seller_city, buyer_city, seller_area, buyer_area, pickup_done, delivery_done, return_initiated, returned, weight_kg, route, estimated_shipping_fee

## Output Contract
- Cited carrier-performance report with per-3PL KPIs:
  - % pickup on-time
  - % delivery on-time
  - % return on-time
  - Average leadtime (hours)
  - Average shipping fee per route (VND)

## Gherkin Scenarios (Q1–Q4 Rules)

### Q1: Area and Route Derivation
Given a shipment with seller_city="Ho Chi Minh City" and buyer_city="Da Nang"
And carrier="Shipping Carrier A"
When derive_route is called
Then Route should be "A-HCMC-DAD" (or similar matrix pattern)
And Area should be "URBAN" if both cities are urban, else "RURAL"

### Q2: SLA Determination
Given a shipment with Area="URBAN" and shipment_type="pickup"
When compute_sla is called
Then SLA_hours should equal the value from the SLA leadtime table (urban-pickup value)

### Q3: On-Time Flags
Given a shipment with actual_time=100 hours and SLA=120 hours
When check_ontime is called
Then on_time should be True (actual ≤ SLA)

### Q4: KPI Aggregation
Given enriched data for Shipping Carrier A with:
- 1000 total shipments
- 950 delivered on-time
- 50 failed deliveries
- average leadtime = 24.5 hours
When compute_kpis is called
Then %delivery_on-time = 95.0%
And %shortage_rate = 5.0%
And avg_leadtime_hours = 24.5

## Success Criteria
1. Enrichment accuracy ≥ 99% vs golden sample (100 rows)
2. Verifier catches 100% of seeded errors (wrong SLA, on-time, route)
3. KPI table reproduces spreadsheet formulas within ±0.1% rounding tolerance
4. Every number in final report cites source rows (no hallucinations)

## Out of Scope (for M5 build)
- Q4b charting/visual dashboards
- Live API ingestion or multi-user deployment
- MCP server packaging
- Predictive/ML forecasting
```

**Verification:**
- File exists at `3pl-ops-agent/specs/3pl_ops_report.md`
- Contains all 4 Q sections with Gherkin Given-When-Then
- Success criteria match decisions.md

---

### Task 4: Encode Q1–Q4 Rules as Deterministic Functions (rules.py)

**Objective:** Create `3pl-ops-agent/rules.py` with pure functions implementing Q1–Q4 case rules.

**Files:**
- Create: `3pl-ops-agent/rules.py`

**Functions to implement:**

```python
# Reference data from workbook Question 1 & 2 sheets
URBAN_CITIES = {"Hanoi", "Ho Chi Minh City", "Da Nang", "Hai Phong", "Can Tho", ...}
# Full list from Q1 "Area definition" table

ROUTE_MATRIX = {
    # (carrier, origin_city_pattern, dest_city_pattern) -> route_code
    # Extract from Q1 Route definition matrix
}

SLA_TABLE = {
    # (area, shipment_type) -> hours
    # From Q2 SLA leadtime table
    ("URBAN", "pickup"): 48,
    ("URBAN", "dropoff"): 72,
    ("RURAL", "pickup"): 72,
    ("RURAL", "dropoff"): 96,
    # ... plus return SLA rules
}

def classify_area(city: str) -> str:
    """Return 'URBAN' if city in urban list, else 'RURAL'."""

def derive_route(carrier: str, origin_city: str, dest_city: str) -> str:
    """Return route code (e.g., 'A-HCMC-DAD') per matrix."""

def compute_sla(area: str, shipment_type: str, has_return: bool = False) -> int:
    """Return SLA hours from table."""

def compute_leadtime_hours(pickup_timestamp: float, delivery_timestamp: float) -> float:
    """Return (delivery - pickup) * 24 (Excel serial hours)."""

def check_ontime(actual_hours: float, sla_hours: int) -> bool:
    """Return True if actual ≤ SLA, else False."""

def compute_on_time_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized: add columns pickup_ontime, delivery_ontime, return_ontime."""

def aggregate_carrier_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Return per-carrier KPIs: shipment_count, delivered_count, failed_count,
    avg_leadtime, %pickup_ontime, %delivery_ontime, %return_ontime, avg_shipping_fee."""
```

**Data loading:** Read reference tables from the same Excel workbook, separate sheets "Question 1" and "Question 2". Cache as module-level constants.

**Verification:**
- Import rules module: `python -c "import rules; print(rules.classify_area('Ho Chi Minh City'))"` outputs "URBAN"
- Write unit tests in `tests/unit/test_rules.py` covering each function with sample inputs from the workbook.

**Commit:**
- `git add rules.py tests/unit/test_rules.py`
- `git commit -m "feat: add deterministic Q1-Q4 rules in rules.py"`

---

## Execution Order

Tasks 1, 2, 3, 4 can run in parallel (no file conflicts). Task 1 edits vault file (outside repo), others modify repo files. After all complete, run integration check:

**Integration check:**
- Read decisions.md — D1 locked
- GitHub repo exists and is public
- Spec file exists with all sections
- rules.py imports without error, basic tests pass

If any task fails, re-dispatch fix subagent.

---

## Next Phase (M5 Tasks Remaining)

After Phase 1 complete, continue with:

5. Build `rule_verifier` that recomputes all derived fields from rules.py and compares with agent output
6. Create golden sample (100 verified rows) + seeded error test set
7. Prove verifier catches 100% seeded errors
8. Implement `enrich_batch` worker function (Flash model call for Area/Route/SLA/leadtime/on-time)
9. Prove enrichment ≥99% vs golden sample
10. Implement orchestrator with planning, batch routing, bounded retry
11. Implement `compute_kpis` aggregate stage
12. Run full end-to-end loop with trace logging
13. Tool minimalism audit

---

## Definition of Done for Phase 1

- [ ] decisions.md D1 locked with problem statement and metrics
- [ ] GitHub repo `im-khang/3pl-ops-agent` public and pushed
- [ ] Spec file `specs/3pl_ops_report.md` exists with BDD scenarios
- [ ] `rules.py` implements all Q1–Q4 functions with reference data loaded
- [ ] Unit tests for rules pass (`pytest tests/unit/test_rules.py -v`)
- [ ] Integration check passes (all components present)

Proceed to Phase 2 only after Phase 1 done.