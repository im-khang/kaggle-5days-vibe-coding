"""ADK eval wrapper: exposes olist_ops.agent as .agent for ADK cli_eval."""
import importlib

agent = importlib.import_module("olist_ops.agent")
