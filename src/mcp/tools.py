from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"

"""
MCP Tools -  oh-my-coder Agent yetenekaciga cikaricin MCP tools

her tool karsilik gelenbir Agent cagri, parametresaydamiletkadar Agent. 
isbolgebaglamotomatikenjekte, yokgerekherkezilet workspace path. 

MCP SDK olabilirkullanzaman (Python 3.10+) donus Tool icinnesne, 
aksi takdirdedonus dict format (manuel stdio uygula) . 
"""

from pathlib import Path
from typing import Any, Optional

# ------------------------------------------------------------------
# MCP Tool kayittablo
# ------------------------------------------------------------------

# isbolgekokdizin (satirzamantarafindan MCPServer enjekte) 
_WORKSPACE: Optional[Path] = None


def set_workspace(workspace: Path) -> None:
    """ayarlaayarisbolgeyol (MCPServer baslatzamancagri) """
    global _WORKSPACE
    _WORKSPACE = workspace.resolve()


def get_workspace() -> Path:
    """alisbolgeyol"""
    return _WORKSPACE or Path.cwd()


def _resolve_path(path: Optional[str]) -> str:
    """ayristiryol: icinyol → isbolgekesinicinyol"""
    if path is None:
        return str(get_workspace())
    p = Path(path)
    if p.is_absolute():
        return path
    return str(get_workspace() / path)


# ------------------------------------------------------------------
# Tool isleyici (herarackarsilik gelenbir Agent cagri) 
# ------------------------------------------------------------------


def _code_review_handler(args: dict[str, Any]) -> dict[str, Any]:
    """omc_code_review - yurutkodinceleme"""
    path = _resolve_path(args.get("path"))
    from ..agents.base import AgentContext
    from ..agents.code_reviewer import CodeReviewerAgent

    try:
        agent = CodeReviewerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"incelemekod: {path}",
            metadata={"paths": [path]},
        )
        # esitlesatir (MCPServer icinizoleilerlesurec, esitleolabilirbaglanal) 
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _debug_handler(args: dict[str, Any]) -> dict[str, Any]:
    """omc_debug - otomatikkonumveduzeltme Bug"""
    path = _resolve_path(args.get("path"))
    error = args.get("error", "")
    from ..agents.base import AgentContext
    from ..agents.debugger import DebuggerAgent

    try:
        agent = DebuggerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"konumveduzeltme Bug: {error}",
            metadata={"paths": [path], "error": error},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _test_handler(args: dict[str, Any]) -> dict[str, Any]:
    """omc_test - icinkod uretimitest durumu"""
    path = _resolve_path(args.get("path"))
    from ..agents.base import AgentContext
    from ..agents.test_engineer import TestEngineerAgent

    try:
        agent = TestEngineerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"icinkod uretimitest durumu: {path}",
            metadata={"paths": [path]},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _refactor_handler(args: dict[str, Any]) -> dict[str, Any]:
    """omc_refactor - yeniden duzenlemekoddegistiriyiyapiveperformans"""
    path = _resolve_path(args.get("path"))
    goal = args.get("goal", "degistiriyikodyapiveperformans")
    from ..agents.architect import ArchitectAgent
    from ..agents.base import AgentContext

    try:
        agent = ArchitectAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"yeniden duzenleme {path}, hedefisaret: {goal}",
            metadata={"paths": [path], "goal": goal},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _security_handler(args: dict[str, Any]) -> dict[str, Any]:
    """omc_security_review - guvenlikinceleme"""
    path = _resolve_path(args.get("path"))
    from ..agents.base import AgentContext
    from ..agents.security import SecurityReviewerAgent

    try:
        agent = SecurityReviewerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"guvenlikinceleme: {path}",
            metadata={"paths": [path]},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _vision_handler(args: dict[str, Any]) -> dict[str, Any]:
    """omc_vision - gorselanaliz (ekran goruntusu / UI kod uretimi) """
    image_path = args.get("image_path", "")
    mode = args.get("mode", "analysis")
    if image_path:
        image_path = _resolve_path(image_path)
    from ..agents.base import AgentContext
    from ..agents.vision import VisionAgent

    try:
        agent = VisionAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"gorselanaliz: {image_path} (mode={mode})",
            metadata={"image_path": image_path, "mode": mode},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _explore_handler(args: dict[str, Any]) -> dict[str, Any]:
    """omc_explore - projekesfet"""
    from ..agents.base import AgentContext
    from ..agents.explore import ExploreAgent

    try:
        agent = ExploreAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description="kesfetproje yapisi",
            metadata=args,
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _plan_handler(args: dict[str, Any]) -> dict[str, Any]:
    """omc_plan - gorevplanlaveayirpuan"""
    task = args.get("task", "")
    from ..agents.base import AgentContext
    from ..agents.planner import PlannerAgent

    try:
        agent = PlannerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=task,
            metadata={"task": task},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


