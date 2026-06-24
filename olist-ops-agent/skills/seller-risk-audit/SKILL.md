---
name: seller-risk-audit
description: "Identify and score risky sellers based on late delivery, poor reviews, and high freight, then recommend interventions."
allowed-tools: "get_seller_kpis,get_review_breakdown,query_bigquery"
metadata:
  agent: "SellerRiskAgent"
  track: "Agents for Business"
---

# Seller Risk Audit Skill

## When to trigger
- User asks about "risky sellers", "seller intervention", "worst performers", "seller health"
- User asks "which sellers should we warn or suspend?"

## Steps
1. Pull bottom 10 sellers by on-time %: `get_seller_kpis(limit=10, min_orders=50, sort_by='on_time_pct', ascending=True)`.
2. Pull bottom 10 sellers by review score: `get_seller_kpis(limit=10, min_orders=50, sort_by='avg_review_score', ascending=True)`.
3. Cross-reference: sellers appearing in BOTH lists are highest risk.
4. For each high-risk seller, compute a risk score: `risk = (100 - on_time_pct) * 0.4 + (5 - avg_review_score) * 30 + (avg_delivery_days / 30) * 30`.
5. Rank by risk score descending.
6. Recommend action per seller:
   - Risk > 80: immediate suspension review
   - Risk 60-80: performance warning + improvement timeline
   - Risk 40-60: monitoring with monthly check-in

## Output format
Markdown table with columns: seller_id, seller_state, orders, on_time_pct, avg_review_score, risk_score, recommended_action.

## Pitfalls
- Always use min_orders >= 50 to avoid flagging new/tiny sellers.
- Do not expose seller_id in external reports without anonymization note.
