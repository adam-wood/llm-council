#!/usr/bin/env python3
"""
One-time migration script to move existing data to user-scoped directories.

Usage:
1. Sign up as the first user in Clerk
2. Get your Clerk user ID from the dashboard (starts with "user_")
3. Set ADMIN_USER_ID below to your Clerk user ID
4. Run: python scripts/migrate_data.py

This script will:
- Move existing conversations from data/conversations/ to data/users/{user_id}/conversations/
- Move existing agents.json to data/users/{user_id}/agents.json
- Move existing prompts.json to data/users/{user_id}/prompts.json
"""

import json
import os
import shutil
from pathlib import Path

# REPLACE THIS with your actual Clerk user ID after signing up
ADMIN_USER_ID = "user_36t0vjhrgqAhUOGorjHiT8ETePQ"

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OLD_CONVERSATIONS_DIR = DATA_DIR / "conversations"
OLD_AGENTS_FILE = DATA_DIR / "agents.json"
OLD_PROMPTS_FILE = DATA_DIR / "prompts.json"


def migrate():
    """Migrate existing data to user-scoped directory structure."""
    if ADMIN_USER_ID.startswith("user_REPLACE"):
        print("ERROR: Please set ADMIN_USER_ID to your actual Clerk user ID")
        print("You can find this in the Clerk dashboard after signing up")
        print()
        print("Steps:")
        print("1. Set up Clerk (see CLAUDE.md for instructions)")
        print("2. Sign up as the first user")
        print("3. Go to Clerk Dashboard > Users > click your user")
        print("4. Copy the User ID (starts with 'user_')")
        print("5. Edit this script and set ADMIN_USER_ID")
        print("6. Run this script again")
        return False

    # Create user directory
    user_dir = DATA_DIR / "users" / ADMIN_USER_ID
    user_conversations_dir = user_dir / "conversations"
    user_conversations_dir.mkdir(parents=True, exist_ok=True)

    migrated_conversations = 0
    migrated_agents = False
    migrated_prompts = False

    # Migrate conversations
    if OLD_CONVERSATIONS_DIR.exists():
        for filename in os.listdir(OLD_CONVERSATIONS_DIR):
            if filename.endswith('.json'):
                old_path = OLD_CONVERSATIONS_DIR / filename
                new_path = user_conversations_dir / filename

                try:
                    # Read and update conversation with user_id
                    with open(old_path, 'r') as f:
                        data = json.load(f)

                    # Add user_id if not present
                    if "user_id" not in data:
                        data["user_id"] = ADMIN_USER_ID

                    # Write to new location
                    with open(new_path, 'w') as f:
                        json.dump(data, f, indent=2)

                    # Remove old file
                    os.remove(old_path)
                    print(f"Migrated conversation: {filename}")
                    migrated_conversations += 1

                except Exception as e:
                    print(f"Error migrating {filename}: {e}")

        # Try to remove old conversations directory if empty
        try:
            OLD_CONVERSATIONS_DIR.rmdir()
            print("Removed old conversations directory")
        except OSError:
            print("Note: Old conversations directory not empty or already removed")

    # Migrate agents
    if OLD_AGENTS_FILE.exists():
        try:
            new_agents_file = user_dir / "agents.json"
            shutil.move(str(OLD_AGENTS_FILE), str(new_agents_file))
            print(f"Migrated agents.json to {new_agents_file}")
            migrated_agents = True
        except Exception as e:
            print(f"Error migrating agents.json: {e}")

    # Migrate prompts
    if OLD_PROMPTS_FILE.exists():
        try:
            new_prompts_file = user_dir / "prompts.json"
            shutil.move(str(OLD_PROMPTS_FILE), str(new_prompts_file))
            print(f"Migrated prompts.json to {new_prompts_file}")
            migrated_prompts = True
        except Exception as e:
            print(f"Error migrating prompts.json: {e}")

    print()
    print("=" * 50)
    print("Migration Summary:")
    print(f"  Conversations migrated: {migrated_conversations}")
    print(f"  Agents migrated: {'Yes' if migrated_agents else 'No (not found)'}")
    print(f"  Prompts migrated: {'Yes' if migrated_prompts else 'No (not found)'}")
    print()
    print(f"Data is now stored at: {user_dir}")
    print("=" * 50)

    return True


if __name__ == "__main__":
    print("LLM Council Data Migration")
    print("=" * 50)
    print()
    migrate()
