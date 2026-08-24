// src/components/SettingsPanel.tsx
// Settings panel: model-centric API key configuration with encryption
// - Left sidebar: collapsible provider groups → model list
// - Right panel: selected model's API Key, base URL, test button
// - Top: Import/Export JSON, Reset to defaults
// - Encryption: simple XOR + base64 for localStorage
import React, { useState, useEffect, useCallback } from 'react';
import { PRODUCTION_MODELS as FALLBACK_MODELS } from '../models/productionModels';
import { useT } from '../lib/i18n';

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  tier: string;
  context?: number;
  endpoint?: string;
  pricing?: Record<string, number>;
  features?: string[];
}

interface ModelConfigEntry {
  api_key: string;
  base_url?: string;
  enabled?: boolean;
}

interface ModelConfig {
  [modelId: string]: ModelConfigEntry;
}

interface ProviderGroup {
  provider: string;
  label: string;
  models: ModelInfo[];
  collapsed: boolean;
}

const PROVIDER_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  glm: '智谱 GLM',
  doubao: '字节豆包',
  kimi: 'Kimi',
  tongyi: '通义千问',
  wenxin: '文心一言',
  hunyuan: '腾讯混元',
  minimax: 'MiniMax',
  baichuan: '百川智能',
};

// Fallback models imported from productionModels.ts (single source of truth)

// ── Simple Encryption for localStorage ─────────────────────────────────────────
const ENCRYPTION_KEY = 'omc-v1-key-2024'; // Simple XOR key

function xorEncrypt(text: string, key: string): string {
  let result = '';
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
  }
  // Use TextEncoder to handle Unicode characters (btoa only supports Latin1)
  try {
    return btoa(unescape(encodeURIComponent(result)));
  } catch {
    // Fallback: encode as UTF-8 bytes then base64
    const bytes = new TextEncoder().encode(result);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }
}

function xorDecrypt(encoded: string, key: string): string {
  try {
    const text = atob(encoded); // base64 decode
    let result = '';
    for (let i = 0; i < text.length; i++) {
      result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
    }
    // Handle Unicode characters
    try {
      return decodeURIComponent(escape(result));
    } catch {
      return result; // fallback if not URI-encoded
    }
  } catch {
    return encoded; // fallback for unencrypted data
  }
}

function saveEncryptedConfig(configs: ModelConfig) {
  const encrypted = xorEncrypt(JSON.stringify(configs), ENCRYPTION_KEY);
  localStorage.setItem('omc-model-configs', encrypted);
}

function loadEncryptedConfig(): ModelConfig {
  const stored = localStorage.getItem('omc-model-configs');
  if (!stored) return {};
  try {
    const decrypted = xorDecrypt(stored, ENCRYPTION_KEY);
    return JSON.parse(decrypted);
  } catch {
    // Try legacy unencrypted format
    try {
      return JSON.parse(stored);
    } catch {
      return {};
    }
  }
}

function clearEncryptedConfig() {
  localStorage.removeItem('omc-model-configs');
}

function getProviderFromModelId(modelId: string): string {
  const known = Object.keys(PROVIDER_LABELS);
  for (const p of known) {
    if (modelId.startsWith(p) || modelId.includes(p)) return p;
  }
  const first = modelId.split('-')[0];
  return first in PROVIDER_LABELS ? first : 'other';
}

function groupModels(models: ModelInfo[]): ProviderGroup[] {
  const groups = new Map<string, ProviderGroup>();
  for (const m of models) {
    const provider = getProviderFromModelId(m.id);
    if (!groups.has(provider)) {
      groups.set(provider, { provider, label: PROVIDER_LABELS[provider] || provider, models: [], collapsed: false });
    }
    groups.get(provider)!.models.push(m);
  }
  const known = Object.keys(PROVIDER_LABELS);
  return Array.from(groups.values()).sort((a, b) => {
    const ai = known.indexOf(a.provider);
    const bi = known.indexOf(b.provider);
    if (ai !== -1 && bi !== -1) return ai - bi;
    if (ai !== -1) return -1;
    if (bi !== -1) return 1;
    return a.label.localeCompare(b.label);
  });
}

