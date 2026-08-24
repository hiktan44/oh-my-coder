// src/components/ModelSelector.tsx — Model selection dropdown
// Triggered by click or Cmd+M, shows grouped model list with tier icons

import { useState, useEffect, useRef, useCallback } from 'react';
import { useT } from '../lib/i18n';

// ── Types ──────────────────────────────────────────────────────────────────────
interface Model {
  id: string;
  name: string;
  provider: string;
  tier: string;
  context?: number;
  endpoint?: string;
  pricing?: Record<string, number>;
  features?: string[];
}

interface ModelSelectorProps {
  models: Model[];
  current: string;
  onSwitch: (id: string) => void;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  trigger: React.ReactNode;
}

// ── Tier display ───────────────────────────────────────────────────────────────
const TIER_ICON: Record<string, string> = { free: '◈', low: '◇', medium: '◆', high: '★' };
const TIER_COLOR: Record<string, string> = {
  free: '#4ade80',
  low: '#94a3b8',
  medium: '#d4a017',
  high: '#f59e0b',
};

// ── Provider labels (will be replaced with translation function) ────────────────────
function getProviderLabel(key: string, lang: string): string {
  const labels: Record<string, { tr: string; en: string }> = {
    deepseek: { tr: 'DeepSeek', en: 'DeepSeek' },
    glm: { tr: 'Zhipu GLM', en: 'Zhipu GLM' },
    doubao: { tr: 'ByteDance Doubao', en: 'ByteDance Doubao' },
    kimi: { tr: 'Kimi', en: 'Kimi' },
    tongyi: { tr: 'Tongyi Qianwen', en: 'Tongyi Qianwen' },
    wenxin: { tr: 'Wenxin Yiyan', en: 'Wenxin Yiyan' },
    hunyuan: { tr: 'Tencent Hunyuan', en: 'Tencent Hunyuan' },
    minimax: { tr: 'MiniMax', en: 'MiniMax' },
    baichuan: { tr: 'Baichuan AI', en: 'Baichuan AI' },
    openai: { tr: 'OpenAI', en: 'OpenAI' },
    anthropic: { tr: 'Anthropic', en: 'Anthropic' },
    google: { tr: 'Google', en: 'Google' },
  };
  return labels[key]?.[lang === 'tr' ? 'tr' : 'en'] || key;
}

function getProviderKey(model: Model): string {
  const id = model.id.toLowerCase();
  const provider = (model.provider || '').toLowerCase();
  // Check id prefix first, then provider field
  for (const key of Object.keys(PROVIDER_LABELS)) {
    if (id.includes(key) || provider.includes(key)) return key;
  }
  return provider || 'other';
}

interface ProviderGroup {
  key: string;
  label: string;
  models: Model[];
}

function groupByProvider(models: Model[], lang: string): ProviderGroup[] {
  const map = new Map<string, ProviderGroup>();
  const knownOrder = ['deepseek', 'glm', 'doubao', 'kimi', 'tongyi', 'wenxin', 'hunyuan', 'minimax', 'baichuan', 'openai', 'anthropic', 'google'];

  for (const m of models) {
    const key = getProviderKey(m);
    if (!map.has(key)) {
      map.set(key, {
        key,
        label: getProviderLabel(key, lang),
        models: [],
      });
    }
    map.get(key)!.models.push(m);
  }

  // Sort: known providers first (by defined order), then alphabetically
  return Array.from(map.values()).sort((a, b) => {
    const ai = knownOrder.indexOf(a.key);
    const bi = knownOrder.indexOf(b.key);
    if (ai !== -1 && bi !== -1) return ai - bi;
    if (ai !== -1) return -1;
    if (bi !== -1) return 1;
    return a.label.localeCompare(b.label);
  });
}

