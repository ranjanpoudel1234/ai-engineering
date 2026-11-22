"""
ToolSearch.py - Tool Search Examples
Based on: https://developers.openai.com/api/docs/guides/tools-tool-search

NOTE: The official guide requires the Responses API (client.responses.create) with gpt-5.5+.
Azure OpenAI does not support the Responses API or gpt-5.5.

This file demonstrates the SAME CONCEPTS using Azure OpenAI Chat Completions:
  - Hosted tool search (simulated via namespace + deferred tool resolution)
  - Client-executed tool search (simulated via two-round-trip tool dispatch)

Each example shows:
  1. The original guide code (commented out)
  2. An Azure-compatible implementation that achieves the same result
"""

import sys
import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)
MODEL = os.environ["AZURE_OPENAI_DEPLOYMENT"]

SEPARATOR = "=" * 60


def section(title: str):
    print(f"\n{SEPARATOR}\n{title}\n{SEPARATOR}")


# ---------------------------------------------------------------------------
# CONCEPT: Tool Search
# ---------------------------------------------------------------------------
# Tool search lets the model discover which tools it needs at runtime rather
# than loading every tool upfront. This is useful when you have many tools
# (e.g. a large CRM suite) and only a subset are needed for any given query.
#
# Two modes:
#   1. Hosted tool search  – the server resolves which tools to load
#   2. Client tool search  – your app resolves which tools to load (returned
#                            via a tool_search_output message)
#
# Original Responses API pattern:
#
#   response = client.responses.create(
#       model="gpt-5.5",
#       input="...",
#       tools=[namespace_definition, {"type": "tool_search"}],
#       parallel_tool_calls=False,
#   )
#
# The response output contains items with .type in:
#   "tool_search_call"   – the model searched for tools
#   "tool_search_output" – the resolved tool list
#   "function_call"      – the model is calling a resolved tool
# ---------------------------------------------------------------------------


# ===========================================================================
# EXAMPLE 1 – Hosted Tool Search (Azure Chat Completions equivalent)
# ===========================================================================
#
# Original guide code (requires Responses API + gpt-5.5):
#
# from openai import OpenAI
# client = OpenAI()
#
# crm_namespace = {
#     "type": "namespace",
#     "name": "crm",
#     "description": "CRM tools for customer lookup and order management.",
#     "tools": [
#         {
#             "type": "function",
#             "name": "get_customer_profile",
#             "description": "Fetch a customer profile by customer ID.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {"customer_id": {"type": "string"}},
#                 "required": ["customer_id"],
#                 "additionalProperties": False,
#             },
#         },
#         {
#             "type": "function",
#             "name": "list_open_orders",
#             "description": "List open orders for a customer ID.",
#             "defer_loading": True,   # <-- key: only load if searched
#             "parameters": {
#                 "type": "object",
#                 "properties": {"customer_id": {"type": "string"}},
#                 "required": ["customer_id"],
#                 "additionalProperties": False,
#             },
#         },
#     ],
# }
#
# response = client.responses.create(
#     model="gpt-5.5",
#     input="List open orders for customer CUST-12345.",
#     tools=[crm_namespace, {"type": "tool_search"}],
#     parallel_tool_calls=False,
# )
# print(response.output)
# ---------------------------------------------------------------------------
# The response.output sequence would be:
#   [tool_search_call, tool_search_output, function_call(list_open_orders)]
# ---------------------------------------------------------------------------

section("EXAMPLE 1 – Hosted Tool Search (Azure equivalent)")

# All tools in the CRM namespace (full catalog)
ALL_CRM_TOOLS = {
    "get_customer_profile": {
        "description": "Fetch a customer profile by customer ID.",
        "params": ["customer_id"],
    },
    "list_open_orders": {
        "description": "List open orders for a customer ID.",
        "defer_loading": True,  # deferred – only available after tool search
        "params": ["customer_id"],
    },
    "get_invoice": {
        "description": "Retrieve an invoice by invoice ID.",
        "defer_loading": True,
        "params": ["invoice_id"],
    },
}

