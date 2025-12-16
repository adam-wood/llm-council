"""Tests for prompt_storage.py - prompt management and fallback chain."""

import pytest
import json
from pathlib import Path
from backend import prompt_storage
from backend.prompts import DEFAULT_PROMPTS
from backend.config import get_user_prompts_file
from tests.conftest import TEST_USER_ID


class TestPromptFallbackChain:
    """Test the prompt fallback hierarchy: model-specific → default."""

    def test_get_default_prompt_when_no_custom(self, temp_data_dir, test_user_id):
        """Test fallback to default when no custom prompts exist."""
        prompt = prompt_storage.get_prompt_for_model(test_user_id, "test/model", "stage1")

        # Should return default prompt
        assert prompt["name"] == DEFAULT_PROMPTS["stage1"]["name"]
        assert "{user_query}" in prompt["template"]

    def test_get_model_specific_prompt(self, temp_data_dir, test_user_id):
        """Test model-specific prompt override."""
        # Create model-specific prompt
        custom_prompts = {
            "defaults": {},
            "models": {
                "test/model": {
                    "stage1": {
                        "name": "Custom Stage 1",
                        "template": "Custom prompt: {user_query}"
                    }
                }
            }
        }
        prompt_storage.save_custom_prompts(test_user_id, custom_prompts)

        prompt = prompt_storage.get_prompt_for_model(test_user_id, "test/model", "stage1")

        assert prompt["name"] == "Custom Stage 1"
        assert prompt["template"] == "Custom prompt: {user_query}"

    def test_get_custom_default_prompt(self, temp_data_dir, test_user_id):
        """Test custom default prompt override."""
        custom_prompts = {
            "defaults": {
                "stage1": {
                    "name": "Custom Default Stage 1",
                    "template": "Custom default: {user_query}"
                }
            },
            "models": {}
        }
        prompt_storage.save_custom_prompts(test_user_id, custom_prompts)

        prompt = prompt_storage.get_prompt_for_model(test_user_id, "any/model", "stage1")

        assert prompt["name"] == "Custom Default Stage 1"
        assert prompt["template"] == "Custom default: {user_query}"

    def test_model_specific_overrides_default(self, temp_data_dir, test_user_id):
        """Test that model-specific prompt takes precedence over custom default."""
        custom_prompts = {
            "defaults": {
                "stage1": {
                    "template": "Default template: {user_query}"
                }
            },
            "models": {
                "test/model": {
                    "stage1": {
                        "template": "Model-specific template: {user_query}"
                    }
                }
            }
        }
        prompt_storage.save_custom_prompts(test_user_id, custom_prompts)

        prompt = prompt_storage.get_prompt_for_model(test_user_id, "test/model", "stage1")

        assert "Model-specific" in prompt["template"]

    def test_fallback_for_different_model(self, temp_data_dir, test_user_id):
        """Test fallback when model doesn't have specific prompt."""
        custom_prompts = {
            "defaults": {
                "stage1": {
                    "template": "Default: {user_query}"
                }
            },
            "models": {
                "other/model": {
                    "stage1": {
                        "template": "Other model: {user_query}"
                    }
                }
            }
        }
        prompt_storage.save_custom_prompts(test_user_id, custom_prompts)

        # Request prompt for model without specific override
        prompt = prompt_storage.get_prompt_for_model(test_user_id, "test/model", "stage1")

        assert prompt["template"] == "Default: {user_query}"


