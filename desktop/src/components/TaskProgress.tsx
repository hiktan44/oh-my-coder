import React from 'react';
import { useT } from '../lib/i18n';

interface Stage {
  name: string;
  status: 'pending' | 'active' | 'completed' | 'error';
}

interface TaskProgressProps {
  stages: Stage[];
  currentStage: number;
}

const getStageIcon = (name: string): string => {
  const icons: Record<string, string> = {
    'requirements': '📋',
    'design': '🏗️',
    'coding': '💻',
    'review': '👀',
    'testing': '🧪',
    '需求分析': '📋',
    '方案设计': '🏗️',
    '代码编写': '💻',
    '代码审查': '👀',
    '测试执行': '🧪',
  };
  return icons[name] || '○';
};

const getStageLabel = (name: string, lang: string): string => {
  const labels: Record<string, { tr: string; en: string }> = {
    'requirements': { tr: 'Gereksinim Analizi', en: 'Requirements Analysis' },
    'design': { tr: 'Tasarım', en: 'Design' },
    'coding': { tr: 'Kodlama', en: 'Coding' },
    'review': { tr: 'İnceleme', en: 'Review' },
    'testing': { tr: 'Test', en: 'Testing' },
    '需求分析': { tr: 'Gereksinim Analizi', en: 'Requirements Analysis' },
    '方案设计': { tr: 'Tasarım', en: 'Design' },
    '代码编写': { tr: 'Kodlama', en: 'Coding' },
    '代码审查': { tr: 'İnceleme', en: 'Review' },
    '测试执行': { tr: 'Test', en: 'Testing' },
  };
  return labels[name]?.[lang === 'tr' ? 'tr' : 'en'] || name;
};

export function TaskProgress({ stages, currentStage }: TaskProgressProps) {
  const { t, lang } = useT();

  return (
    <div className="task-progress">
      <div className="task-progress__header">
        <span className="task-progress__label">{t('task.progress')}</span>
        <span className="task-progress__count">
          {stages.filter(s => s.status === 'completed').length} / {stages.length}
        </span>
      </div>
      <div className="task-progress__bar">
        {stages.map((stage, idx) => {
          const isActive = idx === currentStage;
          const isCompleted = stage.status === 'completed';
          const isError = stage.status === 'error';

          return (
            <div
              key={stage.name}
              className={`task-progress__stage ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isError ? 'error' : ''}`}
            >
              <div className="task-progress__dot">
                {isCompleted ? '✓' : isError ? '✗' : getStageIcon(stage.name)}
              </div>
              <span className="task-progress__name">{getStageLabel(stage.name, lang)}</span>
              {isActive && <div className="task-progress__pulse" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
