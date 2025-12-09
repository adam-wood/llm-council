import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);
  const [showPrompt, setShowPrompt] = useState(false);

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
            {resp.agent_title || resp.model.split('/')[1] || resp.model}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="agent-info">
          <div className="agent-name">
            {currentResponse.agent_title || 'Agent'}
          </div>
          <div className="model-name">{currentResponse.model}</div>
          {currentResponse.prompt && (
            <button
              className="toggle-prompt-btn"
              onClick={() => setShowPrompt(!showPrompt)}
            >
              {showPrompt ? '🔼 Hide Prompt' : '🔽 Show Prompt'}
            </button>
          )}
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
