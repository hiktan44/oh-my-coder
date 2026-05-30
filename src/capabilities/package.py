from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
yetenekpaketsistem - Capability Package System

referans EvoMap  Gene/Capsule akilkavram, uygulayetenekkaynakurettemeltemelislev. 
kullaniciolabilirileiyisonra Agent yapilandirmavurpaketdisa aktar, toplulukbolgeolabilirileortakpaylasbubazi"yetenekpaket". 
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class CapabilityPackage:
    """
    yetenekpaketsayigoreyapi

    icerirtam Agent yapilandirma, modelyapilandirma, araclisteve Prompt sablon, 
    olabiliriledisa aktar, paylasveiceri aktar. 
    """

    # temelbilgi
    name: str  # paketad
    version: str  # surumno (semver)
    description: str  # islevaciklama
    author: str  # yazar
    created_at: str  # olusturzamanarasinda
    tags: list[str] = field(
        default_factory=list
    )  # etiket (e.g., ["code-review", "refactor"])

    # cekirdekyapilandirma
    agents: dict = field(default_factory=dict)  # Agent yapilandirma
    model_config: dict = field(default_factory=dict)  # modelyapilandirma
    tools: list[str] = field(default_factory=list)  # baslatkullanaracliste
    prompts: dict = field(default_factory=dict)  # ozel Prompt sablon

    # ogresayigore
    readme: str = ""  # kullanaciklama
    examples: list[dict] = field(default_factory=list)  # kullanornek

    def save(self, path: Path) -> None:
        """kaydetyetenekpaketkadar JSON dosya"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> CapabilityPackage:
        """ JSON dosyayukleyetenekpaket"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """donusturicinsozluk"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackage:
        """sozlukolustur"""
        return cls(**data)

    def validate(self) -> list[str]:
        """
        dogrulamayetenekpakettam

        Returns:
            hata mesajiliste, boslistetablogosterdogrulamaaraciligiyla
        """
        errors = []

        if not self.name or not self.name.strip():
            errors.append("paketadhayiredebiliricinbos")

        if not self.version:
            errors.append("surumnohayiredebiliricinbos")

        # basittekil semver dogrulama
        version_parts = self.version.split(".")
        if len(version_parts) < 2:
            errors.append("surumnoformatolmaliicin semver (ornegin 1.0.0)")

        if not self.description:
            errors.append("islevaciklamahayiredebiliricinbos")

        if not self.author:
            errors.append("yazarhayiredebiliricinbos")

        return errors


