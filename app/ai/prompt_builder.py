from __future__ import annotations


def build_messages(
    system_prompt: str,
    user_content: str,
    few_shot_examples: list[tuple[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Assemble a chat message list: system prompt, then few-shot (input, output)
    pairs modeled as user/assistant turns, then the real user content last.

    RAG context (Phase 7) is folded into `user_content` by the caller rather
    than handled here, since retrieval is orthogonal to message assembly.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    for example_input, example_output in few_shot_examples or []:
        messages.append({"role": "user", "content": example_input})
        messages.append({"role": "assistant", "content": example_output})

    messages.append({"role": "user", "content": user_content})
    return messages
