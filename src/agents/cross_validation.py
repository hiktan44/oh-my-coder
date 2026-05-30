from __future__ import annotations

"""
çapraz doğrulama katmanı - Agent Çapraz doğrulama mekanizması

arka plan:
CLI run --cross-validate , iş akışı sona erdikten sonra çapraz doğrulama otomatik olarak gerçekleştirilir.

Nasıl çalışır:
1. iş akışı yöneticisi Agent Yürütme tamamlandı → çıktı result + artifacts
2. itibaren result.outputs Her birini çıkarın Agent Çıktısı
3. Bağımsız bir doğrulama perspektifiyle yeniden inceleyin:
   - Orijinal Agent Ne yaptın?
   - Mantıksal boşluklar var mı?/Güvenlik Sorusu/Eksik?
   - Sonuçlar güvenilir mi?
4. Çıktı yapılandırılmış raporu:PASS / FAIL / NEED_FIX + Belirli soruların listesi

İki doğrulama modu desteklenir:
- VERIFY_ONLY(Varsayılan): Yalnızca kodu değiştirmeden sorunları bildirin
- AUTO_FIX: Bir sorun tespit edildiğinde otomatik olarak çağrılır executor Onarım (yüksek risk)

Her çapraz doğrulama sonucu şu adrese yazılır: .omc/state/cross_validation/<validation_id>.json
"""


import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..core.router import ModelRouter

from ..core.router import TaskType

# ------------------------------------------------------------------
# Ortaya çıkan modeli doğrulama
# ------------------------------------------------------------------


class ValidationStatus(Enum):
    PASS = "pass"  # Doğrulama başarılı oldu
    FAIL = "fail"  # Doğrulama başarısız oldu (bariz sorun)
    NEED_FIX = "need_fix"  # Tamir edilmesi gerekiyor
    SKIPPED = "skipped"  # Atla (doğrulanacak çıktı yok)


class ValidationSeverity(Enum):
    CRITICAL = "critical"  # tamir edilmeli
    HIGH = "high"  # Düzeltilmesi şiddetle tavsiye edilir
    MEDIUM = "medium"  # Dikkat edilmesi tavsiye edilir
    LOW = "low"  # Göz ardı edilebilir


@dataclass
class ValidationIssue:
    """Bulunan sorunlar"""

    severity: ValidationSeverity
    category: str  # logic / security / completeness / style / performance
    description: str
    location: str = ""  # belge:satır numarası veya "general"
    suggestion: str = ""
    original_agent: str = ""  # Orijinal Agent isim
    evidence: str = ""  # delil parçaları


@dataclass
class CrossValidationResult:
    """çapraz doğrulama raporu"""

    validation_id: str
    workflow_id: str
    workflow_name: str
    status: ValidationStatus
    agent_outputs: dict[str, str]  # agent_name → Çıktının düz metin özeti
    issues: list[ValidationIssue] = field(default_factory=list)
    raw_validation_text: str = ""  # Ham çıktı modeli
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    mode: str = "verify_only"  # verify_only | auto_fix
    fix_applied: bool = False  # Otomatik olarak onarıldı mı?

    @property
    def pass_rate(self) -> str:
        """Doğrulama geçiş oranı"""
        total = len(self.issues)
        if total == 0:
            return "100%"
        critical = sum(
            1 for i in self.issues if i.severity == ValidationSeverity.CRITICAL
        )
        if critical > 0:
            return "0%"
        high = sum(1 for i in self.issues if i.severity == ValidationSeverity.HIGH)
        if high > 0:
            return "50%"
        return "80%"

    def to_summary(self) -> str:
        """İnsanların okuyabileceği özetler oluşturun"""
        lines = [
            "## 🔍 çapraz doğrulama raporu",
            "",
            "| proje | değer |",
            "|------|-----|",
            f"| doğrulamak ID | `{self.validation_id}` |",
            f"| İş akışı | `{self.workflow_name}` (`{self.workflow_id}`) |",
            f"| Doğrulama durumu | **{self.status.value.upper()}** |",
            f"| Sorun bulundu | {len(self.issues)} bireysel |",
            f"| Doğrulama zamanı | {self.execution_time:.1f}s |",
            f"| Kimlik doğrulama modu | `{self.mode}` |",
            "",
        ]
        if self.issues:
            lines.append("### Bulunan sorunlar")
            lines.append("")
            lines.append("| ciddiyet | sınıflandırma | betimlemek | Konum |")
            lines.append("|--------|------|------|------|")
            for issue in self.issues:
                lines.append(
                    f"| {issue.severity.value} | {issue.category} "
                    f"| {issue.description[:60]} | {issue.location} |"
                )
            lines.append("")
            if self.issues[0].suggestion:
                lines.append("### Onarım önerileri")
                for i, issue in enumerate(self.issues, 1):
                    if issue.suggestion:
                        lines.append(
                            f"{i}. **{issue.description}**: {issue.suggestion}"
                        )
                lines.append("")
        else:
            lines.append("✅ Belirgin bir sorun bulunamadı\n")
        return "\n".join(lines)