class CapabilityPackageManager:
    """
    yetenekpaketyonet

    sorumluyetenekpaketdepolama, yukle, listeveuygulama. 
    """

    def __init__(self, packages_dir: Optional[Path] = None):
        """
        baslatyonet

        Args:
            packages_dir: yetenekpaketdepolamadizin, varsayilan ~/.omc/capabilities/
        """
        if packages_dir is None:
            packages_dir = Path.home() / ".omc" / "capabilities"

        self.packages_dir = packages_dir
        self.packages_dir.mkdir(parents=True, exist_ok=True)

    def _get_package_path(self, name: str) -> Path:
        """alyetenekpaketdosyayol"""
        return self.packages_dir / f"{name}.json"

    def list_packages(self) -> list[CapabilityPackage]:
        """tumunu listelevaryerelyetenekpaket"""
        packages = []

        if not self.packages_dir.exists():
            return packages

        for file_path in self.packages_dir.glob("*.json"):
            try:
                pkg = CapabilityPackage.load(file_path)
                packages.append(pkg)
            except Exception:
                # atlazararkotupaket
                continue

        # goreolusturzamanarasindasirala (enyeniicindeonce) 
        packages.sort(key=lambda p: p.created_at, reverse=True)
        return packages

    def get_package(self, name: str) -> Optional[CapabilityPackage]:
        """albelirtadyetenekpaket"""
        path = self._get_package_path(name)
        if not path.exists():
            return None

        try:
            return CapabilityPackage.load(path)
        except Exception:
            return None

    def save_package(self, package: CapabilityPackage) -> None:
        """kaydetyetenekpaket"""
        path = self._get_package_path(package.name)
        package.save(path)

    def delete_package(self, name: str) -> bool:
        """silyetenekpaket"""
        path = self._get_package_path(name)
        if path.exists():
            path.unlink()
            return True
        return False

    def export_from_config(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        tags: list[str],
        agents: dict,
        model_config: dict,
        tools: list[str],
        prompts: dict,
        readme: str = "",
        examples: Optional[list[dict]] = None,
    ) -> CapabilityPackage:
        """
        mevcutyapilandirmadisa aktaryetenekpaket

        Args:
            name: paketad
            version: surumno
            description: islevaciklama
            author: yazar
            tags: etiketliste
            agents: Agent yapilandirma (yapacakfiltrelehassasbilgi) 
            model_config: modelyapilandirma (yapacakfiltrelehassasbilgi) 
            tools: aracliste
            prompts: Prompt sablon
            readme: kullanaciklama
            examples: kullanornek

        Returns:
            olusturyetenekpaket
        """
        # filtrelehassasbilgi
        safe_model_config = self._sanitize_model_config(model_config)
        safe_agents = self._sanitize_agents(agents)

        package = CapabilityPackage(
            name=name,
            version=version,
            description=description,
            author=author,
            created_at=datetime.now().isoformat(),
            tags=tags,
            agents=safe_agents,
            model_config=safe_model_config,
            tools=tools,
            prompts=prompts,
            readme=readme,
            examples=examples or [],
        )

        self.save_package(package)
        return package

    def _sanitize_model_config(self, config: dict) -> dict:
        """temizlemodelyapilandirmaicindehassasbilgi"""
        safe_config = config.copy()

        # kaldirveyamaskele API Key
        sensitive_keys = ["api_key", "api_secret", "secret", "token", "password"]
        for key in list(safe_config.keys()):
            if any(sk in key.lower() for sk in sensitive_keys):
                value = safe_config[key]
                if isinstance(value, str) and len(value) > 8:
                    # koruonce4konumvesonra4konum, icindearasindakullan *** yerineyedek
                    safe_config[key] = value[:4] + "***" + value[-4:]
                else:
                    safe_config[key] = "***"

        return safe_config

    def _sanitize_agents(self, agents: dict) -> dict:
        """temizle Agent yapilandirmaicindehassasbilgi"""
        safe_agents = {}

        for agent_name, agent_config in agents.items():
            if isinstance(agent_config, dict):
                safe_agents[agent_name] = self._sanitize_model_config(agent_config)
            else:
                safe_agents[agent_name] = agent_config

        return safe_agents

    def apply_package(
        self,
        name: str,
        target_config: Optional[dict] = None,
    ) -> dict:
        """
        uygulamayetenekpaketyapilandirma

        Args:
            name: yetenekpaketad
            target_config: hedefisaretyapilandirmasozluk (yapacakdegistir) 

        Returns:
            uygulamasonrayapilandirma
        """
        package = self.get_package(name)
        if package is None:
            raise ValueError(f"yetenekpaketmevcut degil: {name}")

        if target_config is None:
            target_config = {}

        # birlestirveyapilandirma
        if package.agents:
            target_config.setdefault("agents", {}).update(package.agents)

        if package.model_config:
            target_config.setdefault("model_config", {}).update(package.model_config)

        if package.tools:
            target_config.setdefault("tools", []).extend(package.tools)
            # yinelenenleri kaldir
            target_config["tools"] = list(set(target_config["tools"]))

        if package.prompts:
            target_config.setdefault("prompts", {}).update(package.prompts)

        return target_config


# globalyonetornek
_default_manager: Optional[CapabilityPackageManager] = None


def get_manager() -> CapabilityPackageManager:
    """alvarsayilanyetenekpaketyonet"""
    global _default_manager
    if _default_manager is None:
        _default_manager = CapabilityPackageManager()
    return _default_manager
