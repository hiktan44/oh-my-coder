"""
Ajan durum kalıcılaştırma modülü

Ajan oturum durumunu yerel dosya sistemine kaydeder, yeniden başlatma kurtarması ve export/import destekler.

Dizin yapısı:
    ~/.oh-my-coder/agents/<agent_name>/
    ├── config.json       # Ajan yapılandırma anlık görüntüsü
    ├── history.jsonl     # Sohbet geçmişi (append-only)
    └── state.json        # Çalışma zamanı durumu
"""

from .store import AgentStateStore

__all__ = ["AgentStateStore"]