// ── Component ──────────────────────────────────────────────────────────────────
export function ModelSelector({
  models,
  current,
  onSwitch,
  open,
  onOpenChange,
  trigger,
}: ModelSelectorProps) {
  const { lang } = useT();
  const ref = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState('');
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const searchRef = useRef<HTMLInputElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;

    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onOpenChange(false);
      }
    };

    // Delay to avoid the opening click closing immediately
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClick);
    }, 0);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClick);
    };
  }, [open, onOpenChange]);

  // Focus search on open
  useEffect(() => {
    if (open) {
      setSearch('');
      setTimeout(() => searchRef.current?.focus(), 50);
    }
  }, [open]);

  // Keyboard: Esc to close
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onOpenChange(false);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onOpenChange]);

  const handleSelect = useCallback(
    (id: string) => {
      onSwitch(id);
      onOpenChange(false);
    },
    [onSwitch, onOpenChange]
  );

  const toggleGroup = useCallback((key: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // Filter models by search
  const query = search.toLowerCase().trim();
  const groups = groupByProvider(models, lang);
  const filteredGroups = query
    ? groups
        .map((g) => ({
          ...g,
          models: g.models.filter(
            (m) =>
              m.name.toLowerCase().includes(query) ||
              m.id.toLowerCase().includes(query) ||
              g.label.toLowerCase().includes(query)
          ),
        }))
        .filter((g) => g.models.length > 0)
    : groups;

  return (
    <div className="model-selector" ref={ref}>
      {/* Trigger */}
      <div onClick={() => onOpenChange(!open)}>{trigger}</div>

      {/* Dropdown */}
      {open && (
        <div className="model-selector__dropdown">
          {/* Search */}
          <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
            <input
              ref={searchRef}
              type="text"
              className="model-selector__search"
              placeholder={t('model.searchPlaceholder')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--bg-2)',
                border: '1px solid var(--border-2)',
                borderRadius: 'var(--radius)',
                padding: '6px 10px',
                color: 'var(--text)',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
              }}
            />
          </div>

          {/* Shortcut hint */}
          <div className="model-selector__shortcut-hint">
            <kbd>⌘</kbd>
            <kbd>M</kbd>
            <span style={{ marginLeft: 4 }}>{t('model.toggle')}</span>
          </div>

          {/* Model list */}
          <div
            style={{
              maxHeight: 320,
              overflowY: 'auto',
              padding: '4px 0',
            }}
          >
            {filteredGroups.length === 0 && (
              <div
                style={{
                  padding: '16px 14px',
                  color: 'var(--gray-3)',
                  fontSize: '12px',
                  textAlign: 'center',
                }}
              >
                {t('model.noModelsFound')}
              </div>
            )}
            {filteredGroups.map((group) => {
              const isCollapsed = collapsedGroups.has(group.key);
              return (
                <div key={group.key}>
                  {/* Provider group header */}
                  <button
                    className="model-selector__item"
                    style={{
                      fontWeight: 600,
                      fontSize: '10px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                      color: 'var(--gray-3)',
                      cursor: 'pointer',
                      paddingTop: 6,
                      paddingBottom: 4,
                    }}
                    onClick={() => toggleGroup(group.key)}
                  >
                    <span style={{ fontSize: 8, marginRight: 4 }}>
                      {isCollapsed ? '▶' : '▼'}
                    </span>
                    {group.label}
                    <span style={{ marginLeft: 'auto', fontWeight: 400, fontSize: 10 }}>
                      {group.models.length}
                    </span>
                  </button>

                  {/* Models in group */}
                  {!isCollapsed &&
                    group.models.map((m) => {
                      const isActive = m.id === current;
                      const tier = m.tier || 'low';
                      return (
                        <button
                          key={m.id}
                          className={`model-selector__item${isActive ? ' active' : ''}`}
                          onClick={() => handleSelect(m.id)}
                        >
                          <span style={{ color: TIER_COLOR[tier] || TIER_COLOR.low }}>
                            {TIER_ICON[tier] || '◇'}
                          </span>
                          <span className="model-selector__item-name">{m.name}</span>
                          <span className="model-selector__provider">{m.id}</span>
                        </button>
                      );
                    })}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default ModelSelector;
