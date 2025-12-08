"""Default prompts for the LLM Council system."""

# Default prompts for each stage
DEFAULT_PROMPTS = {
    "stage1": {
        "name": "Stage 1: Initial Response",
        "description": "Prompt used to collect initial responses from council members",
        "template": "{user_query}",
        "notes": "Stage 1 passes the user query directly to each model. The template variable {user_query} will be replaced with the actual question."
    },
    "stage2": {
        "name": "Stage 2: Peer Evaluation",
        "description": "Prompt used for anonymized peer review and ranking",
        "template": """You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:""",
        "notes": "Variables: {user_query}, {responses_text}. The responses_text is automatically formatted with anonymized labels."
    },
    "stage3": {
        "name": "Stage 3: Chairman Synthesis",
        "description": "Prompt used by the chairman to synthesize the final answer",
        "template": """You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:""",
        "notes": "Variables: {user_query}, {stage1_text}, {stage2_text}. These are automatically populated from previous stages."
    }
}


def get_default_prompts():
    """Get the default prompts configuration."""
    return DEFAULT_PROMPTS.copy()


def get_stage_prompt(stage: str, custom_prompts: dict = None):
    """
    Get the prompt template for a specific stage.

    Args:
        stage: The stage identifier ('stage1', 'stage2', or 'stage3')
        custom_prompts: Optional custom prompts to override defaults

    Returns:
        The prompt template string
    """
    if custom_prompts and stage in custom_prompts:
        return custom_prompts[stage].get('template', DEFAULT_PROMPTS[stage]['template'])
    return DEFAULT_PROMPTS[stage]['template']
