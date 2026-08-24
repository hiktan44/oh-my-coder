import React from 'react';
import { useT } from '../lib/i18n';

interface WelcomeScreenProps {
  onExampleClick: (task: string) => void;
}

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onExampleClick }) => {
  const { t, lang } = useT();

  const EXAMPLES = [
    {
      icon: '🌐',
      title: lang === 'tr' ? 'REST API Geliştirme' : 'REST API Development',
      desc: lang === 'tr' ? 'FastAPI Kullanıcı Yönetimi CRUD' : 'FastAPI User Management CRUD',
      task: lang === 'tr'
        ? 'CRUD işlemlerini içeren bir REST API kullanıcı yönetimi arayüzü geliştirin, FastAPI çerçevesini kullanarak'
        : 'Implement a REST API user management interface with CRUD operations using FastAPI framework',
      workflow: 'build',
    },
    {
      icon: '🔍',
      title: lang === 'tr' ? 'Kod İncelemesi' : 'Code Review',
      desc: lang === 'tr' ? 'Kalite + Güvenlik Kontrolü' : 'Quality + Security Check',
      task: lang === 'tr'
        ? 'Mevcut projenin kod kalitesini ve güvenlik açıklarını inceleyin'
        : 'Review the code quality and security vulnerabilities of the current project',
      workflow: 'review',
    },
    {
      icon: '🐛',
      title: lang === 'tr' ? 'Hata Ayıklama' : 'Bug Debugging',
      desc: lang === 'tr' ? 'Sorunları Bul ve Düzelt' : 'Locate and Fix Issues',
      task: lang === 'tr'
        ? 'Giriş sayfasının düzgün yönlendirilememesi sorununu düzeltin'
        : 'Fix the issue where the login page does not redirect correctly',
      workflow: 'debug',
    },
    {
      icon: '🧪',
      title: lang === 'tr' ? 'Test Senaryoları' : 'Test Cases',
      desc: lang === 'tr' ? 'Temel Mantık Tam Kapsama' : 'Core Logic Full Coverage',
      task: lang === 'tr'
        ? 'Projenin temel iş mantığını kapsayan birim testleri yazın'
        : 'Write unit tests for the project that cover core business logic',
      workflow: 'test',
    },
  ];

  return (
    <div className="welcome">
      <div className="welcome__icon">⬡</div>
      <div className="welcome__title">{t('welcome.title')}</div>
      <div className="welcome__sub">{t('welcome.subtitle')}</div>
      <div className="welcome__hint">{t('welcome.description')}</div>

      <div className="welcome__examples">
        <div className="welcome__examples-title">💡 {t('welcome.examples')}</div>
        <div className="welcome__examples-grid">
          {EXAMPLES.map((ex, idx) => (
            <button
              key={idx}
              className="welcome__example-card"
              onClick={() => onExampleClick(ex.task)}
            >
              <span className="welcome__example-icon">{ex.icon}</span>
              <span className="welcome__example-title">{ex.title}</span>
              <span className="welcome__example-desc">{ex.desc}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="welcome__shortcut-hint">
        {t('welcome.shortcutHint')}
      </div>
    </div>
  );
};

export default WelcomeScreen;