# Step 1 – Offer only the eagerly-loaded (non-deferred) tools plus a
#          "tool_search" meta-tool so the model can request deferred ones.
eager_tools = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": meta["description"],
            "parameters": {
                "type": "object",
                "properties": {p: {"type": "string"} for p in meta["params"]},
                "required": meta["params"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
    for name, meta in ALL_CRM_TOOLS.items()
    if not meta.get("defer_loading")
]

tool_search_meta_tool = {
    "type": "function",
    "function": {
        "name": "tool_search",
        "description": (
            "Search for additional CRM tools by describing what you need. "
            "Returns relevant tools from the CRM namespace."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "What you are trying to accomplish.",
                }
            },
            "required": ["goal"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

round1_tools = eager_tools + [tool_search_meta_tool]

messages = [{"role": "user", "content": "List open orders for customer CUST-12345."}]

print("Round 1 – initial request (eager tools + tool_search meta-tool)...")
response1 = client.chat.completions.create(
    model=MODEL, messages=messages, tools=round1_tools
)
msg1 = response1.choices[0].message
messages.append(msg1)

# Simulate tool_search resolution AND handle any direct eager-tool calls
deferred_tools_loaded = []
final_answer_found = False

for tc in msg1.tool_calls or []:
    if tc.function.name == "tool_search":
        args = json.loads(tc.function.arguments)
        print(f"  [tool_search_call] goal='{args['goal']}'")

        # Simulate server resolving which deferred tools match the goal
        resolved = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": meta["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {p: {"type": "string"} for p in meta["params"]},
                        "required": meta["params"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            }
            for name, meta in ALL_CRM_TOOLS.items()
            if meta.get("defer_loading") and "order" in meta["description"].lower()
        ]
        deferred_tools_loaded = resolved
        print(f"  [tool_search_output] loaded {len(resolved)} deferred tool(s):")
        for t in resolved:
            print(f"    - {t['function']['name']}")

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(
                    {
                        "status": "completed",
                        "tools_loaded": [t["function"]["name"] for t in resolved],
                    }
                ),
            }
        )
    elif tc.function.name == "list_open_orders":
        # Model skipped tool_search and called the deferred tool directly
        # (gpt-4o-mini knows what it wants) – treat this as round 2 shortcut
        print(f"  [function_call direct] {tc.function.name}({tc.function.arguments})")
        args = json.loads(tc.function.arguments)
        result = {
            "customer_id": args.get("customer_id", "?"),
            "open_orders": [
                {"order_id": "ORD-001", "item": "Widget A", "status": "Shipped"},
                {"order_id": "ORD-002", "item": "Widget B", "status": "Processing"},
            ],
        }
        messages.append(
            {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)}
        )
        final_answer_found = True
    else:
        # Any other eager tool call – return a generic result
        print(f"  [function_call eager] {tc.function.name}({tc.function.arguments})")
        messages.append(
            {"role": "tool", "tool_call_id": tc.id, "content": json.dumps({"ok": True})}
        )

if final_answer_found or not (msg1.tool_calls):
    # Either model answered directly or called the real tool – just get final response
    response2 = client.chat.completions.create(model=MODEL, messages=messages)
    print("\nFinal answer:")
    print(response2.choices[0].message.content)
else:
    # Step 2 – Re-prompt with the resolved deferred tools now available
    round2_tools = eager_tools + deferred_tools_loaded

    print("\nRound 2 – re-prompt with resolved tools available...")
    response2 = client.chat.completions.create(
        model=MODEL, messages=messages, tools=round2_tools
    )
    msg2 = response2.choices[0].message
    messages.append(msg2)

    # Execute any function calls
    for tc in msg2.tool_calls or []:
        print(f"  [function_call] {tc.function.name}({tc.function.arguments})")
        args = json.loads(tc.function.arguments)
        result = {
            "customer_id": args.get("customer_id", "?"),
            "open_orders": [
                {"order_id": "ORD-001", "item": "Widget A", "status": "Shipped"},
                {"order_id": "ORD-002", "item": "Widget B", "status": "Processing"},
            ],
        }
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            }
        )

    response3 = client.chat.completions.create(model=MODEL, messages=messages)
    print("\nFinal answer:")
    print(response3.choices[0].message.content)


