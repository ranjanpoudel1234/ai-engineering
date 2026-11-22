"""
Tool Calling (Function Calling) Playground
==========================================
Examples from: https://developers.openai.com/api/docs/guides/function-calling

Covers ALL examples from the guide:
1.  Basic end-to-end tool calling (get_horoscope)
2.  Pydantic function schema helper
3.  Multiple function calls in one response
4.  Function routing (call_function dispatcher)
5.  Streaming tool calls
6.  Streaming - accumulating argument deltas
7.  Parallel tool calls
8.  Controlling tool choice (auto / required / none / specific)
9.  Strict mode
10. Namespacing tools
11. Multi-turn conversation with tools

Run individual examples by calling them at the bottom of this file.
"""

import os
import sys
import json
import re
from dotenv import load_dotenv

# Ensure stdout can handle all characters on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from openai import AzureOpenAI
from pydantic import BaseModel, Field

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SETUP: Azure OpenAI client
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
)

DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# FAKE IMPLEMENTATIONS  (stand-ins for real external calls)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_horoscope(sign: str) -> str:
    return f"{sign}: Next Tuesday you will befriend a baby otter."


def get_weather(location: str, units: str = "celsius") -> dict:
    fake_data = {
        "Paris, France":   {"temperature": 18, "condition": "Cloudy"},
        "BogotÃ¡, Colombia": {"temperature": 14, "condition": "Rainy"},
        "Tokyo, Japan":    {"temperature": 22, "condition": "Sunny"},
    }
    data = fake_data.get(location, {"temperature": 20, "condition": "Clear"})
    data["units"] = units
    return data


def send_email(to: str, body: str) -> dict:
    print(f"  [send_email] Sending to={to!r}, body={body!r}")
    return {"status": "sent", "to": to}


def get_customer_profile(customer_id: str) -> dict:
    return {"customer_id": customer_id, "name": "Jane Doe", "tier": "Gold"}


def list_open_orders(customer_id: str) -> list:
    return [
        {"order_id": "ORD-001", "item": "Laptop", "status": "processing"},
        {"order_id": "ORD-002", "item": "Mouse",  "status": "shipped"},
    ]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GENERIC DISPATCHER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def call_function(name: str, args: dict):
    """Route a tool call name+args to the correct local function."""
    dispatch = {
        "get_horoscope":       get_horoscope,
        "get_weather":         get_weather,
        "send_email":          send_email,
        "get_customer_profile": get_customer_profile,
        "list_open_orders":    list_open_orders,
    }
    fn = dispatch.get(name)
    if fn is None:
        return {"error": f"Unknown function: {name}"}
    return fn(**args)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 1 â€” Basic end-to-end tool calling (get_horoscope)
# Guide section: "Function tool example"
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_1_basic_tool_call():
    print("\n" + "â•" * 60)
    print("EXAMPLE 1 â€” Basic end-to-end tool call (get_horoscope)")
    print("â•" * 60)

    # Step 1: Define the tool
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_horoscope",
                "description": "Get today's horoscope for an astrological sign.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sign": {
                            "type": "string",
                            "description": "An astrological sign like Taurus or Aquarius",
                        },
                    },
                    "required": ["sign"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
    ]

    messages = [
        {"role": "user", "content": "What is my horoscope? I am an Aquarius."}
    ]

    # Step 2: Prompt the model with tools defined
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        tools=tools,
    )

    # Append assistant message (may contain tool_calls)
    messages.append(response.choices[0].message)

    # Step 3 & 4: Execute each tool call and append results
    for tool_call in response.choices[0].message.tool_calls or []:
        if tool_call.function.name == "get_horoscope":
            args = json.loads(tool_call.function.arguments)
            horoscope = get_horoscope(args["sign"])
            print(f"  [tool result] {horoscope}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"horoscope": horoscope}),
                }
            )

    # Step 5: Get the final model response
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        tools=tools,
    )

    print("Model response:", response.choices[0].message.content)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 2 â€” Pydantic function schema helper
