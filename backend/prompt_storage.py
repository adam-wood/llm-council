"""Storage for custom prompts."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from .prompts import get_default_prompts

PROMPTS_FILE = Path(__file__).parent.parent / "data" / "prompts.json"


def ensure_data_directory():
    """Ensure the data directory exists."""
    PROMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_custom_prompts() -> Dict[str, Any]:
    """
    Load custom prompts from storage.

    Returns:
        Dict with 'defaults' and 'models' keys, or empty structure if none exist
    """
    ensure_data_directory()

    if not PROMPTS_FILE.exists():
        return {"defaults": {}, "models": {}}

    try:
        with open(PROMPTS_FILE, 'r') as f:
            data = json.load(f)

            # Handle legacy format (migrate to new structure)
            if "defaults" not in data and "models" not in data:
                # This is the old format where prompts were stored flat
                return {"defaults": data, "models": {}}

            return data
    except json.JSONDecodeError:
        return {"defaults": {}, "models": {}}


def save_custom_prompts(prompts: Dict[str, Any]) -> None:
    """
    Save custom prompts to storage.

    Args:
        prompts: Dict of custom prompts to save
    """
    ensure_data_directory()

    with open(PROMPTS_FILE, 'w') as f:
        json.dump(prompts, f, indent=2)


def get_active_prompts() -> Dict[str, Any]:
    """
    Get the currently active default prompts (custom or default).

    Returns:
        Dict with prompts for each stage
    """
    defaults = get_default_prompts()
    custom = load_custom_prompts()

    # Merge custom default prompts over system defaults
    active = defaults.copy()
    for stage, prompt_config in custom["defaults"].items():
        if stage in active:
            active[stage] = {**active[stage], **prompt_config}

    return active


def get_prompt_for_model(model: str, stage: str) -> Dict[str, Any]:
    """
    Get the prompt for a specific model and stage.
    Falls back to default if no model-specific override exists.

    Args:
        model: The model identifier (e.g., "openai/gpt-5.1")
        stage: The stage ('stage1', 'stage2', or 'stage3')

    Returns:
        Prompt configuration dict
    """
    custom = load_custom_prompts()
    defaults = get_active_prompts()

    # Check for model-specific override
    if model in custom["models"] and stage in custom["models"][model]:
        # Merge model-specific prompt over defaults
        return {**defaults[stage], **custom["models"][model][stage]}

    # Return default
    return defaults[stage]


def get_all_model_prompts() -> Dict[str, Any]:
    """
    Get all prompts including defaults and per-model overrides.

    Returns:
        Dict with 'defaults' and 'models' keys
    """
    custom = load_custom_prompts()
    defaults = get_active_prompts()

    return {
        "defaults": defaults,
        "models": custom["models"]
    }


def update_prompt(stage: str, prompt_data: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    """
    Update a specific stage's prompt (default or model-specific).

    Args:
        stage: The stage to update ('stage1', 'stage2', or 'stage3')
        prompt_data: New prompt configuration
        model: Optional model identifier for model-specific prompt

    Returns:
        Updated prompts configuration
    """
    custom = load_custom_prompts()

    if model:
        # Update model-specific prompt
        if model not in custom["models"]:
            custom["models"][model] = {}
        custom["models"][model][stage] = prompt_data
    else:
        # Update default prompt
        custom["defaults"][stage] = prompt_data

    save_custom_prompts(custom)
    return get_all_model_prompts()


def reset_prompt(stage: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Reset a specific stage's prompt to default.

    Args:
        stage: The stage to reset
        model: Optional model identifier for model-specific prompt

    Returns:
        Updated prompts configuration
    """
    custom = load_custom_prompts()

    if model:
        # Reset model-specific prompt
        if model in custom["models"] and stage in custom["models"][model]:
            del custom["models"][model][stage]
            # Clean up empty model entries
            if not custom["models"][model]:
                del custom["models"][model]
    else:
        # Reset default prompt
        if stage in custom["defaults"]:
            del custom["defaults"][stage]

    save_custom_prompts(custom)
    return get_all_model_prompts()


def reset_all_prompts() -> Dict[str, Any]:
    """
    Reset all prompts to defaults.

    Returns:
        Default prompts configuration
    """
    if PROMPTS_FILE.exists():
        PROMPTS_FILE.unlink()
    return get_all_model_prompts()