# ===========================================================================
# EXAMPLE 2 – Client-Executed Tool Search (Azure Chat Completions equivalent)
# ===========================================================================
#
# Original guide code (requires Responses API + gpt-5.5):
#
# first_response = client.responses.create(
#     model="gpt-5.5",
#     input="Find the shipping ETA tool first, then use it for order_42.",
#     tools=[
#         {
#             "type": "tool_search",
#             "execution": "client",        # <-- your app handles the search
#             "description": "Find project-specific tools.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {"goal": {"type": "string"}},
#                 "required": ["goal"],
#                 "additionalProperties": False,
#             },
#         }
#     ],
#     parallel_tool_calls=False,
# )
#
# search_call = next(
#     item for item in first_response.output if item.type == "tool_search_call"
# )
#
# # Your app does the actual tool discovery here:
# loaded_tools = [
#     {
#         "type": "function",
#         "name": "get_shipping_eta",
#         "description": "Look up shipping ETA.",
#         "defer_loading": True,
#         "parameters": {
#             "type": "object",
#             "properties": {"order_id": {"type": "string"}},
#             "required": ["order_id"],
#             "additionalProperties": False,
#         },
#     }
#  ]
#
# second_response = client.responses.create(
#     model="gpt-5.5",
#     input=[
#         *first_response.output,
#         {
#             "type": "tool_search_output",
#             "execution": "client",
#             "call_id": search_call.call_id,
#             "status": "completed",
#             "tools": loaded_tools,
#         },
#     ],
# )
# print(second_response.output)
# ---------------------------------------------------------------------------
# In client mode YOUR app decides which tools match the search goal.
# This is useful when tools come from a database, plugin registry, or
# dynamic source that only your app knows about.
# ---------------------------------------------------------------------------

section("EXAMPLE 2 – Client-Executed Tool Search (Azure equivalent)")

# Our fictional tool registry (discovered at runtime by the client app)
TOOL_REGISTRY = {
    "get_shipping_eta": {
        "description": "Look up the shipping ETA for a given order ID.",
        "params": {"order_id": "string"},
    },
    "cancel_order": {
        "description": "Cancel an order by order ID.",
        "params": {"order_id": "string", "reason": "string"},
    },
    "get_return_label": {
        "description": "Generate a return shipping label for an order.",
        "params": {"order_id": "string"},
    },
}


def client_tool_search(goal: str) -> list[dict]:
    """
    Simulates client-side tool discovery.
    In production this might query a DB, call a plugin registry, etc.
    Returns a list of Chat Completions tool schemas.
    """
    keywords = goal.lower().split()
    matches = []
    for name, meta in TOOL_REGISTRY.items():
        if any(kw in meta["description"].lower() for kw in keywords):
            matches.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": meta["description"],
                        "parameters": {
                            "type": "object",
                            "properties": {
                                p: {"type": t} for p, t in meta["params"].items()
                            },
                            "required": list(meta["params"].keys()),
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                }
            )
    return matches


# The client_tool_search meta-tool (offered in round 1)
client_search_tool = {
    "type": "function",
    "function": {
        "name": "client_tool_search",
        "description": (
            "Search for project-specific tools by describing your goal. "
            "Your application will find and return the relevant tools."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "What you are trying to accomplish.",
                }
            },
            "required": ["goal"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

messages2 = [
    {
        "role": "user",
        "content": "Find the shipping ETA tool first, then use it for order_42.",
    }
]

print("Round 1 – model requests client-side tool search...")
resp_a = client.chat.completions.create(
    model=MODEL, messages=messages2, tools=[client_search_tool]
)
msg_a = resp_a.choices[0].message
messages2.append(msg_a)

discovered_tools = []

for tc in msg_a.tool_calls or []:
    if tc.function.name == "client_tool_search":
        args = json.loads(tc.function.arguments)
        print(f"  [tool_search_call] execution=client, goal='{args['goal']}'")

        # YOUR APP does the tool discovery:
        discovered = client_tool_search(args["goal"])
        discovered_tools = discovered
        print(f"  [tool_search_output] your app returned {len(discovered)} tool(s):")
        for t in discovered:
            print(f"    - {t['function']['name']}")

        messages2.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(
                    {
                        "status": "completed",
                        "tools": [t["function"]["name"] for t in discovered],
                    }
                ),
            }
        )

print("\nRound 2 – re-prompt with discovered tools...")
resp_b = client.chat.completions.create(
    model=MODEL, messages=messages2, tools=discovered_tools if discovered_tools else None
)
msg_b = resp_b.choices[0].message
messages2.append(msg_b)

