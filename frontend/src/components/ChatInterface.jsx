import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const [activeStage, setActiveStage] = useState(null);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const stageRefs = useRef({});

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  // Track which stage is currently in view
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const containerRect = container.getBoundingClientRect();
      const containerTop = containerRect.top;
      const containerHeight = containerRect.height;

      let closestStage = null;
      let closestDistance = Infinity;

      Object.entries(stageRefs.current).forEach(([key, ref]) => {
        if (ref) {
          const rect = ref.getBoundingClientRect();
          const stageTop = rect.top - containerTop;
          const distance = Math.abs(stageTop - containerHeight * 0.3);

          if (distance < closestDistance && stageTop < containerHeight) {
            closestDistance = distance;
            closestStage = key;
          }
        }
      });

      setActiveStage(closestStage);
    };

    container.addEventListener('scroll', handleScroll);
    handleScroll(); // Initial check

    return () => container.removeEventListener('scroll', handleScroll);
  }, [conversation]);

  const scrollToStage = useCallback((stageKey) => {
    const ref = stageRefs.current[stageKey];
    if (ref) {
      ref.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  // Check if we have any stages to navigate to
  const hasStages = conversation?.messages?.some(
    (msg) => msg.role === 'assistant' && (msg.stage1 || msg.stage2 || msg.stage3)
  );

  // Get the latest message's stages for navigation
  const latestAssistantMsg = conversation?.messages
    ?.filter((msg) => msg.role === 'assistant')
    .pop();

  const availableStages = latestAssistantMsg
    ? [
        latestAssistantMsg.stage1 && 'stage1',
        latestAssistantMsg.stage2 && 'stage2',
        latestAssistantMsg.stage3 && 'stage3',
      ].filter(Boolean)
    : [];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to your Personal Boardroom</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  // Get the index of the latest assistant message for ref keys
  const latestAssistantIndex = conversation?.messages
    ?.map((msg, idx) => (msg.role === 'assistant' ? idx : -1))
    .filter((idx) => idx !== -1)
    .pop();

  return (
    <div className="chat-interface">
      <div className="messages-container" ref={messagesContainerRef}>
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the your LLM Board</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">Personal Boardroom</div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && (
                    <div
                      ref={
                        index === latestAssistantIndex
                          ? (el) => (stageRefs.current['stage1'] = el)
                          : null
                      }
                    >
                      <Stage1 responses={msg.stage1} />
                    </div>
                  )}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <div
                      ref={
                        index === latestAssistantIndex
                          ? (el) => (stageRefs.current['stage2'] = el)
                          : null
                      }
                    >
                      <Stage2
                        rankings={msg.stage2}
                        labelToModel={msg.metadata?.label_to_model}
                        aggregateRankings={msg.metadata?.aggregate_rankings}
                      />
                    </div>
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && (
                    <div
                      ref={
                        index === latestAssistantIndex
                          ? (el) => (stageRefs.current['stage3'] = el)
                          : null
                      }
                    >
                      <Stage3 finalResponse={msg.stage3} />
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Stage Navigation */}
      {hasStages && availableStages.length > 0 && (
        <div className="stage-nav">
          <div className="stage-nav-label">Jump to</div>
          {availableStages.includes('stage1') && (
            <button
              className={`stage-nav-btn ${activeStage === 'stage1' ? 'active' : ''}`}
              onClick={() => scrollToStage('stage1')}
              title="Jump to Stage 1: Individual Responses"
            >
              1
            </button>
          )}
          {availableStages.includes('stage2') && (
            <button
              className={`stage-nav-btn ${activeStage === 'stage2' ? 'active' : ''}`}
              onClick={() => scrollToStage('stage2')}
              title="Jump to Stage 2: Peer Rankings"
            >
              2
            </button>
          )}
          {availableStages.includes('stage3') && (
            <button
              className={`stage-nav-btn ${activeStage === 'stage3' ? 'active' : ''}`}
              onClick={() => scrollToStage('stage3')}
              title="Jump to Stage 3: Final Answer"
            >
              3
            </button>
          )}
        </div>
      )}

      {conversation.messages.length === 0 && (
        <form className="input-form" onSubmit={handleSubmit}>
          <textarea
            className="message-input"
            placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={3}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}