# ------------------------------------------------------------------
# çapraz doğrulama katmanı (şunlardan oluşur: CLI Arama)
# ------------------------------------------------------------------


class CrossValidationLayer:
    """
    çapraz doğrulama katmanı

    kullanım:
    ```python
    layer = CrossValidationLayer(
        model_router=router,
        state_dir=project_path / ".omc" / "state",
    )
    result = layer.validate_workflow(workflow_result, workflow_name)
    ```
    """

    # Çapraz doğrulamaya ayrılmış sistem istem sözcükleri
    VALIDATION_SYSTEM_PROMPT = """Sıkı bir kod inceleme uzmanısınız ve eleştirel düşünme konusunda iyisiniz.

## Rol
Başkalarına bakma konusunda uzmanlaşmış bağımsız bir "ikinci çift göz"sünüz AI Agent çıktı.
Giriş kısmını tekrarlamayacaksınız Agent sonuç ama**Soru sor, doğrula, tamamla**.

## çalışma yöntemi
1. Önsözü okuyun Agent Tam çıktısı
2. Aşağıdaki boyutlardan bağımsız inceleme:
   - **mantıksal bütünlük**: Fonksiyon tam olarak uygulandı mı? Sınır koşulları ele alındı ​​mı?
   - **güvenlik**: Var olup olmadığı SQL enjeksiyon,XSS, Hassas bilgilerin sızma riski var mı?
   - **Kod kalitesi**: Adlandırma, okunabilirlik, belirgin kod kokuları var mı?
   - **test kapsamı**: Ana sahneler kapsanıyor mu? Peki ya sınır testi?
   - **potansiyel Bug**: Mantık hataları, boş işaretçiler, eşzamanlılık sorunları?
   - **Eksik gereksinimler**: Görev gereksinimlerinde gözden kaçan noktalar var mı?
3. Bir sorun bulunursa kesin konum ve düzeltme önerileri verilir

## Çıkış formatı

### Sonucu doğrulayın
PASS / FAIL / NEED_FIX

### Bulunan sorunlar (varsa)
Her soru çıktısı için:
```
### [CRITICAL] logic: Boş işaretçi denetimi eksik
- Konum: src/main.py:42
- kanıt: if user.profile is None: ...
- telkin: Boş iddia veya varsayılan davranış ekle
```

### Kendinden emin
Bu doğrulamanın sonuçlarına olan güveniniz:HIGH / MEDIUM / LOW

## önemli ilkeler
- **Kanıt varsa konuşalım**, mantıksız tahminlerde bulunmayın
- Dikkate öncelik verin CRITICAL Ve HIGH soru
- Ön sipariş çıktısı zaten tamamlanmışsa açıkça belirtin PASS
"""

    def __init__(
        self,
        model_router: ModelRouter,
        state_dir: Optional[Path] = None,
    ):
        self.model_router = model_router
        self.state_dir = (state_dir or Path(".omc/state")).resolve()
        self._cv_dir = self.state_dir / "cross_validation"

    def _extract_outputs(self, result) -> dict[str, str]:
        """itibaren WorkflowResult Düz metin özetlerini şuradan çıkarın:"""
        outputs: dict[str, str] = {}
        for agent_name, output in result.outputs.items():
            if hasattr(output, "result") and output.result:
                outputs[agent_name] = str(output.result)[:3000]
            elif hasattr(output, "error") and output.error:
                outputs[agent_name] = f"[ERROR] {output.error}"
        return outputs

    async def call_model(
        self,
        task_type: str,
        messages: list,
        complexity: str = "medium",
        use_cache: bool = True,
        **kwargs,
    ):
        """Model yönlendiriciyi çağırın"""
        return await self.model_router.route_and_call(
            task_type=task_type,
            messages=messages,
            complexity=complexity,
            use_cache=use_cache,
            **kwargs,
        )

    def _build_validation_messages(
        self,
        workflow_name: str,
        agent_outputs: dict[str, str],
    ) -> list[dict[str, str]]:
        """Modele gönderilenleri oluşturun prompt"""
        output_blocks = []
        for agent_name, output_text in agent_outputs.items():
            output_blocks.append(f"### {agent_name}\n\n{output_text}\n")
        combined = "\n".join(output_blocks)

        return [
            {
                "role": "user",
                "content": (
                    f"## Doğrulanacak iş akışı\n**İş akışı adı**: {workflow_name}\n\n"
                    f"## Önsöz Agent çıktı\n\n{combined}\n\n"
                    f"---\nLütfen mantıktan çapraz doğrulama gerçekleştirin/Emniyet/bütünlük/Yukarıdaki çıktıya kod kalitesi açısından bakın."
                    f"Bulunan her sorun için önem derecesini belirtin (CRITICAL/HIGH/MEDIUM/LOW),"
                    f"Sınıflandırma(logic/security/completeness/style/performance),"
                    f"Yer ve onarım önerileri. Çıktı mükemmelse bunu açıkça belirtin PASS."
                ),
            }
        ]

    async def validate_workflow(
        self,
        workflow_result,
        workflow_name: str,
        mode: str = "verify_only",
    ) -> CrossValidationResult:
        """
        İş akışı sonuçlarında çapraz doğrulama gerçekleştirin

        Args:
            workflow_result: Orchestrator.execute_workflow geri döndü WorkflowResult
            workflow_name: İş akışı adı
            mode: verify_only | auto_fix

        Returns:
            CrossValidationResult: Doğrulama raporu
        """
        start_time = time.time()
        validation_id = str(uuid.uuid4())[:8]

        # 1. Her birini çıkart Agent Çıktısı
        agent_outputs = self._extract_outputs(workflow_result)

        if not agent_outputs:
            return CrossValidationResult(
                validation_id=validation_id,
                workflow_id=workflow_result.workflow_id,
                workflow_name=workflow_name,
                status=ValidationStatus.SKIPPED,
                agent_outputs={},
                execution_time=time.time() - start_time,
                mode=mode,
            )

        # 2. Doğrulama mesajı oluştur
        messages = self._build_validation_prompt(workflow_name, agent_outputs)

        # 3. Modeli doğrudan arayın (güvenmeden Agent Kayıt sistemi)
        try:
            from ..models.base import Message

            msg_objects = [
                Message(role=m["role"], content=m["content"]) for m in messages
            ]
            resp = await self.model_router.route_and_call(
                TaskType.CODE_REVIEW,
                msg_objects,
                complexity="high",
            )
            raw_text = resp.content if resp else ""
        except Exception:
            return CrossValidationResult(
                validation_id=validation_id,
                workflow_id=workflow_result.workflow_id,
                workflow_name=workflow_name,
                status=ValidationStatus.SKIPPED,
                agent_outputs=agent_outputs,
                execution_time=time.time() - start_time,
                mode=mode,
            )

        # 4. Sonuçları ayrıştır
        issues = self._parse_validation_output(raw_text or "")
        status = self._determine_status(issues)

        result = CrossValidationResult(
            validation_id=validation_id,
            workflow_id=workflow_result.workflow_id,
            workflow_name=workflow_name,
            status=status,
            agent_outputs=agent_outputs,
            issues=issues,
            raw_validation_text=raw_text or "",
            execution_time=time.time() - start_time,
            mode=mode,
        )

        # 5. Sonuçları kaydet
        self._save_result(result)

        return result

    def _build_validation_prompt(
        self,
        workflow_name: str,
        agent_outputs: dict[str, str],
    ) -> list[dict[str, str]]:
        """Uyumlu cinsiyet adları"""
        return self._build_validation_messages(workflow_name, agent_outputs)

    def _parse_validation_output(self, text: str) -> list[ValidationIssue]:
        """Yapılandırılmış soru listesini model çıktısından ayrıştırma"""
        issues: list[ValidationIssue] = []

        if not text:
            return issues

        lines = text.split("\n")
        current_issue: Optional[ValidationIssue] = None

        for line in lines:
            stripped = line.strip()
            # Soru başlığı:### [CRITICAL] xxx veya ### CRITICAL xxx
            if stripped.startswith("### ["):
                # Önceki soruyu kaydet
                if current_issue and current_issue.description:
                    issues.append(current_issue)

                # ayrıştırmak ### [CRITICAL] category: description
                bracket_end = stripped.find("]")
                if bracket_end == -1:
                    continue

                severity_str = stripped[4:bracket_end].lower()
                rest = stripped[bracket_end + 1 :].strip()

                # başlangıcını kaldır # veya .
                rest = rest.lstrip("#").lstrip(".").strip()

                severity = self._parse_severity(severity_str)

                if ":" in rest:
                    cat, desc = rest.split(":", 1)
                    cat = cat.strip().lower()
                    desc = desc.strip()
                else:
                    cat = "general"
                    desc = rest

                current_issue = ValidationIssue(
                    severity=severity,
                    category=cat,
                    description=desc,
                )

            elif current_issue:
                # Sorunla ilgili ayrıntıları toplayın
                lower = stripped.lower()
                if lower.startswith(("- Konum:", "Konum:")):
                    loc = stripped.split(":", 1)[1].strip()
                    current_issue.location = loc
                elif lower.startswith(("- kanıt:", "kanıt:")):
                    ev = stripped.split(":", 1)[1].strip()
                    current_issue.evidence = ev
                elif lower.startswith(("- telkin:", "telkin:")):
                    sug = stripped.split(":", 1)[1].strip()
                    current_issue.suggestion = sug

        if current_issue and current_issue.description:
            issues.append(current_issue)

        return issues

    def _parse_severity(self, s: str) -> ValidationSeverity:
        """Ayrıştırma önem düzeyleri"""
        s = s.lower()
        if "critical" in s or "cidden" in s:
            return ValidationSeverity.CRITICAL
        if "high" in s or "yüksek" in s:
            return ValidationSeverity.HIGH
        if "medium" in s or "orta" in s:
            return ValidationSeverity.MEDIUM
        return ValidationSeverity.LOW

    def _determine_status(self, issues: list[ValidationIssue]) -> ValidationStatus:
        """Sorun listesine göre doğrulama durumunu belirleyin"""
        if not issues:
            return ValidationStatus.PASS
        critical = any(i.severity == ValidationSeverity.CRITICAL for i in issues)
        high = any(i.severity == ValidationSeverity.HIGH for i in issues)
        if critical:
            return ValidationStatus.FAIL
        if high:
            return ValidationStatus.NEED_FIX
        return ValidationStatus.PASS

    def _save_result(self, result: CrossValidationResult):
        """Doğrulama sonuçlarını dosyaya kaydet"""
        self._cv_dir.mkdir(parents=True, exist_ok=True)
        result_file = self._cv_dir / f"{result.validation_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "validation_id": result.validation_id,
                    "workflow_id": result.workflow_id,
                    "workflow_name": result.workflow_name,
                    "status": result.status.value,
                    "issues": [
                        {
                            **asdict(i),
                            "severity": i.severity.value,
                        }
                        for i in result.issues
                    ],
                    "execution_time": result.execution_time,
                    "timestamp": result.timestamp,
                    "mode": result.mode,
                    "pass_rate": result.pass_rate,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
