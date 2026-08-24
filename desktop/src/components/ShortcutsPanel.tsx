// src/components/ShortcutsPanel.tsx — Keyboard shortcuts help panel
// Reference: OpenCode-style categorized shortcuts with search and click-to-execute

import { useEffect, useRef, useState, useMemo } from 'react';
import { useT } from '../lib/i18n';

// ── Types ─────────────────────────────────────────────────────────────────────
export interface ShortcutItem {
  id: string;
  key: string;
  metaKey?: boolean;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  description: string;
  category: 'global' | 'editor' | 'chat';
  action?: () => void;
}

interface ShortcutsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onExecute?: (shortcut: ShortcutItem) => void;
}

// ── Category Labels (will be replaced with translation function) ─────────────────
function getCategoryLabel(category: string, lang: string): { label: string; icon: string } {
  const labels: Record<string, { tr: { label: string; icon: string }; en: { label: string; icon: string } }> = {
    global: {
      tr: { label: 'Genel', icon: '⌘' },
      en: { label: 'Global', icon: '⌘' }
    },
    editor: {
      tr: { label: 'Editör', icon: '✎' },
      en: { label: 'Editor', icon: '✎' }
    },
    chat: {
      tr: { label: 'Sohbet', icon: '💬' },
      en: { label: 'Chat', icon: '💬' }
    },
  };
  return labels[category]?.[lang === 'tr' ? 'tr' : 'en'] || { label: category, icon: '⌘' };
}

function getShortcutDescription(id: string, lang: string): string {
  const descriptions: Record<string, { tr: string; en: string }> = {
    'new-chat': { tr: 'Yeni Sohbet', en: 'New Chat' },
    'settings': { tr: 'Ayarları Aç', en: 'Open Settings' },
    'shortcuts': { tr: 'Kısayolları Göster', en: 'Show Shortcuts' },
    'escape': { tr: 'Paneli Kapat/İptal', en: 'Close Panel/Cancel' },
    'focus-input': { tr: 'Giriş Kutusuna Odaklan', en: 'Focus Input' },
    'inline-edit': { tr: 'Satır İçi Düzenleme', en: 'Inline Edit' },
    'submit': { tr: 'Mesaj Gönder', en: 'Send Message' },
    'newline': { tr: 'Yeni Satır', en: 'Newline' },
    'switch-model': { tr: 'Model Değiştir', en: 'Switch Model' },
    'clear-chat': { tr: 'Sohbeti Temizle', en: 'Clear Chat' },
    'history-prev': { tr: 'Önceki Geçmiş', en: 'Previous History' },
    'history-next': { tr: 'Sonraki Geçmiş', en: 'Next History' },
  };
  return descriptions[id]?.[lang === 'tr' ? 'tr' : 'en'] || id;
}

// ── All Registered Shortcuts (base definitions, descriptions will be translated) ──
const BASE_SHORTCUTS: Omit<ShortcutItem, 'description'>[] = [
  // Global
  { id: 'new-chat', key: 'n', metaKey: true, category: 'global' },
  { id: 'settings', key: ',', metaKey: true, category: 'global' },
  { id: 'shortcuts', key: '/', metaKey: true, category: 'global' },
  { id: 'escape', key: 'Escape', category: 'global' },

  // Editor
  { id: 'focus-input', key: 'i', metaKey: true, category: 'editor' },
  { id: 'inline-edit', key: 'e', metaKey: true, category: 'editor' },
  { id: 'submit', key: 'Enter', category: 'editor' },
  { id: 'newline', key: 'Enter', shiftKey: true, category: 'editor' },

  // Chat
  { id: 'switch-model', key: 'm', metaKey: true, category: 'chat' },
  { id: 'clear-chat', key: 'l', metaKey: true, category: 'chat' },
  { id: 'history-prev', key: 'ArrowUp', altKey: true, category: 'chat' },
  { id: 'history-next', key: 'ArrowDown', altKey: true, category: 'chat' },
];

// ── Format Key Combo ──────────────────────────────────────────────────────────
function formatKeyCombo(s: ShortcutItem): string {
  const parts: string[] = [];
  
  if (s.metaKey || s.ctrlKey) parts.push('⌘');
  if (s.ctrlKey && !s.metaKey) parts[0] = 'Ctrl';
  if (s.altKey) parts.push('⌥');
  if (s.shiftKey) parts.push('⇧');
  
  // Format key name
  const keyMap: Record<string, string> = {
    'Escape': 'Esc',
    'ArrowUp': '↑',
    'ArrowDown': '↓',
    'ArrowLeft': '←',
    'ArrowRight': '→',
    'Enter': '↵',
    'Tab': '⇥',
    'Backspace': '⌫',
    'Delete': '⌦',
    ' ': 'Space',
  };
  
  parts.push(keyMap[s.key] || s.key.toUpperCase());
  return parts.join('');
}

