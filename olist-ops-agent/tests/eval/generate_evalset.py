from google.adk.evaluation.eval_set import EvalSet
from google.adk.evaluation.eval_case import EvalCase, Invocation
from google.genai import types
from pathlib import Path

cases = [
    ('worst_state_ontime', 'Which state has the worst on-time delivery?'),
    ('seller_reviews_sp', 'Average review score for sellers in SP?'),
    ('late_delivery_reviews', 'Do late deliveries get worse reviews?'),
    ('payment_mix', 'What payment types are most common?'),
    ('cancel_rate', 'How many orders were canceled or unavailable by state?'),
    ('schema_orders', 'Show me the schema of the orders table.'),
    ('list_tables', 'List the tables and views in this dataset.'),
    ('out_of_scope_refuse', "What's the weather in Hanoi today?"),
    ('freight_by_seller_state', 'Average freight value by seller state.'),
    ('worst_sellers_ontime', 'Worst 5 sellers by on-time rate, with their order counts.'),
    ('avg_days_late', 'Average days late vs estimate overall.'),
    ('credit_card_installments', 'Installment distribution for credit card payments.'),
]

def user_inv(text: str) -> Invocation:
    return Invocation(user_content=types.Content(role='user', parts=[types.Part(text=text)]))

eval_set = EvalSet(
    eval_set_id='olist_cases',
    name='olist_cases',
    description='Olist ecommerce ops eval cases',
    eval_cases=[EvalCase(eval_id=case_id, conversation=[user_inv(text)]) for case_id, text in cases],
)
Path('tests/eval/datasets').mkdir(parents=True, exist_ok=True)
Path('tests/eval/datasets/olist_cases.json').write_text(eval_set.model_dump_json(indent=2, by_alias=True))