# Guide section: "Defining functions â€” (Optional) pydantic helper"
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_2_pydantic_schema():
    print("\n" + "â•" * 60)
    print("EXAMPLE 2 â€” Pydantic function schema helper")
    print("â•" * 60)

    # The OpenAI Python SDK provides pydantic_function_tool for building schemas.
    # We replicate the same pattern manually for Azure compatibility.
    class GetWeather(BaseModel):
        location: str = Field(..., description="City and country e.g. Bogota, Colombia")
        units: str = Field(..., description="celsius or fahrenheit")  # required for strict mode

    # Build the tool schema from the pydantic model
    schema = GetWeather.model_json_schema()
    # Ensure additionalProperties is False (required for strict mode)
    schema["additionalProperties"] = False

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Retrieves current weather for the given location.",
                "parameters": schema,
                "strict": True,
            },
        }
    ]

    completion = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": "What's the weather like in Paris today?"}],
        tools=tools,
    )

    tool_calls = completion.choices[0].message.tool_calls
    print("Tool calls returned by model:")
    for tc in (tool_calls or []):
        print(f"  name={tc.function.name}, args={tc.function.arguments}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 3 â€” Multiple tool calls in one response
# Guide section: "Handling function calls â€” Sample response with multiple function calls"
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_3_multiple_tool_calls():
    print("\n" + "â•" * 60)
    print("EXAMPLE 3 â€” Multiple tool calls in a single response")
    print("â•" * 60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current temperature for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City and country e.g. BogotÃ¡, Colombia",
                        },
                        "units": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature units",
                        },
                    },
                    "required": ["location", "units"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Send an email to a recipient.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to":   {"type": "string", "description": "Recipient email"},
                        "body": {"type": "string", "description": "Email body text"},
                    },
                    "required": ["to", "body"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    ]

    messages = [
        {
            "role": "user",
            "content": (
                "What's the weather in Paris and BogotÃ¡ (in celsius)? "
                "Then email alice@example.com with a short weather summary."
            ),
        }
    ]

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        tools=tools,
    )

    messages.append(response.choices[0].message)

    # Handle multiple tool calls â€” from the guide's dispatcher pattern
    for tool_call in response.choices[0].message.tool_calls or []:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        result = call_function(name, args)
        print(f"  [{name}] result â†’ {result}")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": str(result),
        })

    # Final response from the model
    final = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        tools=tools,
    )
    print("Model response:", final.choices[0].message.content)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 4 â€” call_function dispatcher pattern
# Guide section: "Handling function calls â€” call_function routing helper"
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_4_dispatcher_pattern():
    print("\n" + "â•" * 60)
    print("EXAMPLE 4 â€” call_function dispatcher pattern")
    print("â•" * 60)

    # Demonstrate the dispatcher with a standalone test
    test_cases = [
        ("get_weather", {"location": "Tokyo, Japan", "units": "celsius"}),
        ("send_email",  {"to": "alice@example.com", "body": "Hello Alice!"}),
        ("get_horoscope", {"sign": "Leo"}),
    ]

    for name, args in test_cases:
        result = call_function(name, args)
        print(f"  call_function({name!r}, {args}) â†’ {result}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 5 â€” Streaming tool calls
# Guide section: "Streaming â€” Streaming function calls"
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_5_streaming_tool_calls():
    print("\n" + "â•" * 60)
    print("EXAMPLE 5 â€” Streaming tool calls")
    print("â•" * 60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current temperature for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City and country e.g. BogotÃ¡, Colombia",
                        }
                    },
                    "required": ["location"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
    ]

    stream = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": "What's the weather like in Paris today?"}],
        tools=tools,
        stream=True,
    )

    print("  Streaming chunks (tool_calls delta):")
    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.tool_calls:
            for tc_delta in delta.tool_calls:
                print(f"    index={tc_delta.index} | args_delta={tc_delta.function.arguments!r}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 6 â€” Accumulating streamed argument deltas
# Guide section: "Streaming â€” Accumulating tool_call deltas"
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_6_accumulate_stream_deltas():
    print("\n" + "â•" * 60)
    print("EXAMPLE 6 â€” Accumulating streamed argument deltas")
    print("â•" * 60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current temperature for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
    ]

    stream = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": "What's the weather like in Paris today?"}],
        tools=tools,
        stream=True,
    )

    # Accumulate deltas â€” exactly as shown in the guide
    final_tool_calls = {}

    for chunk in stream:
        for tool_call in (chunk.choices[0].delta.tool_calls or []) if chunk.choices else []:
            index = tool_call.index

            if index not in final_tool_calls:
                final_tool_calls[index] = tool_call
                # Initialise arguments as empty string so we can append
                final_tool_calls[index].function.arguments = ""

            final_tool_calls[index].function.arguments += (tool_call.function.arguments or "")

    print("  Fully accumulated tool calls:")
    for idx, tc in final_tool_calls.items():
        print(f"    [{idx}] name={tc.function.name}, full_args={tc.function.arguments}")

    # Now execute each accumulated tool call
    for idx, tc in final_tool_calls.items():
        args = json.loads(tc.function.arguments)
        result = call_function(tc.function.name, args)
        print(f"    [{idx}] result â†’ {result}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 7 â€” Parallel tool calls (multiple locations at once)
# Guide section: "Handling function calls â€” parallel tool calls"
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_7_parallel_tool_calls():
    print("\n" + "â•" * 60)
    print("EXAMPLE 7 â€” Parallel tool calls")
    print("â•" * 60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current temperature for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "units":    {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location", "units"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
    ]

    messages = [
        {
            "role": "user",
            "content": "Compare the weather in Paris, BogotÃ¡, and Tokyo in celsius.",
        }
    ]

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        tools=tools,
        parallel_tool_calls=True,   # explicitly enable (default is True)
    )

    messages.append(response.choices[0].message)

    print(f"  Number of parallel tool calls: {len(response.choices[0].message.tool_calls or [])}")

    for tool_call in response.choices[0].message.tool_calls or []:
        args   = json.loads(tool_call.function.arguments)
        result = call_function(tool_call.function.name, args)
        print(f"  â†’ {args['location']}: {result}")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result),
        })

    final = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        tools=tools,
    )
    print("Model response:", final.choices[0].message.content)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 8 â€” Controlling tool_choice
