"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL
from .prompt_storage import get_prompt_for_model
from . import agent_storage


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council agents.
    Each agent uses their custom prompt, or falls back to model/default prompts.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'agent', 'model', and 'response' keys
    """
    import asyncio

    # Load active agents, or fall back to config models
    agents = agent_storage.get_active_agents()

    # If no agents configured, use legacy model list
    if not agents:
        agents = [
            {"id": f"legacy-{i}", "title": model, "model": model, "prompts": {}}
            for i, model in enumerate(COUNCIL_MODELS)
        ]

    # Create tasks for each agent with their specific prompts
    async def query_with_agent_prompt(agent: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any], str]:
        model = agent["model"]

        # Priority: agent-specific prompt > model-specific prompt > default prompt
        if "stage1" in agent.get("prompts", {}):
            stage1_template = agent["prompts"]["stage1"]
        else:
            stage1_prompt = get_prompt_for_model(model, 'stage1')
            stage1_template = stage1_prompt['template']

        # Format the prompt
        prompt = stage1_template.format(user_query=user_query)
        messages = [{"role": "user", "content": prompt}]

        # Query the model
        response = await query_model(model, messages)
        return agent, response, prompt

    # Query all agents in parallel with their individual prompts
    tasks = [query_with_agent_prompt(agent) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Format results
    stage1_results = []
    for result in results:
        if isinstance(result, Exception):
            # Skip failed queries
            continue
        agent, response, prompt = result
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "agent_id": agent["id"],
                "agent_title": agent.get("title", agent["model"]),
                "model": agent["model"],
                "response": response.get('content', ''),
                "prompt": prompt
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to agent title (for de-anonymization in UI)
    label_to_model = {
        f"Response {label}": {
            "agent_title": result['agent_title'],
            "model": result['model']
        }
        for label, result in zip(labels, stage1_results)
    }

    # Build the anonymized responses text (same for all agents)
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    # Load active agents for ranking
    agents = agent_storage.get_active_agents()

    # If no agents configured, use legacy model list
    if not agents:
        agents = [
            {"id": f"legacy-{i}", "model": result["model"], "prompts": {}}
            for i, result in enumerate(stage1_results)
        ]

    # Create tasks for each agent with their specific prompts
    async def query_ranking_with_agent_prompt(agent: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any], str]:
        model = agent["model"]

        # Priority: agent-specific prompt > model-specific prompt > default prompt
        if "stage2" in agent.get("prompts", {}):
            stage2_template = agent["prompts"]["stage2"]
        else:
            stage2_prompt = get_prompt_for_model(model, 'stage2')
            stage2_template = stage2_prompt['template']

        # Format the prompt template
        ranking_prompt = stage2_template.format(
            user_query=user_query,
            responses_text=responses_text
        )

        messages = [{"role": "user", "content": ranking_prompt}]

        # Query the model
        response = await query_model(model, messages)
        return agent, response, ranking_prompt

    # Query all agents in parallel with their individual prompts
    import asyncio
    tasks = [query_ranking_with_agent_prompt(agent) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Format results
    stage2_results = []
    for result in results:
        if isinstance(result, Exception):
            # Skip failed queries
            continue
        agent, response, prompt = result
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "agent_id": agent.get("id"),
                "agent_title": agent.get("title", agent["model"]),
                "model": agent["model"],
                "ranking": full_text,
                "parsed_ranking": parsed,
                "prompt": prompt
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Get chairman agent or use default
    chairman = agent_storage.get_chairman()
    if chairman:
        chairman_model = chairman["model"]
        # Priority: agent-specific prompt > model-specific prompt > default prompt
        if "stage3" in chairman.get("prompts", {}):
            stage3_template = chairman["prompts"]["stage3"]
        else:
            stage3_prompt = get_prompt_for_model(chairman_model, 'stage3')
            stage3_template = stage3_prompt['template']
    else:
        chairman_model = CHAIRMAN_MODEL
        stage3_prompt = get_prompt_for_model(chairman_model, 'stage3')
        stage3_template = stage3_prompt['template']

    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"{result['agent_title']}: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"{result['agent_title']}: {result['ranking']}"
        for result in stage2_results
    ])

    # Format the prompt template
    chairman_prompt = stage3_template.format(
        user_query=user_query,
        stage1_text=stage1_text,
        stage2_text=stage2_text
    )

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(chairman_model, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "agent_title": chairman.get("title", "Chairman") if chairman else "Chairman",
            "model": chairman_model,
            "response": "Error: Unable to generate final synthesis.",
            "prompt": chairman_prompt
        }

    return {
        "agent_title": chairman.get("title", "Chairman") if chairman else "Chairman",
        "model": chairman_model,
        "response": response.get('content', ''),
        "prompt": chairman_prompt
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all agents.

    Args:
        stage2_results: Rankings from each agent
        label_to_model: Mapping from anonymous labels to agent info {agent_title, model}

    Returns:
        List of dicts with agent info and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each agent (by agent_title)
    agent_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                agent_info = label_to_model[label]
                agent_title = agent_info["agent_title"]
                agent_positions[agent_title].append(position)

    # Calculate average position for each agent
    aggregate = []
    for agent_title, positions in agent_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            # Get model from label_to_model
            model = next(
                (info["model"] for label, info in label_to_model.items()
                 if info["agent_title"] == agent_title),
                ""
            )
            aggregate.append({
                "agent_title": agent_title,
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
