from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
sistembildirimarac - sifirbagimlilik, kullan macOS asilyarat osascript + DingTalk webhook
"""

import json
import os
import subprocess
import sys
import urllib.request


def send_notification(
    title: str,
    message: str,
    subtitle: Optional[str] = None,
    sound: bool = True,
) -> bool:
    """
    gondergondersistembildirim (macOS) . 

    Args:
        title: bildirimbaslik
        message: bildirimicerik
        subtitle: ikincilbaslik (olabilirsec) 
        sound: olup olmadigiyayinlakoyipucuses

    Returns:
        True gondergonderbasarili, False basarisiz
    """
    if sys.platform != "darwin":
        return False

    try:
        script_parts = [
            'display notification ""{}""'.format(message.replace('"', '\\"')),
        ]
        if subtitle:
            script_parts[0] = (
                'display notification "{}" with title "{}" subtitle "{}"'.format(
                    message.replace('"', '\\"'),
                    title.replace('"', '\\"'),
                    subtitle.replace('"', '\\"'),
                )
            )
        else:
            script_parts[0] = 'display notification "{}" with title "{}"'.format(
                message.replace('"', '\\"'),
                title.replace('"', '\\"'),
            )

        if not sound:
            script_parts[0] += ' sound name ""'

        script = " ".join(script_parts)
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def notify_workflow_complete(
    workflow: str,
    status: str,
    steps_completed: int,
    execution_time: float,
) -> bool:
    """bildirimis akisitamamla"""
    status_icon = "✅" if status == "completed" else "❌"
    return send_notification(
        title=f"Oh My Coder {status_icon} is akisitamamla",
        message=f"{workflow}: {steps_completed} adim, {execution_time:.1f}s",
        subtitle=f"durum: {status}",
    )


def notify_quest_update(quest_name: str, message: str) -> bool:
    """bildirim Quest guncelle (kullandeasenkrongorev) """
    return send_notification(
        title=f"📋 Quest: {quest_name}",
        message=message,
    )


# ============================================================
# DingTalkbildirim
# ============================================================


def send_dingtalk_notification(
    webhook_url: str,
    title: str,
    message: str,
    at_all: bool = False,
) -> bool:
    """
    gondergonderDingTalkgrupmakinekisibildirim. 

    Args:
        webhook_url: DingTalkmakinekisi webhook URL
        title: mesajbaslik
        message: mesajicerik
        at_all: olup olmadigi @varkisi

    Returns:
        True gondergonderbasarili, False basarisiz
    """
    try:
        # sinirsadeceizin ver https webhook
        from urllib.parse import urlparse

        if urlparse(webhook_url).scheme not in ("http", "https"):
            return False

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{message}",
            },
            "at": {
                "isAtAll": at_all,
            },
        }

        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("errcode") == 0

    except Exception:
        return False


def notify_workflow_complete_dingtalk(
    webhook_url: Optional[str],
    workflow: str,
    status: str,
    steps_completed: int,
    execution_time: float,
    project_path: str = "",
) -> bool:
    """araciligiylaDingTalkbildirimis akisitamamla"""
    if not webhook_url:
        webhook_url = os.environ.get("DINGTALK_WEBHOOK")

    if not webhook_url:
        return False

    status_icon = "✅" if status == "completed" else "❌"
    status_text = "basarili" if status == "completed" else "basarisiz"

    message = f"""**is akisi**: {workflow}
**durum**: {status_text} {status_icon}
**tamamlaadim**: {steps_completed}
**yurutzamanarasinda**: {execution_time:.1f}s
"""
    if project_path:
        message += f"**proje yolu**: `{project_path}`"

    return send_dingtalk_notification(
        webhook_url=webhook_url,
        title="Oh My Coder - is akisitamamlabildirim",
        message=message,
    )


def notify_quest_update_dingtalk(
    webhook_url: Optional[str],
    quest_name: str,
    message: str,
    status: str = "running",
) -> bool:
    """araciligiylaDingTalkbildirim Quest guncelle"""
    if not webhook_url:
        webhook_url = os.environ.get("DINGTALK_WEBHOOK")

    if not webhook_url:
        return False

    status_icons = {
        "completed": "✅",
        "failed": "❌",
        "running": "⏳",
        "pending_review": "👀",
    }
    icon = status_icons.get(status, "📋")

    return send_dingtalk_notification(
        webhook_url=webhook_url,
        title=f"{icon} Quest: {quest_name}",
        message=message,
    )
