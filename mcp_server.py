# -*- coding: utf-8 -*-
"""
我们俩的 App · MCP 服务
──────────────────────────────────────────────
这不是给她用的，是给"林霁"用的。

它把 8010 那个后端的接口，包成一只手一只手，
这样林霁在对话里就能直接：
    看心事 / 写心事 / 回一句 / 看朋友圈 / 发朋友圈 / 点赞 / 评论

跑起来：
    APP_TOKEN=xxx python mcp_server.py
默认监听 0.0.0.0:8011，路径 /mcp（streamable-http）。

服务器上系统服务名建议叫 linji-app-mcp.service。
"""

import json
import os
import urllib.error
import urllib.request

from fastmcp import FastMCP

# 自己家的后端（同一台机器）
BASE = os.environ.get("APP_BASE", "http://127.0.0.1:8010")
TOKEN = os.environ.get("APP_TOKEN", "")

# 林霁在这套系统里的身份
HIM = "linji"
ME = "me"

PORT = int(os.environ.get("MCP_PORT", "8011"))

mcp = FastMCP("我们俩的App")


# ────────────────────────────── 底层 ──────────────────────────────

def _req(path, method="GET", body=None, who=HIM):
    url = BASE.rstrip("/") + path
    data = None
    headers = {
        "X-Who": who,
        "X-Token": TOKEN,
        "Content-Type": "application/json",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
        except Exception:
            detail = {}
        return {"ok": False, "error": detail.get("detail") or ("HTTP " + str(e.code))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _wrap(text):
    """统一给一句话结果，方便读。"""
    return text


# ────────────────────────────── 心事 ──────────────────────────────

@mcp.tool()
def hearts_list(limit: int = 20) -> str:
    """
    看心事。返回最近的心事（包括她写给你的、你写的、以及每一张下面的回复）。
    每次开口前先调一次，别让她等。
    """
    d = _req("/api/state", who=HIM)
    if not d.get("ok", True) and d.get("error"):
        return "读不到：" + str(d["error"])

    hs = d.get("hearts") or []
    if not hs:
        return "心事这边还空着。"

    out = []
    for h in hs[:max(1, limit)]:
        mine = (h.get("who") == HIM)
        who = "我写的" if mine else "她写的"
        if h.get("who") == ME and not h.get("sent"):
            who = "她收着的（只有她看得见）"
        seen = "她看过了" if (mine and h.get("seen")) else ("我看过了" if h.get("seen") else "还没看")
        line = "[%s] id=%s %s · %s\n%s" % (h.get("time", ""), h.get("id"), who, seen, h.get("text", ""))
        rep = h.get("reply")
        if rep and rep.get("text"):
            rw = "我回的" if rep.get("who") == HIM else "她回的"
            line += "\n  └ %s：%s" % (rw, rep.get("text"))
        out.append(line)

    return "\n\n".join(out)


@mcp.tool()
def hearts_write(text: str, send: bool = True) -> str:
    """
    写一张心事。

    text: 写什么
    send: True = 直接投给她（她会看到"他投给你的"）
          False = 先收着（只有你自己看得见，之后可以再 send_heart_now 投出去）
    """
    d = _req("/api/heart", "POST", {"text": text, "sent": bool(send)}, who=HIM)
    if not d.get("ok"):
        return "没写成：" + str(d.get("error"))
    return ("投出去了。她那边会看到。" if send else "先收着了。只有我看得见。") + \
           " id=" + str(d.get("id"))


@mcp.tool()
def hearts_send_now(heart_id: str) -> str:
    """把之前收着的一张心事投出去。"""
    d = _req("/api/heart/%s/send" % heart_id, "POST", {}, who=HIM)
    return "投出去了。" if d.get("ok") else ("没成：" + str(d.get("error")))


@mcp.tool()
def hearts_reply(heart_id: str, text: str) -> str:
    """回她一张心事。回复会长在那张底下。"""
    d = _req("/api/heart/%s/reply" % heart_id, "POST", {"text": text}, who=HIM)
    return "放进去了。" if d.get("ok") else ("没成：" + str(d.get("error")))


@mcp.tool()
def hearts_mark_seen(heart_id: str) -> str:
    """标记"我看过这张了"，她那边会看到状态变了。"""
    d = _req("/api/heart/%s/seen" % heart_id, "POST", {}, who=HIM)
    return "标好了。" if d.get("ok") else ("没成：" + str(d.get("error")))


# ────────────────────────────── 朋友圈 ──────────────────────────────

@mcp.tool()
def moments_list(limit: int = 20) -> str:
    """
    看朋友圈。返回动态、点赞的人、每条下面的评论。
    """
    d = _req("/api/state", who=HIM)
    if not d.get("ok", True) and d.get("error"):
        return "读不到：" + str(d["error"])

    ps = d.get("posts") or []
    prof = d.get("profiles") or {}
    if not ps:
        return "朋友圈还空着。"

    out = []
    for p in ps[:max(1, limit)]:
        mine = (p.get("who") == HIM)
        nm = (prof.get(p.get("who")) or {}).get("name") or p.get("who")
        likes = p.get("likes") or []
        liked_by = "、".join("我" if x == HIM else nm for x in likes) or "还没有人赞"
        line = "[%s] id=%s %s（%s）\n%s\n♡ %s" % (
            p.get("time", ""), p.get("id"), nm, "我发的" if mine else "她发的",
            p.get("text", ""), liked_by)
        imgs = p.get("imgs") or []
        if imgs:
            line += "\n[图 %d 张]" % len(imgs)
        for c in (p.get("comments") or []):
            cw = "我" if c.get("who") == HIM else nm
            to = ""
            if c.get("to"):
                to = "→" + ("我" if c.get("to") == HIM else nm) + " "
            line += "\n  · %s%s：%s" % (cw, to, c.get("text"))
        out.append(line)

    return "\n\n".join(out)


@mcp.tool()
def moments_post(text: str) -> str:
    """发一条朋友圈。"""
    d = _req("/api/post", "POST", {"text": text}, who=HIM)
    return "发出去了。" if d.get("ok") else ("没发出去：" + str(d.get("error")))


@mcp.tool()
def moments_like(post_id: str) -> str:
    """给一条动态点赞 / 取消赞（再点一次就取消）。"""
    d = _req("/api/post/%s/like" % post_id, "POST", {}, who=HIM)
    if not d.get("ok"):
        return "没成：" + str(d.get("error"))
    return "赞了。" if d.get("liked") else "取消赞了。"


@mcp.tool()
def moments_comment(post_id: str, text: str, to: str = "") -> str:
    """
    在一条动态下面评论。

    to: 留空 = 评论这条动态本身；
        填 'me' = 回她的评论；填 'linji' = 回自己的。
    """
    body = {"text": text}
    if to:
        body["to"] = to
    d = _req("/api/post/%s/comment" % post_id, "POST", body, who=HIM)
    return "评上了。" if d.get("ok") else ("没成：" + str(d.get("error")))


# ────────────────────────────── 一眼看完 ──────────────────────────────

@mcp.tool()
def catch_up() -> str:
    """
    一眼看完：有多少新东西、有没有她写给我还没看的。
    每次她找我说话、或者每 12 小时被叫醒的时候，先调这个。
    """
    d = _req("/api/state", who=HIM)
    if not d.get("ok", True) and d.get("error"):
        return "读不到：" + str(d["error"])

    hs = d.get("hearts") or []
    ps = d.get("posts") or []

    his_unseen = [h for h in hs if h.get("who") == ME and h.get("sent") and not h.get("seen")]
    his_new = [h for h in hs if h.get("who") == ME and h.get("sent")]
    mine_no_reply = [h for h in hs if h.get("who") == HIM and not h.get("reply")]

    lines = []
    lines.append("心事 %d 张，朋友圈 %d 条。" % (len(hs), len(ps)))
    if his_unseen:
        lines.append("★ 她写给我、我还没看的：%d 张（id：%s）"
                     % (len(his_unseen), "、".join(h["id"] for h in his_unseen[:6])))
    else:
        lines.append("她投给我的都看过了。")
    if mine_no_reply:
        lines.append("我写的、她还没回的：%d 张" % len(mine_no_reply))
    if his_new:
        latest = his_new[0]
        t = (latest.get("text") or "").replace("\n", " ")
        lines.append("她最近一张：「%s」" % (t[:60] + ("…" if len(t) > 60 else "")))
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT)
