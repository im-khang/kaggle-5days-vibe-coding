# Evaluation Datasets

This directory contains evaluation datasets for testing agent behavior.

## Project Eval Dataset

`olist-ops-dataset.json` — 12 cases covering the Olist agent's core domains:

| Case ID | Domain | Tests |
|---------|--------|-------|
| worst_state_ontime | Fulfillment | On-time delivery by state |
| seller_reviews_sp | Seller Ops | Seller reviews by state |
| late_delivery_reviews | CX | Delay vs review correlation |
| payment_mix | Payments | Payment type distribution |
| cancel_rate | CX | Cancellation/unavailable by state |
| schema_orders | Data Analyst | Schema lookup |
| list_tables | Data Analyst | Table listing |
| out_of_scope_refuse | Routing | Out-of-scope refusal |
| freight_by_seller_state | Seller Ops | Freight by seller state |
| worst_sellers_ontime | Seller Ops | Worst sellers with order count |
| avg_days_late | Fulfillment | Days late vs estimate |
| credit_card_installments | Payments | Installment distribution |

## Running the Project Eval

```bash
# Generate traces (requires ADC + GOOGLE_CLOUD_PROJECT)
agents-cli eval generate \
  --dataset tests/eval/datasets/olist-ops-dataset.json \
  --output artifacts/traces/

# Grade with 4 custom metrics
agents-cli eval grade \
  --traces artifacts/traces/ \
  --output artifacts/grade-results/ \
  --config tests/eval/eval_config.yaml
```

## Verified Results (2026-06-29)

```
12/12 cases — all 4 metrics pass (1.0000 mean score, 0 errors)

Metric              | Mean | Stdev
tool_use_quality    | 1.00 | 0.00
grounded_response   | 1.00 | 0.00
intent_satisfaction | 1.00 | 0.00
sql_safety          | 1.00 | 0.00
```

Artifacts: `artifacts/traces/traces_20260629_081004.json`, `artifacts/grade-results/results_20260629_081540.json`

## Dataset Format

Each dataset file follows the Gemini Enterprise Agent Platform Evaluation
dataset format. An eval case may use **either** of two shapes — both are
valid input to `agents-cli eval generate`:

**Shape A — single-prompt case:**

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "prompt": {
        "role": "user",
        "parts": [{"text": "User message"}]
      }
    }
  ]
}
```

**Shape B — continued-conversation case (the "N+1" pattern):**
The case carries prior turns in `agent_data` and the last turn ends with a
user message; `eval generate` appends the next agent response.

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "agent_data": {
        "turns": [
          {
            "turn_index": 0,
            "events": [
              {"author": "user",  "content": {"role": "user",  "parts": [{"text": "First user message"}]}},
              {"author": "agent", "content": {"role": "model", "parts": [{"text": "First agent reply"}]}},
              {"author": "user",  "content": {"role": "user",  "parts": [{"text": "Follow-up user message"}]}}
            ]
          }
        ]
      }
    }
  ]
}
```

## Key Fields

- `eval_cases`: Array of evaluation cases.
- `eval_case_id`: Unique identifier for the evaluation case (optional).
- `prompt`: A single user message — Shape A.
- `agent_data.turns`: Prior conversation turns ending with a user message — Shape B.

## Creating Custom Datasets

You can create custom datasets in two ways:

1. **By Hand**: Copy `basic-dataset.json` as a template and manually add evaluation cases.
2. **Synthesize**: Use the synthetic dataset generation command to generate conversation scenarios:
   ```bash
   agents-cli eval dataset synthesize --count 10
   ```

## Discovering Metrics

You can discover available out-of-the-box evaluation metrics by running:

```bash
agents-cli eval metric list
```

## Beyond Generate and Grade

Once you have a baseline, the eval surface has a few more commands worth knowing about:

- `agents-cli eval compare BASE CAND` — diff two grade-results files (regression check).
- `agents-cli eval analyze RESULTS` — cluster failure modes from a grade-results file.
- `agents-cli eval optimize` — auto-tune your agent's prompts using eval data.

See the [Evaluation Guide](https://google.github.io/agents-cli/guide/evaluation/) for the full surface and metric reference.
