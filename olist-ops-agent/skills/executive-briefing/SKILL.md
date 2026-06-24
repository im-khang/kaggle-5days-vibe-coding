---
name: executive-briefing
description: "Generate a full executive briefing on Olist marketplace supply-chain health by orchestrating parallel KPI collection and synthesis."
allowed-tools: "get_delivery_stats,get_seller_kpis,get_review_breakdown,get_cancel_rate,query_bigquery"
metadata:
  agent: "ChiefSupplyChainOfficer"
  track: "Agents for Business"
---

# Executive Briefing Skill

## When to trigger
- User asks for "executive summary", "health report", "briefing", "overview of operations"
- User asks "how is our supply chain doing?"

## Steps
1. Collect fulfillment KPIs: call `get_delivery_stats()` for overall on-time %, avg delivery days, avg last-mile days.
2. Collect seller KPIs: call `get_seller_kpis(limit=10, min_orders=50, sort_by='on_time_pct', ascending=True)` to identify the riskiest sellers.
3. Collect CX KPIs: call `get_review_breakdown()` for review-score distribution by delay bucket, and `get_cancel_rate()` for cancel trends.
4. Synthesize: combine findings into a structured executive briefing with:
   - Overall health score (good/warning/critical based on on-time % thresholds)
   - Top risks (late sellers, review drops)
   - Recommended actions (seller intervention, lane investigation)

## Output format
Markdown with headers: ## Overall Health, ## Fulfillment, ## Seller Risk, ## Customer Impact, ## Recommendations.

## Pitfalls
- Do NOT hallucinate numbers. Only use tool outputs.
- If a tool returns an error, report "data unavailable for this section" rather than guessing.
- Always disclose Olist dataset caveats (no carrier_id, no returns table).