for tc in msg_b.tool_calls or []:
    print(f"  [function_call] {tc.function.name}({tc.function.arguments})")
    args = json.loads(tc.function.arguments)
    result = {
        "order_id": args.get("order_id", "?"),
        "eta": "2026-05-09",
        "carrier": "FedEx",
        "status": "In Transit",
    }
    messages2.append(
        {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)}
    )

resp_c = client.chat.completions.create(model=MODEL, messages=messages2)
print("\nFinal answer:")
print(resp_c.choices[0].message.content)


# ===========================================================================
# EXAMPLE 3 – Namespace-Based Lazy Loading (defer_loading pattern)
# ===========================================================================
# In the Responses API a tool with "defer_loading": True is declared in the
# namespace but NOT sent to the model until tool_search selects it.
#
# We simulate this by keeping two tool pools:
#   - EAGER: always available
#   - DEFERRED: only added after the model explicitly asks for them
#
# This scales to very large tool catalogs without token overhead.

section("EXAMPLE 3 – Namespace / Lazy Loading Pattern")

# Simulate a large namespace with many deferred tools
NAMESPACE_TOOLS = {
    # Eager – always loaded
    "ping": {
        "description": "Check if the service is healthy.",
        "defer": False,
        "params": {},
    },
    # Deferred – only loaded on demand
    "get_repair_estimate": {
        "description": "Get a repair cost estimate for a vehicle by VIN.",
        "defer": True,
        "params": {"vin": "string"},
    },
    "schedule_service": {
        "description": "Schedule a service appointment for a vehicle.",
        "defer": True,
        "params": {"vin": "string", "date": "string"},
    },
    "get_vehicle_history": {
        "description": "Retrieve full service history for a VIN.",
        "defer": True,
        "params": {"vin": "string"},
    },
}


def build_tool_schema(name: str, meta: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": meta["description"],
            "parameters": {
                "type": "object",
                "properties": {p: {"type": t} for p, t in meta["params"].items()},
                "required": list(meta["params"].keys()),
                "additionalProperties": False,
            },
            "strict": True,
        },
    }


eager_ns_tools = [
    build_tool_schema(n, m) for n, m in NAMESPACE_TOOLS.items() if not m["defer"]
]

namespace_search_tool = {
    "type": "function",
    "function": {
        "name": "namespace_tool_search",
        "description": "Search the vehicle-service namespace for tools matching your goal.",
        "parameters": {
            "type": "object",
            "properties": {"goal": {"type": "string"}},
            "required": ["goal"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

messages3 = [
    {"role": "user", "content": "What is the repair estimate for VIN 1HGBH41JXMN109186?"}
]

print("Round 1 – eager tools + namespace search meta-tool...")
r1 = client.chat.completions.create(
    model=MODEL, messages=messages3, tools=eager_ns_tools + [namespace_search_tool]
)
m1 = r1.choices[0].message
messages3.append(m1)

loaded_ns_tools = []

for tc in m1.tool_calls or []:
    if tc.function.name == "namespace_tool_search":
        args = json.loads(tc.function.arguments)
        print(f"  [tool_search_call] goal='{args['goal']}'")

        resolved = [
            build_tool_schema(n, m)
            for n, m in NAMESPACE_TOOLS.items()
            if m["defer"] and any(
                kw in m["description"].lower()
                for kw in args["goal"].lower().split()
            )
        ]
        loaded_ns_tools = resolved
        print(f"  [tool_search_output] resolved: {[t['function']['name'] for t in resolved]}")

        messages3.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps({"loaded": [t["function"]["name"] for t in resolved]}),
            }
        )

print("\nRound 2 – with resolved deferred tools...")
r2 = client.chat.completions.create(
    model=MODEL, messages=messages3, tools=eager_ns_tools + loaded_ns_tools
)
m2 = r2.choices[0].message
messages3.append(m2)

for tc in m2.tool_calls or []:
    print(f"  [function_call] {tc.function.name}({tc.function.arguments})")
    args = json.loads(tc.function.arguments)
    result = {
        "vin": args.get("vin", "?"),
        "estimate": "$1,450.00",
        "items": ["Oil change", "Brake pads", "Air filter"],
    }
    messages3.append(
        {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)}
    )

r3 = client.chat.completions.create(model=MODEL, messages=messages3)
print("\nFinal answer:")
print(r3.choices[0].message.content)

print(f"\n{SEPARATOR}")
print("All ToolSearch examples completed.")
print(SEPARATOR)
