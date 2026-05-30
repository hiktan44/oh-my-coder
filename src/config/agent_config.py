from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Agent yapilandirmamodul - destek YAML/JSON yapilandirmayukle

kullanyontem:
    from src.config.agent_config import AgentConfig, load_config_file

    config = load_config_file("agents/code_review.yaml")
    agent = config.to_agent()
"""


import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────
# sayigoremodel
# ─────────────────────────────────────────────────────────────


@dataclass
class ToolConfig:
    """aracyapilandirma"""

    name: str
    enabled: bool = True
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentConfig:
    """ortamyapilandirma"""

    max_tokens: int = 8000
    temperature: float = 0.7
    timeout: int = 60
    retry: int = 3


@dataclass
class PromptTemplate:
    """Prompt sablon"""

    name: str
    template: str
    variables: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Agent yapilandirma"""

    name: str
    description: str
    model: str = "deepseek"
    tools: list[str] = field(default_factory=list)
    permissions: dict[str, Any] = field(default_factory=dict)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    prompts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_system_prompt(self) -> str:
        """al system prompt"""
        return self.prompts.get("system", f"sendirbirozelendustri {self.name} Agent. ")

    def get_prompt_template(self, key: str) -> str:
        """albelirt key  prompt sablon, destek {{degismiktar}} degistir"""
        return self.prompts.get(key, "")

    def render_template(self, key: str, **kwargs: Any) -> str:
        """render prompt sablon, degistir {{degismiktar}}"""
        template = self.get_prompt_template(key)
        for var_name, var_value in kwargs.items():
            template = template.replace(f"{{{{{var_name}}}}}", str(var_value))
        return template

    def to_dict(self) -> dict[str, Any]:
        """siraicin dict"""
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "tools": self.tools,
            "permissions": self.permissions,
            "environment": {
                "max_tokens": self.environment.max_tokens,
                "temperature": self.environment.temperature,
                "timeout": self.environment.timeout,
                "retry": self.environment.retry,
            },
            "prompts": self.prompts,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        """ dict terssira"""
        env_data = data.get("environment", {})
        env = EnvironmentConfig(
            max_tokens=env_data.get("max_tokens", 8000),
            temperature=env_data.get("temperature", 0.7),
            timeout=env_data.get("timeout", 60),
            retry=env_data.get("retry", 3),
        )
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            model=data.get("model", "deepseek"),
            tools=data.get("tools", []),
            permissions=data.get("permissions", {}),
            environment=env,
            prompts=data.get("prompts", {}),
            metadata=data.get("metadata", {}),
        )

    def validate(self) -> list[str]:
        """dogrulamayapilandirmabirlestiryontem, donushataliste"""
        errors = []

        if not self.name or not re.match(r"^[a-z0-9_-]+$", self.name):
            errors.append("name zorunludirharfana/sayiharf/altplansatir/baglakaraktergrupbirlestir")

        if self.environment.max_tokens < 100:
            errors.append("max_tokens enkucukicin 100")

        if not (0 <= self.environment.temperature <= 2):
            errors.append("temperature zorunluicinde 0-2 arasinda")

        denied = self.permissions.get("denied_patterns", [])
        if denied:
            for pattern in denied:
                try:
                    re.compile(pattern)
                except re.error as e:
                    errors.append(f"denied_patterns regexhata: {e}")

        return errors


# ─────────────────────────────────────────────────────────────
# yukle
# ─────────────────────────────────────────────────────────────


def load_config_file(path: str | Path) -> AgentConfig:
    """
    yukle YAML veya JSON format Agent yapilandirma dosyasi

    Args:
        path: yapilandirma dosyasiyol

    Returns:
        AgentConfig ornek

    Raises:
        FileNotFoundError: dosyamevcut degil
        ValueError: formathayirdestekveyaayristirma basarisiz
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"yapilandirma dosyasimevcut degil: {path}")

    raw = p.read_text(encoding="utf-8")

    if p.suffix in (".yaml", ".yml"):
        data = _load_yaml(raw)
    elif p.suffix == ".json":
        data = json.loads(raw)
    else:
        raise ValueError(f"hayirdestekdosyaformat: {p.suffix}, sadecedestek .yaml/.yml/.json")

    return AgentConfig.from_dict(data)


def load_config_dir(dir_path: str | Path) -> list[AgentConfig]:
    """
    yukledizinaltvar YAML/JSON yapilandirma dosyasi

    Args:
        dir_path: dizin yolu

    Returns:
        AgentConfig liste
    """
    p = Path(dir_path)
    if not p.is_dir():
        return []

    configs: list[AgentConfig] = []
    for ext in ("*.yaml", "*.yml", "*.json"):
        for fp in p.glob(ext):
            try:
                configs.append(load_config_file(fp))
            except Exception:
                pass  # atlaayristirma basarisizdosya

    return configs


def validate_config_file(path: str | Path) -> tuple[bool, list[str]]:
    """
    dogrulamayapilandirma dosyasibirlestiryontem

    Returns:
        (olup olmadigibirlestiryontem, hataliste)
    """
    try:
        config = load_config_file(path)
        errors = config.validate()
        return len(errors) == 0, errors
    except FileNotFoundError:
        return False, ["yapilandirma dosyasimevcut degil"]
    except Exception as e:
        return False, [f"ayristirma basarisiz: {type(e).__name__}"]


def list_configs_in_dir(dir_path: str | Path) -> list[str]:
    """listeledizinaltvaryapilandirma dosyasikesinicinyol"""
    p = Path(dir_path)
    if not p.is_dir():
        return []

    result: list[str] = []
    for ext in ("*.yaml", "*.yml", "*.json"):
        result.extend([str(fp.resolve()) for fp in p.glob(ext)])

    return sorted(result)


# ─────────────────────────────────────────────────────────────
# icindekisim
# ─────────────────────────────────────────────────────────────


def _load_yaml(raw: str) -> dict[str, Any]:
    """ayristir YAML (kullanstandartkutuphaneuygula, sifirbagimlilik) """
    try:
        from ._yaml import yaml_safe_load

        return yaml_safe_load(raw)
    except ImportError:
        pass

    # standartkutuphane fallback: manuelayristirbasittekil YAML
    result: dict[str, Any] = {}
    current_key: Optional[str] = None
    current_list: Optional[list[str]] = None
    current_dict: Optional[dict[str, Any]] = None
    in_dict = False

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # algilamakucultilerle
        content = stripped.rstrip()

        # listeogre
        if content.startswith("- "):
            item = content[2:].strip()
            if current_list is not None:
                current_list.append(item)
            elif current_dict is not None:
                # dict icindeliste
                if current_key:
                    if current_key not in result:
                        result[current_key] = []
                    result[current_key].append(item)
        elif ":" in content and not content.startswith(":"):
            key, _, value = content.partition(":")
            key = key.strip()
            value = value.strip()

            if value:
                # basittekilanahtardegericin
                if current_dict is not None:
                    current_dict[key] = _parse_value(value)
                else:
                    result[key] = _parse_value(value)
            else:
                # iciceicinnesne
                if in_dict and current_dict is not None:
                    # isle dict bitir
                    if current_key and current_key not in result:
                        result[current_key] = current_dict
                current_key = key
                current_dict = {}
                in_dict = True

    if current_dict and current_key:
        result[current_key] = current_dict

    return result


def _parse_value(value: str) -> Any:
    """ayristir YAML deger"""
    v = value.strip('"').strip("'")
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if v.lower() == "null":
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v
