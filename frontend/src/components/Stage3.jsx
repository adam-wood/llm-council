import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage3.css';

export default function Stage3({ finalResponse }) {
  const [showPrompt, setShowPrompt] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = finalResponse?.response;
    if (text) {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!finalResponse) {
    return null;
  }

  return (
    <div className="stage stage3">
      <h3 className="stage-title">Stage 3: Final Council Answer</h3>
      <div className="final-response">
        <div className="chairman-info">
          <div className="chairman-label">
            {finalResponse.emoji && <span className="chairman-emoji">{finalResponse.emoji}</span>}
            Chairman: {finalResponse.agent_title || 'Chairman'}
          </div>
          <div className="chairman-model">
            {finalResponse.model}
          </div>
          <div className="chairman-actions">
            {finalResponse.prompt && (
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
        {showPrompt && finalResponse.prompt && (
          <div className="prompt-display">
            <h4>Prompt Used:</h4>
            <pre className="prompt-text">{finalResponse.prompt}</pre>
          </div>
        )}
        <div className="final-text markdown-content">
          <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
