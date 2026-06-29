from __future__ import annotations


def _generate_feedback_prompt() -> str:
    """Return a concise instruction to halt reasoning and produce a direct answer."""
    return (
        "Your previous response was interrupted due to excessive repetition. "
        "Provide only the final answer now, directly and concisely. "
        "Do not reason, think step-by-step, or output chain-of-thought tokens."
    )
