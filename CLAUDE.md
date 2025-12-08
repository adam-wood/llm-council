# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

**Evolution to Board of Directors:** The project now supports an agent-based system where each LLM can be configured as a specialized board member (Ethics Advisor, Tech Expert, etc.) with custom prompts and roles, transforming the generic council into a personal board of advisors.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` (list of OpenRouter model identifiers)
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`openrouter.py`**
- `query_model()`: Single async model query
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with 'content' and optional 'reasoning_details'
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic (Agent-Aware as of v0.3.0)
- `stage1_collect_responses()`:
  - Loads active agents from storage (falls back to COUNCIL_MODELS if none)
  - Each agent uses their custom prompt with priority: agent-specific → model-specific → default
  - Returns list with `agent_id`, `agent_title`, `model`, and `response`
- `stage2_collect_rankings()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping with both `agent_title` and `model` for de-anonymization
  - Each agent evaluates with their custom prompt (same fallback hierarchy)
  - Returns tuple: (rankings_list, label_to_model_dict)
  - Each ranking includes `agent_id`, `agent_title`, `model`, raw text, and `parsed_ranking` list
- `stage3_synthesize_final()`:
  - Uses designated chairman agent or falls back to CHAIRMAN_MODEL
  - Chairman uses their custom prompt with same fallback hierarchy
  - Context includes agent titles instead of raw model names for readability
  - Returns dict with `agent_title`, `model`, and `response`
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section, handles both numbered lists and plain format
- `calculate_aggregate_rankings()`: Computes average rank position by agent_title across all peer evaluations

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, stage1, stage2, stage3}`
- Note: metadata (label_to_model, aggregate_rankings) is NOT persisted to storage, only returned via API

**`agent_storage.py`** (v0.3.0)
- JSON-based agent storage in `data/agents.json`
- Agent structure: `{id, title, role, model, prompts{}, active, created_at, updated_at}`
- CRUD operations: create, get, update, delete agents
- Chairman designation separate from council members
- `initialize_default_agents()` creates 4 pre-configured board members
- Falls back to `COUNCIL_MODELS` in config if no agents exist

**`prompt_storage.py`** (v0.2.0)
- JSON-based prompt storage in `data/prompts.json`
- Structure: `{defaults: {stage1, stage2, stage3}, models: {model_id: {stage1, stage2, stage3}}}`
- Supports default prompts and per-model overrides
- `get_prompt_for_model()` implements fallback chain: model-specific → default
- All prompts use template variables like `{user_query}`, `{responses_text}`, etc.

**`prompts.py`** (v0.2.0)
- Defines `DEFAULT_PROMPTS` for all three stages
- Each prompt includes: name, description, template, and notes about variables
- Provides `get_stage_prompt()` for easy prompt retrieval

**`main.py`**
- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- POST `/api/conversations/{id}/message` returns metadata in addition to stages
- Metadata includes: label_to_model mapping and aggregate_rankings

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage
- Important: metadata is stored in the UI state for display but not persisted to backend JSON

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding

**`components/Stage1.jsx`**
- Tab view of individual model responses
- ReactMarkdown rendering with markdown-content wrapper

**`components/Stage2.jsx`**
- **Critical Feature**: Tab view showing RAW evaluation text from each model
- De-anonymization happens CLIENT-SIDE for display (models receive anonymous labels)
- Shows "Extracted Ranking" below each evaluation so users can validate parsing
- Aggregate rankings shown with average position and vote count
- Explanatory text clarifies that boldface model names are for readability only

**`components/Stage3.jsx`**
- Final synthesized answer from chairman
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Agent System Architecture (v0.3.0)

### Agent Configuration
Agents are the foundation of the Board of Directors concept. Each agent represents a specialized advisor:

**Agent Data Structure:**
```json
{
  "id": "uuid",
  "title": "Ethics & Values Advisor",
  "role": "Provides ethical guidance...",
  "model": "anthropic/claude-sonnet-4.5",
  "prompts": {
    "stage1": "You are the Ethics & Values Advisor...",
    "stage2": "optional custom stage2 prompt",
    "stage3": "optional custom stage3 prompt"
  },
  "active": true,
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

**Prompt Fallback Hierarchy:**
When an agent needs a prompt, the system checks in this order:
1. Agent-specific prompt (from agent's `prompts` dict)
2. Model-specific prompt (from prompt_storage for that model)
3. Default prompt (from DEFAULT_PROMPTS)

This allows maximum flexibility: define prompts per-agent, per-model, or use sensible defaults.

**Chairman vs Council:**
- Council members (agents) participate in all 3 stages
- Chairman is designated from existing agents (or uses fallback CHAIRMAN_MODEL)
- Chairman only participates in Stage 3 synthesis

**Legacy Fallback:**
If no agents are configured, the system falls back to `COUNCIL_MODELS` from config, creating pseudo-agents on-the-fly with model names as titles.

### Default Agent Templates
Four pre-configured agents demonstrate the Board of Directors concept:
1. **Ethics & Values Advisor** - Evaluates moral implications
2. **Technology & Innovation Expert** - Analyzes technical feasibility
3. **Leadership & Strategy Coach** - Provides strategic guidance
4. **Financial & Business Advisor** - Evaluates economic impact

Each has a role-aware Stage 1 prompt that instructs them to respond from their specialized perspective.

## Key Design Decisions

### Stage 2 Prompt Format
The Stage 2 prompt is very specific to ensure parseable output:
```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations.

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency
- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration
Models are hardcoded in `backend/config.py`. Chairman can be same or different from council members. The current default is Gemini as chairman per user preference.

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order
4. **Missing Metadata**: Metadata is ephemeral (not persisted), only available in API responses

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file
- Streaming responses instead of batch loading
- Export conversations to markdown/PDF
- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling

## Testing Notes

Use `test_openrouter.py` to verify API connectivity and test different model identifiers before adding to council. The script tests both streaming and non-streaming modes.

## Data Flow Summary

```
User Query
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Stage 2: Anonymize → Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context
    ↓
Return: {stage1, stage2, stage3, metadata}
    ↓
Frontend: Display with tabs + validation UI
```

The entire flow is async/parallel where possible to minimize latency.
