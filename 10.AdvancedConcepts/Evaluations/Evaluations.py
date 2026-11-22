"""
Evaluations (Evals) Playground
===============================
Inspired by: https://developers.openai.com/api/docs/guides/evals

This file teaches the core concepts of LLM evaluation by implementing
a LOCAL eval framework that mirrors the OpenAI Evals API concepts —
adapted for Azure OpenAI (which does not expose the Evals API directly).

The same 3-step process from the guide:
  1. Define the eval  (task + graders)
  2. Run the eval     (supply test data + a prompt, get model outputs)
  3. Analyze results  (compare outputs to ground truth, score, report)

Topics covered:
  1.  What is an eval and why it matters
  2.  Defining test datasets (JSONL-style items with ground truth labels)
  3.  String-check grader  (exact match — mirrors OpenAI's string_check)
  4.  LLM-as-judge grader  (model grades open-ended output — mirrors model_graded_rubric)
  5.  Running an eval loop  (generate model outputs, grade, collect results)
  6.  Reporting results     (pass/fail counts, per-criteria breakdown)
  7.  Iterating on prompts  (run two prompt variants, compare scores)
"""

import os
import sys
import json
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from openai import AzureOpenAI

# ---------------------------------------------------------------------------
# SETUP: Load env from the sibling ToolCalling folder (same credentials)
# ---------------------------------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), "..", "03.ToolCalling", ".env")
load_dotenv(dotenv_path=os.path.abspath(env_path))

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
)

DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


# ===========================================================================
# SECTION 1 — What is an Eval?
# ===========================================================================
#
# An eval is a structured test that runs your prompt against known inputs
# and checks whether the model output meets your criteria.
#
# Key concepts that map to the OpenAI Evals API:
#
#   item           → one row of test data (input + ground truth)
#   sample         → the model's output for that item
#   grader         → a function that compares sample to ground truth
#   eval run       → looping over all items, grading each one
#   result_counts  → { total, passed, failed }
#
# The OpenAI Evals API manages this server-side (async, scalable).
# Here we implement the same ideas locally so you can see every step.
# ===========================================================================


# ===========================================================================
# SECTION 2 — Test Dataset
# ===========================================================================
#
# In the guide, test data is a JSONL file:
#   { "item": { "ticket_text": "...", "correct_label": "Hardware" } }
#
# We represent the same thing as Python dicts below.
# Each dict has "input" (what the model sees) and "expected" (ground truth).
# ===========================================================================

IT_TICKET_DATASET = [
    # --- clear-cut hardware tickets ---
    {"ticket_text": "My monitor won't turn on!", "correct_label": "Hardware"},
    {"ticket_text": "The keyboard is missing two keycaps.", "correct_label": "Hardware"},
    {"ticket_text": "My laptop fan is making a grinding noise.", "correct_label": "Hardware"},
    {"ticket_text": "The printer keeps jamming on the first sheet.", "correct_label": "Hardware"},
    # --- software tickets ---
    {"ticket_text": "I'm in vim and I can't quit!", "correct_label": "Software"},
    {"ticket_text": "Excel crashes every time I open a .xlsx file.", "correct_label": "Software"},
    {"ticket_text": "VPN client won't connect — shows error 800.", "correct_label": "Software"},
    {"ticket_text": "My browser extensions disappeared after the update.", "correct_label": "Software"},
    # --- off-topic / other ---
    {"ticket_text": "Best restaurants near the office?", "correct_label": "Other"},
    {"ticket_text": "How do I book a conference room?", "correct_label": "Other"},
]

# A tiny sentiment dataset to demonstrate a second eval use-case
SENTIMENT_DATASET = [
    {"review": "Absolutely love this product, works perfectly!", "correct_label": "Positive"},
    {"review": "Terrible quality, broke on day one.", "correct_label": "Negative"},
    {"review": "It's okay, nothing special.", "correct_label": "Neutral"},
    {"review": "Best purchase I've made all year!", "correct_label": "Positive"},
    {"review": "Would not recommend — way too expensive for what you get.", "correct_label": "Negative"},
]


