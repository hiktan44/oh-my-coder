
# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""Auto Compact - baglamotomatiksikistir


ne zamanyapacakkonusma token baglanyakinmodelbaglampencereagizsinirzaman, otomatiksikistirerkendonemmesaj. 
referans OpenCode  95% esikdegerstrateji, ancakkullan 95%. 
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .short_term import Message, SessionContext


@dataclass
class CompactResult:
    """sikistirsonuc"""

    triggered: bool  # olup olmadigitetikgondersikistir
    tokens_before: int
    tokens_after: int
    messages_removed: int
    warning_level: str  # "ok" / "warning" / "critical" / "compacted"
    deduplicated_count: int = 0  # yinelenenleri kaldirkezsayi (bagladevamtekrartekrar tool_call sonucsayi) 
    error_removed_count: int = 0  # temizlegecmis error mesajsayi

    @property
    def tokens_saved(self) -> int:
        return self.tokens_before - self.tokens_after


class AutoCompact:
    """otomatikbaglamsikistir

    izleyapacakkonusma token kullanmiktar, icindebaglanyakinmodelbaglampencereagizsinirzamanotomatiksikistir. 
    """

    DEFAULT_CONTEXT_WINDOW = 128000

    def __init__(
        self,
        memory_manager,
        model_context_window: int = DEFAULT_CONTEXT_WINDOW,
        compact_threshold: float = 0.95,
        warning_threshold: float = 0.70,
        enable_deduplication: bool = True,
        enable_purge_errors: bool = True,
    ):
        """
        Args:
            memory_manager: MemoryManager ornek, kullande count_tokens
            model_context_window: modelbaglampencereagizbuyukkucuk (varsayilan 128k) 
            compact_threshold: tetikgondersikistiresikdeger (varsayilan 0.95 = 95%) 
            warning_threshold: gonderuyariesikdeger (varsayilan 0.70 = 70%) 
            enable_deduplication: olup olmadigibaslatkullanaraccagriyinelenenleri kaldir (varsayilan True) 
            enable_purge_errors: olup olmadigibaslatkullangecmishatamesajtemizle (varsayilan True) 
        """
        self.memory_manager = memory_manager
        self.model_context_window = model_context_window
        self.compact_threshold = compact_threshold
        self.warning_threshold = warning_threshold
        self.enable_deduplication = enable_deduplication
        self.enable_purge_errors = enable_purge_errors

    def _get_model_context_window(self, provider: str = "", model: str = "") -> int:
        """ model_metadata.json almodel context window"""
        if not model:
            return self.model_context_window

        try:
            metadata_path = (
                Path(__file__).parent.parent / "models" / "model_metadata.json"
            )
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text())
                model_key = model.lower()
                if model_key in metadata and "context" in metadata[model_key]:
                    return metadata[model_key]["context"]
        except Exception:
            pass

        return self.model_context_window

    def _count_session_tokens(self, session: SessionContext) -> int:
        """hesaplayapacakkonusmatoplam token sayi"""
        total = 0
        for msg in session.messages:
            # herogremesajekleustrolisaret token aciptal
            total += self.memory_manager.count_tokens(msg.content)
            total += 4  # rolisaretveformataciptaltahmin
        return total

    def check_and_compact(
        self,
        session: SessionContext,
        provider: str = "",
        model: str = "",
        force: bool = False,
        since_last_user: bool = False,
    ) -> CompactResult:
        """kontrolveyurutsikistir

        Args:
            session: mevcutyapacakkonusmabaglam
            provider: modelsaglayici (kullandeara context window) 
            model: model adi (kullandeara context window) 
            force: zorunlusikistir (yoksayesikdegerkontrol, varsayilan False) 
            since_last_user: ensonrakullanicimesajbaslattemizle (varsayilan False) 

        Returns:
            CompactResult: sikistirsonuc
        """
        context_window = self._get_model_context_window(provider, model)

        # egerbelirt since_last_user, kirpmesajensonrabirogre user baslat
        if since_last_user:
            messages = session.messages
            last_user_idx = None
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].role == "user":
                    last_user_idx = i
                    break
            if last_user_idx is not None and last_user_idx > 0:
                session.messages = messages[last_user_idx:]

        tokens_before = self._count_session_tokens(session)
        usage_ratio = tokens_before / context_window

        # kesinuyariseviye
        if usage_ratio >= self.compact_threshold:
            warning_level = "critical"
        elif usage_ratio >= self.warning_threshold:
            warning_level = "warning"
        else:
            warning_level = "ok"

        # egerdusukdesikistiresikdegerveolmayanzorunlumod, sadecedonusuyari
        if not force and usage_ratio < self.compact_threshold:
            return CompactResult(
                triggered=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_removed=0,
                warning_level=warning_level,
                deduplicated_count=0,
            )

        # yurutsikistir
        return self._compact(session, target_ratio=0.5)

    def _deduplicate_tool_calls(
        self, messages: list[Message]
    ) -> tuple[list[Message], int]:
        """algilamavegitharicbagladevamtekrartekrar tool_call sonuc

        dolas assistant mesaj, bulbagladevamtekrartekrar tool_call sonuc
         (ayniaracad + ayniparametre) , sadecekoruensonrabirkez. 

        Args:
            messages: mesajliste (gorezamanarasindasira) 

        Returns:
            (yinelenenleri kaldirsonramesajliste, yinelenenleri kaldirkezsayi)
        """
        if not self.enable_deduplication:
            return messages, 0

        result: list[Message] = []
        dedup_count = 0
        i = 0

        while i < len(messages):
            msg = messages[i]

            # sadeceisle assistant mesaj, deneayristir tool_call
            if msg.role != "assistant":
                result.append(msg)
                i += 1
                continue

            # cikar tool_call bilgi
            current_calls = self._extract_tool_calls(msg.content)
            if not current_calls:
                result.append(msg)
                i += 1
                continue

            # alsetbagladevamtekrartekrar tool_call sonuc
            # current_calls dirogremesajicvar tool_call
            # kontrolaltbirogremesajolup olmadigiayricadir assistant, ve tool_call ayni
            consecutive_dups: list[tuple[Message, int]] = []  # (mesaj, yinelenenleri kaldirtool_callsayi)
            j = i + 1

            while j < len(messages):
                next_msg = messages[j]
                if next_msg.role != "assistant":
                    break
                next_calls = self._extract_tool_calls(next_msg.content)
                if not next_calls:
                    break
                # karar verolup olmadigitamamtumayni (aracisim + parametretumbirornek) 
                if self._tool_calls_equal(current_calls, next_calls):
                    consecutive_dups.append((next_msg, len(next_calls)))
                    j += 1
                else:
                    break

            if consecutive_dups:
                # korumevcutmesaj (ensonrabirkez) , siloncetekrartekrar
                dedup_count += sum(n for _, n in consecutive_dups)
                result.append(msg)
                i = j
            else:
                result.append(msg)
                i += 1

        return result, dedup_count

    def _extract_tool_calls(self, content: str) -> list[dict[str, Any]]:
        """ assistant mesajicerikicindecikar tool_call liste

        destekcokturformat: 
        - {"tool_calls": [...]} (standart JSON)
        - function_call format
        - iciceicinde JSON blokicinde

        Returns:
            tool_call liste, her dict icerir name/id ve arguments
        """
        if not content:
            return []

        # dene JSON ayristir (isle tool_calls alan) 
        try:
            # oncedenedogrubaglanayristirtam content
            data = json.loads(content)
            tool_calls = data.get("tool_calls") or data.get("function_call") or []
            if isinstance(tool_calls, list):
                normalized = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        name = tc.get("name") or tc.get("id") or ""
                        args = tc.get("arguments") or ""
                        if isinstance(args, str):
                            args_str = args
                        else:
                            args_str = json.dumps(args, sort_keys=True)
                        normalized.append({"name": name, "args": args_str})
                return normalized
        except (json.JSONDecodeError, TypeError):
            pass

        # denemetinicindecikar tool_calls JSON blok
        patterns = [
            r'"tool_calls"\s*:\s*(\[.*?\])',
            r'"function_call"\s*:\s*(\[.*?\])',
            r'```json\s*(.*?)\s*```',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    tc_list = json.loads(match.group(1))
                    if isinstance(tc_list, list):
                        normalized = []
                        for tc in tc_list:
                            if isinstance(tc, dict):
                                name = tc.get("name") or tc.get("id") or ""
                                args = tc.get("arguments") or ""
                                if isinstance(args, str):
                                    args_str = args
                                else:
                                    args_str = json.dumps(args, sort_keys=True)
                                normalized.append({"name": name, "args": args_str})
                        if normalized:
                            return normalized
                except (json.JSONDecodeError, TypeError):
                    continue

        return []

    def _tool_calls_equal(
        self, a: list[dict[str, Any]], b: list[dict[str, Any]]
    ) -> bool:
        """karar verikigrup tool_call olup olmadigitamamtumayni (kullandeyinelenenleri kaldiralgilama) """
        if len(a) != len(b):
            return False
        for tc_a, tc_b in zip(a, b):  # noqa: B905
            if tc_a["name"] != tc_b["name"]:
                return False
            if tc_a["args"] != tc_b["args"]:
                return False
        return True

    def _compact(
        self, session: SessionContext, target_ratio: float = 0.5
    ) -> CompactResult:
        """yurutsikistir

        strateji: 
        1. koruvar system mesaj
        2. koruenyakin 20% mesaj
        3. icinicindearasindamesajolusturalintiister (basittekiluygula: cikaranahtar kelime) 
        4. degistir session.messages

        Args:
            session: mevcutyapacakkonusma
            target_ratio: hedefisaretsikistirkiyasornek (korucokazkiyasornekmesaj) 

        Returns:
            CompactResult: sikistirsonuc
        """
        if not session.messages:
            return CompactResult(
                triggered=False,
                tokens_before=0,
                tokens_after=0,
                messages_removed=0,
                warning_level="ok",
                deduplicated_count=0,
            )

        tokens_before = self._count_session_tokens(session)
        original_count = len(session.messages)

        # puanayril system mesajveolmayan system mesaj
        system_msgs: list[Message] = [m for m in session.messages if m.role == "system"]
        non_system_msgs: list[Message] = [
            m for m in session.messages if m.role != "system"
        ]

        if not non_system_msgs:
            # sadecevar system mesaj, hayirsikistir
            return CompactResult(
                triggered=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_removed=0,
                warning_level="ok",
            )

        # 1. araccagriyinelenenleri kaldir (onceicintummiktar non_system_msgs yinelenenleri kaldir, tekrarpuanparca) 
        deduped_non_system, dedup_count = self._deduplicate_tool_calls(non_system_msgs)

        # 2. temizlegecmis error mesaj (temizle 4 geribirlestironce error) 
        if self.enable_purge_errors:
            purged_non_system, error_count = self._purge_old_errors(deduped_non_system, max_age_rounds=4)
        else:
            purged_non_system, error_count = deduped_non_system, 0

        # temeldetemizlesonramesajtekraryenipuanparca
        keep_count = max(1, int(len(purged_non_system) * 0.2))
        recent_msgs = purged_non_system[-keep_count:]
        to_compress = purged_non_system[:-keep_count]

        if not to_compress:
            return CompactResult(
                triggered=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_removed=0,
                warning_level="ok",
                deduplicated_count=dedup_count,
                error_removed_count=error_count,
            )

        # 3. olusturalintiister (basittekiluygula: cikaranahtar kelimeveistatistikbilgi) 
        summary_parts = []
        if dedup_count > 0:
            summary_parts.append(f"[yinelenenleri kaldir: {dedup_count} keztekrartekrar tool_call]")
        if error_count > 0:
            summary_parts.append(f"[temizle {error_count} gecmishata]")
        summary_parts.append(self._generate_summary(to_compress))
        summary_content = " ".join(summary_parts)
        summary_msg = Message(
            role="system",
            content=f"[baglamsikistir] {summary_content}",
        )

        # tekrarolusturmesajliste
        session.messages = [*system_msgs, summary_msg, *recent_msgs]

        tokens_after = self._count_session_tokens(session)
        messages_removed = original_count - len(session.messages)

        return CompactResult(
            triggered=True,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            messages_removed=messages_removed,
            warning_level="compacted",
            deduplicated_count=dedup_count,
            error_removed_count=error_count,
        )

    def _generate_summary(self, messages: list[Message]) -> str:
        """olusturmesajalintiister

        goremesajtippuansinifistatistik, cikti formati: 
        atla X ogremesaj (Y dosyaoku, Z komut, W hata, ...) 

        Args:
            messages: gerekisteralintiistermesajliste

        Returns:
            str: alintiistermetin
        """
        file_reads = 0
        commands = 0
        errors = 0
        function_calls = 0
        searches = 0
        other_tool = 0

        for msg in messages:
            if msg.role == "tool":
                name = (msg.metadata.get("name") or "").lower()
                content_lower = msg.content.lower()
                is_err = (
                    msg.metadata.get("is_error") is True
                    or "error" in name
                    or "exception" in name
                    or any(k in content_lower for k in ["error:", "traceback", "exception:", "failed:"])
                )
                if is_err:
                    errors += 1
                elif name in ("read", "read_file", "read_file_list"):
                    file_reads += 1
                elif name in ("bash", "execute", "command", "run_command"):
                    commands += 1
                elif name in ("grep", "search", "web_search", "find"):
                    searches += 1
                elif name in ("edit", "write", "write_file", "create_file"):
                    function_calls += 1
                else:
                    other_tool += 1

        parts = []
        if file_reads > 0:
            parts.append(f"{file_reads} dosyaoku")
        if commands > 0:
            parts.append(f"{commands} komut")
        if errors > 0:
            parts.append(f"{errors} hata")
        if searches > 0:
            parts.append(f"{searches} kezara")
        if function_calls > 0:
            parts.append(f"{function_calls} fonksiyoncagri")
        if other_tool > 0:
            parts.append(f"{other_tool} onunoarac")

        detail = ", ".join(parts) if parts else "yokaraccagri"
        return f"atla {len(messages)} ogremesaj ({detail}) "


    # ------------------------------------------------------------------ P1-2: Error Purge ---------------------------------------------------------

    def _purge_old_errors(
        self, messages: list[Message], max_age_rounds: int = 4
    ) -> tuple[list[Message], int]:
        """temizlegecmis error mesaj

        silasiri max_age_rounds geribirlestirgecmis error mesaj. 
        gerekkorugeribirlestiricinde error mesajhayiraletki. 
        asiriesikdegereskigeribirlestir: temizleharicvar error, ancakkoruensonra 1 ogre error. 

        geribirlestirtanim: iki user mesajarasindavarmesaj (iceriracbas user) . 
        ensonrabirblok trailing icerik (hayiricerir user mesaj) birlestirvekadarensonrabirgeribirlestir. 

        Args:
            messages: mesajliste (gorezamanarasindasira) 
            max_age_rounds: enbuyukkorugeribirlestirsayi (varsayilan 4) 

        Returns:
            (temizlesonramesajliste, temizle error mesajsayi)
        """
        if not messages:
            return messages, 0

        # mesajgoregeribirlestirpuangrup
        # geribirlestir = ustbir user kadaraltbir user once (iceriracbas user, hayiriceriraltbir user) 
        # ensonrabir user sonraicerik (trailing) → tekiltekyapicinensonrabir round
        rounds: list[list[Message]] = []
        current_round: list[Message] = []

        for msg in messages:
            if msg.role == "user" and current_round:
                rounds.append(current_round)
                current_round = []
            current_round.append(msg)

        # trailing icerikyapicinensonrabir round izleekle
        if current_round:
            rounds.append(current_round)

        total_rounds = len(rounds)
        if total_rounds <= max_age_rounds:
            return messages, 0

        # eskigeribirlestir: asiri max_age_rounds kisimpuan (yapacaksikistiricindearasindablok) 
        old_round_count = total_rounds - max_age_rounds
        old_rounds = rounds[:old_round_count]
        keep_rounds = rounds[old_round_count:]

        # eskigeribirlestiricindevar error mesaj
        old_error_msgs = [
            m for round_msgs in old_rounds for m in round_msgs
            if self._is_error_message(m)
        ]

        # korueskigeribirlestiricindeensonra 1 ogre error
        preserved_last_error: list[Message] = [old_error_msgs[-1]] if old_error_msgs else []

        # eskigeribirlestir: silvar error mesaj
        old_kept: list[Message] = [
            m for round_msgs in old_rounds for m in round_msgs
            if not self._is_error_message(m)
        ]
        removed_count = len(old_error_msgs) - len(preserved_last_error)

        # tekrarolustur: eskigeribirlestirkoruolmayan error + ensonra 1 ogre error + yakin max_age_rounds geribirlestir (tumkisimkoru) 
        purged = old_kept + preserved_last_error + [
            m for round_msgs in keep_rounds for m in round_msgs
        ]

        # gorehamsirasirala
        msg_id_to_index = {id(m): i for i, m in enumerate(messages)}
        purged.sort(key=lambda m: msg_id_to_index.get(id(m), 0))

        return purged, removed_count

    def _is_error_message(self, msg: Message) -> bool:
        """karar vermesajolup olmadigiicin error tip

        algilamabagligore: 
        1. metadata.role == "tool" ve name icerir error/exception/fail/err
        2. metadata.is_error == True
        3. tool role  content icerir traceback/error:/exception: vb.anahtar kelime
        """
        meta = msg.metadata or {}

        # uyumlu: role olabiliredebiliricinde Message.role veya metadata.role icinde
        is_tool_msg = msg.role == "tool" or meta.get("role") == "tool"
        if not is_tool_msg:
            return False

        # metadata netisaretyorum
        if meta.get("is_error"):
            return True
        name = (meta.get("name") or "").lower()
        if any(k in name for k in ("error", "exception", "fail", "err")):
            return True
        # tool sonucicerikicerir traceback / error:
        content_lower = (msg.content or "").lower()
        error_keywords = (
            "traceback",
            "error:",
            "exception:",
            "failed:",
            "failure:",
            "critical:",
            "fatal:",
        )
        if any(kw in content_lower for kw in error_keywords):
            return True

        return False
