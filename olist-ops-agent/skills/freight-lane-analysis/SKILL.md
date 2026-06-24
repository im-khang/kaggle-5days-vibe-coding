---
name: freight-lane-analysis
description: "Analyze seller-to-customer freight lanes to identify expensive, slow, or underperforming routes."
allowed-tools: "get_state_pairs,get_lane_performance,get_delivery_stats"
metadata:
  agent: "GeoRoutingAgent"
  track: "Agents for Business"
---

# Freight Lane Analysis Skill

## When to trigger
- User asks about "freight by lane", "expensive routes", "lane optimization", "shipping costs by state pair"
- User asks "which routes are slowest?"

## Steps
1. Get top 100 lanes by volume: `get_state_pairs(limit=100)`.
2. Identify the 10 most expensive lanes (sort by avg_freight descending).
3. Identify the 10 slowest lanes (sort by avg_delivery_days descending).
4. Cross-reference with `get_lane_performance()` to see if slow lanes also have poor on-time %.
5. Present findings as:
   - Most expensive lanes (table: seller_state -> customer_state, orders, avg_freight)
   - Slowest lanes (table: seller_state -> customer_state, orders, avg_delivery_days)
   - Lanes that are BOTH expensive AND slow (highest priority for optimization)
6. Recommend actions:
   - Consider warehouse/hub placement between high-traffic expensive pairs
   - Suggest seller incentives for same-state fulfillment

## Output format
Three markdown tables + a "Recommendations" section.

## Pitfalls
- The geolocation table has ~1M rows. Never request raw geolocation data.
- Olist has no carrier_id. "Lane" means seller_state x customer_state pair.
- Small-volume lanes (< 50 orders) may have noisy averages; note this caveat.