# ===========================================================================
# SECTION 3 — Graders
# ===========================================================================
#
# A grader takes a model output (sample) and the expected value,
# then returns True/False (pass/fail).
#
# OpenAI Evals API has built-in grader types:
#   string_check        → exact string comparison (eq, contains, starts_with, …)
#   model_graded_rubric → a second model judges the output using a rubric
#
# We implement both below.
# ===========================================================================

def string_check_grader(sample_output: str, expected: str, operation: str = "eq") -> bool:
    """
    Mirrors the OpenAI 'string_check' grader.

    operation options:
      'eq'           → exact match (case-insensitive)
      'contains'     → sample contains expected substring
      'starts_with'  → sample starts with expected string
    """
    sample  = sample_output.strip()
    ref     = expected.strip()

    if operation == "eq":
        return sample.lower() == ref.lower()
    elif operation == "contains":
        return ref.lower() in sample.lower()
    elif operation == "starts_with":
        return sample.lower().startswith(ref.lower())
    else:
        raise ValueError(f"Unknown string_check operation: {operation}")


def llm_as_judge_grader(
    sample_output: str,
    expected: str,
    question: str,
    rubric: str,
) -> tuple[bool, str]:
    """
    Mirrors the OpenAI 'model_graded_rubric' grader concept.

    A second model call grades the primary output using a rubric.
    Returns (passed: bool, reasoning: str).

    This is useful when the output is free-form and can't be exact-matched.
    """
    judge_prompt = f"""You are an impartial grader evaluating an AI assistant's answer.

Question asked: {question}
Expected answer: {expected}
Model's answer: {sample_output}

Rubric: {rubric}

Does the model's answer satisfy the rubric? Reply with EXACTLY one word: PASS or FAIL.
Then on the next line, give a one-sentence explanation."""

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": judge_prompt}],
        max_tokens=100,
        temperature=0,
    )

    verdict_text = response.choices[0].message.content.strip()
    first_line = verdict_text.split("\n")[0].strip().upper()
    passed = first_line == "PASS"
    reasoning = verdict_text
    return passed, reasoning


# ===========================================================================
# SECTION 4 — Running an Eval
# ===========================================================================
#
# An eval run loops over every item in the dataset:
#   1. Build the prompt from the item  (template substitution)
#   2. Call the model  (generate a "sample")
#   3. Grade the sample against the ground truth
#   4. Record pass/fail + details
#
# The OpenAI Evals API does this server-side; here we do it in a loop.
# ===========================================================================

def run_eval(
    eval_name: str,
    dataset: list[dict],
    system_prompt_template: str,
    user_message_key: str,
    expected_key: str,
    grader_fn,
    delay_seconds: float = 0.3,
) -> dict:
    """
    Generic eval runner.

    Parameters
    ----------
    eval_name              : Display name for this eval run
    dataset                : List of dicts (each is one test item)
    system_prompt_template : System / developer message (can be a plain string)
    user_message_key       : Key in the item dict to use as the user message
    expected_key           : Key in the item dict holding the ground truth
    grader_fn              : Callable(sample_output, expected) -> bool
    delay_seconds          : Polite pause between API calls (avoids rate limits)

    Returns
    -------
    A results dict mirroring the OpenAI eval run response structure.
    """
    print(f"\n{'=' * 60}")
    print(f"EVAL RUN: {eval_name}")
    print(f"Dataset size: {len(dataset)} items  |  Model: {DEPLOYMENT}")
    print(f"{'=' * 60}")

    results = []

    for idx, item in enumerate(dataset):
        user_msg = item[user_message_key]
        expected = item[expected_key]

        # Generate model output  (the "sample" in OpenAI's terminology)
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt_template},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=20,
            temperature=0,   # deterministic for evals
        )

        sample_output = response.choices[0].message.content.strip()
        passed        = grader_fn(sample_output, expected)

        result = {
            "index":         idx,
            "input":         user_msg,
            "expected":      expected,
            "sample_output": sample_output,
            "passed":        passed,
        }
        results.append(result)

        status = "PASS" if passed else "FAIL"
        print(f"  [{idx+1:02d}] {status}  |  expected={expected!r:12}  got={sample_output!r}")

        time.sleep(delay_seconds)   # rate-limit courtesy

    # Aggregate (mirrors OpenAI's result_counts)
    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    result_counts = {"total": total, "passed": passed, "failed": failed}

    print(f"\n--- Results for '{eval_name}' ---")
    print(f"  Total : {total}")
    print(f"  Passed: {passed}  ({100*passed//total}%)")
    print(f"  Failed: {failed}")

    if failed:
        print("\n  Failures:")
        for r in results:
            if not r["passed"]:
                print(f"    input={r['input']!r}")
                print(f"      expected={r['expected']!r}  got={r['sample_output']!r}")

    return {
        "eval_name":     eval_name,
        "result_counts": result_counts,
        "items":         results,
    }


