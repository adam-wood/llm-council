"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from . import prompt_storage
from . import agent_storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class UpdatePromptRequest(BaseModel):
    """Request to update a prompt."""
    name: str
    description: str
    template: str
    notes: str = ""


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""
    title: str
    role: str
    model: str
    prompts: Dict[str, str] = {}
    active: bool = True


class UpdateAgentRequest(BaseModel):
    """Request to update an agent."""
    title: str = None
    role: str = None
    model: str = None
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


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    success = storage.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
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
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

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


@app.get("/api/agents")
async def list_agents(active_only: bool = False):
    """
    Get all agent configurations.

    Args:
        active_only: If True, only return active agents
    """
    if active_only:
        return agent_storage.get_active_agents()
    return agent_storage.get_all_agents()


@app.post("/api/agents")
async def create_agent(request: CreateAgentRequest):
    """Create a new agent configuration."""
    agent = agent_storage.create_agent(
        title=request.title,
        role=request.role,
        model=request.model,
        prompts=request.prompts,
        active=request.active
    )
    return agent


@app.post("/api/agents/initialize")
async def initialize_default_agents():
    """Initialize default agent templates."""
    agents = agent_storage.initialize_default_agents()
    return {"agents": agents, "count": len(agents)}


@app.get("/api/agents/chairman")
async def get_chairman_agent():
    """Get the current chairman agent configuration."""
    chairman = agent_storage.get_chairman()
    return {"chairman": chairman}


@app.put("/api/agents/chairman/{agent_id}")
async def set_chairman_agent(agent_id: str):
    """Set which agent is the chairman."""
    success = agent_storage.set_chairman(agent_id if agent_id != "default" else None)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "chairman": agent_id}


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get a specific agent configuration."""
    agent = agent_storage.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, request: UpdateAgentRequest):
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

    agent = agent_storage.update_agent(agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent configuration."""
    success = agent_storage.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True}


@app.get("/api/models")
async def get_models():
    """Get the list of council models and chairman."""
    return {
        "council": COUNCIL_MODELS,
        "chairman": CHAIRMAN_MODEL,
        "all": list(set(COUNCIL_MODELS + [CHAIRMAN_MODEL]))
    }


@app.get("/api/prompts")
async def get_prompts(model: str = None):
    """
    Get all active prompts (custom or default).

    Args:
        model: Optional model identifier to get model-specific prompts
    """
    if model:
        # Return prompts for specific model (with fallback to defaults)
        return {
            "stage1": prompt_storage.get_prompt_for_model(model, "stage1"),
            "stage2": prompt_storage.get_prompt_for_model(model, "stage2"),
            "stage3": prompt_storage.get_prompt_for_model(model, "stage3"),
        }
    else:
        # Return all prompts (defaults and per-model overrides)
        return prompt_storage.get_all_model_prompts()


@app.put("/api/prompts/{stage}")
async def update_prompt(stage: str, request: UpdatePromptRequest, model: str = None):
    """
    Update a specific stage's prompt (default or model-specific).

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

    updated_prompts = prompt_storage.update_prompt(stage, prompt_data, model)
    return updated_prompts


@app.delete("/api/prompts/{stage}")
async def reset_prompt(stage: str, model: str = None):
    """
    Reset a specific stage's prompt to default.

    Args:
        stage: The stage to reset ('stage1', 'stage2', or 'stage3')
        model: Optional model identifier for model-specific prompt
    """
    if stage not in ['stage1', 'stage2', 'stage3']:
        raise HTTPException(status_code=400, detail="Invalid stage. Must be 'stage1', 'stage2', or 'stage3'")

    updated_prompts = prompt_storage.reset_prompt(stage, model)
    return updated_prompts


@app.delete("/api/prompts")
async def reset_all_prompts():
    """Reset all prompts to defaults."""
    default_prompts = prompt_storage.reset_all_prompts()
    return default_prompts


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