# Guide section: "Controlling when tools are called â€” tool_choice"
# Options: "auto" | "required" | "none" | specific function
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_8_tool_choice():
    print("\n" + "â•" * 60)
    print("EXAMPLE 8 â€” Controlling tool_choice")
    print("â•" * 60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current temperature for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
    ]

    prompt = "What's the weather in Paris?"

    # --- tool_choice="auto" (default: model decides) ---
    resp_auto = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice="auto",
    )
    finish_auto = resp_auto.choices[0].finish_reason
    calls_auto  = resp_auto.choices[0].message.tool_calls
    print(f"  tool_choice='auto'     â†’ finish_reason={finish_auto}, tool_calls={len(calls_auto or [])}")

    # --- tool_choice="required" (model MUST call a tool) ---
    resp_req = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice="required",
    )
    finish_req = resp_req.choices[0].finish_reason
    calls_req  = resp_req.choices[0].message.tool_calls
    print(f"  tool_choice='required' â†’ finish_reason={finish_req}, tool_calls={len(calls_req or [])}")

    # --- tool_choice="none" (model MUST NOT call tools) ---
    resp_none = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice="none",
    )
    finish_none = resp_none.choices[0].finish_reason
    content_none = resp_none.choices[0].message.content
    print(f"  tool_choice='none'     â†’ finish_reason={finish_none}, content={repr(content_none)[:60]}")

    # --- tool_choice=specific function (force a specific tool) ---
    resp_specific = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": "Tell me a joke."}],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "get_weather"}},
    )
    calls_specific = resp_specific.choices[0].message.tool_calls
    print(f"  tool_choice=specific   â†’ tool_calls={[tc.function.name for tc in (calls_specific or [])]}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 9 â€” Strict mode
# Guide section: "Defining functions â€” strict"
# With strict=True the model guarantees arguments match the schema exactly
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_9_strict_mode():
    print("\n" + "â•" * 60)
    print("EXAMPLE 9 â€” Strict mode (schema adherence guaranteed)")
    print("â•" * 60)

    # Strict=True requires all properties to be listed in "required"
    # and "additionalProperties" must be False
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Retrieves current weather for the given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City and country e.g. BogotÃ¡, Colombia",
                        },
                        "units": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Units the temperature will be returned in.",
                        },
                    },
                    "required": ["location", "units"],
                    "additionalProperties": False,
                },
                "strict": True,   # â† key flag
            },
        }
    ]

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": "What's the weather in Paris in celsius?"}],
        tools=tools,
    )

    tc = response.choices[0].message.tool_calls[0]
    args = json.loads(tc.function.arguments)
    print(f"  strict=True  â†’ args={args}")
    print(f"  'location' present: {'location' in args}, 'units' present: {'units' in args}")

    result = get_weather(**args)
    print(f"  weather result: {result}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 10 â€” Namespacing tools
# Guide section: "Defining namespaces"
# Note: namespace type is a Responses API / newer feature.
# We simulate the concept using well-named tool groups in Chat Completions.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_10_namespace_tools():
    print("\n" + "â•" * 60)
    print("EXAMPLE 10 â€” Namespacing tools (CRM domain group)")
    print("â•" * 60)

    # The guide shows namespaces as a Responses API feature.
    # In the Chat Completions API we replicate the concept by prefixing
    # function names with the namespace, matching the guide's intent.
    tools = [
        {
            "type": "function",
            "function": {
                "name": "crm__get_customer_profile",   # namespace prefix
                "description": "Fetch a customer profile by customer ID. (CRM namespace)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string", "description": "The customer ID"},
                    },
                    "required": ["customer_id"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "crm__list_open_orders",       # namespace prefix
                "description": "List open orders for a customer ID. (CRM namespace)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string", "description": "The customer ID"},
                    },
                    "required": ["customer_id"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    ]

    messages = [
        {
            "role": "user",
            "content": "Look up customer CUST-42 and list their open orders.",
        }
    ]

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        tools=tools,
    )

    messages.append(response.choices[0].message)

    # Strip namespace prefix when routing to real functions
    namespace_map = {
        "crm__get_customer_profile": get_customer_profile,
        "crm__list_open_orders":     list_open_orders,
    }

    for tool_call in response.choices[0].message.tool_calls or []:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        fn   = namespace_map.get(name)
        result = fn(**args) if fn else {"error": "unknown"}
        print(f"  [{name}] â†’ {result}")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result),
        })

    final = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        tools=tools,
    )
    print("Model response:", final.choices[0].message.content)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXAMPLE 11 â€” Multi-turn conversation with tools
