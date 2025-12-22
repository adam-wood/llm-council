import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  currentView,
  onViewChange,
}) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>Personal Boardroom</h1>
        <div className="view-switcher">
          <button
            className={`view-btn ${currentView === 'chat' ? 'active' : ''}`}
            onClick={() => onViewChange('chat')}
          >
            Conversations
          </button>
          <button
            className={`view-btn ${currentView === 'agents' ? 'active' : ''}`}
            onClick={() => onViewChange('agents')}
          >
            Manage Board
          </button>
          <button
            className={`view-btn ${currentView === 'prompts' ? 'active' : ''}`}
            onClick={() => onViewChange('prompts')}
          >
            Manage Prompts
          </button>
        </div>
      </div>

      {currentView === 'chat' && (
        <>
          <button className="new-conversation-btn" onClick={onNewConversation}>
            + New Conversation
          </button>

          <div className="conversation-list">
            {conversations.length === 0 ? (
              <div className="no-conversations">No conversations yet</div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item ${
                    conv.id === currentConversationId ? 'active' : ''
                  }`}
                >
                  <div
                    className="conversation-content"
                    onClick={() => onSelectConversation(conv.id)}
                  >
                    <div className="conversation-title">
                      {conv.title || 'New Conversation'}
                    </div>
                    <div className="conversation-meta">
                      {conv.message_count} messages
                    </div>
                  </div>
                  <button
                    className="delete-conversation-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete "${conv.title || 'New Conversation'}"?`)) {
                        onDeleteConversation(conv.id);
                      }
                    }}
                    title="Delete conversation"
                  >
                    🗑️
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {currentView === 'agents' && (
        <div className="prompts-sidebar-info">
          <p>Configure your personal board of directors - specialized AI agents that provide perspective-aware guidance.</p>
        </div>
      )}

      {currentView === 'prompts' && (
        <div className="prompts-sidebar-info">
          <p>Configure the prompts used in each stage of the council deliberation process.</p>
        </div>
      )}
    </div>
  );
}
