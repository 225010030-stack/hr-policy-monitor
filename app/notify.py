from __future__ import annotations

import os
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from typing import Any

import requests


def send_wecom_text(text: str, user_ids: list[str]) -> dict[str, Any]:
    corp_id = os.getenv("WECOM_CORP_ID", "").strip()
    agent_id = os.getenv("WECOM_AGENT_ID", "").strip()
    secret = os.getenv("WECOM_AGENT_SECRET", "").strip()
    if not all([corp_id, agent_id, secret]):
        return {"ok": False, "error": "WECOM_CORP_ID / WECOM_AGENT_ID / WECOM_AGENT_SECRET required"}
    if not user_ids:
        return {"ok": False, "error": "POLICY_DIGEST_WECOM_USERS is empty"}

    token_resp = requests.get(
        "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        params={"corpid": corp_id, "corpsecret": secret},
        timeout=30,
    )
    token_resp.raise_for_status()
    token_data = token_resp.json()
    if token_data.get("errcode", 0) != 0:
        return {"ok": False, "error": f"gettoken failed: {token_data}"}

    access_token = token_data["access_token"]
    results: list[dict[str, Any]] = []
    for uid in user_ids:
        uid = uid.strip()
        if not uid:
            continue
        payload = {
            "touser": uid,
            "msgtype": "text",
            "agentid": int(agent_id),
            "text": {"content": text[:2048]},
            "safe": 0,
        }
        resp = requests.post(
            "https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={"access_token": access_token},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode", 0) != 0:
            results.append({"user": uid, "error": data})
        else:
            results.append({"user": uid, "ok": True})
        time.sleep(0.2)
    return {"ok": True, "results": results}


def send_email(subject: str, text: str, to_addrs: list[str]) -> dict[str, Any]:
    host = os.getenv("POLICY_SMTP_HOST", "").strip()
    port = int(os.getenv("POLICY_SMTP_PORT", "587"))
    user = os.getenv("POLICY_SMTP_USER", "").strip()
    password = os.getenv("POLICY_SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("POLICY_SMTP_FROM", user).strip()
    if not host or not to_addrs:
        return {"ok": False, "error": "POLICY_SMTP_HOST or POLICY_DIGEST_EMAIL_TO not configured"}

    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if os.getenv("POLICY_SMTP_TLS", "true").lower() in {"1", "true", "yes"}:
                smtp.starttls(context=ssl.create_default_context())
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(from_addr, to_addrs, msg.as_string())
        return {"ok": True, "to": to_addrs}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