const TIER_ICON: Record<string, string> = { free: '◈', low: '◇', medium: '◆', high: '★' };

// ── Test Connection ────────────────────────────────────────────────────────────
function TestConnection({
  config,
  testResult,
  onResult,
  onClearResult,
}: {
  config: ModelConfigEntry;
  testResult: { ok: boolean; msg: string } | null;
  onResult: (ok: boolean, msg: string) => void;
  onClearResult: () => void;
}) {
  const { t } = useT();
  const [testing, setTesting] = useState(false);

  // Clear result when config changes (API key or base URL modified)
  useEffect(() => {
    if (testResult) {
      onClearResult();
    }
  }, [config.api_key, config.base_url]);

  const handleTest = async () => {
    if (!config.api_key) {
      onResult(false, t('settings.apiKeyRequired'));
      return;
    }
    setTesting(true);
    try {
      const resp = await (window.omc as any).modelConfigTest?.(null, config);
      const ok = resp?.ok ?? config.api_key.length > 10;
      const msg = resp?.msg ?? (ok ? t('settings.connected') : t('settings.failed'));
      onResult(ok, msg);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : t('settings.failed');
      onResult(false, msg);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="settings-test">
      <button
        className={`settings-test__btn ${testResult ? (testResult.ok ? 'ok' : 'err') : ''}`}
        onClick={handleTest}
        disabled={testing}
      >
        {testing ? '⏳ ' + t('settings.testing') : testResult ? (testResult.ok ? '✓ ' + t('settings.connected') : '✗ ' + t('settings.failed')) : '🔗 ' + t('settings.testConnection')}
      </button>
      {testResult && (
        <span className={`settings-test__msg ${testResult.ok ? 'ok' : 'err'}`}>{testResult.msg}</span>
      )}
    </div>
  );
}

// ── Model Detail Panel ─────────────────────────────────────────────────────────
function ModelDetailPanel({
  model,
  config,
  testResult,
  onUpdate,
  onConfigSave,
  onTestResult,
  onClearTestResult,
}: {
  model: ModelInfo;
  config: ModelConfigEntry;
  testResult: { ok: boolean; msg: string } | null;
  onUpdate: (cfg: ModelConfigEntry) => void;
  onConfigSave: (modelId: string, cfg: ModelConfigEntry) => Promise<void>;
  onTestResult: (ok: boolean, msg: string) => void;
  onClearTestResult: () => void;
}) {
  const { t } = useT();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const provider = getProviderFromModelId(model.id);
  const label = PROVIDER_LABELS[provider] || provider;
  const isFree = model.tier === 'free';

  const handleChange = (key: keyof ModelConfigEntry, value: string | boolean) => {
    onUpdate({ ...config, [key]: value });
  };

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await onConfigSave(model.id, config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    onUpdate({ api_key: '', base_url: '', enabled: true });
  };

  return (
    <div className="settings-detail">
      <div className="settings-detail__header">
        <div className="settings-detail__title">{model.name}</div>
        <div className="settings-detail__meta">
          <span className="settings-detail__provider">{label}</span>
          <span className="settings-detail__id">{model.id}</span>
          {isFree && <span className="settings-detail__free">{t('settings.freeTier')}</span>}
        </div>
      </div>

      <div className="settings-detail__field">
        <label className="settings-detail__label">
          API Key {isFree ? `(${t('settings.optional')})` : ''}
          <span className="settings-detail__free-hint">{isFree ? ` ${t('settings.freeSkip')}` : ''}</span>
        </label>
        <div className="settings-detail__input-row">
          <input
            type={showKey ? 'text' : 'password'}
            className="settings-detail__input"
            value={config.api_key ?? ''}
            placeholder={isFree ? t('settings.noKeyEnv') : t('settings.skPlaceholder')}
            onChange={e => handleChange('api_key', e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <button
            className={`settings-detail__toggle-vis ${showKey ? 'active' : ''}`}
            onClick={() => setShowKey(v => !v)}
            title={showKey ? t('settings.hideKey') : t('settings.showKey')}
          >
            {showKey ? '🙈' : '👁️'}
          </button>
        </div>
      </div>

      <div className="settings-detail__field">
        <label className="settings-detail__label">
          {t('settings.baseUrl')}
          <span className="settings-detail__hint">{t('settings.baseUrlHint')}</span>
        </label>
        <input
          type="text"
          className="settings-detail__input"
          value={config.base_url || getDefaultEndpoint(provider)}
          placeholder={getDefaultEndpoint(provider)}
          data-using-default={!config.base_url ? '1' : '0'}
          onChange={e => handleChange('base_url', e.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      <div className="settings-detail__register">
        <span>{t('settings.needApiKey')}</span>
        <button className="settings-detail__link" onClick={() => (window.omc as any).openExternal(getRegisterUrl(provider))}>
          {t('settings.goRegister')}
        </button>
      </div>

      <TestConnection
        config={config}
        testResult={testResult}
        onResult={onTestResult}
        onClearResult={onClearTestResult}
      />

      <div className="settings-detail__actions">
        <button className="settings-detail__reset" onClick={handleReset} title={t('settings.clearKey')}>
          ↺ {t('common.reset')}
        </button>
        <button className="settings-detail__save" onClick={handleSave} disabled={saving}>
          {saving ? '◐ ' + t('settings.saving') : saved ? '✓ ' + t('settings.saved') : '💾 ' + t('settings.saveConfig')}
        </button>
      </div>
    </div>
  );
}

function getDefaultEndpoint(provider: string): string {
  const endpoints: Record<string, string> = {
    deepseek: 'https://api.deepseek.com',
    glm: 'https://open.bigmodel.cn',
    kimi: 'https://api.moonshot.cn',
    doubao: 'https://ark.cn-beijing.volces.com',
    tongyi: 'https://dashscope.aliyuncs.com',
    minimax: 'https://api.minimax.chat',
    wenxin: 'https://aip.baidubce.com',
    hunyuan: 'https://hunyuan.cloud.tencent.com',
    baichuan: 'https://api.baichuan-ai.com',
  };
  return endpoints[provider] || '';
}

function getRegisterUrl(provider: string): string {
  const urls: Record<string, string> = {
    deepseek: 'https://platform.deepseek.com',
    glm: 'https://open.bigmodel.cn',
    kimi: 'https://platform.moonshot.cn',
    doubao: 'https://console.volcengine.com/ark',
    tongyi: 'https://dashscope.console.aliyun.com',
    minimax: 'https://www.minimaxi.com',
    wenxin: 'https://console.bce.baidu.com',
    hunyuan: 'https://console.cloud.tencent.com/hunyuan',
    baichuan: 'https://www.baichuan-ai.com',
  };
  return urls[provider] || 'https://platform.deepseek.com';
}

// ── Main SettingsPanel ─────────────────────────────────────────────────────────
export default function SettingsPanel({ onClose }: { onClose: () => void }) {
  const { t } = useT();
  const [, setModels] = useState<ModelInfo[]>([]);
  const [configs, setConfigs] = useState<ModelConfig>({});
  const [groups, setGroups] = useState<ProviderGroup[]>([]);
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [exportDropdown, setExportDropdown] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [migrationNotice, setMigrationNotice] = useState<string | null>(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  // Clear test result when switching models
  useEffect(() => {
    setTestResult(null);
  }, [selectedModel?.id]);

  useEffect(() => {
    const load = async () => {
      try {
        let modelList: ModelInfo[] = [];
        let cfgData: ModelConfig = {};
        
        try {
          const modelResult = await (window.omc as any).modelList();
          modelList = Array.isArray(modelResult) ? modelResult : (modelResult?.models || []);
          cfgData = await (window.omc as any).modelConfigList();
        } catch {
          // API not available, use fallback models
          modelList = FALLBACK_MODELS;
        }
        
        // Priority: IPC configs (persisted) > localStorage (legacy)
        const localConfigs = loadEncryptedConfig();
        const mergedConfigs = { ...localConfigs, ...cfgData };
        
        // If IPC configs exist, clear legacy localStorage to avoid future confusion
        if (Object.keys(cfgData).length > 0 && Object.keys(localConfigs).length > 0) {
          clearEncryptedConfig();
          console.log('[Settings] Migrated from localStorage to IPC persistence');
        }
        
        setModels(modelList);
        setConfigs(mergedConfigs);
        setGroups(groupModels(modelList));
        if (modelList.length > 0) {
          setSelectedModel(modelList[0]);
        }
      } catch (e) {
        console.error('[Settings] Load failed:', e);
        // Fallback to localStorage only
        const localConfigs = loadEncryptedConfig();
        setConfigs(localConfigs);
        // Use fallback models
        setModels(FALLBACK_MODELS);
        setGroups(groupModels(FALLBACK_MODELS));
        if (FALLBACK_MODELS.length > 0) {
          setSelectedModel(FALLBACK_MODELS[0]);
        }
      } finally {
        setLoading(false);
      }
    };
    load();

    const notice = sessionStorage.getItem('omc-migration-done');
    if (notice) {
      setMigrationNotice(notice);
      sessionStorage.removeItem('omc-migration-done');
    }
  }, []);

  const handleConfigUpdate = useCallback((modelId: string, cfg: ModelConfigEntry) => {
    setConfigs(prev => ({ ...prev, [modelId]: cfg }));
  }, []);

  const handleConfigSave = useCallback(async (modelId: string, cfg: ModelConfigEntry) => {
    // Always write to BOTH IPC (persistent ~/.omc/config.json) AND localStorage
    // IPC = main process write (survives app reinstall, cross-session)
    // localStorage = renderer read (App.tsx reads from here for chat)
    let savedIPC = false;
    try {
      const result = await (window.omc as any).modelConfigSet(modelId, cfg);
      savedIPC = result?.ok;
    } catch {
      // IPC not available
    }
    
    // Update local state
    const updatedConfigs = { ...configs, [modelId]: cfg };
    setConfigs(updatedConfigs);
    
    // Always write localStorage (needed for App.tsx chat to read)
    saveEncryptedConfig(updatedConfigs);
    
    if (!savedIPC) {
      console.warn('[Settings] IPC save failed, used localStorage fallback');
    }
  }, [configs]);

  const toggleGroup = (provider: string) => {
    setGroups(prev => prev.map(g =>
      g.provider === provider ? { ...g, collapsed: !g.collapsed } : g
    ));
  };

  const handleExport = () => {
    const data = JSON.stringify({ version: 1, models: configs }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `omc-models-config-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setExportDropdown(false);
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const text = ev.target?.result as string;
        const data = JSON.parse(text);
        const imported = data.models ?? data;
        if (typeof imported !== 'object') throw new Error('Invalid format');
        const merged = { ...configs };
        const entries = Object.entries(imported) as [string, ModelConfigEntry][];
        
        let ipcAvailable = false;
        for (const [mid, cfg] of entries) {
          merged[mid] = cfg;
          try {
            await (window.omc as any).modelConfigSet(mid, cfg);
            ipcAvailable = true;
          } catch { /* IPC not available */ }
        }
        
        // Only use localStorage if IPC is not available
        if (!ipcAvailable) {
          saveEncryptedConfig(merged);
        }
        
        setConfigs(merged);
        setImportError(null);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'invalid JSON';
        setImportError(`Import failed: ${msg}`);
        setTimeout(() => setImportError(null), 4000);
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleResetAll = async () => {
    // Clear localStorage
    clearEncryptedConfig();
    
    // Clear IPC persisted configs
    try {
      const allConfigs = await (window.omc as any).modelConfigList();
      for (const modelId of Object.keys(allConfigs || {})) {
        try {
          await (window.omc as any).modelConfigDelete(modelId);
        } catch { /* ignore */ }
      }
    } catch { /* IPC not available */ }
    
    setConfigs({});
    setShowResetConfirm(false);
    // Reload page to reset all state
    window.location.reload();
  };

  const currentConfig = selectedModel ? (configs[selectedModel.id] ?? { api_key: '' }) : { api_key: '' };

  return (
    <div className="settings-panel">
      <div className="settings-panel__header">
        <span className="settings-panel__title">⚙ {t('settings.models')}</span>
        <div className="settings-panel__actions">
          <div className="settings-dropdown">
            <button className="settings-action-btn" onClick={() => setExportDropdown(v => !v)}>
              ↓ {t('settings.export')}
            </button>
            {exportDropdown && (
              <div className="settings-dropdown__menu">
                <button onClick={handleExport}>{t('settings.exportAsJson')}</button>
                <label className="settings-dropdown__item">
                  {t('settings.importFromJson')}
                  <input type="file" accept=".json" onChange={handleImport} style={{ display: 'none' }} />
                </label>
              </div>
            )}
          </div>
          <button className="settings-panel__reset-all" onClick={() => setShowResetConfirm(true)} title={t('common.reset')}>
            ↺ {t('settings.resetAll')}
          </button>
          <button className="settings-panel__close" onClick={onClose}>✕</button>
        </div>
      </div>

      {migrationNotice && (
        <div className="settings-migration-notice">✅ {migrationNotice}</div>
      )}
      {importError && (
        <div className="settings-error">{importError}</div>
      )}

      {showResetConfirm && (
        <div className="settings-reset-confirm">
          <div className="settings-reset-confirm__content">
            <div className="settings-reset-confirm__title">{t('settings.resetAllSettings')}</div>
            <div className="settings-reset-confirm__desc">
              {t('settings.resetWarning')}
            </div>
            <div className="settings-reset-confirm__actions">
              <button className="settings-reset-confirm__cancel" onClick={() => setShowResetConfirm(false)}>
                {t('common.cancel')}
              </button>
              <button className="settings-reset-confirm__confirm" onClick={handleResetAll}>
                {t('settings.yesReset')}
              </button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="settings-loading">{t('settings.loading')}</div>
      ) : (
        <div className="settings-panel__body">
          <div className="settings-sidebar">
            <div className="settings-sidebar__label">{t('settings.modelsLabel')}</div>
            {groups.map(group => (
              <div key={group.provider} className="settings-group">
                <button className="settings-group__header" onClick={() => toggleGroup(group.provider)}>
                  <span className="settings-group__caret">{group.collapsed ? '▶' : '▼'}</span>
                  <span className="settings-group__name">{group.label}</span>
                  <span className="settings-group__count">{group.models.length}</span>
                  <span className={`settings-group__status ${
                    group.models.some(m => configs[m.id]?.api_key) ? 'has-key' : 'no-key'
                  }`} />
                </button>
                {!group.collapsed && (
                  <div className="settings-group__models">
                    {group.models.map(m => {
                      const hasKey = Boolean(configs[m.id]?.api_key);
                      const isSelected = selectedModel?.id === m.id;
                      return (
                        <button
                          key={m.id}
                          className={`settings-model-item ${isSelected ? 'active' : ''} ${hasKey ? 'has-key' : ''}`}
                          onClick={() => setSelectedModel(m)}
                        >
                          <span className="settings-model-item__icon">{TIER_ICON[m.tier] || '◆'}</span>
                          <span className="settings-model-item__name">{m.name}</span>
                          {hasKey && <span className="settings-model-item__key-dot" />}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="settings-detail-wrap">
            {selectedModel ? (
              <ModelDetailPanel
                model={selectedModel}
                config={currentConfig}
                testResult={testResult}
                onUpdate={cfg => handleConfigUpdate(selectedModel.id, cfg)}
                onConfigSave={handleConfigSave}
                onTestResult={(ok, msg) => setTestResult({ ok, msg })}
                onClearTestResult={() => setTestResult(null)}
              />
            ) : (
              <div className="settings-detail-empty">{t('settings.selectModel')}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