// ── Key Combo Component ───────────────────────────────────────────────────────
function KeyCombo({ shortcut, small }: { shortcut: ShortcutItem; small?: boolean }) {
  const keys = [];
  if (shortcut.metaKey || shortcut.ctrlKey) keys.push('⌘');
  if (shortcut.ctrlKey && !shortcut.metaKey) keys[0] = 'Ctrl';
  if (shortcut.altKey) keys.push('⌥');
  if (shortcut.shiftKey) keys.push('⇧');
  
  const keyMap: Record<string, string> = {
    'Escape': 'Esc', 'ArrowUp': '↑', 'ArrowDown': '↓',
    'ArrowLeft': '←', 'ArrowRight': '→', 'Enter': '↵',
    'Tab': '⇥', 'Backspace': '⌫', 'Delete': '⌦', ' ': 'Space',
  };
  keys.push(keyMap[shortcut.key] || shortcut.key.toUpperCase());
  
  return (
    <span className={`key-combo ${small ? 'key-combo--small' : ''}`}>
      {keys.map((k, i) => (
        <kbd key={i} className="key-combo__key">{k}</kbd>
      ))}
    </span>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function ShortcutsPanel({ isOpen, onClose, onExecute }: ShortcutsPanelProps) {
  const { t, lang } = useT();
  const overlayRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Generate shortcuts with translated descriptions
  const ALL_SHORTCUTS: ShortcutItem[] = useMemo(() => {
    return BASE_SHORTCUTS.map(shortcut => ({
      ...shortcut,
      description: getShortcutDescription(shortcut.id, lang)
    }));
  }, [lang]);

  // Focus search on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSearch('');
      setSelectedId(null);
    }
  }, [isOpen]);

  // Filter shortcuts
  const filtered = useMemo(() => {
    if (!search.trim()) return ALL_SHORTCUTS;
    const q = search.toLowerCase();
    return ALL_SHORTCUTS.filter(s =>
      s.description.toLowerCase().includes(q) ||
      formatKeyCombo(s).toLowerCase().includes(q) ||
      s.category.toLowerCase().includes(q)
    );
  }, [search, ALL_SHORTCUTS]);

  // Group by category
  const grouped = useMemo(() => {
    const groups: Record<string, ShortcutItem[]> = {};
    filtered.forEach(s => {
      if (!groups[s.category]) groups[s.category] = [];
      groups[s.category].push(s);
    });
    return groups;
  }, [filtered]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Close on overlay click
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose();
  };

  // Execute shortcut
  const handleExecute = (s: ShortcutItem) => {
    setSelectedId(s.id);
    onExecute?.(s);
    // Visual feedback
    setTimeout(() => setSelectedId(null), 200);
  };

  if (!isOpen) return null;

  return (
    <div 
      ref={overlayRef}
      className="shortcuts-overlay"
      onClick={handleOverlayClick}
    >
      <div className="shortcuts-panel shortcuts-panel--enhanced">
        {/* Header with search */}
        <div className="shortcuts-header">
          <div className="shortcuts-header__left">
            <span className="shortcuts-title">{t('shortcuts.title')}</span>
            <span className="shortcuts-count">{filtered.length}</span>
          </div>
          <button className="shortcuts-close" onClick={onClose} aria-label={t('common.close')}>✕</button>
        </div>

        {/* Search bar */}
        <div className="shortcuts-search">
          <span className="shortcuts-search__icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            className="shortcuts-search__input"
            placeholder={t('shortcuts.search')}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button 
              className="shortcuts-search__clear" 
              onClick={() => { setSearch(''); inputRef.current?.focus(); }}
            >
              ✕
            </button>
          )}
          <span className="shortcuts-search__hint">
            <KeyCombo small shortcut={{ key: '/', metaKey: true, description: '', category: 'global' }} />
          </span>
        </div>
        
        {/* Body with categories */}
        <div className="shortcuts-body shortcuts-body--scrollable">
          {Object.keys(grouped).length === 0 ? (
            <div className="shortcuts-empty">
              <span className="shortcuts-empty__icon">🔍</span>
              <span>{t('shortcuts.notFound')}</span>
            </div>
          ) : (
            Object.entries(grouped).map(([category, items]) => {
              const catLabel = getCategoryLabel(category, lang);
              return (
                <div key={category} className="shortcuts-section">
                  <div className="shortcuts-section__header">
                    <span className="shortcuts-section__icon">
                      {catLabel.icon}
                    </span>
                    <span className="shortcuts-section__title">
                      {catLabel.label}
                    </span>
                    <span className="shortcuts-section__count">{items.length}</span>
                  </div>
                <div className="shortcuts-list">
                  {items.map(s => (
                    <div
                      key={s.id}
                      className={`shortcuts-item ${selectedId === s.id ? 'shortcuts-item--active' : ''}`}
                      onClick={() => handleExecute(s)}
                      title={t('shortcuts.execute')}
                    >
                      <span className="shortcuts-item__desc">{s.description}</span>
                      <KeyCombo shortcut={s} />
                    </div>
                  ))}
                </div>
              </div>
              );
            })
          )}
        </div>
        
        {/* Footer */}
        <div className="shortcuts-footer">
          <span className="shortcuts-hint">
            <KeyCombo small shortcut={{ key: 'Enter', description: '', category: 'global' }} />
            {t('shortcuts.execute')}
          </span>
          <span className="shortcuts-hint">
            <KeyCombo small shortcut={{ key: 'Escape', description: '', category: 'global' }} />
            {t('common.close')}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Exports ───────────────────────────────────────────────────────────────────
export { BASE_SHORTCUTS as SHORTCUTS, formatKeyCombo };
export default ShortcutsPanel;

