// website/i18n.js - Vanilla JS i18n for static HTML pages
// Usage: Add data-i18n="key" attributes to HTML elements, then load this script

(function() {
  'use strict';

  // Translation dictionary
  const DICT = {
    // Navigation
    'nav.security': { tr: '安全合规', en: 'Security & Compliance' },
    'nav.features': { tr: '核心特性', en: 'Core Features' },
    'nav.agents': { tr: 'Agent 工作流', en: 'Agent Workflow' },
    'nav.screenshots': { tr: '界面预览', en: 'Interface Preview' },
    'nav.quickstart': { tr: '快速开始', en: 'Quick Start' },
    'nav.faq': { tr: '常见问题', en: 'FAQ' },
    'nav.blog': { tr: '博客', en: 'Blog' },
    'nav.github': { tr: 'GitHub', en: 'GitHub' },
    
    // Hero section
    'hero.badge': { tr: '🛡️ 国产替代方案 · 本地运行 · 数据不出境', en: '🛡️ Domestic Alternative · Local Execution · Data Stays Local' },
    'hero.title1': { tr: '国产首个', en: 'The First Domestic' },
    'hero.title2': { tr: '多 Agent 协作编程框架', en: 'Multi-Agent Collaborative Programming Framework' },
    'hero.subtitle1': { tr: '<strong>31 个专业 Agent</strong> · <strong>12 家国产大模型</strong> · <strong>完全本地运行</strong>', en: '<strong>31 Professional Agents</strong> · <strong>12 Domestic LLMs</strong> · <strong>100% Local Execution</strong>' },
    'hero.subtitle2': { tr: '代码不上传云端，数据不出境，中小企业合规首选', en: 'No code uploaded to cloud, no data crosses borders, the top compliance choice for SMEs' },
    'hero.btn.start': { tr: '⚡ 3 分钟上手', en: '⚡ Get Started in 3 Minutes' },
    'hero.btn.github': { tr: '⭐ GitHub Star', en: '⭐ Star on GitHub' },
    
    // Stats
    'stat.agents': { tr: '专业 Agent', en: 'Professional Agents' },
    'stat.models': { tr: '国产模型', en: 'Domestic Models' },
    'stat.cost': { tr: '元起步', en: 'Starting from 0¥' },
    'stat.local': { tr: '本地运行', en: 'Local Execution' },
    
    // Terminal
    'terminal.demo': { tr: 'omc run "实现用户登录功能"', en: 'omc run "implement user login"' },
    'terminal.step1': { tr: '分析需求：需要 JWT 认证 + 密码哈希 + 数据库模型', en: 'Analyzing requirements: Need JWT auth + password hash + database models' },
    'terminal.step2': { tr: '生成代码：auth.py, models.py, routes.py (156 行)', en: 'Generating code: auth.py, models.py, routes.py (156 lines)' },
    'terminal.step3': { tr: '代码审查：发现 2 处安全问题，已修复', en: 'Code review: Found 2 security issues, fixed' },
    'terminal.step4': { tr: '运行测试：✅ 12/12 通过', en: 'Running tests: ✅ 12/12 passed' },
    'terminal.complete': { tr: '✅ 任务完成！代码已保存到 src/auth/', en: '✅ Task completed! Code saved to src/auth/' },
    
    // Trust section
    'trust.title': { tr: '🔒 企业级安全合规', en: '🔒 Enterprise-level Security & Compliance' },
    'trust.item1.title': { tr: '完全本地运行', en: '100% Local Execution' },
    'trust.item1.desc': { tr: '代码在本地处理，<strong>不上传任何云端服务器</strong>，源代码不会离开你的机器', en: 'Code processed locally, <strong>never uploaded to any cloud server</strong>, source code never leaves your machine' },
    'trust.item2.title': { tr: '密钥本地存储', en: 'Local Key Storage' },
    'trust.item2.desc': { tr: 'API Key 仅保存在本地环境变量，<strong>不存储在第三方服务器</strong>，企业数据自主可控', en: 'API keys only stored in local environment variables, <strong>not on third-party servers</strong>, enterprise data remains autonomous' },
    'trust.item3.title': { tr: '国产模型直连', en: 'Direct Domestic Model Connection' },
    'trust.item3.desc': { tr: '支持 DeepSeek、智谱 GLM、Kimi 等 <strong>12 家国产大模型</strong>，无需翻墙，合规使用', en: 'Supports DeepSeek, GLM, Kimi, and <strong>12+ domestic LLMs</strong>, no VPN needed, compliant usage' },
    'trust.item4.title': { tr: '自动安全审查', en: 'Automated Security Review' },
    'trust.item4.desc': { tr: '内置 SecurityReviewerAgent，<strong>自动扫描漏洞</strong>：SQL 注入、XSS、硬编码密钥等', en: 'Built-in SecurityReviewerAgent, <strong>automatically scans vulnerabilities</strong>: SQL injection, XSS, hardcoded keys, etc.' },
    'trust.item5.title': { tr: 'Diff 预览确认', en: 'Diff Preview & Confirmation' },
    'trust.item5.desc': { tr: '修改文件前<strong>预览变更内容</strong>，GitMasterAgent 管理版本，避免误操作', en: '<strong>Preview changes</strong> before modifying files, GitMasterAgent manages versions, prevents accidents' },
    'trust.item6.title': { tr: '开源可审计', en: 'Open Source & Auditable' },
    'trust.item6.desc': { tr: '<strong>MIT 开源协议</strong>，代码完全透明，支持私有化部署、二次开发、安全审计', en: '<strong>MIT open source license</strong>, fully transparent code, supports private deployment, secondary development, security auditing' },
    
    // Features section
    'features.title': { tr: '核心特性', en: 'Core Features' },
    'features.subtitle': { tr: '31 个专业 Agent + 5 大创新系统，覆盖完整开发流程', en: '31 Professional Agents + 5 Innovative Systems, Covering Complete Development Process' },
    
    // Agents section
    'agents.title': { tr: 'Agent 工作流', en: 'Agent Workflow' },
    'agents.subtitle': { tr: '像团队一样协作，比一个人更高效', en: 'Collaborate like a team, more efficient than working alone' },
    'agents.planner': { tr: 'Planner', en: 'Planner' },
    'agents.planner.desc': { tr: '分析需求<br>制定计划', en: 'Analyze requirements<br>Make plans' },
    'agents.coder': { tr: 'Coder', en: 'Coder' },
    'agents.coder.desc': { tr: '编写代码<br>生成测试', en: 'Write code<br>Generate tests' },
    'agents.reviewer': { tr: 'Reviewer', en: 'Reviewer' },
    'agents.reviewer.desc': { tr: '代码审查<br>安全检查', en: 'Code review<br>Security checks' },
    'agents.executor': { tr: 'Executor', en: 'Executor' },
    'agents.executor.desc': { tr: '运行测试<br>部署执行', en: 'Run tests<br>Deploy & Execute' },
    
    // Screenshots section
    'screenshots.title': { tr: '界面预览', en: 'Interface Preview' },
    'screenshots.subtitle': { tr: 'CLI 命令行、Web 界面、Desktop 桌面端三种使用方式', en: 'Three usage modes: CLI, Web Interface, and Desktop App' },
    'screenshots.tab.cli': { tr: '💻 CLI 命令行', en: '💻 CLI Command Line' },
    'screenshots.tab.web': { tr: '🌐 Web 界面', en: '🌐 Web Interface' },
    'screenshots.tab.desktop': { tr: '🖥️ Desktop 桌面端', en: '🖥️ Desktop App' },
    
    // Quick start section
    'quickstart.title': { tr: '快速开始', en: 'Quick Start' },
    'quickstart.subtitle': { tr: '3 分钟上手，选择适合你的方式', en: 'Get started in 3 minutes, choose the method that suits you' },
    
    // FAQ section
    'faq.title': { tr: '常见问题', en: 'Frequently Asked Questions' },
    'faq.subtitle': { tr: '快速找到答案，开始使用', en: 'Find answers quickly and get started' },
    'faq.install.title': { tr: '安装配置', en: 'Installation & Configuration' },
    'faq.install.desc': { tr: '如何安装、配置 API Key、验证安装', en: 'How to install, configure API keys, verify installation' },
    'faq.usage.title': { tr: '使用教程', en: 'Usage Tutorial' },
    'faq.usage.desc': { tr: '第一次使用、CLI vs Web、工作流选择', en: 'First-time usage, CLI vs Web, workflow selection' },
    'faq.model.title': { tr: '模型选择', en: 'Model Selection' },
    'faq.model.desc': { tr: '选哪个模型、多 Key 配置、Key 泄露处理', en: 'Which model to choose, multi-key configuration, handling key leaks' },
    'faq.trouble.title': { tr: '故障排查', en: 'Troubleshooting' },
    'faq.trouble.desc': { tr: 'Key 未配置、超时、代码错误修复', en: 'Key not configured, timeouts, fixing code errors' },
    'faq.more': { tr: '查看全部 15+ 个问题 →', en: 'View All 15+ Questions →' },
    
    // Footer
    'footer.text': { tr: '开源项目 · GitHub · MIT 协议', en: 'Open Source Project · GitHub · MIT License' },
    'footer.author': { tr: 'Made with ❤️ by VOBC', en: 'Made with ❤️ by VOBC' },
    
    // Language switcher
    'lang.switch': { tr: 'English', en: 'Türkçe' },
    'lang.title': { tr: '切换语言', en: 'Switch Language' },

    // FAQ page specific
    'header.back': { tr: '← 返回首页', en: '← Back to Home' },
    'faq.tab.all': { tr: '全部', en: 'All' },
    'faq.tab.install': { tr: '安装配置', en: 'Installation' },
    'faq.tab.usage': { tr: '使用教程', en: 'Usage' },
    'faq.tab.model': { tr: '模型选择', en: 'Models' },
    'faq.tab.trouble': { tr: '故障排查', en: 'Troubleshooting' },
    'faq.tab.advanced': { tr: '高级功能', en: 'Advanced' },
    'faq.category.install': { tr: '📦 安装配置', en: '📦 Installation & Configuration' },
    'faq.category.usage': { tr: '🚀 使用教程', en: '🚀 Usage Tutorial' },
    'faq.category.model': { tr: '🤖 模型选择', en: '🤖 Model Selection' },
    'faq.category.trouble': { tr: '🔧 故障排查', en: '🔧 Troubleshooting' },
    'faq.category.advanced': { tr: '⚡ 高级功能', en: '⚡ Advanced Features' },
    'faq.footer.notfound': { tr: '还没找到答案？', en: 'Haven\'t found an answer yet?' },
    'faq.footer.links': { tr: '📖 <a href="https://github.com/VOBC/oh-my-coder/tree/main/docs">查看完整文档</a> · 🐛 <a href="https://github.com/VOBC/oh-my-coder/issues">提交 Issue</a> · 💬 <a href="https://github.com/VOBC/oh-my-coder/discussions">参与讨论</a>', en: '📖 <a href="https://github.com/VOBC/oh-my-coder/tree/main/docs">View Full Documentation</a> · 🐛 <a href="https://github.com/VOBC/oh-my-coder/issues">Submit Issue</a> · 💬 <a href="https://github.com/VOBC/oh-my-coder/discussions">Join Discussion</a>' },

    // Blog page specific
    'blog.title': { tr: '📝 技术博客', en: '📝 Technical Blog' },
    'blog.subtitle': { tr: '原创技术文章，分享 oh-my-coder 的开发心得与 AI 编程实践', en: 'Original technical articles sharing development insights and AI programming practices of oh-my-coder' },
    'blog.nav.home': { tr: '首页', en: 'Home' },
    'blog.nav.security': { tr: '安全合规', en: 'Security' },
    'blog.nav.features': { tr: '核心特性', en: 'Features' },
    'blog.nav.agents': { tr: 'Agent 工作流', en: 'Agent Workflow' },
    'blog.nav.screenshots': { tr: '界面预览', en: 'Screenshots' },
    'blog.nav.quickstart': { tr: '快速开始', en: 'Quick Start' },
    'blog.nav.faq': { tr: '常见问题', en: 'FAQ' },
    'blog.nav.blog': { tr: '博客', en: 'Blog' },
    'blog.footer.text': { tr: '📄 文章发布于 <a href="https://juejin.cn/user/4285265106965034/posts" target="_blank">稀土掘金</a>，亦可在 <a href="https://blog.csdn.net/VOBCIO" target="_blank">CSDN</a> 查看 · Oh My Coder © 2026', en: '📄 Articles published on <a href="https://juejin.cn/user/4285265106965034/posts" target="_blank">Juejin</a>, also available on <a href="https://blog.csdn.net/VOBCIO" target="_blank">CSDN</a> · Oh My Coder © 2026' },
    'blog.card.new.title': { tr: '不上云、不翻墙、不花一分钱——Oh My Coder 官网上线了！', en: 'No Cloud, No VPN, No Cost—Oh My Coder Official Website Launch!' },
    'blog.card.new.brief': { tr: '完全本地运行、数据不出境、零成本起步的AI多Agent编程框架。官网正式上线，三分钟上手，CLI/Web/Desktop三种方式任选，31个专业Agent协同工作。', en: 'AI multi-Agent programming framework with completely local execution, no data crossing borders, and zero cost start. Official website launches with three-minute onboarding, CLI/Web/Desktop options, and 31 professional agents working together.' },
    'blog.card.tutorial.title': { tr: 'Oh My Coder 试用教程', en: 'Oh My Coder Tutorial' },
    'blog.card.tutorial.brief': { tr: '本文档面向首次使用的普通用户，手把手教你从安装到运行第一个 AI 编程任务，建议先从简单的任务开始，比如"分析项目结构"或"优化一个函数"，逐步熟悉工具的使用。', en: 'This document is for first-time users, teaching you step-by-step from installation to running your first AI programming task. Start with simple tasks like "analyze project structure" or "optimize a function" to gradually get familiar with the tool.' },
    'blog.card.readmore': { tr: '阅读全文 →', en: 'Read More →' }
  };

  // Language detection with fallbacks
  async function detectLanguage() {
    const storageKey = 'ui_lang';
    const cookieKey = 'ui_lang';
    
    // 1. Check localStorage preference (highest priority)
    const storedLang = localStorage.getItem(storageKey);
    if (storedLang === 'tr' || storedLang === 'en') {
      return storedLang;
    }
    
    // 2. Check cookie
    const cookieMatch = document.cookie.match(new RegExp('(^|;)\\s*' + cookieKey + '\\s*=\\s*([^;]+)'));
    if (cookieMatch) {
      const lang = cookieMatch[2];
      if (lang === 'tr' || lang === 'en') {
        localStorage.setItem(storageKey, lang);
        return lang;
      }
    }
    
    // 3. IP-based detection (try ipwho.is as primary, fallback to ipapi.co)
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      
      // Try ipwho.is first (as specified in requirements)
      try {
        const response = await fetch('https://ipwho.is/', {
          signal: controller.signal,
          timeout: 2000
        });
        clearTimeout(timeoutId);
        
        if (response.ok) {
          const data = await response.json();
          if (data?.country_code) {
            const countryCode = data.country_code.toUpperCase();
            // Cache result for 24 hours
            localStorage.setItem('omc_ip_country', JSON.stringify({
              country: countryCode,
              timestamp: Date.now()
            }));
            
            if (countryCode === 'TR') return 'tr';
            if (countryCode) return 'en'; // Default to English for non-TR countries
          }
        }
      } catch (ipwhoError) {
        console.log('ipwho.is failed, trying ipapi.co:', ipwhoError);
        
        // Fallback to ipapi.co if ipwho.is fails
        try {
          const response = await fetch('https://ipapi.co/json/', {
            signal: controller.signal,
            timeout: 2000
          });
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const data = await response.json();
            if (data?.country_code) {
              const countryCode = data.country_code.toUpperCase();
              // Cache result
              localStorage.setItem('omc_ip_country', JSON.stringify({
                country: countryCode,
                timestamp: Date.now()
              }));
              
              if (countryCode === 'TR') return 'tr';
              if (countryCode) return 'en';
            }
          }
        } catch (ipapiError) {
          console.log('Both IP services failed:', ipapiError);
        }
      }
    } catch (error) {
      console.warn('IP detection failed completely:', error);
    }
    
    // 4. Fallback to navigator.language
    const navLang = navigator.language.toLowerCase();
    if (navLang.startsWith('tr')) return 'tr';
    
    // 5. Default to TR (as specified in requirements)
    return 'tr';
  }

  // Set language and persist
  function setLanguage(lang) {
    const storageKey = 'ui_lang';
    const cookieKey = 'ui_lang';
    
    // Save to localStorage
    localStorage.setItem(storageKey, lang);
    
    // Set cookie for 1 year
    const maxAge = 365 * 24 * 60 * 60;
    document.cookie = `${cookieKey}=${lang}; path=/; max-age=${maxAge}; SameSite=Lax`;
    
    // Apply translations
    applyTranslations(lang);
    
    // Update language switch button
    updateLangSwitchButton(lang);
    
    // Update HTML lang attribute
    document.documentElement.lang = lang === 'tr' ? 'tr' : 'en-US';
  }

  // Apply translations to elements with data-i18n attributes
  function applyTranslations(lang) {
    document.querySelectorAll('[data-i18n]').forEach(element => {
      const key = element.getAttribute('data-i18n');
      const translation = DICT[key]?.[lang];
      
      if (translation) {
        // Handle HTML content vs text content
        if (element.hasAttribute('data-i18n-html')) {
          element.innerHTML = translation;
        } else {
          element.textContent = translation;
        }
      }
    });
    
    // Update document title
    const titleKey = document.body.getAttribute('data-i18n-title');
    if (titleKey && DICT[titleKey]) {
      document.title = DICT[titleKey][lang];
    }
  }

  // Create or update language switch button
  function updateLangSwitchButton(currentLang) {
    let langBtn = document.getElementById('lang-switch-btn');
    
    if (!langBtn) {
      // Create language switch button
      langBtn = document.createElement('button');
      langBtn.id = 'lang-switch-btn';
      langBtn.className = 'lang-switch-btn';
      langBtn.setAttribute('aria-label', DICT['lang.title'][currentLang]);
      langBtn.title = DICT['lang.title'][currentLang];
      
      // Add click handler
      langBtn.addEventListener('click', () => {
        const newLang = currentLang === 'tr' ? 'en' : 'tr';
        setLanguage(newLang);
      });
      
      // Insert into navbar actions
      const navbarActions = document.querySelector('.navbar-actions');
      if (navbarActions) {
        navbarActions.insertBefore(langBtn, navbarActions.firstChild);
      }
    }
    
    // Update button content
    const targetLang = currentLang === 'tr' ? 'en' : 'tr';
    langBtn.innerHTML = `${currentLang.toUpperCase()} → ${targetLang.toUpperCase()}`;
    langBtn.setAttribute('aria-label', DICT['lang.switch'][currentLang]);
    langBtn.title = DICT['lang.title'][currentLang];
  }

  // Initialize i18n
  async function initI18n() {
    const lang = await detectLanguage();
    setLanguage(lang);
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initI18n);
  } else {
    initI18n();
  }
  
  // Export for external use if needed
  window.websiteI18n = {
    setLanguage,
    detectLanguage,
    DICT
  };
})();
