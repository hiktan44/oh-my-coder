// i18n.js - IP-based TR/EN language system with manual override
// TR IP -> Turkish, non-TR IP -> English

(function() {
    'use strict';

    // Translation dictionary
    const translations = {
        // Navigation (shared across all templates)
        'nav_home': { tr: 'Ana Sayfa', en: 'Home' },
        'nav_dashboard': { tr: 'Kontrol Paneli', en: 'Dashboard' },
        'nav_history': { tr: 'Geçmiş', en: 'History' },
        'nav_coverage': { tr: 'Kapsam', en: 'Coverage' },
        'nav_docs': { tr: 'Dokümantasyon', en: 'Docs' },
        'nav_settings': { tr: 'Ayarlar', en: 'Settings' },
        'nav_agents': { tr: 'Durum', en: 'Status' },
        
        // Common UI elements
        'theme_toggle_title': { tr: 'Tema Değiştir', en: 'Toggle Theme' },
        'loading': { tr: 'Yükleniyor...', en: 'Loading...' },
        'error': { tr: 'Hata', en: 'Error' },
        'success': { tr: 'Başarılı', en: 'Success' },
        'save': { tr: 'Kaydet', en: 'Save' },
        'cancel': { tr: 'İptal', en: 'Cancel' },
        'delete': { tr: 'Sil', en: 'Delete' },
        'edit': { tr: 'Düzenle', en: 'Edit' },
        'close': { tr: 'Kapat', en: 'Close' },
        'search': { tr: 'Ara', en: 'Search' },
        'refresh': { tr: 'Yenile', en: 'Refresh' },
        
        // Index.html specific strings
        'hero_badge': { tr: 'GLM-4.7-Flash tarafından desteklenmektedir · Sıfır maliyetli akıllı kodlama', en: 'Powered by GLM-4.7-Flash · Zero-cost intelligent coding' },
        'hero_title': { tr: 'Yapay Zeka Ekibi Kodunuzu Yazsın', en: 'Let AI Team Write Code for You' },
        'hero_desc': { tr: 'Çoklu ajan işbirliği, gereksinim analizinden kod uygulamasına kadar eksiksiz süreci otomatikleştirir. Profesyonel bir mühendislik ekibini yönettiğiniz gibi, birden fazla yapay zeka ajanının işbirliği ile geliştirme yapın.', en: 'Multi-agent collaboration automatically completes the full process from requirement analysis to code implementation. Like commanding a professional engineering team, command multiple AI agents to collaborate in development.' },
        'available_models': { tr: 'Kullanılabilir Modeller', en: 'Available Models' },
        'step_explore': { tr: 'Keşfet', en: 'Explore' },
        'step_analyze': { tr: 'Analiz', en: 'Analyze' },
        'step_design': { tr: 'Tasarım', en: 'Design' },
        'step_implementation': { tr: 'Uygulama', en: 'Implement' },
        'step_verify': { tr: 'Doğrula', en: 'Verify' },
        
        'start_task_title': { tr: '🚀 Yeni Görev Başlat', en: '🚀 Start New Task' },
        'start_task_desc': { tr: 'İhtiyaçlarınızı açıklayın, yapay zeka ekibi otomatik olarak işbirliği ile tamamlayacak', en: 'Describe your requirements, AI team will complete automatically with collaboration' },
        'task_description': { tr: 'Görev Açıklaması', en: 'Task Description' },
        'task_placeholder': { tr: 'Örneğin: Bir kullanıcı kimlik doğrulama sistemi uygulayın, kayıt, giriş, JWT jetonu, şifre sıfırlama vb. işlevleri içerir', en: 'For example: Implement a user authentication system including registration, login, JWT token, password reset, etc.' },
        'task_hint': { tr: '💡 Daha detaylı gereksinim açıklaması, yapay zeka ekibinin anlayışı ve uygulama etkisi o kadar iyi olur', en: '💡 More detailed requirement description, the better the AI team understanding and implementation effect' },
        
        'analysis_target': { tr: 'Analiz Hedefi', en: 'Analysis Target' },
        'target_local': { tr: '📂 Yerel Yol', en: '📂 Local Path' },
        'target_github': { tr: '🔗 GitHub', en: '🔗 GitHub' },
        'target_url': { tr: '🌐 Web Sayfası', en: '🌐 Webpage' },
        'local_path_placeholder': { tr: 'Yerel klasör yolunu girin veya aşağıdaki hızlı butona tıklayın', en: 'Enter local folder path or click the quick button below' },
        'quick_desktop': { tr: '📁 Masaüstü', en: '📁 Desktop' },
        'quick_documents': { tr: '📄 Belgeler', en: '📄 Documents' },
        'quick_home': { tr: '🏠 Ana Dizin', en: '🏠 Home Directory' },
        'quick_current': { tr: '📂 Mevcut Dizin', en: '📂 Current Directory' },
        'path_hint': { tr: 'Yapay zekanın hangi kod klasörünü analiz etmesini istiyorsunuz? Boş bırakılırsa mevcut dizini analiz eder', en: 'Which code folder do you want AI to analyze? If left empty, analyzes current directory' },
        'github_url_placeholder': { tr: 'https://github.com/kullaniciadi/depo', en: 'https://github.com/username/repo' },
        'github_hint': { tr: 'GitHub deposu bağlantısını yapıştırın, yapay zeka otomatik klonlar ve analiz eder', en: 'Paste GitHub repository link, AI will automatically clone and analyze' },
        'web_url_placeholder': { tr: 'https://ornek.com/sayfa', en: 'https://example.com/page' },
        'web_hint': { tr: 'Web sayfası bağlantısını yapıştırın, yapay zeka içeriği analiz bağlamı olarak alır', en: 'Paste webpage link, AI will fetch content as analysis context' },
        
        'model_selection': { tr: 'Model Seçimi', en: 'Model Selection' },
        'model_option1': { tr: 'DeepSeek V4 (Önerilen·Düşük Maliyet)', en: 'DeepSeek V4 (Recommended·Low Cost)' },
        'model_option2': { tr: 'GLM-4.7-Flash (Ücretsiz)', en: 'GLM-4.7-Flash (Free)' },
        'model_option3': { tr: 'MiMo Flash (Ücretsiz)', en: 'MiMo Flash (Free)' },
        'model_option4': { tr: 'Kimi 128K (Düşük Maliyet)', en: 'Kimi 128K (Low Cost)' },
        'model_option5': { tr: 'Doubao-Pro (Düşük Maliyet)', en: 'Doubao-Pro (Low Cost)' },
        'model_option6': { tr: 'Tiangong 3.0 (Düşük Maliyet)', en: 'Tiangong 3.0 (Low Cost)' },
        'model_option7': { tr: 'Baichuan 4 (Düşük Maliyet)', en: 'Baichuan 4 (Low Cost)' },
        'model_settings_link': { tr: '⚙️ Sağlayıcı Yönetimi/Özel Model Ekle', en: '⚙️ Manage Providers/Add Custom Models' },
        
        'workflow_selection': { tr: 'İş Akışı', en: 'Workflow' },
        'workflow_build': { tr: '🚀 Tam Geliştirme (build)', en: '🚀 Full Development (build)' },
        'workflow_review': { tr: '🔍 Kod İncelemesi', en: '🔍 Code Review' },
        'workflow_debug': { tr: '🐛 Hata Ayıklama', en: '🐛 Debug Fix' },
        'workflow_test': { tr: '🧪 Test Durumları', en: '🧪 Test Cases' },
        'workflow_refactor': { tr: '♻️ Yeniden Düzenleme', en: '♻️ Refactor' },
        'workflow_doc': { tr: '📖 Dokümantasyon Oluşturma', en: '📖 Documentation' },
        'workflow_pair': { tr: '👥 Çift Programlama', en: '👥 Pair Programming' },
        'workflow_autopilot': { tr: '🤖 Otopilot', en: '🤖 Autopilot' },
        'workflow_sequential': { tr: '📋 Sıralı Yürütme', en: '📋 Sequential' },
        
        'submit_button': { tr: '▶ Yapay Zeka Ekibini Başlat', en: '▶ Launch AI Team' },
        
        'try_examples': { tr: '💡 Bu Görevleri Deneyin', en: '💡 Try These Tasks' },
        'example_rest_title': { tr: 'REST API Geliştirme', en: 'REST API Development' },
        'example_rest_desc': { tr: 'FastAPI Kullanıcı Yönetimi CRUD', en: 'FastAPI User Management CRUD' },
        'example_review_title': { tr: 'Kod İncelemesi', en: 'Code Review' },
        'example_review_desc': { tr: 'Kalite + Güvenlik Kontrolü', en: 'Quality + Security Check' },
        'example_debug_title': { tr: 'Hata Ayıklama', en: 'Debugging' },
        'example_debug_desc': { tr: 'Sorunları Bul ve Düzelt', en: 'Locate and Fix Issues' },
        'example_test_title': { tr: 'Test Durumları', en: 'Test Cases' },
        'example_test_desc': { tr: 'Temel Mantık Tam Kapsam', en: 'Core Logic Full Coverage' },
        
        'core_features': { tr: '⚡ Temel Yetenekler', en: '⡡ Core Capabilities' },
        'feature_smart_routing': { tr: 'Akıllı Yönlendirme', en: 'Smart Routing' },
        'feature_smart_routing_desc': { tr: 'Görev karmaşıklığına göre otomatik model seçimi, %30-50 Token tasarrufu', en: 'Automatically select optimal model by task complexity, save 30-50% tokens' },
        'feature_multi_agent': { tr: 'Çoklu Ajan İşbirliği', en: 'Multi-Agent Collaboration' },
        'feature_multi_agent_desc': { tr: 'Birçok profesyonel ajen işbirliği', en: 'Multiple professional agents collaborate' },
        'feature_zero_cost': { tr: 'Sıfır Maliyetli Çalışma', en: 'Zero-Cost Operation' },
        'feature_zero_cost_desc': { tr: 'Öncelikle GLM-4.7-Flash ücretsiz kotasını kullanır', en: 'Prioritize using GLM-4.7-Flash free quota' },
        'feature_full_process': { tr: 'Tam Süreç Kapsamı', en: 'Full Process Coverage' },
        'feature_full_process_desc': { tr: 'Keşif analizinden kod uygulamasına, test doğrulamasına kadar', en: 'From exploration analysis to code implementation, test verification' },
        
        'footer_credits': { tr: '❤️ ile Oh My Coder tarafından yapıldı · GLM-4.7-Flash ve Çoklu Ajan Mimarisi tarafından desteklenmektedir', en: 'Made with ❤️ by Oh My Coder · Powered by GLM-4.7-Flash & Multi-Agent Architecture' },
        
        // Response tabs
        'tab_result': { tr: '📋 Uygulama Sonucu', en: '📋 Execution Result' },
        'tab_explore': { tr: '🔍 Keşfet', en: '🔍 Explore' },
        'tab_analyst': { tr: '🧠 Analist', en: '🧠 Analyst' },
        'tab_architect': { tr: '🏗️ Mimari', en: '🏗️ Architect' },
        'tab_executor': { tr: '💻 Uygulayıcı', en: '💻 Executor' },
        'tab_stats': { tr: '📊 İstatistikler', en: '📊 Statistics' },
        
        // Dashboard.html specific strings
        'dashboard_title': { tr: '📊 Proje Kontrol Paneli', en: '📊 Project Dashboard' },
        'dashboard_desc': { tr: 'Proje durumunu, ajan işbirliğini ve çalışma metriklerini gerçek zamanlı görüntüleyin.', en: 'View project status, agent collaboration and runtime metrics in real-time.' },
        'card_completed': { tr: 'Tamamlanan Görevler', en: 'Completed Tasks' },
        'card_cumulative': { tr: 'Kümülatif Yürütme', en: 'Cumulative Execution' },
        'card_tokens': { tr: 'Token Tüketimi', en: 'Token Consumption' },
        'card_tokens_sub': { tr: 'Toplam Tokenlar', en: 'Total Tokens' },
        'card_cost': { tr: 'Tahmini Maliyet', en: 'Estimated Cost' },
        'card_cost_sub': { tr: 'DeepSeek ücretsiz kotası dahilinde', en: 'Within DeepSeek free quota' },
        'card_agent_status': { tr: '🤖 Ajan Durumu', en: '🤖 Agent Status' },
        'card_project_files': { tr: '📁 Proje Dosyaları', en: '📁 Project Files' },
        'card_open_folder': { tr: '📂 Aç', en: '📂 Open' },
        
        'agent_idle': { tr: 'Boşta', en: 'Idle' },
        'agent_running': { tr: 'Çalışıyor', en: 'Running' },
        'agent_error': { tr: 'Hata', en: 'Error' },
        
        'loading_files': { tr: 'Yükleniyor...', en: 'Loading...' },
        'cannot_load_files': { tr: 'Dosya listesi yüklenemiyor', en: 'Cannot load file list' },
        
        // Agents.html specific strings
        'agents_title': { tr: '🤖 Ajan Durumu', en: '🤖 Agent Status' },
        'agents_desc': { tr: 'Tüm ajanların mevcut durumunu ve detaylı bilgiyi görüntüleyin.', en: 'View current status and detailed information of all agents.' },
        
        'agent_explorer': { tr: 'Keşifçi', en: 'Explorer' },
        'agent_explorer_desc': { tr: 'Proje yapısını keşfeder, kod kütüphanesini anlar, bağlam bilgisi toplar', en: 'Explore project structure, understand codebase, collect context information' },
        'agent_analyst': { tr: 'Analist', en: 'Analyst' },
        'agent_analyst_desc': { tr: 'Gereksinimleri analiz eder, görevleri ayırır, uygulama planı hazırlar', en: 'Analyze requirements, break down tasks, formulate execution plan' },
        'agent_architect': { tr: 'Mimar', en: 'Architect' },
        'agent_architect_desc': { tr: 'Mimari çözüm tasarlar, teknoloji seçimini ve kod yapısını belirler', en: 'Design architecture solution, determine technology selection and code structure' },
        'agent_executor': { tr: 'Uygulayıcı', en: 'Executor' },
        'agent_executor_desc': { tr: 'Kod yazar, işlevleri uygular, dosyaları değiştirir', en: 'Write code, implement functionality, modify files' },
        'agent_verifier': { tr: 'Doğrulayıcı', en: 'Verifier' },
        'agent_verifier_desc': { tr: 'Sonuçları doğrular, testleri çalıştırır, kod kalitesini onaylar', en: 'Verify results, run tests, confirm code quality' },
        'agent_debugger': { tr: 'Hata Ayıklayıcı', en: 'Debugger' },
        'agent_debugger_desc': { tr: 'Hataları konumlandırır, hataları analiz eder, sorunları düzeltir', en: 'Locate bugs, analyze errors, fix issues' },
        'agent_code_reviewer': { tr: 'Kod İnceleyici', en: 'Code Reviewer' },
        'agent_code_reviewer_desc': { tr: 'Kod incelemesi, olası sorunları bulur, iyileştirme önerileri sunar', en: 'Code review, discover potential issues, suggest improvements' },
        'agent_security': { tr: 'Güvenlik Denetimi', en: 'Security Audit' },
        'agent_security_desc': { tr: 'Güvenlik taraması, açıkları algılar, uyumluluğu doğrular', en: 'Security scanning, detect vulnerabilities, verify compliance' },
        
        'status_idle': { tr: 'Boşta', en: 'Idle' },
        'status_running': { tr: 'Çalışıyor', en: 'Running' },
        'status_error': { tr: 'Hata', en: 'Error' },
        
        // Coverage.html specific strings
        'coverage_title': { tr: '📊 Test Kapsamı', en: '📊 Test Coverage' },
        'coverage_desc': { tr: 'Kod test kapsamını görüntüleyin, kapsanmamış kod alanlarını belirleyin', en: 'View code test coverage, identify uncovered code areas' },
        
        'reanalyze_button': { tr: '🔄 Yiden Analiz', en: '🔄 Re-analyze' },
        'analyzing': { tr: '⏳ Analiz ediliyor...', en: '⏳ Analyzing...' },
        'running_tests': { tr: 'Testleri çalıştır ve kapsam verilerini topla, lütfen bekleyin...', en: 'Running tests and collecting coverage data, please wait...' },
        'load_failed': { tr: 'Yükleme başarısız:', en: 'Load failed:' },
        'analyze_failed': { tr: 'Analiz başarısız:', en: 'Analysis failed:' },
        
        'overall_coverage': { tr: 'Genel Kapsam', en: 'Overall Coverage' },
        'file_count': { tr: 'Dosya Sayısı', en: 'File Count' },
        'total_statements': { tr: 'Toplam ifade', en: 'Total Statements' },
        'missing_statements': { tr: 'Eksik İfadeler', en: 'Missing Statements' },
        'file_details': { tr: 'Dosya Detayları', en: 'File Details' },
        'file_path': { tr: 'Dosya Yolu', en: 'File Path' },
        'statements': { tr: 'İfadeler', en: 'Statements' },
        'missing': { tr: 'Eksik', en: 'Missing' },
        'coverage_percent': { tr: 'Kapsam%', en: 'Coverage%' },
        'sort_file': { tr: 'Dosya ↕', en: 'File ↕' },
        'sort_coverage': { tr: 'Kapsam ↕', en: 'Coverage ↕' },
        
        // History.html specific strings
        'history_title': { tr: '📋 Görev Geçmişi', en: '📋 Task History' },
        'history_desc': { tr: 'Tüm yürütülen görevleri ve sonuçları görüntüleyin.', en: 'View all executed tasks and results.' },
        
        'search_tasks': { tr: '🔍 Görev ara...', en: '🔍 Search tasks...' },
        'refresh_button': { tr: 'Yenile', en: 'Refresh' },
        'clear_all': { tr: 'Tümünü Temizle', en: 'Clear All' },
        'no_history': { tr: 'Geçmiş kayıt yok', en: 'No history records' },
        'no_history_desc': { tr: 'Görevler yürütüldükten sonra geçmiş kayıtları burada görünecektir.', en: 'History records will appear here after tasks are executed.' },
        'load_failed': { tr: 'Yükleme başarısız', en: 'Load failed' },
        'load_failed_desc': { tr: 'Geçmiş kayıtları alınamıyor.', en: 'Cannot get history records.' },
        
        'status_success': { tr: 'Başarılı', en: 'Success' },
        'status_failed': { tr: 'Başarısız', en: 'Failed' },
        
        'delete_task': { tr: 'Görevi sil', en: 'Delete task' },
        'delete_confirm': { tr: 'Bu görevi silmek istediğinizden emin misiniz?', en: 'Are you sure you want to delete this task?' },
        'delete_failed': { tr: 'Silme başarısız', en: 'Delete failed' },
        'delete_success': { tr: 'Silindi', en: 'Deleted' },
        
        'clear_all_confirm': { tr: 'Tüm görev kayıtlarını temizlemek istediğinizden emin misiniz? Bu işlem geri alınamaz.', en: 'Are you sure you want to clear all task records? This operation cannot be undone.' },
        'clear_failed': { tr: 'Temizleme başarısız:', en: 'Clear failed:' },
        
        'task_detail_title': { tr: 'Görev Detayları', en: 'Task Details' },
        'task_detail_loading': { tr: 'Yükleniyor...', en: 'Loading...' },
        'task_status': { tr: 'Durum:', en: 'Status:' },
        'task_status_success': { tr: '✅ Başarılı', en: '✅ Success' },
        'task_status_failed': { tr: '❌ Başarısız', en: '❌ Failed' },
        'task_workflow': { tr: 'İş Akışı:', en: 'Workflow:' },
        'task_model': { tr: 'Model:', en: 'Model:' },
        'task_project_path': { tr: 'Proje Yolu:', en: 'Project Path:' },
        'task_start_time': { tr: 'Başlangıç Zamanı:', en: 'Start Time:' },
        'task_complete_time': { tr: 'Tamamlanma Zamanı:', en: 'Complete Time:' },
        
        'statistics': { tr: '📊 İstatistikler', en: '📊 Statistics' },
        'tokens': { tr: 'Tokenlar', en: 'Tokens' },
        'execution_time': { tr: 'Yürütme Süresi', en: 'Execution Time' },
        'completed_steps': { tr: 'Tamamlanan Adımlar', en: 'Completed Steps' },
        
        'result': { tr: '📝 Sonuç', en: '📝 Result' },
        'error': { tr: '⚠️ Hata', en: '⚠️ Error' },
        
        'save_report': { tr: '📄 Raporu Masaüstüne Kaydet', en: '📄 Save Report to Desktop' },
        'saving': { tr: 'Kaydediliyor...', en: 'Saving...' },
        'report_saved': { tr: '✅ Kaydedildi', en: '✅ Saved' },
        'save_failed': { tr: 'Kaydetme başarısız:', en: 'Save failed:' },
        
        // Docs.html specific strings
        'docs_title': { tr: '📖 Kullanım Dokümantasyonu', en: '📖 Documentation' },
        'docs_desc': { tr: 'Kurulumdan ileri seviyeye kadar Oh My Coder\'ın tüm yeteneklerini hızlıca öğrenin.', en: 'Quickly master all capabilities of Oh My Coder from installation to advanced.' },
        
        'quick_start': { tr: 'Hızlı Başlangıç', en: 'Quick Start' },
        'install': { tr: 'Kurulum', en: 'Installation' },
        'first_task': { tr: 'İlk Görev', en: 'First Task' },
        'config_api': { tr: 'API Key Yapılandırması', en: 'Configure API Key' },
        
        'core_concepts': { tr: 'Temel Kavramlar', en: 'Core Concepts' },
        'workflows': { tr: 'İş Akışları', en: 'Workflows' },
        'agent_system': { tr: 'Ajan Sistemi', en: 'Agent System' },
        'model_routing': { tr: 'Model Yönlendirme', en: 'Model Routing' },
        
        'advanced': { tr: 'İleri Seviye', en: 'Advanced' },
        'cli_usage': { tr: 'CLI Kullanımı', en: 'CLI Usage' },
        'plugin_system': { tr: 'Eklenti Sistemi', en: 'Plugin System' },
        'local_models': { tr: 'Yerel Modeller', en: 'Local Models' },
        
        // Settings.html specific strings
        'settings_title': { tr: 'Ayarlar', en: 'Settings' },
        'settings_desc': { tr: 'Modelleri, API anahtarlarını ve çalışma zamanı tercihlerini yapılandırın.', en: 'Configure models, API keys, and runtime preferences.' },
        
        'model_selection_panel': { tr: '🖥️ Model Seçimi', en: '🖥️ Model Selection' },
        'model_selection_desc': { tr: 'Size uygun modeli seçin, yerel modeller sıfır maliyetli ve gizlilik korumalıdır.', en: 'Choose the model that suits you, local models are zero-cost and privacy-protected.' },
        
        'ollama_detecting': { tr: 'Tespit ediliyor...', en: 'Detecting...' },
        'ollama_running': { tr: 'Ollama Çalışıyor', en: 'Ollama Running' },
        'ollama_not_running': { tr: 'Ollama Çalışmıyor', en: 'Ollama Not Running' },
        'ollama_models': { tr: 'Yerel Modeller (Ollama)', en: 'Local Models (Ollama)' },
        'ollama_no_models': { tr: 'Yerel model yok, şunu çalıştırın', en: 'No local models, run' },
        'ollama_install': { tr: 'Ollama Kur:', en: 'Install Ollama:' },
        'ollama_install_link': { tr: 'ollama.ai', en: 'ollama.ai' },
        
        'cloud_models': { tr: '☁️ Bulut Modelleri', en: '☁️ Cloud Models' },
        'model_deepseek': { tr: 'DeepSeek V4', en: 'DeepSeek V4' },
        'model_deepseek_desc': { tr: 'Yüksek performanslı konuşma modeli, fonksiyon çağrısı destekler', en: 'High-performance conversation model, supports function calling' },
        'model_glm': { tr: 'GLM-4.7-Flash', en: 'GLM-4.7-Flash' },
        'model_glm_desc': { tr: 'Ücretsiz yüksek performans, fonksiyon çağrısı, görsel destekler', en: 'Free high-performance, supports function calling, vision' },
        'model_mimo': { tr: 'MiMo Flash', en: 'MiMo Flash' },
        'model_mimo_desc': { tr: 'Xiaomi MiMo, ücretsiz ultra uzun bağlam (256K)', en: 'Xiaomi MiMo, free ultra-long context (256K)' },
        'model_kimi': { tr: 'Kimi 128K', en: 'Kimi 128K' },
        'model_kimi_desc': { tr: 'Moonshot, 128K ultra uzun bağlam', en: 'Moonshot, 128K ultra-long context' },
        'model_doubao': { tr: 'Doubao-Pro', en: 'Doubao-Pro' },
        'model_doubao_desc': { tr: 'ByteDance büyük modeli, yüksek fiyat-performans', en: 'ByteDance large model, high cost-performance' },
        'model_tiangong': { tr: 'Tiangong 3.0', en: 'Tiangong 3.0' },
        'model_tiangong_desc': { tr: 'Tiangong büyük modeli 3.0', en: 'Tiangong large model 3.0' },
        'model_baichuan': { tr: 'Baichuan 4', en: 'Baichuan 4' },
        'model_baichuan_desc': { tr: 'Baichuan Akıllı 4', en: 'Baichuan Intelligence 4' },
        
        'api_keys_panel': { tr: '🔑 API Anahtarları', en: '🔑 API Keys' },
        'api_keys_desc': { tr: 'Her model sağlayıcısı için API anahtarlarını yapılandırın. Anahtarlar sadece yerel depolanır, yüklenmez.', en: 'Configure API keys for each model provider. Keys are stored locally only, not uploaded.' },
        
        'preferences_panel': { tr: '⚙️ Tercihler', en: '⚙️ Preferences' },
        'preferences_desc': { tr: 'Çalışma zamanı varsayılan davranışlarını özelleştirin.', en: 'Customize runtime default behavior.' },
        
        'workflows_panel': { tr: '🔄 İş Akışları', en: '🔄 Workflows' },
        'workflows_desc': { tr: 'Yerleşik iş akışlarını görüntüleyin veya özel iş akışları oluşturun/düzenleyin.', en: 'View built-in workflows or create/edit custom workflows.' },
        
        'default_model': { tr: 'Varsayılan Model', en: 'Default Model' },
        'default_workflow': { tr: 'Varsayılan İş Akışı', en: 'Default Workflow' },
        'task_timeout': { tr: 'Görev Zaman Aşımı (saniye)', en: 'Task Timeout (seconds)' },
        'prefer_local': { tr: 'Yerel Modelleri Öncelikle Kullan', en: 'Prefer Local Models' },
        'prefer_local_yes': { tr: 'Evet (Sıfır Maliyet, Gizlilik Koruması)', en: 'Yes (Zero Cost, Privacy Protection)' },
        'prefer_local_no': { tr: 'Hayır (Bulut modellerini öncelikle kullan)', en: 'No (Prioritize cloud models)' },
        
        'save_preferences': { tr: 'Tercihleri Kaydet', en: 'Save Preferences' },
        'preferences_saved': { tr: 'Tercihler kaydedildi', en: 'Preferences saved' },
        'preferences_save_failed': { tr: 'Kaydetme başarısız', en: 'Save failed' },
        
        'low_cost': { tr: 'Düşük Maliyet', en: 'Low Cost' },
        'free': { tr: 'Ücretsiz', en: 'Free' },
        'medium': { tr: 'Orta', en: 'Medium' },
        'domestic': { tr: '🇨🇳 Yurtiçi Doğrudan Bağlantı', en: '🇨🇳 Domestic Direct Connection' },
        'builtin': { tr: 'Yerleşik', en: 'Builtin' },
        'custom': { tr: 'Özel', en: 'Custom' },
        'user': { tr: 'Kullanıcı', en: 'User' },
        
        'add_custom_model': { tr: 'Özel Model Ekle', en: 'Add Custom Model' },
        'add_custom_provider': { tr: 'Diğer OpenAI Uyumlu Sağlayıcı Ekle', en: 'Add Other OpenAI Compatible Provider' },
        'supports_openai': { tr: 'Herhangi bir OpenAI API uyumlu modeli destekler', en: 'Supports any OpenAI API compatible model' },
        
        'provider_name': { tr: 'Sağlayıcı Adı', en: 'Provider Name' },
        'model_id': { tr: 'Model ID', en: 'Model ID' },
        'base_url': { tr: 'API Adresi', en: 'API URL' },
        'api_key_label': { tr: 'API Anahtarı', en: 'API Key' },
        'local_model_optional': { tr: 'Yerel model için boş bırakılabilir', en: 'Can be empty for local models' },
        
        'configured': { tr: 'Yapılandırıldı', en: 'Configured' },
        'not_configured': { tr: 'Yapılandırılmadı', en: 'Not Configured' },
        'test_connection': { tr: 'Test', en: 'Test' },
        'reset_provider': { tr: 'Sıfırla', en: 'Reset' },
        'save_provider': { tr: 'Kaydet', en: 'Save' },
        
        'testing_connection': { tr: 'Test ediliyor...', en: 'Testing...' },
        'connection_success': { tr: '✓ Başarılı', en: '✓ Success' },
        'connection_failed': { tr: '✗ Başarısız', en: '✗ Failed' },
        'please_fill_key': { tr: 'Lütfen önce API Anahtarı doldurun', en: 'Please fill API Key first' },
        'connection_error': { tr: 'Bağlantı başarısız:', en: 'Connection failed:' },
        
        'view_details': { tr: '🔍 Detayları Görüntüle', en: '🔍 View Details' },
        'edit_workflow': { tr: '✏️ Düzenle', en: '✏️ Edit' },
        'delete_workflow': { tr: '🗑️ Sil', en: '🗑️ Delete' },
        
        'new_workflow': { tr: '+ Yeni İş Akışı', en: '+ New Workflow' },
        'workflow_loading': { tr: 'Yükleniyor...', en: 'Loading...' },
        'no_workflows': { tr: 'İş akışı yok', en: 'No workflows' },
        'create_first': { tr: 'İlkini oluştur', en: 'Create first' },
        'load_failed_retry': { tr: 'Yükleme başarısız:', en: 'Load failed:' },
        'retry': { tr: 'Yeniden dene', en: 'Retry' },
        
        'workflow_steps': { tr: 'adım', en: 'steps' },
        'confirm_delete': { tr: '⚠️ Silmeyi Onayla', en: '⚠️ Confirm Delete' },
        'delete_confirm_msg': { tr: 'İş akışını silmek istediğinizden emin misiniz', en: 'Are you sure you want to delete workflow' },
        'operation_irreversible': { tr: '⚠️ Bu işlem geri alınamaz', en: '⚠️ This operation cannot be undone' },
        'confirm_delete_button': { tr: 'Onayla Sil', en: 'Confirm Delete' },
        
        'workflow_saved': { tr: '✅ İş akışı kaydedildi', en: '✅ Workflow saved' },
        'save_failed_msg': { tr: '❌ Kaydetme başarısız:', en: '❌ Save failed:' },
        'workflow_created': { tr: '✅ İş akışı oluşturuldu', en: '✅ Workflow created' },
        'create_failed': { tr: '❌ Oluşturma başarısız:', en: '❌ Create failed:' },
        'deleted': { tr: '✅ Silindi', en: '✅ Deleted' },
        
        'language_toggle': { tr: 'TR', en: 'EN' }
    };

    let currentLang = 'tr'; // Default

    // Get language from localStorage or detect IP
    async function determineLanguage() {
        // 1. Check localStorage for manual override
        const savedLang = localStorage.getItem('ui_lang');
        if (savedLang && (savedLang === 'tr' || savedLang === 'en')) {
            return savedLang;
        }

        // 2. Check sessionStorage cache (24h TTL)
        const cached = sessionStorage.getItem('country_cache');
        if (cached) {
            const data = JSON.parse(cached);
            const age = Date.now() - data.timestamp;
            if (age < 24 * 60 * 60 * 1000) { // 24 hours
                return data.country === 'TR' ? 'tr' : 'en';
            }
        }

        // 3. Fetch IP geolocation
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2500); // 2.5s timeout

            let country = null;
            
            try {
                // Try ipapi.co first
                const response = await fetch('https://ipapi.co/json/', {
                    signal: controller.signal,
                    timeout: 2500
                });
                if (response.ok) {
                    const data = await response.json();
                    country = data.country;
                }
            } catch (e) {
                // Fallback to ipwho.is
                try {
                    const response = await fetch('https://ipwho.is/', {
                        signal: controller.signal,
                        timeout: 2500
                    });
                    if (response.ok) {
                        const data = await response.json();
                        country = data.country_code;
                    }
                } catch (e2) {
                    console.warn('IP detection failed, using default language');
                }
            }
            
            clearTimeout(timeoutId);

            // Cache the result
            if (country) {
                sessionStorage.setItem('country_cache', JSON.stringify({
                    country: country,
                    timestamp: Date.now()
                }));
                return country === 'TR' ? 'tr' : 'en';
            }
        } catch (e) {
            console.warn('Language detection error:', e);
        }

        // 4. Default to Turkish
        return 'tr';
    }

    // Update all elements with data-i18n attribute
    function updatePageLanguage(lang) {
        currentLang = lang;
        document.documentElement.lang = lang;
        
        // Update all elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (translations[key] && translations[key][lang]) {
                // Preserve child elements if any (e.g., icons, spans)
                if (element.children.length === 0) {
                    element.textContent = translations[key][lang];
                } else {
                    // If element has children, only update text nodes
                    let textChanged = false;
                    element.childNodes.forEach(node => {
                        if (node.nodeType === Node.TEXT_NODE) {
                            node.textContent = translations[key][lang];
                            textChanged = true;
                        }
                    });
                }
            }
        });

        // Update language toggle button
        const toggleBtn = document.getElementById('langToggle');
        if (toggleBtn) {
            toggleBtn.textContent = lang === 'tr' ? 'EN' : 'TR';
        }

        // Store preference
        localStorage.setItem('ui_lang', lang);
    }

    // Toggle language function
    function toggleLanguage() {
        const newLang = currentLang === 'tr' ? 'en' : 'tr';
        updatePageLanguage(newLang);
    }

    // Initialize on page load
    async function initI18n() {
        const lang = await determineLanguage();
        updatePageLanguage(lang);
        
        // Expose toggle function globally
        window.toggleLanguage = toggleLanguage;
        
        // Add event listener to toggle button if exists
        const toggleBtn = document.getElementById('langToggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleLanguage);
        }
    }

    // Run initialization when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initI18n);
    } else {
        initI18n();
    }
})();