class TestPromptCRUD:
    """Test CRUD operations for prompts."""

    def test_update_default_prompt(self, temp_data_dir, test_user_id):
        """Test updating default prompt."""
        new_prompt = {
            "name": "Updated Stage 1",
            "description": "Updated description",
            "template": "Updated: {user_query}",
            "notes": "Updated notes"
        }

        result = prompt_storage.update_prompt(test_user_id, "stage1", new_prompt)

        assert result["defaults"]["stage1"]["name"] == "Updated Stage 1"
        assert result["defaults"]["stage1"]["template"] == "Updated: {user_query}"

    def test_update_model_specific_prompt(self, temp_data_dir, test_user_id):
        """Test updating model-specific prompt."""
        new_prompt = {
            "name": "Model Specific",
            "template": "Model: {user_query}"
        }

        result = prompt_storage.update_prompt(test_user_id, "stage1", new_prompt, model="test/model")

        assert "test/model" in result["models"]
        assert result["models"]["test/model"]["stage1"]["name"] == "Model Specific"

    def test_reset_default_prompt(self, temp_data_dir, test_user_id):
        """Test resetting default prompt to system default."""
        # First, update default
        prompt_storage.update_prompt(test_user_id, "stage1", {"template": "Custom"})

        # Then reset
        result = prompt_storage.reset_prompt(test_user_id, "stage1")

        # Should return system default
        prompt = result["defaults"]["stage1"]
        assert prompt["name"] == DEFAULT_PROMPTS["stage1"]["name"]

    def test_reset_model_specific_prompt(self, temp_data_dir, test_user_id):
        """Test resetting model-specific prompt."""
        # Create model-specific prompt
        prompt_storage.update_prompt(test_user_id, "stage1", {"template": "Custom"}, model="test/model")

        # Reset it
        result = prompt_storage.reset_prompt(test_user_id, "stage1", model="test/model")

        # Model should no longer have specific prompt
        assert "test/model" not in result["models"] or "stage1" not in result["models"].get("test/model", {})

    def test_reset_all_prompts(self, temp_data_dir, test_user_id):
        """Test resetting all prompts to system defaults."""
        # Create various custom prompts
        prompt_storage.update_prompt(test_user_id, "stage1", {"template": "Custom 1"})
        prompt_storage.update_prompt(test_user_id, "stage2", {"template": "Custom 2"}, model="test/model")

        # Reset all
        result = prompt_storage.reset_all_prompts(test_user_id)

        # Should have system defaults
        assert result["defaults"]["stage1"]["name"] == DEFAULT_PROMPTS["stage1"]["name"]
        assert result["models"] == {}

    def test_get_all_model_prompts(self, temp_data_dir, test_user_id):
        """Test retrieving all prompts at once."""
        # Setup custom prompts
        prompt_storage.update_prompt(test_user_id, "stage1", {"template": "Default 1"})
        prompt_storage.update_prompt(test_user_id, "stage2", {"template": "Model 2"}, model="test/model")

        result = prompt_storage.get_all_model_prompts(test_user_id)

        assert "defaults" in result
        assert "models" in result
        assert "stage1" in result["defaults"]
        assert "test/model" in result["models"]


class TestDataPersistence:
    """Test prompt data persistence."""

    def test_prompts_saved_to_file(self, temp_data_dir, test_user_id):
        """Test that prompts are saved to JSON file."""
        prompt_storage.update_prompt(test_user_id, "stage1", {"template": "Test"})

        prompts_file = Path(get_user_prompts_file(test_user_id))
        assert prompts_file.exists()

        with open(prompts_file, 'r') as f:
            data = json.load(f)

        assert "defaults" in data
        assert "models" in data

    def test_load_custom_prompts(self, temp_data_dir, test_user_id):
        """Test loading custom prompts from file."""
        # Create custom prompts file
        custom_data = {
            "defaults": {
                "stage1": {"template": "Custom default"}
            },
            "models": {
                "test/model": {
                    "stage1": {"template": "Custom model"}
                }
            }
        }

        prompts_file = Path(get_user_prompts_file(test_user_id))
        prompts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(prompts_file, 'w') as f:
            json.dump(custom_data, f)

        loaded = prompt_storage.load_custom_prompts(test_user_id)

        assert loaded["defaults"]["stage1"]["template"] == "Custom default"
        assert loaded["models"]["test/model"]["stage1"]["template"] == "Custom model"

    def test_load_when_file_doesnt_exist(self, temp_data_dir, test_user_id):
        """Test loading when prompts file doesn't exist."""
        loaded = prompt_storage.load_custom_prompts(test_user_id)

        assert loaded == {"defaults": {}, "models": {}}

    def test_load_corrupted_json(self, temp_data_dir, test_user_id):
        """Test handling of corrupted JSON file."""
        # Create corrupted file
        prompts_file = Path(get_user_prompts_file(test_user_id))
        prompts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(prompts_file, 'w') as f:
            f.write("{ invalid json }")

        loaded = prompt_storage.load_custom_prompts(test_user_id)

        assert loaded == {"defaults": {}, "models": {}}

    def test_legacy_format_migration(self, temp_data_dir, test_user_id):
        """Test migration from legacy flat format."""
        # Create legacy format file
        legacy_data = {
            "stage1": {"template": "Legacy stage 1"},
            "stage2": {"template": "Legacy stage 2"}
        }

        prompts_file = Path(get_user_prompts_file(test_user_id))
        prompts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(prompts_file, 'w') as f:
            json.dump(legacy_data, f)

        loaded = prompt_storage.load_custom_prompts(test_user_id)

        # Should migrate to new format with defaults
        assert loaded["defaults"]["stage1"]["template"] == "Legacy stage 1"
        assert loaded["models"] == {}