# ------------------------------------------------------------------
# MCP Tool tanim (dict format, uyumlu Python 3.9 asilyaratuygula) 
# ------------------------------------------------------------------

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "omc_code_review",
        "description": "yurutkodinceleme, analizkodkalitemiktar, potansiyelicindesorunvedegistirilerleoneri",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "kodyol (dosyaveyadizin, icinyolotomatikbirlestirbaglanisbolge) ",
                }
            },
            "required": ["path"],
        },
        "handler": _code_review_handler,
    },
    {
        "name": "omc_debug",
        "description": "otomatikkonumveduzeltme Bug, analizhatalogvekod",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "kodyol",
                },
                "error": {
                    "type": "string",
                    "description": "hata mesajiveyalogparca",
                },
            },
            "required": ["path"],
        },
        "handler": _debug_handler,
    },
    {
        "name": "omc_test",
        "description": "icinkod uretimitest durumu (pytest format) ",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "kodyol (olusturtestdosya) ",
                }
            },
            "required": ["path"],
        },
        "handler": _test_handler,
    },
    {
        "name": "omc_refactor",
        "description": "yeniden duzenlemekoddegistiriyiyapiveperformans",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "kodyol",
                },
                "goal": {
                    "type": "string",
                    "description": "yeniden duzenlemehedefisaret (olabilirsec, varsayilan: degistiriyikodyapiveperformans) ",
                },
            },
            "required": ["path"],
        },
        "handler": _refactor_handler,
    },
    {
        "name": "omc_security_review",
        "description": "guvenlikinceleme, taraenjekte, XSS, hassasbilgivb.guvenlikguvenlik acigi",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "kodyol",
                }
            },
            "required": ["path"],
        },
        "handler": _security_handler,
    },
    {
        "name": "omc_vision",
        "description": "gorselanaliz: ekran goruntusu UI analiz + UI kodotomatikolustur (ekran goruntusu → HTML/CSS) ",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "ekran goruntusuyol (dosyayol) ",
                },
                "mode": {
                    "type": "string",
                    "enum": ["analysis", "ui_code"],
                    "description": "mod: analysis/ui_code (gorselanalizveyaUIkod uretimi)",
                },
            },
        },
        "handler": _vision_handler,
    },
    {
        "name": "omc_explore",
        "description": "kesfetproje yapisi, olusturdosyaagacveprojealintiister",
        "inputSchema": {
            "type": "object",
            "properties": {
                "depth": {
                    "type": "integer",
                    "description": "dizindolasderinlik (varsayilan 3) ",
                },
                "include_patterns": {
                    "type": "string",
                    "description": "icerirdosyamod, virgulnopuanayir (ornegin: *.py,*.js) ",
                },
            },
        },
        "handler": _explore_handler,
    },
    {
        "name": "omc_plan",
        "description": "gorevplanlaveayirpuan, olusturolabiliryurutadimliste",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "isterplanlagorev aciklamasi",
                }
            },
            "required": ["task"],
        },
        "handler": _plan_handler,
    },
]


def get_mcp_tools() -> list[dict[str, Any]]:
    """tumunu al MCP tools (dict format, uyumlu Python 3.9) """
    return MCP_TOOLS


def get_tool_handler(name: str):
    """gorearacisimalisleyici"""
    for tool in MCP_TOOLS:
        if tool["name"] == name:
            return tool["handler"]
    return None
