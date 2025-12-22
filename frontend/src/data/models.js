/**
 * Predefined list of OpenRouter models.
 * Add or remove models as needed - this list is for convenience only.
 * Users can still enter custom model identifiers not in this list.
 *
 * Format: provider/model-name
 * Source: OpenRouter available models as of December 2025
 */

const MODELS = [
  // Anthropic
  'anthropic/claude-opus-4.5',
  'anthropic/claude-sonnet-4.5',
  'anthropic/claude-opus-4',
  'anthropic/claude-3.5-sonnet',
  'anthropic/claude-3.5-haiku',
  'anthropic/claude-3-opus',

  // OpenAI
  'openai/gpt-5.2-pro',
  'openai/gpt-5.2',
  'openai/gpt-5.2-chat',
  'openai/gpt-5.1',
  'openai/gpt-4.1',
  'openai/gpt-4.1-mini',
  'openai/gpt-4o',
  'openai/gpt-4o-mini',
  'openai/o1',
  'openai/o1-mini',
  'openai/o1-pro',
  'openai/o3',
  'openai/o3-mini',
  'openai/o4-mini',

  // Google
  'google/gemini-3-pro-preview',
  'google/gemini-3-flash-preview',
  'google/gemini-2.5-pro',
  'google/gemini-2.5-flash',
  'google/gemini-2.0-flash',
  'google/gemini-2.0-flash-lite',

  // xAI
  'x-ai/grok-4',
  'x-ai/grok-3',
  'x-ai/grok-3-mini',
  'x-ai/grok-2',

  // Meta
  'meta-llama/llama-4-maverick',
  'meta-llama/llama-4-scout',
  'meta-llama/llama-3.3-70b-instruct',
  'meta-llama/llama-3.1-405b-instruct',

  // Mistral
  'mistralai/mistral-large',
  'mistralai/mistral-medium',
  'mistralai/mistral-small',
  'mistralai/codestral',

  // DeepSeek
  'deepseek/deepseek-r1',
  'deepseek/deepseek-chat',
  'deepseek/deepseek-coder',

  // Cohere
  'cohere/command-r-plus',
  'cohere/command-r',

  // Perplexity
  'perplexity/sonar-pro',
  'perplexity/sonar',
];

export default MODELS;
