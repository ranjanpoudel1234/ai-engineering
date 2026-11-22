"""
Instructor Structured Output Playground
========================================
Examples from: https://python.useinstructor.com/getting-started/#working-with-complex-models

Run individual examples by calling them from main() at the bottom.
"""

import os
from dotenv import load_dotenv

load_dotenv()

import instructor
from openai import AzureOpenAI
from pydantic import BaseModel, Field, field_validator
from typing import List

# ─────────────────────────────────────────────────────────────
# SETUP: Azure OpenAI (rome-innovation-dev-openai)
# ─────────────────────────────────────────────────────────────
azure_client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
)

DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

client = instructor.from_openai(azure_client)


# ─────────────────────────────────────────────────────────────
# EXAMPLE 1: Basic Structured Output
# ─────────────────────────────────────────────────────────────
class UserInfo(BaseModel):
    name: str
    age: int


def example_1_basic():
    print("\n" + "=" * 50)
    print("EXAMPLE 1: Basic Structured Output")
    print("=" * 50)

    user_info = client.chat.completions.create(
        model=DEPLOYMENT,
        response_model=UserInfo,
        messages=[
            {"role": "user", "content": "John Doe is 30 years old."}
        ],
    )

    print(f"Name: {user_info.name}, Age: {user_info.age}")
    print(f"Full object: {user_info}")


# ─────────────────────────────────────────────────────────────
# EXAMPLE 2: Validation and Error Handling
# ─────────────────────────────────────────────────────────────
class ValidatedUser(BaseModel):
    name: str
    age: int = Field(gt=0, lt=120)  # Age must be between 0 and 120

    @field_validator("name")
    @classmethod
    def name_must_have_space(cls, v):
        if " " not in v:
            raise ValueError("Name must include first and last name")
        return v


def example_2_validation():
    print("\n" + "=" * 50)
    print("EXAMPLE 2: Validation and Error Handling")
    print("=" * 50)

    # This will make the LLM retry if validation fails (e.g., "Tom" has no last name)
    user = client.chat.completions.create(
        model=DEPLOYMENT,
        response_model=ValidatedUser,
        messages=[
            {"role": "user", "content": "Extract: Tom  is 25 years old."}
        ],
    )

    print(f"Name: {user.name}, Age: {user.age}")
    print("(Note: LLM had to infer a last name since validation requires first + last)")


# ─────────────────────────────────────────────────────────────
# EXAMPLE 3: Complex Nested Models
# ─────────────────────────────────────────────────────────────
class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str


class Person(BaseModel):
    name: str
    age: int
    addresses: List[Address]


def example_3_complex_models():
    print("\n" + "=" * 50)
    print("EXAMPLE 3: Working with Complex Nested Models")
    print("=" * 50)

    person = client.chat.completions.create(
        model=DEPLOYMENT,
        response_model=Person,
        messages=[
            {
                "role": "user",
                "content": """
                Extract: John Smith is 35 years old.
                He has homes at 123 Main St, Springfield, IL 62704 and
                456 Oak Ave, Chicago, IL 60601.
                """,
            }
        ],
    )

    print(f"Name: {person.name}, Age: {person.age}")
    for i, addr in enumerate(person.addresses, 1):
        print(f"  Address {i}: {addr.street}, {addr.city}, {addr.state} {addr.zip_code}")
    print(f"\nFull object:\n{person.model_dump_json(indent=2)}")


# ─────────────────────────────────────────────────────────────
# EXAMPLE 4: Streaming Responses
# ─────────────────────────────────────────────────────────────
def example_4_streaming():
    print("\n" + "=" * 50)
    print("EXAMPLE 4: Streaming Responses")
    print("=" * 50)

    stream = client.chat.completions.create_partial(
        model=DEPLOYMENT,
        response_model=Person,
        messages=[
            {
                "role": "user",
                "content": "Extract a person profile: Jane Doe, 28, lives at 789 Elm St, Austin, TX 73301.",
            }
        ],
    )

    print("Streaming partial results:")
    for partial in stream:
        print(f"  -> {partial}")

    print("\nStreaming complete!")


# ─────────────────────────────────────────────────────────────
# EXAMPLE 5: Your Own Custom Prompt (Playground)
# ─────────────────────────────────────────────────────────────
class ExtractedFact(BaseModel):
    subject: str
    predicate: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0.0 to 1.0")


class FactList(BaseModel):
    facts: List[ExtractedFact]
    summary: str


def example_5_custom_playground():
    print("\n" + "=" * 50)
    print("EXAMPLE 5: Custom Playground - Fact Extraction")
    print("=" * 50)

    text = """
    Tesla was founded in 2003 by Martin Eberhard and Marc Tarpenning.
    Elon Musk joined as chairman of the board in 2004 and became CEO in 2008.
    The company is headquartered in Austin, Texas. In 2023, Tesla delivered
    approximately 1.8 million vehicles worldwide.
    """

    result = client.chat.completions.create(
        model=DEPLOYMENT,
        response_model=FactList,
        messages=[
            {
                "role": "system",
                "content": "You are an expert fact extractor. Extract key facts with subject, predicate, and value.",
            },
            {"role": "user", "content": f"Extract facts from this text:\n{text}"},
        ],
    )

    print(f"Summary: {result.summary}\n")
    print("Extracted facts:")
    for fact in result.facts:
        print(f"  [{fact.confidence:.0%}] {fact.subject} -> {fact.predicate}: {fact.value}")


# ─────────────────────────────────────────────────────────────
# MAIN: Run examples
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Toggle which examples to run
    run_examples = {
        1: True,   # Basic structured output
        2: True,   # Validation & error handling
        3: True,   # Complex nested models
        4: True,  # Streaming (set True to try it)
        5: True,   # Custom playground - fact extraction
    }

    if run_examples.get(1):
        example_1_basic()

    if run_examples.get(2):
        example_2_validation()

    if run_examples.get(3):
        example_3_complex_models()

    if run_examples.get(4):
        example_4_streaming()

    if run_examples.get(5):
        example_5_custom_playground()

    print("\n\nDone! Flip the run_examples flags at the bottom to toggle examples.")
