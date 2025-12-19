"""FastAPI backend for LLM Council."""

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from . import prompt_storage
from . import agent_storage
from .auth import get_current_user_id
from .council import (
    run_full_council, generate_conversation_title,
    stage1_collect_responses, stage2_collect_rankings,
    stage3_synthesize_final, calculate_aggregate_rankings
)
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL
from .openrouter import OpenRouterCreditsExhaustedError

app = FastAPI(title="LLM Council API")

# CORS configuration - allow localhost for dev and production domain
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]

# Add production domain if set
PRODUCTION_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN")
if PRODUCTION_URL:
    CORS_ORIGINS.append(f"https://{PRODUCTION_URL}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str = Field(..., min_length=1, max_length=50000)


class UpdatePromptRequest(BaseModel):
    """Request to update a prompt."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., max_length=1000)
    template: str = Field(..., min_length=1, max_length=50000)
    notes: str = Field(default="", max_length=5000)


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""
    title: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=1000)
    model: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+$')
    prompts: Dict[str, str] = {}
    active: bool = True


class UpdateAgentRequest(BaseModel):
    """Request to update an agent."""
    title: str = Field(default=None, min_length=1, max_length=255)
    role: str = Field(default=None, min_length=1, max_length=1000)
    model: str = Field(default=None, min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+$')
    prompts: Dict[str, str] = None
    active: bool = None


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {"status": "ok", "service": "LLM Council API"}


# Conversation endpoints - all require auth
@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(user_id: str = Depends(get_current_user_id)):
    """List all conversations for the current user (metadata only)."""
    return storage.list_conversations(user_id)


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(
    request: CreateConversationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new conversation for the current user."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(user_id, conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(user_id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a conversation."""
    success = storage.delete_conversation(user_id, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(user_id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(user_id, conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(user_id, conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        user_id, request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        user_id,
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(user_id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(user_id, conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(user_id, request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(user_id, request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(user_id, request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(user_id, conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                user_id,
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except OpenRouterCreditsExhaustedError as e:
            # Send specific error for credits exhausted
            yield f"data: {json.dumps({'type': 'error', 'error_code': 'credits_exhausted', 'message': str(e)})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# Agent endpoints - all require auth
@app.get("/api/agents")
async def list_agents(
    active_only: bool = False,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get all agent configurations for the current user.

    Args:
        active_only: If True, only return active agents
    """
    if active_only:
        return agent_storage.get_active_agents(user_id)
    return agent_storage.get_all_agents(user_id)


@app.post("/api/agents")
async def create_agent(
    request: CreateAgentRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new agent configuration for the current user."""
    agent = agent_storage.create_agent(
        user_id,
        title=request.title,
        role=request.role,
        model=request.model,
        prompts=request.prompts,
        active=request.active
    )
    return agent


@app.post("/api/agents/initialize")
async def initialize_default_agents(user_id: str = Depends(get_current_user_id)):
    """Initialize default agent templates for the current user."""
    agents = agent_storage.initialize_default_agents(user_id)
    return {"agents": agents, "count": len(agents)}


@app.get("/api/agents/chairman")
async def get_chairman_agent(user_id: str = Depends(get_current_user_id)):
    """Get the current chairman agent configuration for the user."""
    chairman = agent_storage.get_chairman(user_id)
    return {"chairman": chairman}


@app.put("/api/agents/chairman/{agent_id}")
async def set_chairman_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Set which agent is the chairman for the user."""
    success = agent_storage.set_chairman(user_id, agent_id if agent_id != "default" else None)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "chairman": agent_id}


@app.get("/api/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific agent configuration."""
    agent = agent_storage.get_agent_by_id(user_id, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.put("/api/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Update an agent configuration."""
    # Build updates dict from non-None fields
    updates = {}
    if request.title is not None:
        updates["title"] = request.title
    if request.role is not None:
        updates["role"] = request.role
    if request.model is not None:
        updates["model"] = request.model
    if request.prompts is not None:
        updates["prompts"] = request.prompts
    if request.active is not None:
        updates["active"] = request.active

    agent = agent_storage.update_agent(user_id, agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.delete("/api/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete an agent configuration."""
    success = agent_storage.delete_agent(user_id, agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True}


# Model and prompt endpoints - all require auth
@app.get("/api/models")
async def get_models(user_id: str = Depends(get_current_user_id)):
    """Get the list of council models and chairman."""
    return {
        "council": COUNCIL_MODELS,
        "chairman": CHAIRMAN_MODEL,
        "all": list(set(COUNCIL_MODELS + [CHAIRMAN_MODEL]))
    }


@app.get("/api/prompts")
async def get_prompts(
    model: str = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get all active prompts for the current user (custom or default).

    Args:
        model: Optional model identifier to get model-specific prompts
    """
    if model:
        # Return prompts for specific model (with fallback to defaults)
        return {
            "stage1": prompt_storage.get_prompt_for_model(user_id, model, "stage1"),
            "stage2": prompt_storage.get_prompt_for_model(user_id, model, "stage2"),
            "stage3": prompt_storage.get_prompt_for_model(user_id, model, "stage3"),
        }
    else:
        # Return all prompts (defaults and per-model overrides)
        return prompt_storage.get_all_model_prompts(user_id)


@app.put("/api/prompts/{stage}")
async def update_prompt(
    stage: str,
    request: UpdatePromptRequest,
    model: str = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update a specific stage's prompt for the current user (default or model-specific).

    Args:
        stage: The stage to update ('stage1', 'stage2', or 'stage3')
        request: New prompt configuration
        model: Optional model identifier for model-specific prompt
    """
    if stage not in ['stage1', 'stage2', 'stage3']:
        raise HTTPException(status_code=400, detail="Invalid stage. Must be 'stage1', 'stage2', or 'stage3'")

    prompt_data = {
        "name": request.name,
        "description": request.description,
        "template": request.template,
        "notes": request.notes
    }

    updated_prompts = prompt_storage.update_prompt(user_id, stage, prompt_data, model)
    return updated_prompts


@app.delete("/api/prompts/{stage}")
async def reset_prompt(
    stage: str,
    model: str = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Reset a specific stage's prompt to default for the current user.

    Args:
        stage: The stage to reset ('stage1', 'stage2', or 'stage3')
        model: Optional model identifier for model-specific prompt
    """
    if stage not in ['stage1', 'stage2', 'stage3']:
        raise HTTPException(status_code=400, detail="Invalid stage. Must be 'stage1', 'stage2', or 'stage3'")

    updated_prompts = prompt_storage.reset_prompt(user_id, stage, model)
    return updated_prompts


@app.delete("/api/prompts")
async def reset_all_prompts(user_id: str = Depends(get_current_user_id)):
    """Reset all prompts to defaults for the current user."""
    default_prompts = prompt_storage.reset_all_prompts(user_id)
    return default_prompts


# Static file serving for production (must be after all API routes)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for any non-API route."""
        # Check if it's a static file
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
