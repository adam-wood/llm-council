import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with the agent title or model name
  Object.entries(labelToModel).forEach(([label, info]) => {
    const displayName = info.agent_title || info.model?.split('/')[1] || info.model || label;
    result = result.replace(new RegExp(label, 'g'), `**${displayName}**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const [activeTab, setActiveTab] = useState(0);
  const [showPrompt, setShowPrompt] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = rankings[activeTab]?.ranking;
    if (text) {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!rankings || rankings.length === 0) {
    return null;
  }

  const currentRanking = rankings[activeTab];

  return (
    <div className="stage stage2">
      <h3 className="stage-title">Stage 2: Peer Rankings</h3>

      <h4>Raw Evaluations</h4>
      <p className="stage-description">
        Each model evaluated all responses (anonymized as Response A, B, C, etc.) and provided rankings.
        Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
      </p>

      <div className="tabs">
        {rankings.map((rank, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {rank.agent_title || rank.model.split('/')[1] || rank.model}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="agent-info">
          <div className="agent-name">
            {currentRanking.agent_title || 'Agent'}
          </div>
          <div className="ranking-model">
            {currentRanking.model}
          </div>
          <div className="agent-actions">
            {currentRanking.prompt && (
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
              title="Copy evaluation as markdown"
            >
              {copied ? '✓ Copied' : '📋 Copy'}
            </button>
          </div>
        </div>
        {showPrompt && currentRanking.prompt && (
          <div className="prompt-display">
            <h4>Prompt Used:</h4>
            <pre className="prompt-text">{currentRanking.prompt}</pre>
          </div>
        )}
        <div className="ranking-content markdown-content">
          <ReactMarkdown>
            {deAnonymizeText(currentRanking.ranking, labelToModel)}
          </ReactMarkdown>
        </div>

        {currentRanking.parsed_ranking &&
         currentRanking.parsed_ranking.length > 0 && (
          <div className="parsed-ranking">
            <strong>Extracted Ranking:</strong>
            <ol>
              {currentRanking.parsed_ranking.map((label, i) => {
                const info = labelToModel && labelToModel[label];
                const displayName = info?.agent_title || info?.model?.split('/')[1] || info?.model || label;
                return <li key={i}>{displayName}</li>;
              })}
            </ol>
          </div>
        )}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings (Street Cred)</h4>
          <p className="stage-description">
            Combined results across all peer evaluations (lower score is better):
          </p>
          <div className="aggregate-list">
            {aggregateRankings.map((agg, index) => (
              <div key={index} className="aggregate-item">
                <span className="rank-position">#{index + 1}</span>
                <span className="rank-model">
                  {agg.agent_title || agg.model.split('/')[1] || agg.model}
                </span>
                <span className="rank-score">
                  Avg: {agg.average_rank.toFixed(2)}
                </span>
                <span className="rank-count">
                  ({agg.rankings_count} votes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
