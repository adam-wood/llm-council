# TODO List - LLM Council to Board of Directors

## Phase 1: Prompt Management & Customization

- [x] **Expose prompts in frontend UI** ✅ (v0.2.0)
  - Display current Stage 1, Stage 2, and Stage 3 prompts
  - Add edit/preview mode for prompt modification
  - Real-time validation of prompt changes

- [x] **Support per-model prompt customization** ✅ (v0.2.0)
  - Refactor prompt system to allow model-specific prompts
  - Create prompt template system with variable substitution
  - Add fallback to default prompts if model-specific prompt not defined

- [x] **Agent configuration system** ✅ (v0.3.0)
  - Define agent structure: `{title, role, model, stage1_prompt, stage2_prompt}`
  - Example agents: Ethics Advisor, Leadership Coach, Technology Strategist, Financial Advisor, Career Mentor
  - Store agent configurations in persistent storage (JSON/YAML)

## Phase 2: Agent Management UI

- [x] **Agent configuration interface** ✅ (v0.4.0)
  - Add "Manage Agents" page/modal in frontend
  - CRUD operations for agents (Create, Read, Update, Delete)
  - ~~Drag-and-drop to reorder agent priority/seating~~ (deferred)

- [x] **Agent role templates** ✅ (v0.4.0)
  - Pre-built agent templates for common roles:
    - Ethics & Values Advisor
    - Leadership & Strategy Coach
    - Technology & Innovation Expert
    - Financial & Business Advisor
    - Career & Personal Development Mentor
    - Health & Wellness Counselor
    - Creativity & Innovation Catalyst
  - One-click installation of template agents

- [x] **Visual agent representation** ✅ (v0.4.0)
  - Add avatar/icon for each agent
  - Display agent role/title in Stage 1 tabs
  - Color-coding by agent category

- [ ] **Functional Improvements**
  - Allow the creation of multiple 'boards' with different sets of agents. 1 or more boards can be active at any time and receive queries. However we should optimise for 1 board to be active at any time.
    - The idea is that you could switch between a board of identical prompts between different models (useful for research) and a board of different coaches (useful for life/business guidance).

## Phase 3: Enhanced Deliberation System

- [ ] **Role-aware Stage 1 responses**
  - Each agent responds from their specialized perspective
  - Inject role context into Stage 1 prompts automatically
  - Example: "You are the Ethics Advisor on this board. Evaluate from an ethical standpoint..."

- [ ] **Role-aware Stage 2 evaluations**
  - Agents evaluate based on their expertise criteria
  - Ethics agent scores on ethical considerations
  - Tech agent scores on technical feasibility
  - Custom evaluation dimensions per agent type

- [ ] **Enhanced Stage 3 synthesis**
  - Chairman considers agent roles when synthesizing
  - Weighted synthesis based on question type (ethical question → Ethics agent weighted higher)
  - Include multi-perspective summary highlighting different viewpoints

## Phase 4: Conversation & Context Management

- [ ] **Multi-turn conversations with memory**
  - Maintain conversation context across multiple exchanges
  - Each agent remembers previous advice given to user
  - "Continue this conversation" feature

- [ ] **Topic/category tagging**
  - Tag conversations by topic (Career, Ethics, Technology, etc.)
  - Filter conversation history by category
  - Agent-specific conversation archives

- [ ] **Personal context injection**
  - Store user profile/context (goals, values, situation)
  - Automatically inject relevant context into agent prompts
  - Privacy-first: all data stored locally

## Phase 5: Analytics & Insights

- [ ] **Agent performance tracking**
  - Track which agents' advice is most frequently followed
  - User feedback on individual agent responses
  - Identify which agent types are most helpful for which questions

- [ ] **Conversation insights**
  - Export conversation summaries
  - Highlight key recommendations across multiple sessions
  - Track personal growth/decision-making patterns over time

- [ ] **Board composition recommendations**
  - Suggest additional agent types based on user questions
  - Identify gaps in current board composition