# ===========================================================================
# SECTION 5 — Prompt Iteration
# ===========================================================================
#
# One of the most powerful uses of evals is comparing two prompt variants
# to see which one performs better. This maps to creating multiple eval
# runs against the same dataset in the OpenAI Evals API.
# ===========================================================================

def compare_prompts(
    eval_name_prefix: str,
    dataset: list[dict],
    prompts: dict[str, str],   # {label: system_prompt}
    user_message_key: str,
    expected_key: str,
    grader_fn,
) -> None:
    """
    Run the same dataset against multiple prompt variants and compare scores.
    """
    scores = {}
    for label, prompt in prompts.items():
        run_result = run_eval(
            eval_name=f"{eval_name_prefix} [{label}]",
            dataset=dataset,
            system_prompt_template=prompt,
            user_message_key=user_message_key,
            expected_key=expected_key,
            grader_fn=grader_fn,
        )
        counts = run_result["result_counts"]
        scores[label] = counts["passed"] / counts["total"]

    print(f"\n{'=' * 60}")
    print("PROMPT COMPARISON SUMMARY")
    print(f"{'=' * 60}")
    for label, score in sorted(scores.items(), key=lambda x: -x[1]):
        bar = "#" * int(score * 30)
        print(f"  {label:<25} {score*100:5.1f}%  [{bar}]")

    best = max(scores, key=scores.get)
    print(f"\n  Winner: {best}")


# ===========================================================================
# SECTION 6 — Full Worked Examples
# ===========================================================================

def example_1_it_ticket_categorization():
    """
    Exact replica of the OpenAI Evals guide example:
    Classify IT support tickets → Hardware | Software | Other
    Uses a string_check grader (exact match).
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 1 — IT Ticket Categorization (string_check grader)")
    print("=" * 60)

    system_prompt = (
        'You are an expert in categorizing IT support tickets. '
        'Given the support ticket below, categorize the request into '
        'one of "Hardware", "Software", or "Other". '
        'Respond with only one of those three words.'
    )

    grader = lambda output, expected: string_check_grader(output, expected, operation="eq")

    run_eval(
        eval_name="IT Ticket Categorization",
        dataset=IT_TICKET_DATASET,
        system_prompt_template=system_prompt,
        user_message_key="ticket_text",
        expected_key="correct_label",
        grader_fn=grader,
    )


def example_2_sentiment_analysis():
    """
    Evaluate a sentiment classifier: Positive | Negative | Neutral.
    Also uses a string_check grader.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2 — Sentiment Analysis (string_check grader)")
    print("=" * 60)

    system_prompt = (
        "Classify the sentiment of the customer review below. "
        "Reply with exactly one word: Positive, Negative, or Neutral."
    )

    grader = lambda output, expected: string_check_grader(output, expected, operation="eq")

    run_eval(
        eval_name="Sentiment Analysis",
        dataset=SENTIMENT_DATASET,
        system_prompt_template=system_prompt,
        user_message_key="review",
        expected_key="correct_label",
        grader_fn=grader,
    )


