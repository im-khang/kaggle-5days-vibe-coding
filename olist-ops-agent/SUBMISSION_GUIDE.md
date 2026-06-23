# Kaggle Capstone — Upload Guide + Video Script

## Part 1: Upload Notebook to Kaggle

### Step-by-step

1. Go to https://www.kaggle.com/competitions/vibecoding-agents-capstone-project
2. Click "Join Competition" if not already joined
3. Click "New Notebook" (or "Submit" → "New Notebook")
4. In the notebook editor:
   - Click File → Import Notebook
   - Upload `kaggle_notebook.ipynb` from this repo
   - OR: Create a new notebook and copy-paste cells manually
5. Once imported:
   - Click "Settings" on the right panel
   - Set "Internet" to ON (needed for ADK/BigQuery calls)
   - Set "Environment" → Pip → add: `google-adk>=2.3.0 google-genai python-dotenv`
6. Add cover image:
   - In the notebook settings panel, find "Cover Image"
   - Upload `cover_image.png` from this repo
7. Add GitHub repo link:
   - Edit notebook description (top of page)
   - Add: "GitHub: https://github.com/im-khang/kaggle-5days-vibe-coding"
8. Save → "Commit" (not "Save Version" — use "Commit" to finalize)
9. Make sure visibility is set to "Public"
10. Go back to competition page → "Submit" → select your notebook

### Important: BigQuery credentials on Kaggle

Kaggle notebooks run in a sandboxed environment. To authenticate with BigQuery:

Option A (recommended): Add GCP service account JSON as Kaggle Secret
1. Go to Add-ons → Secrets in the notebook
2. Add a secret named `GOOGLE_APPLICATION_CREDENTIALS` with your service account JSON content
3. In a notebook cell, write the JSON to a temp file and set the env var

Option B: Use `google-cloud-bigquery` with a service account key file uploaded as a dataset

Note: The demo cells in the notebook show cached outputs. For the Kaggle submission,
the notebook should run end-to-end. If BigQuery auth is complex, you can:
- Keep the cached outputs (Kaggle allows notebooks with prior run outputs)
- Add a note: "Outputs are from a live run on 2026-06-23. To reproduce, set up BigQuery credentials."

---

## Part 2: Video Script (3-5 minutes)

### Recording setup

**Tools needed:**
- Screen recorder (QuickTime on macOS: File → New Screen Recording)
- ADK web UI running locally (`uv run adk web --port 8001 .`)
- Browser open on http://localhost:8001 with olist_ops selected
- This script beside you

**Recording tips:**
- Record in a quiet room
- Speak clearly, slightly slower than normal
- Have the ADK web UI loaded and ready BEFORE hitting record
- Practice the demo questions once before recording

---

### Script

**[0:00 — 0:30] Problem statement**

*(Show: README.md or notebook top cell)*

"Hi, I'm Khang. This is my capstone project for the Kaggle 5-Day AI Agents course.

The problem: Olist is Brazil's largest marketplace with 3,000 sellers shipping to 27 states. An ops analyst asking 'which state has the worst delivery and does that hurt reviews' needs to join 6 tables and write complex SQL — every single time.

I built a multi-agent system that answers these questions in natural language, with cited data."

**[0:30 — 1:30] Architecture**

*(Show: Architecture diagram from notebook or README)*

"The system is a 21-agent supply-chain company built on Google ADK 2.3.

At the top is the Chief Supply Chain Officer — the CSCO. It calls 5 departments as tools using the AgentTool pattern. This is important: unlike sub-agent transfer, the CSCO stays in control, can call multiple departments, and synthesizes their answers.

Each department has specialists:
- Fulfillment handles orders, lanes, and geo-routing
- Seller Ops covers performance and risk
- Customer Experience tracks reviews and complaints
- Finance handles payments
- BI does ad-hoc SQL

There's also an Executive Briefing Pipeline — a SequentialAgent with a ParallelAgent inside that gathers KPIs concurrently and synthesizes a briefing."

**[1:30 — 3:00] Live demo (3 questions)**

*(Show: ADK web UI at localhost:8001)*

"Let me show you live. I'll ask three questions."

**Question 1 — single domain:**
*(Type into ADK web UI: "Which customer state has the worst on-time delivery rate? Show bottom 5.")*
"This routes to HeadOfFulfillment, which calls LaneAgent. AL has the worst on-time rate at 76%."

**Question 2 — cross-domain synthesis:**
*(Type: "Do late deliveries get worse review scores? Show the breakdown.")*
"This is where the AgentTool pattern matters. The CSCO calls HeadOfFulfillment for delay buckets AND HeadOfCX for review scores, then synthesizes. Late 8+ days → 79% chance of 1-2 star reviews."

**Question 3 — executive briefing pipeline:**
*(Type: "Give me an executive briefing on Olist marketplace health.")*
"This triggers the ExecutiveBriefingPipeline — a deterministic SequentialAgent. Parallel KPI collectors gather from 3 departments concurrently, then a SynthesisAgent produces the briefing. 91.88% on-time overall, but delays tank reviews."

**[3:00 — 3:45] Evaluation**

*(Show: eval results table from notebook)*

"I built 4 custom eval metrics: tool use quality, grounded response, intent satisfaction, and SQL safety. All 17 test cases pass — including cross-domain synthesis, executive briefing, and out-of-scope refusal."

**[3:45 — 4:15] Design decisions**

*(Show: design rationale section)*

"Key decisions: AgentTool over sub-agent transfer for synthesis. Specialist tools over raw SQL for safety — every query is SELECT-only with a 10 GB billing cap. And honesty about data gaps — the agent says 'Olist has no carrier_id' instead of hallucinating."

**[4:15 — 4:30] Closing**

*(Show: GitHub repo page)*

"The full code is on GitHub at github.com/im-khang/kaggle-5days-vibe-coding. Thanks for watching."

---

### After recording

1. Trim if needed (keep under 5 minutes)
2. Export as MP4
3. Upload to YouTube as unlisted (or public)
4. In Kaggle notebook: Edit → Media → Add video URL
5. OR: Attach video file directly if Kaggle supports it

---

## Checklist before submit

- [ ] Notebook uploaded to Kaggle and runs (or has cached outputs)
- [ ] Cover image attached
- [ ] GitHub repo link in notebook description
- [ ] Video recorded and attached
- [ ] Notebook set to Public
- [ ] Submitted via competition page before July 6 2026 11:59 PM PT