## Phase 6: Advanced Features

- [ ] **Reasoning model support**
  - Special handling for o1, o3, etc. with extended thinking time
  - Display reasoning traces when available
  - Optional reasoning-only agents

- [ ] **Async/scheduled deliberations**
  - Submit question and get answer later (for expensive models)
  - Background processing for long-running councils
  - Email/notification when deliberation complete

- [ ] **Debate mode**
  - Agents can challenge each other's responses
  - Multi-round deliberation with refinement
  - Devil's advocate agent that deliberately counters consensus

- [ ] **Private vs. shared agents**
  - Personal agents with custom context
  - Shared agent templates in community library
  - Import/export agent configurations

- [ ] **Voice/audio interface**
  - Text-to-speech for agent responses
  - Voice input for questions
  - Different voices per agent role

## Technical Debt & Improvements

- [ ] **Persist metadata to storage**
  - Save label_to_model mapping and aggregate rankings to JSON
  - Allow historical analysis of agent performance

- [ ] **Streaming responses**
  - Stream Stage 1 responses as they arrive (don't wait for all)
  - Progressive UI updates
  - Better perceived performance

- [ ] **Error handling improvements**
  - Retry logic for failed model requests
  - Fallback agents if primary agent fails
  - User-visible error states with retry options

- [ ] **Testing infrastructure**
  - Unit tests for ranking parser
  - Integration tests for full deliberation flow
  - Mock model responses for frontend testing

- [ ] **Configuration UI**
  - Move hardcoded config (models, ports) to UI-configurable settings
  - API key management in frontend
  - Model marketplace/browser integration with OpenRouter
 
- [x] Make the LLM model selectable from a drop down.
    - The dropdown options should be based on a list be stored in a config file so new models can be easily added.
      - Pre fill this config file from the available openrouter models as of 2025-12
    - The dropdown should support filter/typeahead.

- [x] Make the vertical divider between left and right hand panes movable / resizeable
- [x] Enable conversations to be deleted from sidebar
- [x] Enable the prompt that was used for each LLM/Agent response to be viewed in the conversation view. The prompt should be shown/hidden from a toggle. This is becuase the prompts can now change. 
- [ ] For the 'Aggregate Rankings (Street Cred)' section, show how the votes were calculated. This could be via a matrix where we see what each agent voted for each response. The cells could be colour coded to show clusters/patterns.

- [x] Enable responses to be easily copied in markdown format from a button. 
- [x] Add vertical scroll bar to Agent Management Screen
- [x] In conversation view, it is often neccesary to scroll for extended lengths to get to the start of each stage - suggestion: Add floating buttons in conversation view to easily jump to stage 1, 2, 3.
- [x] If openrouter indicates we have run out of credit, provide an info message to prompt the user to try again after midnight UK time.
- [x] Allow user to assign their own emoji to each agent, and persist this.
- [ ] Warning on first login that this service is a proof of concept and has not been optimised for security/privacy. Users should not enter private or confidential material into the chat.


## Documentation

- [ ] **User guide**
  - How to set up your personal board of directors
  - Best practices for agent configuration
  - Example use cases and sample questions

- [ ] **Developer documentation**
  - Architecture diagram with new agent system
  - API documentation for agent management endpoints
  - Contribution guidelines

## Future Vision Ideas

- [ ] **Agent personality tuning**
  - Adjust agent "temperature" (conservative vs. bold advice)
  - Communication style preferences (direct, gentle, Socratic)

- [ ] **Goal tracking integration**
  - Link deliberations to personal goals
  - Periodic check-ins with board on goal progress
  - Accountability partner agent

- [ ] **Decision journal**
  - Record decisions made based on board advice
  - Follow-up on outcomes
  - Learn from past decisions

- [ ] **Collaborative sessions**
  - Multiple users with their own boards
  - Shared deliberations for team decisions
  - Organizational board of directors mode
