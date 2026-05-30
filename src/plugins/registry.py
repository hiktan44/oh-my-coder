from __future__ import annotations

"""
eklentikayittablo

saglareklentiogrebilgiyonet, @register dekoratifveglobalkayittablo. 
"""

import contextlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class PluginStatus(str, Enum):
    """eklentidurum"""

    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


class PluginMetadata(BaseModel):
    """eklentiogresayigore"""

    name: str
    version: str
    description: str = ""
    author: str = ""
    homepage: str = ""
    license: str = "MIT"
    requires: list[str] = []  # bagimlilikonunoeklentiisim
    entrypoint: str = ""
    tags: list[str] = []


@dataclass
class Plugin:
    """eklentiornek"""

    metadata: PluginMetadata
    status: PluginStatus = PluginStatus.DISABLED
    module: Optional[Any] = None
    instance: Optional[PluginBase] = None
    error: Optional[str] = None
    config: dict[str, Any] = field(default_factory=dict)


class PluginBase(ABC):
    """
    eklentitemel sinif

    vareklentizorunludevamustlenbusinifveuygulagerekliisteryontem. 

    Example::

        class MyPlugin(PluginBase):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(name="my", version="0.1.0")

            def on_load(self) -> None:
                print("loaded")
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """donuseklentiogresayigore"""

    @abstractmethod
    def on_load(self) -> None:
        """eklentiyuklezamancagri"""

    def on_enable(self) -> None:
        """eklentibaslatkullanzamancagri"""

    def on_disable(self) -> None:
        """eklentiyasakkullanzamancagri"""

    def on_unload(self) -> None:
        """eklentikaldiryuklezamancagri"""

    def register_agents(self) -> list[type]:
        """kayit Agent sinif"""
        return []

    def register_skills(self) -> dict[str, Callable]:
        """kayitteknikedebilirfonksiyon"""
        return {}

    def register_hooks(self) -> dict[str, Callable]:
        """kayitkancaaltfonksiyon"""
        return {}


class PluginRegistry:
    """
    eklentikayittablo

    yonetkayiteklentiogrebilgiveornek. 
    destekaraciligiyla @register dekoratifveyamanuelkayit. 
    """

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._agents: dict[str, type] = {}
        self._skills: dict[str, Callable] = {}
        self._hooks: dict[str, list[Callable]] = {}

    # ---- kayit ----

    def register_plugin(self, plugin_cls: type[PluginBase]) -> Plugin:
        """
        kayitbireklentisinif (hayiryukle, sadecekayitogrebilgi) . 

        Args:
            plugin_cls: eklentisinif (zorunludevamustlen PluginBase) 

        Returns:
            Plugin ornek

        Raises:
            TypeError: eger plugin_cls hayirdir PluginBase altsinif
        """
        if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, PluginBase)):
            raise TypeError(f"{plugin_cls} hayirdir PluginBase altsinif")

        # geçicizamanornekalogrebilgi
        temp = plugin_cls()
        meta = temp.metadata

        plugin = Plugin(metadata=meta, instance=temp)
        self._plugins[meta.name] = plugin
        return plugin

    def unregister(self, name: str) -> bool:
        """
        yorumiptaleklenti. 

        Args:
            name: eklentiad

        Returns:
            basarili mi
        """
        if name not in self._plugins:
            return False
        del self._plugins[name]
        return True

    # ---- sorgu ----

    def get(self, name: str) -> Optional[Plugin]:
        """aleklenti"""
        return self._plugins.get(name)

    def list_plugins(self) -> list[Plugin]:
        """tumunu listelevareklenti"""
        return list(self._plugins.values())

    def list_by_status(self, status: PluginStatus) -> list[Plugin]:
        """goredurumfiltreleeklenti"""
        return [p for p in self._plugins.values() if p.status == status]

    def get_agent(self, name: str) -> Optional[type]:
        """alkayit Agent sinif"""
        return self._agents.get(name)

    def get_skill(self, name: str) -> Optional[Callable]:
        """alkayitteknikedebilir"""
        return self._skills.get(name)

    def execute_hook(self, name: str, *args: Any, **kwargs: Any) -> list[Any]:
        """
        yurutkancaalt

        Args:
            name: kancaaltad

        Returns:
            kancaaltyurutme sonuculiste
        """
        hooks = self._hooks.get(name, [])
        results: list[Any] = []
        for hook in hooks:
            with contextlib.suppress(Exception):
                results.append(hook(*args, **kwargs))
        return results

    # ---- kaynakkayit (tarafindan loader cagri) ----

    def _register_agents(self, agents: list[type]) -> None:
        for agent_cls in agents:
            self._agents[agent_cls.__name__] = agent_cls

    def _register_skills(self, skills: dict[str, Callable]) -> None:
        self._skills.update(skills)

    def _register_hooks(self, hooks: dict[str, Callable]) -> None:
        for hook_name, hook_fn in hooks.items():
            if hook_name not in self._hooks:
                self._hooks[hook_name] = []
            self._hooks[hook_name].append(hook_fn)

    def _clear_resources(self, name: str) -> None:
        """temizleharicbelirteklentikayitkaynak"""
        plugin = self._plugins.get(name)
        if not plugin or not plugin.instance:
            return

        # temizleharic agents
        for agent_cls in plugin.instance.register_agents():
            self._agents.pop(agent_cls.__name__, None)

        # temizleharic skills
        for skill_name in plugin.instance.register_skills():
            self._skills.pop(skill_name, None)

        # temizleharic hooks
        for hook_name in plugin.instance.register_hooks():
            hook_list = self._hooks.get(hook_name, [])
            self._hooks[hook_name] = [
                h
                for h in hook_list
                if h not in plugin.instance.register_hooks().values()
            ]


# ---- globalkayittablo ----

_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """alglobaleklentikayittablo"""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


# ---- @register dekoratif ----


def register(cls: type[PluginBase]) -> type[PluginBase]:
    """
    sinifdekoratif, eklentisinifkayitkadarglobalkayittablo. 

    Example::

        @register
        class MyPlugin(PluginBase):
            @property
            def metadata(self):
                return PluginMetadata(name="my", version="0.1.0")

            def on_load(self):
                pass

    Args:
        cls: eklentisinif

    Returns:
        hamsinif (yokdegistir) 
    """
    get_registry().register_plugin(cls)
    return cls
