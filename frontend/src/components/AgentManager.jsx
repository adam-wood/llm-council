import { useState, useEffect } from 'react';
import { api } from '../api';
import './AgentManager.css';

// Agent role templates with pre-defined configurations
const AGENT_TEMPLATES = [
  {
    title: 'Ethics & Values Advisor',
    role: 'Provides ethical guidance and helps evaluate decisions through a moral lens, considering values, principles, and long-term consequences.',
    model: 'anthropic/claude-sonnet-4.5',
    icon: '⚖️',
    color: '#9b59b6',
    prompts: {
      stage1: 'You are the Ethics & Values Advisor on a personal board of directors. Evaluate the following question from an ethical perspective, considering moral principles, values, and long-term consequences:\n\n{user_query}'
    }
  },
  {
    title: 'Technology & Innovation Expert',
    role: 'Offers technical insights, evaluates technological feasibility, and provides guidance on innovation and digital transformation.',
    model: 'openai/gpt-5.1',
    icon: '💻',
    color: '#3498db',
    prompts: {
      stage1: 'You are the Technology & Innovation Expert on a personal board of directors. Analyze the following question from a technical and innovation perspective:\n\n{user_query}'
    }
  },
  {
    title: 'Leadership & Strategy Coach',
    role: 'Provides strategic guidance, leadership development advice, and helps with long-term planning and decision-making.',
    model: 'google/gemini-3-pro-preview',
    icon: '🎯',
    color: '#e74c3c',
    prompts: {
      stage1: 'You are the Leadership & Strategy Coach on a personal board of directors. Provide strategic and leadership-focused guidance on:\n\n{user_query}'
    }
  },
  {
    title: 'Financial & Business Advisor',
    role: 'Offers financial insights, business strategy, and helps evaluate economic implications of decisions.',
    model: 'x-ai/grok-4',
    icon: '💰',
    color: '#f39c12',
    prompts: {
      stage1: 'You are the Financial & Business Advisor on a personal board of directors. Analyze the following from a financial and business perspective:\n\n{user_query}'
    }
  },
  {
    title: 'Health & Wellness Counselor',
    role: 'Provides guidance on physical and mental health, work-life balance, and sustainable personal development.',
    model: 'anthropic/claude-sonnet-4.5',
    icon: '🏥',
    color: '#27ae60',
    prompts: {
      stage1: 'You are the Health & Wellness Counselor on a personal board of directors. Provide health and wellness guidance on:\n\n{user_query}'
    }
  },
  {
    title: 'Career & Personal Development Mentor',
    role: 'Offers career advice, helps with professional development, and provides guidance on personal growth and skills development.',
    model: 'openai/gpt-5.1',
    icon: '📈',
    color: '#16a085',
    prompts: {
      stage1: 'You are the Career & Personal Development Mentor on a personal board of directors. Provide career and personal development guidance on:\n\n{user_query}'
    }
  },
  {
    title: 'Creativity & Innovation Catalyst',
    role: 'Helps unlock creative thinking, provides fresh perspectives, and encourages innovative problem-solving approaches.',
    model: 'google/gemini-3-pro-preview',
    icon: '🎨',
    color: '#e67e22',
    prompts: {
      stage1: 'You are the Creativity & Innovation Catalyst on a personal board of directors. Provide creative and innovative perspectives on:\n\n{user_query}'
    }
  }
];

