"""
ornekeklenti

oynagosterorneginnekullan @register dekoratifolustureklenti. 
"""

from src.plugins.registry import PluginBase, PluginMetadata, register


@register
class ExamplePlugin(PluginBase):
    """ornekeklenti, gostereklentisistemtemelkullanyontem"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="example",
            version="0.1.0",
            description="ornekeklenti, gostereklentisistemtemelkullanyontem",
            author="oh-my-coder",
            tags=["example", "demo"],
        )

    def on_load(self) -> None:
        print("[example] eklentiyukle")

    def on_enable(self) -> None:
        print("[example] eklentibaslatkullan")

    def on_disable(self) -> None:
        print("[example] eklentiyasakkullan")

    def on_unload(self) -> None:
        print("[example] eklentikaldiryukle")

    def register_skills(self):
        return {
            "example_greet": self._greet,
        }

    def register_hooks(self):
        return {
            "on_startup": self._on_startup,
        }

    @staticmethod
    def _greet(name: str = "World") -> str:
        """ornekteknikedebilir: selam"""
        return f"Hello, {name}! From example plugin."

    @staticmethod
    def _on_startup() -> None:
        """baslatkancaalt"""
        print("[example] sistembaslatbildirim")
