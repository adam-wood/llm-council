import { useState, useEffect } from 'react';
import './PromptManager.css';

function PromptManager({ api }) {
  const [prompts, setPrompts] = useState(null);
  const [models, setModels] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedStage, setSelectedStage] = useState('stage1');
  const [selectedModel, setSelectedModel] = useState('defaults');
  const [editedPrompt, setEditedPrompt] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (prompts && selectedModel) {
      loadPromptForSelection();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStage, selectedModel, prompts]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [promptsData, modelsData] = await Promise.all([
        api.getPrompts(),
        api.getModels(),
      ]);
      setPrompts(promptsData);
      setModels(modelsData);
      setError(null);
    } catch (err) {
      setError('Failed to load data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadPromptForSelection = () => {
    if (!prompts) return;

    let promptData;
    if (selectedModel === 'defaults') {
      promptData = prompts.defaults[selectedStage];
    } else {
      // Check if there's a model-specific override
      if (prompts.models[selectedModel] && prompts.models[selectedModel][selectedStage]) {
        promptData = {
          ...prompts.defaults[selectedStage],
          ...prompts.models[selectedModel][selectedStage],
          _hasOverride: true
        };
      } else {
        // Use default but mark that there's no override
        promptData = {
          ...prompts.defaults[selectedStage],
          _hasOverride: false
        };
      }
    }

    setEditedPrompt(promptData);
    setIsEditing(false);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setSaveMessage('');

      const dataToSave = {
        name: editedPrompt.name,
        description: editedPrompt.description,
        template: editedPrompt.template,
        notes: editedPrompt.notes || ''
      };

      const model = selectedModel === 'defaults' ? null : selectedModel;
      await api.updatePrompt(selectedStage, dataToSave, model);
      await loadData();
      setIsEditing(false);
      setSaveMessage('Saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      setError('Failed to save prompt: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    const modelName = selectedModel === 'defaults' ? 'default' : selectedModel;
    if (!confirm(`Reset ${selectedStage} for ${modelName} to default?`)) {
      return;
    }

    try {
      setSaving(true);
      setSaveMessage('');
      const model = selectedModel === 'defaults' ? null : selectedModel;
      await api.resetPrompt(selectedStage, model);
      await loadData();
      setIsEditing(false);
      setSaveMessage('Reset to default!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      setError('Failed to reset prompt: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleResetAll = async () => {
    if (!confirm('Reset ALL prompts to defaults? This cannot be undone.')) {
      return;
    }

    try {
      setSaving(true);
      setSaveMessage('');
      await api.resetAllPrompts();
      await loadData();
      setIsEditing(false);
      setSaveMessage('All prompts reset to defaults!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      setError('Failed to reset all prompts: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    loadPromptForSelection();
    setIsEditing(false);
  };

  if (loading) {
    return <div className="prompt-manager loading">Loading prompts...</div>;
  }

  if (error) {
    return (
      <div className="prompt-manager error">
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={loadData}>Retry</button>
      </div>
    );
  }

  const hasOverride = editedPrompt && editedPrompt._hasOverride;
  const isModelSpecific = selectedModel !== 'defaults';

  return (
    <div className="prompt-manager">
      <div className="prompt-header">
        <h1>Prompt Management</h1>
        <p className="prompt-subtitle">
          Customize the prompts used in each stage of the council deliberation
        </p>
      </div>

      {saveMessage && <div className="save-message">{saveMessage}</div>}

      <div className="model-selector">
        <label htmlFor="model-select">Edit prompts for:</label>
        <select
          id="model-select"
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          disabled={saving}
        >
          <option value="defaults">Defaults (All Models)</option>
          <optgroup label="Council Members">
            {models?.council.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </optgroup>
          {models?.chairman && !models.council.includes(models.chairman) && (
            <optgroup label="Chairman">
              <option value={models.chairman}>{models.chairman}</option>
            </optgroup>
          )}
        </select>
        {isModelSpecific && (
          <div className="model-hint">
            {hasOverride ? (
              <span className="override-badge">Has custom override</span>
            ) : (
              <span className="default-badge">Using default prompts</span>
            )}
          </div>
        )}
      </div>

      <div className="stage-tabs">
        {['stage1', 'stage2', 'stage3'].map((stage) => (
          <button
            key={stage}
            className={`stage-tab ${selectedStage === stage ? 'active' : ''}`}
            onClick={() => setSelectedStage(stage)}
          >
            {prompts.defaults[stage]?.name || stage}
          </button>
        ))}
      </div>

      {editedPrompt && (
        <div className="prompt-editor">
          <div className="prompt-field">
            <label htmlFor="prompt-name">Name</label>
            <input
              id="prompt-name"
              type="text"
              value={editedPrompt.name}
              onChange={(e) => {
                setEditedPrompt({ ...editedPrompt, name: e.target.value });
                setIsEditing(true);
              }}
              disabled={saving}
            />
          </div>

          <div className="prompt-field">
            <label htmlFor="prompt-description">Description</label>
            <input
              id="prompt-description"
              type="text"
              value={editedPrompt.description}
              onChange={(e) => {
                setEditedPrompt({
                  ...editedPrompt,
                  description: e.target.value,
                });
                setIsEditing(true);
              }}
              disabled={saving}
            />
          </div>

          <div className="prompt-field">
            <label htmlFor="prompt-template">Prompt Template</label>
            <div className="template-info">
              Available variables: {editedPrompt.notes}
            </div>
            <textarea
              id="prompt-template"
              value={editedPrompt.template}
              onChange={(e) => {
                setEditedPrompt({ ...editedPrompt, template: e.target.value });
                setIsEditing(true);
              }}
              rows={20}
              disabled={saving}
              className="template-editor"
            />
          </div>

          <div className="prompt-field">
            <label htmlFor="prompt-notes">Notes</label>
            <textarea
              id="prompt-notes"
              value={editedPrompt.notes || ''}
              onChange={(e) => {
                setEditedPrompt({ ...editedPrompt, notes: e.target.value });
                setIsEditing(true);
              }}
              rows={3}
              disabled={saving}
            />
          </div>

          <div className="prompt-actions">
            <div className="action-group">
              {isEditing && (
                <>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="btn-primary"
                  >
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                  <button
                    onClick={handleCancel}
                    disabled={saving}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                </>
              )}
              {!isEditing && (isModelSpecific && hasOverride || !isModelSpecific) && (
                <button
                  onClick={handleReset}
                  disabled={saving}
                  className="btn-warning"
                >
                  {isModelSpecific ? 'Remove Override' : 'Reset to Default'}
                </button>
              )}
            </div>
            <button
              onClick={handleResetAll}
              disabled={saving}
              className="btn-danger"
            >
              Reset All Prompts
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default PromptManager;
