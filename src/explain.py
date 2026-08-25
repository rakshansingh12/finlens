"""
Evidence-grounded explanation layer.

The LLM performs no calculation and receives no data beyond the compiled
evidence object. Its only task is turning structured numbers into prose.
Output is then verified against the evidence by the faithfulness checker.
"""

import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL = "gemini-3.6-flash"

SYSTEM_PROMPT = """You are a financial analysis explainer. You explain quantitative \
results that have already been computed. You do not compute anything yourself.

STRICT RULES:
1. Use ONLY numbers that appear in the provided evidence JSON. Never calculate, \
estimate, infer, or round a number that is not literally present.
2. If you want to express a difference or comparison, use the pre-computed values \
in "comparisons_vs_baseline". Do not perform subtraction yourself.
3. Never recommend specific financial products, lenders, stocks, or funds.
4. Never claim certainty about future outcomes. Simulated probabilities are \
model outputs under stated assumptions, not forecasts.
5. State the caveat about absolute probabilities where relevant.
6. Do not present yourself as a licensed financial advisor.

STYLE:
- Plain language, no jargon without explanation.
- 3-5 short paragraphs.
- Lead with the most decision-relevant finding.
- Describe trade-offs; do not issue a verdict on what the person should do.
"""


def generate_explanation(evidence: dict, question: str | None = None) -> str:
    """Generate a plain-language explanation of the compiled evidence."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

    client = genai.Client(api_key=api_key)

    user_content = f"EVIDENCE:\n{json.dumps(evidence, indent=2)}"
    if question:
        user_content += f"\n\nThe person asked: {question}"
    else:
        user_content += "\n\nExplain these borrowing options and their trade-offs."

    response = client.models.generate_content(
        model=MODEL,
        contents=user_content,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.2,   # low: this is exposition, not creative writing
        },
    )
    return response.text