# Guide section: "Incorporating results" & agentic loop
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def example_11_multi_turn():
    print("\n" + "â•" * 60)
    print("EXAMPLE 11 â€” Multi-turn conversation with tools")
    print("â•" * 60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current temperature for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "units":    {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location", "units"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
    ]

    # Conversation starts
    messages = [
        {"role": "system", "content": "You are a helpful weather assistant."},
        {"role": "user",   "content": "What's the weather in Paris in celsius?"},
    ]

    # Agentic loop â€” keep going until the model stops calling tools
    max_turns = 5
    for turn in range(max_turns):
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=messages,
            tools=tools,
        )

        choice = response.choices[0]
        messages.append(choice.message)

        if choice.finish_reason == "tool_calls":
            for tool_call in choice.message.tool_calls or []:
                args   = json.loads(tool_call.function.arguments)
                result = call_function(tool_call.function.name, args)
                print(f"  Turn {turn+1}: tool={tool_call.function.name}, result={result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })
        else:
            # Model gave a final answer
            print(f"  Final answer (turn {turn+1}): {choice.message.content}")

            # Follow-up user message to show multi-turn
            if turn == 0:
                messages.append({
                    "role": "user",
                    "content": "Now what about Tokyo in fahrenheit?",
                })
            else:
                break   # conversation done


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAIN â€” run all examples
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if __name__ == "__main__":
    examples = [
        ("01", "Basic end-to-end tool call",           example_1_basic_tool_call),
        ("02", "Pydantic schema helper",                example_2_pydantic_schema),
        ("03", "Multiple tool calls",                   example_3_multiple_tool_calls),
        ("04", "call_function dispatcher",              example_4_dispatcher_pattern),
        ("05", "Streaming tool calls",                  example_5_streaming_tool_calls),
        ("06", "Accumulate streamed argument deltas",   example_6_accumulate_stream_deltas),
        ("07", "Parallel tool calls",                   example_7_parallel_tool_calls),
        ("08", "Controlling tool_choice",               example_8_tool_choice),
        ("09", "Strict mode",                           example_9_strict_mode),
        ("10", "Namespaced tools",                      example_10_namespace_tools),
        ("11", "Multi-turn conversation with tools",    example_11_multi_turn),
    ]

    print("OpenAI Function Calling Playground")
    print("Source: https://developers.openai.com/api/docs/guides/function-calling")
    print(f"Model:  {DEPLOYMENT}")
    print()

    for num, label, fn in examples:
        try:
            fn()
        except Exception as exc:
            print(f"\n  [ERROR in example {num} â€” {label}]: {exc}")

    print("\n" + "â•" * 60)
    print("All examples complete.")
    print("â•" * 60)