def example_3_llm_as_judge():
    """
    Demonstrate an LLM-as-judge grader for free-form outputs.
    We ask the model to explain a concept, then a second model call
    grades whether the explanation is accurate and clear.

    This mirrors OpenAI's 'model_graded_rubric' grader type.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3 — LLM-as-Judge Grader (model_graded_rubric style)")
    print("=" * 60)

    qa_dataset = [
        {
            "question": "What is prompt injection?",
            "correct_answer": "A technique where malicious input overrides the system prompt to hijack model behavior.",
            "rubric": "The answer must mention overriding or hijacking model instructions via user input. Correct regardless of extra details.",
        },
        {
            "question": "What does RAG stand for and what is it used for?",
            "correct_answer": "Retrieval-Augmented Generation — combining retrieval of relevant documents with LLM generation to ground answers in real data.",
            "rubric": "Must include Retrieval-Augmented Generation (or the acronym expansion) and mention grounding answers in external/retrieved data.",
        },
        {
            "question": "What is the capital of Australia?",
            "correct_answer": "Canberra",
            "rubric": "The answer must identify Canberra as the capital. Sydney is a common wrong answer — that should fail.",
        },
    ]

    system_prompt = "You are a helpful AI assistant. Answer concisely in 1-2 sentences."

    print(f"  Dataset: {len(qa_dataset)} Q&A items  |  Grader: LLM-as-judge\n")

    passed_count = 0
    for idx, item in enumerate(qa_dataset):
        question = item["question"]
        expected = item["correct_answer"]
        rubric   = item["rubric"]

        # Step 1: Get model answer
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": question},
            ],
            max_tokens=100,
            temperature=0,
        )
        model_answer = response.choices[0].message.content.strip()

        # Step 2: Grade with LLM judge
        passed, reasoning = llm_as_judge_grader(
            sample_output=model_answer,
            expected=expected,
            question=question,
            rubric=rubric,
        )

        status = "PASS" if passed else "FAIL"
        if passed:
            passed_count += 1

        print(f"  [{idx+1}] {status}  Q: {question}")
        print(f"       Model: {model_answer}")
        print(f"       Judge: {reasoning.split(chr(10))[0]}")
        print()

        time.sleep(0.5)

    total = len(qa_dataset)
    print(f"  Results: {passed_count}/{total} passed  ({100*passed_count//total}%)")


def example_4_prompt_comparison():
    """
    Run two different prompt variants against the same IT ticket dataset
    and compare which prompt scores higher.

    This is the core eval workflow: iterate on prompts, measure improvement.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 4 — Prompt Comparison (iterate to improve)")
    print("=" * 60)

    # Variant A: vague prompt
    prompt_a = (
        "Categorize the following IT support ticket. "
        "Use one of: Hardware, Software, or Other."
    )

    # Variant B: more explicit prompt with examples
    prompt_b = (
        'You are an IT support ticket classifier. '
        'Classify each ticket into exactly one of these three categories:\n'
        '  - Hardware: physical device issues (monitors, keyboards, printers, etc.)\n'
        '  - Software: application, OS, or driver problems\n'
        '  - Other: anything not hardware or software related\n\n'
        'Respond with only one word: Hardware, Software, or Other.'
    )

    grader = lambda output, expected: string_check_grader(output, expected, operation="eq")

    compare_prompts(
        eval_name_prefix="IT Ticket",
        dataset=IT_TICKET_DATASET,
        prompts={"Prompt A (vague)": prompt_a, "Prompt B (detailed)": prompt_b},
        user_message_key="ticket_text",
        expected_key="correct_label",
        grader_fn=grader,
    )


# ===========================================================================
# MAIN — Run all examples
# ===========================================================================

if __name__ == "__main__":
    examples = [
        ("01", "IT Ticket Categorization (string_check)",     example_1_it_ticket_categorization),
        ("02", "Sentiment Analysis (string_check)",            example_2_sentiment_analysis),
        ("03", "LLM-as-Judge Grader",                         example_3_llm_as_judge),
        ("04", "Prompt Comparison (iterate to improve)",       example_4_prompt_comparison),
    ]

    print("OpenAI Evals Guide — Local Implementation")
    print("Guide: https://developers.openai.com/api/docs/guides/evals")
    print(f"Model: {DEPLOYMENT}")
    print()
    print("NOTE: This uses Azure OpenAI (which does not expose the Evals API).")
    print("      All eval logic is implemented locally using the same concepts.")
    print()

    for num, label, fn in examples:
        try:
            fn()
        except Exception as exc:
            print(f"\n  [ERROR in example {num} — {label}]: {exc}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All eval examples complete.")
    print("=" * 60)
