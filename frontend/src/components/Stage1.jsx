import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);
  const [showPrompt, setShowPrompt] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = responses[activeTab]?.response;
    if (text) {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!responses || responses.length === 0) {
    return null;
  }

  const currentResponse = responses[activeTab];

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.emoji && <span className="tab-emoji">{resp.emoji}</span>}
            {resp.agent_title || resp.model.split('/')[1] || resp.model}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="agent-info">
          <div className="agent-name">
            {currentResponse.emoji && <span className="agent-emoji">{currentResponse.emoji}</span>}
            {currentResponse.agent_title || 'Agent'}
          </div>
          <div className="model-name">{currentResponse.model}</div>
          <div className="agent-actions">
            {currentResponse.prompt && (
              <button
                className="toggle-prompt-btn"
                onClick={() => setShowPrompt(!showPrompt)}
              >
                {showPrompt ? '🔼 Hide Prompt' : '🔽 Show Prompt'}
              </button>
            )}
            <button
              className="copy-btn"
              onClick={handleCopy}
              title="Copy response as markdown"
            >
              {copied ? '✓ Copied' : '📋 Copy'}
            </button>
          </div>
        </div>
        {showPrompt && currentResponse.prompt && (
          <div className="prompt-display">
            <h4>Prompt Used:</h4>
            <pre className="prompt-text">{currentResponse.prompt}</pre>
          </div>
        )}
        <div className="response-text markdown-content">
          <ReactMarkdown>{currentResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
