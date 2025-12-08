/**
 * API client for the LLM Council backend.
 */

const API_BASE = 'http://localhost:8001';

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  /**
   * Get the list of models.
   */
  async getModels() {
    const response = await fetch(`${API_BASE}/api/models`);
    if (!response.ok) {
      throw new Error('Failed to get models');
    }
    return response.json();
  },

  /**
   * Get all active prompts.
   * @param {string} model - Optional model identifier
   */
  async getPrompts(model = null) {
    const url = model
      ? `${API_BASE}/api/prompts?model=${encodeURIComponent(model)}`
      : `${API_BASE}/api/prompts`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to get prompts');
    }
    return response.json();
  },

  /**
   * Update a specific stage's prompt.
   * @param {string} stage - The stage to update ('stage1', 'stage2', or 'stage3')
   * @param {object} promptData - The prompt configuration
   * @param {string} model - Optional model identifier for model-specific prompt
   */
  async updatePrompt(stage, promptData, model = null) {
    const url = model
      ? `${API_BASE}/api/prompts/${stage}?model=${encodeURIComponent(model)}`
      : `${API_BASE}/api/prompts/${stage}`;
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(promptData),
    });
    if (!response.ok) {
      throw new Error('Failed to update prompt');
    }
    return response.json();
  },

  /**
   * Reset a specific stage's prompt to default.
   * @param {string} stage - The stage to reset
   * @param {string} model - Optional model identifier for model-specific prompt
   */
  async resetPrompt(stage, model = null) {
    const url = model
      ? `${API_BASE}/api/prompts/${stage}?model=${encodeURIComponent(model)}`
      : `${API_BASE}/api/prompts/${stage}`;
    const response = await fetch(url, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to reset prompt');
    }
    return response.json();
  },

  /**
   * Reset all prompts to defaults.
   */
  async resetAllPrompts() {
    const response = await fetch(`${API_BASE}/api/prompts`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to reset all prompts');
    }
    return response.json();
  },
};
