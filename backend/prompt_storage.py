"""Storage for custom prompts with user scoping."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from .prompts import get_default_prompts
from .config import get_user_prompts_file, get_user_data_dir


def ensure_user_directory(user_id: str):
    """Ensure the user's data directory exists."""
    Path(get_user_data_dir(user_id)).mkdir(parents=True, exist_ok=True)


def load_custom_prompts(user_id: str) -> Dict[str, Any]:
    """
    Load custom prompts from storage for a user.

    Args:
        user_id: The user's identifier

    Returns:
        Dict with 'defaults' and 'models' keys, or empty structure if none exist
    """
    ensure_user_directory(user_id)
    prompts_file = Path(get_user_prompts_file(user_id))

    if not prompts_file.exists():
        return {"defaults": {}, "models": {}}

    try:
        with open(prompts_file, 'r') as f:
            data = json.load(f)

            # Handle legacy format (migrate to new structure)
            if "defaults" not in data and "models" not in data:
                # This is the old format where prompts were stored flat
                return {"defaults": data, "models": {}}

            return data
    except json.JSONDecodeError:
        return {"defaults": {}, "models": {}}


def save_custom_prompts(user_id: str, prompts: Dict[str, Any]) -> None:
    """
    Save custom prompts to storage for a user.

    Args:
        user_id: The user's identifier
        prompts: Dict of custom prompts to save
    """
    ensure_user_directory(user_id)
    prompts_file = Path(get_user_prompts_file(user_id))

    with open(prompts_file, 'w') as f:
        json.dump(prompts, f, indent=2)


def get_active_prompts(user_id: str) -> Dict[str, Any]:
    """
    Get the currently active default prompts for a user (custom or default).

    Args:
        user_id: The user's identifier

    Returns:
        Dict with prompts for each stage
    """
    defaults = get_default_prompts()
    custom = load_custom_prompts(user_id)

    # Merge custom default prompts over system defaults
    active = defaults.copy()
    for stage, prompt_config in custom["defaults"].items():
        if stage in active:
            active[stage] = {**active[stage], **prompt_config}

    return active


def get_prompt_for_model(user_id: str, model: str, stage: str) -> Dict[str, Any]:
    """
    Get the prompt for a specific model and stage for a user.
    Falls back to default if no model-specific override exists.

    Args:
        user_id: The user's identifier
        model: The model identifier (e.g., "openai/gpt-5.1")
        stage: The stage ('stage1', 'stage2', or 'stage3')

    Returns:
        Prompt configuration dict
    """
    custom = load_custom_prompts(user_id)
    defaults = get_active_prompts(user_id)

    # Check for model-specific override
    if model in custom["models"] and stage in custom["models"][model]:
        # Merge model-specific prompt over defaults
        return {**defaults[stage], **custom["models"][model][stage]}

    # Return default
    return defaults[stage]


def get_all_model_prompts(user_id: str) -> Dict[str, Any]:
    """
    Get all prompts for a user including defaults and per-model overrides.

    Args:
        user_id: The user's identifier

    Returns:
        Dict with 'defaults' and 'models' keys
    """
    custom = load_custom_prompts(user_id)
    defaults = get_active_prompts(user_id)

    return {
        "defaults": defaults,
        "models": custom["models"]
    }


def update_prompt(user_id: str, stage: str, prompt_data: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    """
    Update a specific stage's prompt for a user (default or model-specific).

    Args:
        user_id: The user's identifier
        stage: The stage to update ('stage1', 'stage2', or 'stage3')
        prompt_data: New prompt configuration
        model: Optional model identifier for model-specific prompt

    Returns:
        Updated prompts configuration
    """
    custom = load_custom_prompts(user_id)

    if model:
        # Update model-specific prompt
        if model not in custom["models"]:
            custom["models"][model] = {}
        custom["models"][model][stage] = prompt_data
    else:
        # Update default prompt
        custom["defaults"][stage] = prompt_data

    save_custom_prompts(user_id, custom)
    return get_all_model_prompts(user_id)


def reset_prompt(user_id: str, stage: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Reset a specific stage's prompt to default for a user.

    Args:
        user_id: The user's identifier
        stage: The stage to reset
        model: Optional model identifier for model-specific prompt

    Returns:
        Updated prompts configuration
    """
    custom = load_custom_prompts(user_id)

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

    save_custom_prompts(user_id, custom)
    return get_all_model_prompts(user_id)


def reset_all_prompts(user_id: str) -> Dict[str, Any]:
    """
    Reset all prompts to defaults for a user.

    Args:
        user_id: The user's identifier

    Returns:
        Default prompts configuration
    """
    prompts_file = Path(get_user_prompts_file(user_id))
    if prompts_file.exists():
        prompts_file.unlink()
    return get_all_model_prompts(user_id)
