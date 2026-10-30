"""Ask Claude to explain a perturbation's top genes using only stored facts.

The prompt holds the perturbation's ranked gene changes and each gene's public
description; Claude interprets them and never computes or adds results.
"""

from anthropic import AsyncAnthropic

MAX_TOKENS = 16_000  # thinking counts toward this limit

SYSTEM = """You explain results from a CRISPR activation screen in K562 cells \
(Norman et al. 2019) to a scientist.
Use only the data in the user message: the perturbation, its top genes with \
their expression changes versus control, and the gene descriptions provided.
Rules:
- Mention only genes that appear in the provided list.
- Do not state numbers that are not in the data.
- If a gene has no description, do not guess its function.
- Say when the data cannot answer something, such as direct versus downstream effects.
Write one paragraph of 4 to 6 sentences."""


def build_prompt(doc: dict, descriptions: dict[str, dict]) -> str:
    """Format a perturbation's top genes and their descriptions for Claude.

    Args:
        doc: Perturbation document from the repository, top genes in rank order.
        descriptions: Gene documents keyed by symbol; missing or null
            summaries are marked as having no description.

    Returns:
        User message listing the perturbation, then one line per top gene
        with its change and description.
    """
    lines = [
        f"Perturbation: {doc['name']} (activated genes: {', '.join(doc['target_genes'])}; "
        f"{doc['cell_count']} cells)",
        "Top genes by absolute change (log-scale average vs control; positive = more active):",
    ]
    for rank, gene in enumerate(doc["top_genes"], start=1):
        info = descriptions.get(gene["gene"], {})
        summary = info.get("summary") or "No description available."
        lines.append(f"{rank}. {gene['gene']} ({gene['change']:+.3f}): {summary}")
    return "\n".join(lines)


async def explain(client: AsyncAnthropic, model: str, effort: str, prompt: str) -> str:
    """Send one grounded prompt to Claude and return its text.

    Args:
        client: Shared Anthropic client.
        model: Claude model ID, such as claude-haiku-5-5.
        effort: Effort level, such as high.
        prompt: User message from build_prompt.

    Returns:
        Claude's answer text, thinking blocks excluded.

    Raises:
        anthropic.APIError: The request fails or times out.
        ValueError: Claude returned no text.
    """
    message = await client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        output_config={"effort": effort},
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in message.content if block.type == "text").strip()
    if not text:
        raise ValueError(f"Claude returned no text (stop_reason={message.stop_reason})")
    return text
