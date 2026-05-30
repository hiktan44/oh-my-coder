"""
baglamsikistiriyi - akilliedebilirsikistirstatik bilgi, korudinamikakil yurutme

cekirdekstrateji: 
1. tanistatik bilgi (dosyaicerik, dokumantasyon, yapilandirma) → sikistiricinalintiister
2. korudinamikakil yurutme (dusunce zinciri, kararsurec, hataduzeltme) → tamkoru
3. puanseviyesikistir: goremesajtipvetekraristeruygulamahayiraynisikistirstrateji
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MessageType(Enum):
    """mesajtippuansinif"""

    STATIC_KNOWLEDGE = "static"  # statik bilgi: dosyaicerik, dokumantasyon, yapilandirma
    DYNAMIC_REASONING = "dynamic"  # dinamikakil yurutme: dusunce zinciri, analizsurec
    TOOL_EXECUTION = "tool"  # aracyurut: komutcikti, arasonuc
    ERROR = "error"  # hata mesaji
    SYSTEM = "system"  # sistemmesaj
    USER = "user"  # kullanicigirdi
    ASSISTANT = "assistant"  # yardimcigeritekrar


class CompressionLevel(Enum):
    """sikistirseviye"""

    NONE = 0  # hayirsikistir (korutam) 
    LIGHT = 1  # hafifderecesikistir (koruanahtarbilgi) 
    MEDIUM = 2  # icindederecesikistir (olusturalintiister) 
    HEAVY = 3  # tekrarderecesikistir (sadecekoruogresayigore) 


@dataclass
class CompressionRule:
    """sikistirkural"""

    message_type: MessageType
    level: CompressionLevel
    priority: int  # oncelikseviye, sayiharfasirikucukasiritekrarister
    description: str


# varsayilansikistirkural: dinamikakil yurutme > kullanicigirdi > sistemmesaj > aracyurut > statik bilgi > hata
DEFAULT_RULES = [
    CompressionRule(
        MessageType.DYNAMIC_REASONING, CompressionLevel.NONE, 1, "korutamakil yurutmesurec"
    ),
    CompressionRule(MessageType.USER, CompressionLevel.NONE, 2, "korukullanicigirdi"),
    CompressionRule(MessageType.SYSTEM, CompressionLevel.LIGHT, 3, "hafifderecesikistirsistemmesaj"),
    CompressionRule(
        MessageType.ASSISTANT, CompressionLevel.LIGHT, 4, "hafifderecesikistiryardimcigeritekrar"
    ),
    CompressionRule(
        MessageType.TOOL_EXECUTION, CompressionLevel.MEDIUM, 5, "icindederecesikistiraraccikti"
    ),
    CompressionRule(
        MessageType.STATIC_KNOWLEDGE, CompressionLevel.HEAVY, 6, "tekrarderecesikistirstatik bilgi"
    ),
    CompressionRule(MessageType.ERROR, CompressionLevel.MEDIUM, 7, "icindederecesikistirgecmishata"),
]


@dataclass
class CompressedMessage:
    """sikistirsonramesaj"""

    original_role: str
    original_content: str
    compressed_content: str
    message_type: MessageType
    compression_level: CompressionLevel
    tokens_saved: int
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextCompressor:
    """baglamsikistir

    akilliedebilirtanimesajtip, uygulamafarkfarklisikistirstrateji: 
    - statik bilgi (dosyaicerik, dokumantasyon) → cikaranahtarbilgi, silfazlakalan
    - dinamikakil yurutme (dusunce zinciri, analiz) → tamkoru
    - aracyurut (komutcikti) → korusonuc, atlasurec
    """

    def __init__(self, rules: Optional[list[CompressionRule]] = None):
        self.rules = rules or DEFAULT_RULES
        self.rules_map = {r.message_type: r for r in self.rules}

    def classify_message(self, role: str, content: str) -> MessageType:
        """puansinifmesajtip"""
        # sistemmesaj
        if role == "system":
            return MessageType.SYSTEM

        # kullanicimesaj
        if role == "user":
            return MessageType.USER

        # hatamesaj
        if self._is_error(content):
            return MessageType.ERROR

        # dinamikakil yurutme (dusunce zinciri, analizsurec) 
        if self._is_reasoning(content):
            return MessageType.DYNAMIC_REASONING

        # statik bilgi (dosyaicerik, dokumantasyon, yapilandirma) 
        if self._is_static_knowledge(content):
            return MessageType.STATIC_KNOWLEDGE

        # aracyurut
        if role == "tool" or self._is_tool_execution(content):
            return MessageType.TOOL_EXECUTION

        # varsayilan
        return MessageType.ASSISTANT

    def compress(
        self, role: str, content: str, tokens_before: int
    ) -> CompressedMessage:
        """sikistirtekilogremesaj"""
        msg_type = self.classify_message(role, content)
        rule = self.rules_map.get(msg_type, DEFAULT_RULES[-1])

        if rule.level == CompressionLevel.NONE:
            return CompressedMessage(
                original_role=role,
                original_content=content,
                compressed_content=content,
                message_type=msg_type,
                compression_level=rule.level,
                tokens_saved=0,
            )

        compressed, saved = self._apply_compression(content, rule.level, tokens_before)

        return CompressedMessage(
            original_role=role,
            original_content=content,
            compressed_content=compressed,
            message_type=msg_type,
            compression_level=rule.level,
            tokens_saved=saved,
        )

    def compress_session(
        self,
        messages: list[dict[str, Any]],
        token_counter: Optional[Any] = None,
    ) -> tuple[list[dict[str, Any]], CompressionSummary]:
        """sikistirtamyapacakkonusma

        Args:
            messages: mesajliste, herogredir {"role": str, "content": str}
            token_counter: token hesapsayifonksiyon

        Returns:
            (sikistirsonramesajliste, sikistiralintiister)
        """
        compressed_messages = []
        total_saved = 0
        type_stats = {t: 0 for t in MessageType}

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # tahmin token sayi
            tokens_before = (
                len(content) // 4 if token_counter is None else token_counter(content)
            )

            result = self.compress(role, content, tokens_before)

            compressed_messages.append(
                {
                    "role": role,
                    "content": result.compressed_content,
                    "_compressed": result.compression_level != CompressionLevel.NONE,
                    "_original_type": result.message_type.value,
                }
            )

            total_saved += result.tokens_saved
            type_stats[result.message_type] += 1

        summary = CompressionSummary(
            total_messages=len(messages),
            total_tokens_saved=total_saved,
            type_distribution=type_stats,
        )

        return compressed_messages, summary

    # ===== icindekisimyontem =====

    def _is_error(self, content: str) -> bool:
        """karar verolup olmadigiicinhatamesaj"""
        error_patterns = [
            r"error:",
            r"exception:",
            r"traceback",
            r"failed:",
            r"^\s*error\s",
            r"^\s*exception\s",
        ]
        content_lower = content.lower()
        return any(re.search(p, content_lower) for p in error_patterns)

    def _is_reasoning(self, content: str) -> bool:
        """karar verolup olmadigiicindinamikakil yurutme (dusunce zinciri) """
        reasoning_patterns = [
            r"izin verbendusuncesinabiralt",
            r"analiz.*asilneden",
            r"akil yurutme.*surec",
            r"karar.*bagligore",
            r"secsec.*nedenicin",
            r"kiyaskiyas.*iyikotu",
            r"degerlendir.*plan",
            r"dusuncesina.*adim",
            r"^\d+\.\s+(ilkonce|sonra|baglanaltgel|ensonra)",
            r"(planning|reasoning|thinking|analysis)",
        ]
        return any(re.search(p, content, re.IGNORECASE) for p in reasoning_patterns)

    def _is_static_knowledge(self, content: str) -> bool:
        """karar verolup olmadigiicinstatik bilgi"""
        static_patterns = [
            r"^\s*```\w+",  # kodblok
            r"^\s*#+\s+",  # Markdown baslik
            r"^\s*[-*]\s+",  # liste
            r"dosyaicerik",
            r"dokumantasyonaciklama",
            r"yapilandirmaparametre",
            r"^\s*\{",  # JSON
            r"^\s*<",  # XML/HTML
        ]
        return any(re.search(p, content) for p in static_patterns)

    def _is_tool_execution(self, content: str) -> bool:
        """karar verolup olmadigiicinaracyurutme sonucu"""
        tool_patterns = [
            r"^\s*\$\s+",  # komutsatir
            r"^\s*>",  # komutcikti
            r"yurutme sonucu",
            r"ciktiicerik",
            r"^\s*\[\d{4}-\d{2}-\d{2}",  # zamanarasindadamgalog
        ]
        return any(re.search(p, content) for p in tool_patterns)

    def _apply_compression(
        self,
        content: str,
        level: CompressionLevel,
        tokens_before: int,
    ) -> tuple[str, int]:
        """uygulamasikistirstrateji"""
        if level == CompressionLevel.LIGHT:
            # hafifderece: silcokkalanbossatir, birlestirvebagladevambos
            compressed = re.sub(r"\n{3,}", "\n\n", content)
            compressed = re.sub(r" {2,}", " ", compressed)
            saved = tokens_before - len(compressed) // 4
            return compressed, max(0, saved)

        elif level == CompressionLevel.MEDIUM:
            # icindederece: cikaranahtarbilgi, olusturalintiister
            compressed = self._extract_key_info(content)
            saved = tokens_before - len(compressed) // 4
            return compressed, max(0, saved)

        elif level == CompressionLevel.HEAVY:
            # tekrarderece: sadecekoruogresayigoreveanahtarsonuc
            compressed = self._extract_metadata(content)
            saved = tokens_before - len(compressed) // 4
            return compressed, max(0, saved)

        return content, 0

    def _extract_key_info(self, content: str) -> str:
        """cikaranahtarbilgi (icindederecesikistir) """
        lines = content.split("\n")
        key_lines = []

        for line in lines:
            # koruiceriranahtarbilgisatir
            if any(
                kw in line.lower()
                for kw in [
                    "sonuc",
                    "basarili",
                    "basarisiz",
                    "hata",
                    "uyari",
                    "result",
                    "success",
                    "fail",
                    "error",
                    "warning",
                    "toplam",
                    "tartis",
                    "summary",
                    "conclusion",
                ]
            ):
                key_lines.append(line)

        if key_lines:
            return "[alintiister] " + " | ".join(key_lines[:5])
        return content[:200] + "..." if len(content) > 200 else content

    def _extract_metadata(self, content: str) -> str:
        """cikarogresayigore (tekrarderecesikistir) """
        # istatistikbilgi
        lines = content.split("\n")
        code_blocks = len(re.findall(r"```", content)) // 2
        urls = len(re.findall(r"https?://\S+", content))

        meta = f"[sikistiricerik: {len(lines)}satir"
        if code_blocks > 0:
            meta += f", {code_blocks}kodblok"
        if urls > 0:
            meta += f", {urls}baglanti"
        meta += "]"

        # koruincibirsatir (sikdirbaslik/alintiister) 
        first_line = lines[0][:100] if lines else ""
        return f"{meta}\n{first_line}..."


@dataclass
class CompressionSummary:
    """sikistiralintiister"""

    total_messages: int
    total_tokens_saved: int
    type_distribution: dict[MessageType, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_messages": self.total_messages,
            "total_tokens_saved": self.total_tokens_saved,
            "type_distribution": {
                k.value: v for k, v in self.type_distribution.items()
            },
        }