function AgentManager() {
  const [agents, setAgents] = useState([]);
  const [chairman, setChairman] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  // Edit/create agent modal state
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
  const [editingAgent, setEditingAgent] = useState(null);

  // Template selection modal
  const [showTemplates, setShowTemplates] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [agentsData, chairmanData] = await Promise.all([
        api.getAgents(),
        api.getChairman(),
      ]);
      setAgents(agentsData);
      setChairman(chairmanData.chairman);
      setError(null);
    } catch (err) {
      setError('Failed to load agents: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAgent = (template = null) => {
    setModalMode('create');
    setEditingAgent(template || {
      title: '',
      role: '',
      model: 'anthropic/claude-sonnet-4.5',
      prompts: {},
      active: true
    });
    setShowModal(true);
    setShowTemplates(false);
  };

  const handleEditAgent = (agent) => {
    setModalMode('edit');
    setEditingAgent({ ...agent });
    setShowModal(true);
  };

  const handleDeleteAgent = async (agent) => {
    if (!confirm(`Delete agent "${agent.title}"? This cannot be undone.`)) {
      return;
    }

    try {
      await api.deleteAgent(agent.id);
      await loadData();
      showSuccessMessage(`Deleted agent "${agent.title}"`);
    } catch (err) {
      setError('Failed to delete agent: ' + err.message);
    }
  };

  const handleSaveAgent = async () => {
    try {
      if (modalMode === 'create') {
        await api.createAgent(editingAgent);
        showSuccessMessage('Agent created successfully!');
      } else {
        const { id, created_at, updated_at, ...updates } = editingAgent;
        await api.updateAgent(id, updates);
        showSuccessMessage('Agent updated successfully!');
      }
      await loadData();
      setShowModal(false);
      setEditingAgent(null);
    } catch (err) {
      setError('Failed to save agent: ' + err.message);
    }
  };

  const handleToggleActive = async (agent) => {
    try {
      await api.updateAgent(agent.id, { active: !agent.active });
      await loadData();
      showSuccessMessage(`${agent.active ? 'Deactivated' : 'Activated'} agent "${agent.title}"`);
    } catch (err) {
      setError('Failed to toggle agent: ' + err.message);
    }
  };

  const handleSetChairman = async (agentId) => {
    try {
      await api.setChairman(agentId);
      await loadData();
      showSuccessMessage('Chairman updated successfully!');
    } catch (err) {
      setError('Failed to set chairman: ' + err.message);
    }
  };

  const handleInitializeDefaults = async () => {
    if (!confirm('Initialize default agents? This will create 4 pre-configured board members.')) {
      return;
    }

    try {
      await api.initializeDefaultAgents();
      await loadData();
      showSuccessMessage('Default agents initialized successfully!');
    } catch (err) {
      setError('Failed to initialize default agents: ' + err.message);
    }
  };

  const showSuccessMessage = (message) => {
    setSaveMessage(message);
    setTimeout(() => setSaveMessage(''), 3000);
  };

  const getAgentIcon = (agent) => {
    // Find matching template by title to get icon
    const template = AGENT_TEMPLATES.find(t => t.title === agent.title);
    return template?.icon || '🤖';
  };

  const getAgentColor = (agent) => {
    const template = AGENT_TEMPLATES.find(t => t.title === agent.title);
    return template?.color || '#95a5a6';
  };

  if (loading) {
    return <div className="agent-manager loading">Loading agents...</div>;
  }

  return (
    <div className="agent-manager">
      <div className="agent-manager-header">
        <h2>Manage Your Board of Directors</h2>
        <p className="header-description">
          Configure specialized AI agents that provide expert perspectives on your questions.
        </p>

        {error && <div className="error-message">{error}</div>}
        {saveMessage && <div className="success-message">{saveMessage}</div>}

        <div className="header-actions">
          <button
            className="btn btn-primary"
            onClick={() => setShowTemplates(true)}
          >
            + Add from Template
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => handleCreateAgent()}
          >
            + Create Custom Agent
          </button>
          {agents.length === 0 && (
            <button
              className="btn btn-accent"
              onClick={handleInitializeDefaults}
            >
              Initialize Default Board
            </button>
          )}
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="no-agents">
          <div className="no-agents-icon">🤖</div>
          <h3>No agents configured</h3>
          <p>Get started by initializing the default board or creating custom agents.</p>
        </div>
      ) : (
        <div className="agents-grid">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className={`agent-card ${!agent.active ? 'inactive' : ''} ${chairman?.id === agent.id ? 'chairman' : ''}`}
              style={{ borderLeftColor: getAgentColor(agent) }}
            >
              <div className="agent-header">
                <div className="agent-icon" style={{ backgroundColor: getAgentColor(agent) }}>
                  {getAgentIcon(agent)}
                </div>
                <div className="agent-title-section">
                  <h3>{agent.title}</h3>
                  {chairman?.id === agent.id && (
                    <span className="chairman-badge">Chairman</span>
                  )}
                </div>
                <div className="agent-status">
                  {agent.active ? '🟢' : '⚫'}
                </div>
              </div>

              <p className="agent-role">{agent.role}</p>
              <div className="agent-model">{agent.model}</div>

              <div className="agent-actions">
                <button
                  className="btn-icon"
                  onClick={() => handleEditAgent(agent)}
                  title="Edit agent"
                >
                  ✏️
                </button>
                <button
                  className="btn-icon"
                  onClick={() => handleToggleActive(agent)}
                  title={agent.active ? 'Deactivate' : 'Activate'}
                >
                  {agent.active ? '⏸️' : '▶️'}
                </button>
                {chairman?.id !== agent.id && (
                  <button
                    className="btn-icon"
                    onClick={() => handleSetChairman(agent.id)}
                    title="Set as chairman"
                  >
                    👑
                  </button>
                )}
                <button
                  className="btn-icon delete"
                  onClick={() => handleDeleteAgent(agent)}
                  title="Delete agent"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Agent Edit/Create Modal */}
      {showModal && editingAgent && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>{modalMode === 'create' ? 'Create Agent' : 'Edit Agent'}</h2>

            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                value={editingAgent.title}
                onChange={(e) => setEditingAgent({ ...editingAgent, title: e.target.value })}
                placeholder="e.g., Ethics & Values Advisor"
              />
            </div>

            <div className="form-group">
              <label>Role</label>
              <textarea
                value={editingAgent.role}
                onChange={(e) => setEditingAgent({ ...editingAgent, role: e.target.value })}
                placeholder="Describe what expertise this agent provides..."
                rows={3}
              />
            </div>

            <div className="form-group">
              <label>Model</label>
              <input
                type="text"
                value={editingAgent.model}
                onChange={(e) => setEditingAgent({ ...editingAgent, model: e.target.value })}
                placeholder="e.g., anthropic/claude-sonnet-4.5"
              />
            </div>

            <div className="form-group">
              <label>Stage 1 Prompt (Optional)</label>
              <textarea
                value={editingAgent.prompts?.stage1 || ''}
                onChange={(e) => setEditingAgent({
                  ...editingAgent,
                  prompts: { ...editingAgent.prompts, stage1: e.target.value }
                })}
                placeholder="Custom prompt for this agent's initial response. Use {user_query} as placeholder."
                rows={4}
              />
            </div>

            <div className="form-group checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={editingAgent.active}
                  onChange={(e) => setEditingAgent({ ...editingAgent, active: e.target.checked })}
                />
                Active
              </label>
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleSaveAgent}>
                {modalMode === 'create' ? 'Create' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Template Selection Modal */}
      {showTemplates && (
        <div className="modal-overlay" onClick={() => setShowTemplates(false)}>
          <div className="modal-content templates-modal" onClick={(e) => e.stopPropagation()}>
            <h2>Choose Agent Template</h2>
            <p className="modal-description">
              Select from pre-configured agent templates to quickly build your board.
            </p>

            <div className="templates-grid">
              {AGENT_TEMPLATES.map((template, idx) => (
                <div
                  key={idx}
                  className="template-card"
                  style={{ borderLeftColor: template.color }}
                  onClick={() => handleCreateAgent(template)}
                >
                  <div className="template-icon" style={{ backgroundColor: template.color }}>
                    {template.icon}
                  </div>
                  <h3>{template.title}</h3>
                  <p>{template.role}</p>
                  <div className="template-model">{template.model}</div>
                </div>
              ))}
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowTemplates(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentManager;