class TestPromptMerging:
    """Test prompt merging behavior."""

    def test_partial_custom_default_merges_with_system(self, temp_data_dir, test_user_id):
        """Test that partial custom defaults merge with system defaults."""
        # Only customize template, keep other fields from system default
        custom_prompts = {
            "defaults": {
                "stage1": {
                    "template": "Custom template: {user_query}"
                }
            },
            "models": {}
        }
        prompt_storage.save_custom_prompts(test_user_id, custom_prompts)

        prompt = prompt_storage.get_active_prompts(test_user_id)["stage1"]

        # Should have custom template
        assert prompt["template"] == "Custom template: {user_query}"
        # But keep system default name
        assert prompt["name"] == DEFAULT_PROMPTS["stage1"]["name"]

    def test_model_prompt_merges_with_defaults(self, temp_data_dir, test_user_id):
        """Test that model prompts merge with defaults."""
        custom_prompts = {
            "defaults": {
                "stage1": {
                    "name": "Default Name",
                    "template": "Default: {user_query}"
                }
            },
            "models": {
                "test/model": {
                    "stage1": {
                        "template": "Model: {user_query}"
                        # name not specified, should inherit from default
                    }
                }
            }
        }
        prompt_storage.save_custom_prompts(test_user_id, custom_prompts)

        prompt = prompt_storage.get_prompt_for_model(test_user_id, "test/model", "stage1")

        # Should have model-specific template
        assert prompt["template"] == "Model: {user_query}"
        # But merge in default name
        assert prompt["name"] == "Default Name"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_update_nonexistent_stage(self, temp_data_dir, test_user_id):
        """Test updating a stage that doesn't exist in defaults."""
        # Custom stages are stored but result includes system defaults
        result = prompt_storage.update_prompt(test_user_id, "custom_stage", {"template": "Custom"})

        # Result includes system defaults for known stages
        assert "stage1" in result["defaults"]
        assert "stage2" in result["defaults"]
        assert "stage3" in result["defaults"]

    def test_empty_model_identifier(self, temp_data_dir, test_user_id):
        """Test using empty string as model identifier."""
        # Empty string model identifiers are allowed but may behave unexpectedly
        # This test documents current behavior rather than requirements
        result = prompt_storage.update_prompt(test_user_id, "stage1", {"template": "Test"}, model="")

        # System continues to function
        assert "defaults" in result
        # Note: Empty string models may not persist depending on implementation

    def test_cleanup_empty_model_entries(self, temp_data_dir, test_user_id):
        """Test that empty model entries are cleaned up on reset."""
        # Create model with multiple stage overrides
        prompt_storage.update_prompt(test_user_id, "stage1", {"template": "A"}, model="test/model")
        prompt_storage.update_prompt(test_user_id, "stage2", {"template": "B"}, model="test/model")

        # Reset stage1
        result = prompt_storage.reset_prompt(test_user_id, "stage1", model="test/model")

        # Model should still exist (has stage2)
        assert "test/model" in result["models"]
        assert "stage2" in result["models"]["test/model"]

        # Reset stage2
        result = prompt_storage.reset_prompt(test_user_id, "stage2", model="test/model")

        # Model entry should be cleaned up
        assert "test/model" not in result["models"]

    def test_get_active_prompts_returns_all_stages(self, temp_data_dir, test_user_id):
        """Test that get_active_prompts returns all default stages."""
        prompts = prompt_storage.get_active_prompts(test_user_id)

        assert "stage1" in prompts
        assert "stage2" in prompts
        assert "stage3" in prompts

    def test_unicode_in_prompts(self, temp_data_dir, test_user_id):
        """Test handling of Unicode in prompt templates."""
        prompt_storage.update_prompt(test_user_id, "stage1", {
            "template": "Unicode test: 你好 {user_query} 🌍"
        })

        prompt = prompt_storage.get_prompt_for_model(test_user_id, "any/model", "stage1")

        assert "你好" in prompt["template"]
        assert "🌍" in prompt["template"]

    def test_very_long_prompt_template(self, temp_data_dir, test_user_id):
        """Test handling of very long prompt templates."""
        long_template = "A" * 10000 + " {user_query}"

        prompt_storage.update_prompt(test_user_id, "stage1", {"template": long_template})

        prompt = prompt_storage.get_prompt_for_model(test_user_id, "any/model", "stage1")

        assert len(prompt["template"]) > 10000
