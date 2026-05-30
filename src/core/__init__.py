"""
Core modul - cekirdekislev

saglar: 
- Agent temel sinifvekayitmekanizma
- modelyoltarafindan
- gorevyoltarafindan
- orkestrasyon
- gorevgecmisvegeri oynat
- baglamyonet
"""

from .dependency_resolver import (
    DependencyInfo,
    DependencyResolver,
    ResolutionResult,
    get_resolver,
    resolve_dependencies,
)
from .history import (
    HistoryManager,
    StepExecution,
    TaskCheckpoint,
    TaskHistory,
    TaskReplay,
    complete_step_execution,
    create_step_execution,
    fail_step_execution,
)
from .orchestrator import Orchestrator, WorkflowResult, WorkflowStep
from .router import ModelRouter, TaskType

__all__ = [
    # Dependency Resolver
    "DependencyResolver",
    "DependencyInfo",
    "ResolutionResult",
    "get_resolver",
    "resolve_dependencies",
    # Router
    "ModelRouter",
    "TaskType",
    # Orchestrator
    "Orchestrator",
    "WorkflowResult",
    "WorkflowStep",
    # History
    "HistoryManager",
    "TaskHistory",
    "TaskReplay",
    "TaskCheckpoint",
    "StepExecution",
    "create_step_execution",
    "complete_step_execution",
    "fail_step_execution",
]
