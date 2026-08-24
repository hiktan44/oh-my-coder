// src/components/LangSwitch.tsx — Language switcher component (TR/EN toggle)
import React from 'react';
import { useT, pickByLang } from '../lib/i18n';
import './LangSwitch.css';

export function LangSwitch() {
  const { lang, setLang, t } = useT();
  
  return (
    <button
      onClick={() => setLang(lang === 'tr' ? 'en' : 'tr')}
      className="lang-switch"
      aria-label={pickByLang(lang, 'Switch to English', 'Türkçe\'ye geç')}
      title={pickByLang(lang, 'Switch to English', 'Türkçe\'ye geç')}
    >
      <span className="lang-switch__current">{lang.toUpperCase()}</span>
      <span className="lang-switch__arrow">→</span>
      <span className="lang-switch__target">{(lang === 'tr' ? 'en' : 'tr').toUpperCase()}</span>
    </button>
  );
}

export default LangSwitch;
