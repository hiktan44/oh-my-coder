"""
eklentisistem

destekinciucyon Agent eklentidinamikyukleveyonet. 

cekirdekgrupogre:
- registry: eklentikayittablo, @register dekoratif
- loader:   eklentiyukle, bagimliliksiralayukle

ornekeklenti:
- example_plugin: ornekeklenti
"""

from src.plugins.loader import PluginLoader, get_loader
from src.plugins.registry import (
    Plugin,
    PluginBase,
    PluginMetadata,
    PluginRegistry,
    PluginStatus,
    get_registry,
    register,
)

__all__ = [
    "Plugin",
    "PluginBase",
    "PluginLoader",
    "PluginMetadata",
    "PluginRegistry",
    "PluginStatus",
    "get_loader",
    "get_registry",
    "register",
]


# otomatikkesfetveyukleicindeayareklenti (saglar main.py cagri) 
def discover_and_load() -> list[str]:
    """kesfetvaricindeayareklentivegorebagimliliksirayukle, donusbasariliyukleeklentiisimliste"""
    loader = get_loader()
    loader.discover()
    return loader.load_all()
