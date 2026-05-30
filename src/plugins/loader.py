from __future__ import annotations

from typing import Optional

"""
eklentiyukle

sorumlueklentikesfet, yuklevebagimliliksirala. 
"""

import importlib
import importlib.util
import sys
from pathlib import Path

from src.plugins.registry import (
    Plugin,
    PluginBase,
    PluginMetadata,
    PluginRegistry,
    PluginStatus,
    get_registry,
)


class PluginLoaderError(Exception):
    """eklentiyuklefarklisik"""


class PluginLoader:
    """
    eklentiyukle

    tarabelirtdizinalt .py dosya, kesfetveyukleeklenti. 
    destekgorebagimliliktopolojisiralayukle. 

    Example::

        loader = PluginLoader(registry=get_registry())
        loader.discover()  # tara src/plugins/ alt .py dosya
        loader.load_all()  # gorebagimliliksirayukle
    """

    # atlamodulisim
    SKIP_MODULES = {"__init__", "registry", "loader"}

    def __init__(
        self,
        registry: Optional[PluginRegistry] = None,
        plugin_dir: Optional[Path] = None,
    ) -> None:
        """
        Args:
            registry: eklentikayittablo, varsayilankullanglobalkayittablo
            plugin_dir: eklentitaradizin, varsayilanicin src/plugins/
        """
        self.registry = registry or get_registry()
        self.plugin_dir = plugin_dir or self._default_plugin_dir()
        self._loaded: list[str] = []

    @staticmethod
    def _default_plugin_dir() -> Path:
        """varsayilaneklentidizin = src/plugins/"""
        return Path(__file__).parent

    # ---- kesfet ----

    def discover(self) -> list[PluginMetadata]:
        """
        tara plugin_dir altvar .py dosya, kesfetolabilirkullaneklenti. 

        atla __init__.py, registry.py, loader.py vb.iskeletdosya. 
        icinher .py dosyadinamikiceri aktar, ara @register dekoratif PluginBase altsinif
        veyadogrubaglantanim PluginBase altsinif. 

        Returns:
            kesfeteklentiogrebilgiliste
        """
        discovered: list[PluginMetadata] = []

        if not self.plugin_dir.exists():
            return discovered

        for py_file in sorted(self.plugin_dir.glob("*.py")):
            module_name = py_file.stem
            if module_name in self.SKIP_MODULES:
                continue

            try:
                self._import_module(py_file, module_name)
            except Exception:
                continue

        # iceri aktarsonrakayittabloicindeisevar @register dekoratifeklenti
        # tekrartaramodul, arahenuzkayitancakvar PluginBase altsinif
        for py_file in sorted(self.plugin_dir.glob("*.py")):
            module_name = py_file.stem
            if module_name in self.SKIP_MODULES:
                continue

            try:
                mod = sys.modules.get(f"src.plugins.{module_name}")
                if mod is None:
                    continue

                # aramodulicindevar PluginBase altsinif
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, PluginBase)
                        and attr is not PluginBase
                    ):
                        # kontrololup olmadigiicindekayittablo
                        try:
                            temp = attr()
                            meta = temp.metadata
                            if not self.registry.get(meta.name):
                                self.registry.register_plugin(attr)
                            if meta not in discovered:
                                discovered.append(meta)
                        except Exception:
                            continue
            except Exception:
                continue

        # birlestirvearaciligiyla @register kayit
        for plugin in self.registry.list_plugins():
            if plugin.metadata not in discovered:
                discovered.append(plugin.metadata)

        return discovered

    def _import_module(self, py_file: Path, module_name: str) -> object:
        """dinamikiceri aktartekil .py dosyaicinmodul"""
        full_name = f"src.plugins.{module_name}"

        # egericeri aktar, oncekaldiryukleiledesteksicaktekraryukle
        if full_name in sys.modules:
            del sys.modules[full_name]

        spec = importlib.util.spec_from_file_location(full_name, str(py_file))
        if spec is None or spec.loader is None:
            raise PluginLoaderError(f"yokyontemolusturmodul spec: {py_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = module
        spec.loader.exec_module(module)
        return module

    # ---- bagimliliksirala ----

    def _topological_sort(self, plugins: list[PluginMetadata]) -> list[PluginMetadata]:
        """
        gorebagimliliktopolojisirala, bagimlilikeklentionceyukle. 

        Args:
            plugins: beklesiralaeklentiogrebilgiliste

        Returns:
            siralasonraliste

        Raises:
            PluginLoaderError: algilamakadardongubagimlilik
        """
        name_map: dict[str, PluginMetadata] = {p.name: p for p in plugins}
        plugin_names = set(name_map.keys())

        # olusturkomsubaglantablo: name -> bagimlilikoeklenti (tersyonkenar) 
        dependents: dict[str, list[str]] = {n: [] for n in plugin_names}
        in_degree: dict[str, int] = dict.fromkeys(plugin_names, 0)

        for p in plugins:
            for req in p.requires:
                if req in plugin_names:
                    dependents[req].append(p.name)
                    in_degree[p.name] += 1
                # disindakisimbagimlilikatla (hayirbloklayukle, tarafindansatirzamankontroldogrula) 

        # Kahn hesaplayontem
        queue: list[str] = [n for n in plugin_names if in_degree[n] == 0]
        sorted_names: list[str] = []

        while queue:
            # harfanasirakararliayarlasirala
            queue.sort()
            name = queue.pop(0)
            sorted_names.append(name)
            for dep_name in dependents[name]:
                in_degree[dep_name] -= 1
                if in_degree[dep_name] == 0:
                    queue.append(dep_name)

        if len(sorted_names) != len(plugins):
            raise PluginLoaderError("algilamakadardongubagimlilik, yokyontemkesinyuklesira")

        return [name_map[n] for n in sorted_names]

    # ---- yukle ----

    def load(self, name: str) -> Optional[Plugin]:
        """
        yukletekileklenti. 

        Args:
            name: eklentiad

        Returns:
            yuklesonra Plugin ornek, basarisizdonus None
        """
        plugin = self.registry.get(name)
        if plugin is None:
            return None

        if plugin.status == PluginStatus.ENABLED:
            return plugin

        try:
            plugin.status = PluginStatus.LOADING

            if plugin.instance is None:
                raise PluginLoaderError(f"eklenti {name} yokvarornek")

            # cagri on_load
            plugin.instance.on_load()

            # kayitkaynak
            self.registry._register_agents(plugin.instance.register_agents())
            self.registry._register_skills(plugin.instance.register_skills())
            self.registry._register_hooks(plugin.instance.register_hooks())

            plugin.status = PluginStatus.DISABLED
            self._loaded.append(name)
            return plugin

        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error = f"{type(e).__name__}: {e}"
            return None

    def load_all(self) -> list[str]:
        """
        kesfetvareklenti, gorebagimliliksirayukle. 

        aynizamanislearaciligiyla @register veya register_plugin manuelkayit
        ancakhenuzhenuzyukleeklenti. 

        Returns:
            basariliyukleeklentiisimliste
        """
        discovered = self.discover()

        # birlestirvekayittabloicindekayitancakhenuzicinde discovered icindeeklenti
        registered = self.registry.list_plugins()
        registered_metas = [p.metadata for p in registered]
        for meta in registered_metas:
            if meta not in discovered:
                discovered.append(meta)

        if not discovered:
            return list(self._loaded)

        sorted_plugins = self._topological_sort(discovered)

        for meta in sorted_plugins:
            self.load(meta.name)

        return list(self._loaded)

    def enable(self, name: str) -> bool:
        """baslatkullaneklenti"""
        plugin = self.registry.get(name)
        if not plugin or plugin.status == PluginStatus.ERROR:
            return False

        try:
            if plugin.instance:
                plugin.instance.on_enable()
            plugin.status = PluginStatus.ENABLED
            return True
        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error = f"{type(e).__name__}: {e}"
            return False

    def disable(self, name: str) -> bool:
        """yasakkullaneklenti"""
        plugin = self.registry.get(name)
        if not plugin:
            return False

        try:
            if plugin.instance:
                plugin.instance.on_disable()
            plugin.status = PluginStatus.DISABLED
            return True
        except Exception:
            return False

    def unload(self, name: str) -> bool:
        """
        kaldiryukleeklenti. 

        Args:
            name: eklentiad

        Returns:
            basarili mi
        """
        plugin = self.registry.get(name)
        if not plugin:
            return False

        try:
            if plugin.instance:
                plugin.instance.on_unload()
            self.registry._clear_resources(name)
            if name in self._loaded:
                self._loaded.remove(name)
            plugin.status = PluginStatus.DISABLED
            plugin.instance = None
            return True
        except Exception:
            return False


# ---- globalyukle ----

_loader: Optional[PluginLoader] = None


def get_loader() -> PluginLoader:
    """alglobaleklentiyukle"""
    global _loader
    if _loader is None:
        _loader = PluginLoader()
    return _loader
