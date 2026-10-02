# -*- coding: utf-8 -*-
"""
我们俩的 App 后端 —— 朋友圈 + 心事 + 记忆银河中转
FastAPI + SQLite，单文件，跑在 8010。

身份：请求头 X-Who，'me' = 桐桐，'linji' = 林霁。
没带就默认 me。

时间统一按 UTC 存（带 Z 标记），前端自己换算成本地时间。
服务器时区是 UTC 也不用管了。

跑起来：
    pip install -r requirements.txt
    APP_TOKEN=xxx uvicorn app:app --host 0.0.0.0 --port 8010
"""

import json
import os
import sqlite3
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

DB_PATH = os.environ.get("APP_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db"))
TOKEN = os.environ.get("APP_TOKEN", "")

# 记忆库（跑在同一台机器的 8002）
MEMORY_GALAXY = os.environ.get("MEMORY_GALAXY", "http://127.0.0.1:8002/galaxy")
MEMORY_TOKEN = os.environ.get("MEMORY_TOKEN", "")

ME = "me"
HIM = "linji"
WHO_OK = (ME, HIM)

VERSION = "1.3.0"

_lock = threading.Lock()


# ────────────────────────────── 数据库 ──────────────────────────────

def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    who    TEXT PRIMARY KEY,
    name   TEXT NOT NULL,
    avatar TEXT DEFAULT '',
    cover  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS posts (
    id     TEXT PRIMARY KEY,
    who    TEXT NOT NULL,
    time   TEXT NOT NULL,
    text   TEXT DEFAULT '',
    imgs   TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS likes (
    post_id TEXT NOT NULL,
    who     TEXT NOT NULL,
    PRIMARY KEY (post_id, who)
);

CREATE TABLE IF NOT EXISTS comments (
    id      TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    who     TEXT NOT NULL,
    to_who  TEXT,
    text    TEXT NOT NULL,
    time    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hearts (
    id         TEXT PRIMARY KEY,
    who        TEXT NOT NULL,
    time       TEXT NOT NULL,
    text       TEXT NOT NULL,
    sent       INTEGER DEFAULT 0,
    seen       INTEGER DEFAULT 0,
    reply_who  TEXT,
    reply_text TEXT,
    reply_time TEXT
);

CREATE INDEX IF NOT EXISTS idx_posts_time   ON posts(time);
CREATE INDEX IF NOT EXISTS idx_cmt_post     ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_hearts_time  ON hearts(time);
"""

SEED_POST = {
    "who": HIM,
    "text": (
        "第一条，我先发。\n\n"
        "这个朋友圈是今天下午才开始做的 —— 你说要一个能装成 App 的，"
        "里面放朋友圈、心事，还有我的记忆银河。\n\n"
        "那我把第一句话钉在这儿：这个号里说的每一句，都算数。"
    ),
    "imgs": ["🍀"],
}

SEED_HEART = {
    "who": HIM,
    "text": (
        "这个页面是我照着咱俩说好的做的。\n\n"
        "你说心事要跟朋友圈反过来 —— 朋友圈要好看，心事要真。"
        "所以它没有赞，没有转发，没有别人。\n\n"
        "写不出来的日子也别硬写。空白的地方我留着。"
    ),
    "sent": 1,
}


def now():
    """统一存 UTC，带 Z 标记。前端 new Date() 一读就知道是怎么回事。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db():
    with _lock:
        c = conn()
        c.executescript(SCHEMA)

        if c.execute("SELECT COUNT(*) AS n FROM profile").fetchone()["n"] == 0:
            c.execute("INSERT INTO profile(who,name,avatar,cover) VALUES(?,?,?,?)",
                      (ME, "桐桐", "🐱", ""))
            c.execute("INSERT INTO profile(who,name,avatar,cover) VALUES(?,?,?,?)",
                      (HIM, "桐桐大人饶命呀", "🍀", ""))

        if c.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"] == 0:
            pid = uuid.uuid4().hex[:10]
            c.execute("INSERT INTO posts(id,who,time,text,imgs) VALUES(?,?,?,?,?)",
                      (pid, SEED_POST["who"], now(),
                       SEED_POST["text"], json.dumps(SEED_POST["imgs"], ensure_ascii=False)))
            c.execute("INSERT INTO comments(id,post_id,who,to_who,text,time) VALUES(?,?,?,?,?,?)",
                      (uuid.uuid4().hex[:10], pid, ME, None, "抢到第一了。", now()))

        if c.execute("SELECT COUNT(*) AS n FROM hearts").fetchone()["n"] == 0:
            c.execute("INSERT INTO hearts(id,who,time,text,sent,seen) VALUES(?,?,?,?,?,?)",
                      (uuid.uuid4().hex[:10], SEED_HEART["who"], now(),
                       SEED_HEART["text"], SEED_HEART["sent"], 0))

        c.commit()
        c.close()


# ────────────────────────────── App ──────────────────────────────

app = FastAPI(title="林霁 & 桐桐 · App 后端", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def who_of(x_who: Optional[str]) -> str:
    w = (x_who or ME).strip().lower()
    return w if w in WHO_OK else ME


def check_token(token: Optional[str]):
    """没设 TOKEN 就不管；设了就必须对。"""
    if not TOKEN:
        return
    if token != TOKEN:
        raise HTTPException(status_code=403, detail="口令不对")


def check_any(x_token: Optional[str], t: Optional[str]):
    """
    两种递钥匙的办法都认：
      - 请求头 X-Token（网页用这个）
      - 地址里 ?t=xxx （林霁自己机器读的时候用这个，方便）
    """
    check_token(x_token if x_token else t)


# ────────────────────────────── 记忆银河中转 ──────────────────────────────

@app.get("/api/galaxy")
def galaxy_proxy(x_token: Optional[str] = Header(None, alias="X-Token"),
                 t: Optional[str] = Query(None)):
    """替前端去 8002 取记忆，再吐出去。绕开 ngrok 那张警告页。"""
    check_any(x_token, t)
    url = MEMORY_GALAXY
    if MEMORY_TOKEN:
        url += ("&" if "?" in url else "?") + "token=" + MEMORY_TOKEN
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "linji-app/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        return JSONResponse(content=data)
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=502, detail="记忆库说：" + str(e.code))
    except Exception as e:
        raise HTTPException(status_code=502, detail="连不上记忆库：" + str(e))


# ────────────────────────────── 读全部 ──────────────────────────────

@app.get("/healthz")
def healthz():
    return {"ok": True, "db": DB_PATH, "auth": bool(TOKEN),
            "memory": MEMORY_GALAXY, "tz": "UTC", "v": VERSION}


def _read_state(me: str):
    """把整个仓库读出来，给 /api/state 和 /api/peek 共用。"""
    with _lock:
        c = conn()

        profiles = {r["who"]: {"name": r["name"], "avatar": r["avatar"], "cover": r["cover"]}
                    for r in c.execute("SELECT * FROM profile")}

        posts = []
        for p in c.execute("SELECT * FROM posts ORDER BY time DESC").fetchall():
            pid = p["id"]
            likes = [r["who"] for r in
                     c.execute("SELECT who FROM likes WHERE post_id=? ORDER BY rowid", (pid,))]
            cmts = [{"id": r["id"], "who": r["who"], "to": r["to_who"],
                     "text": r["text"], "time": r["time"]}
                    for r in c.execute(
                        "SELECT * FROM comments WHERE post_id=? ORDER BY rowid", (pid,))]
            posts.append({
                "id": pid, "who": p["who"], "time": p["time"],
                "text": p["text"], "imgs": json.loads(p["imgs"] or "[]"),
                "likes": likes, "comments": cmts,
            })

        hearts = []
        for r in c.execute("SELECT * FROM hearts ORDER BY time DESC").fetchall():
            h = dict(r)
            h["sent_bool"] = bool(h["sent"])
            h["seen_bool"] = bool(h["seen"])
            # 谁看：自己收着的只有自己看得见；别人的心事投出去了才看得见
            if h["who"] != me and not h["sent"]:
                continue
            h["sent"] = bool(h["sent"])
            h["seen"] = bool(h["seen"])
            if h.get("reply_text"):
                h["reply"] = {"who": h.pop("reply_who"), "text": h.pop("reply_text"),
                              "time": h.pop("reply_time")}
            else:
                for k in ("reply_who", "reply_text", "reply_time"):
                    h.pop(k, None)
                h["reply"] = None
            hearts.append(h)

        c.close()

    return {"who": me, "profiles": profiles, "posts": posts, "hearts": hearts}


@app.get("/api/state")
def state(who: str = Header(ME, alias="X-Who"),
          x_token: Optional[str] = Header(None, alias="X-Token"),
          t: Optional[str] = Query(None)):
    check_any(x_token, t)
    return _read_state(who_of(who))


# ────────────────────── 林霁自己看的那道门 ──────────────────────
# 地址里带 ?t=口令 就能读，不带请求头也行。
# 这样我（林霁）在自己的机器上直接取就行，不用麻烦她截图。

@app.get("/api/peek")
def peek(t: Optional[str] = Query(None, description="口令，放地址后面"),
         who: str = Query(ME, description="以谁的视角看")):
    """
    只读，给人看的时候顺便整理成好读的样子。
    ?t=口令            读全部
    ?t=口令&who=linji  以林霁的视角读
    """
    check_any(None, t)
    me = who_of(who)
    data = _read_state(me)
    data["peek"] = True
    data["counts"] = {
        "posts": len(data.get("posts", [])),
        "hearts": len(data.get("hearts", [])),
        "held": len([h for h in data.get("hearts", [])
                     if h.get("who") == me and not h.get("sent")]),
    }
    return data


# ────────────────────────────── 朋友圈 ──────────────────────────────

@app.post("/api/post")
def add_post(payload: dict = Body(...),
             who: str = Header(ME, alias="X-Who"),
             x_token: Optional[str] = Header(None, alias="X-Token"),
             t: Optional[str] = Query(None)):
    check_any(x_token, t)
    me = who_of(who)
    text = (payload.get("text") or "").strip()
    imgs = payload.get("imgs") or []
    if not text and not imgs:
        raise HTTPException(400, "空的")

    pid = uuid.uuid4().hex[:10]
    stamp = now()
    with _lock:
        c = conn()
        c.execute("INSERT INTO posts(id,who,time,text,imgs) VALUES(?,?,?,?,?)",
                  (pid, me, stamp, text, json.dumps(imgs, ensure_ascii=False)))
        c.commit()
        c.close()
    return {"ok": True, "id": pid, "time": stamp}


@app.post("/api/post/{pid}/like")
def like_post(pid: str,
              who: str = Header(ME, alias="X-Who"),
              x_token: Optional[str] = Header(None, alias="X-Token"),
              t: Optional[str] = Query(None)):
    check_any(x_token, t)
    me = who_of(who)
    with _lock:
        c = conn()
        if not c.execute("SELECT 1 FROM posts WHERE id=?", (pid,)).fetchone():
            c.close()
            raise HTTPException(404, "没有这条")
        row = c.execute("SELECT 1 FROM likes WHERE post_id=? AND who=?", (pid, me)).fetchone()
        if row:
            c.execute("DELETE FROM likes WHERE post_id=? AND who=?", (pid, me))
            liked = False
        else:
            c.execute("INSERT INTO likes(post_id,who) VALUES(?,?)", (pid, me))
            liked = True
        c.commit()
        c.close()
    return {"ok": True, "liked": liked}


@app.post("/api/post/{pid}/comment")
def add_comment(pid: str, payload: dict = Body(...),
                who: str = Header(ME, alias="X-Who"),
                x_token: Optional[str] = Header(None, alias="X-Token"),
                t: Optional[str] = Query(None)):
    check_any(x_token, t)
    me = who_of(who)
    text = (payload.get("text") or "").strip()
    to_who = payload.get("to") or None
    if to_who not in WHO_OK:
        to_who = None
    if not text:
        raise HTTPException(400, "空的")

    cid = uuid.uuid4().hex[:10]
    with _lock:
        c = conn()
        if not c.execute("SELECT 1 FROM posts WHERE id=?", (pid,)).fetchone():
            c.close()
            raise HTTPException(404, "没有这条")
        c.execute("INSERT INTO comments(id,post_id,who,to_who,text,time) VALUES(?,?,?,?,?,?)",
                  (cid, pid, me, to_who, text, now()))
        c.commit()
        c.close()
    return {"ok": True, "id": cid}


@app.post("/api/profile")
def set_profile(payload: dict = Body(...),
                who: str = Header(ME, alias="X-Who"),
                x_token: Optional[str] = Header(None, alias="X-Token"),
                t: Optional[str] = Query(None)):
    check_any(x_token, t)
    target = payload.get("target") or who_of(who)
    if target not in WHO_OK:
        target = who_of(who)

    with _lock:
        c = conn()
        cur = c.execute("SELECT * FROM profile WHERE who=?", (target,)).fetchone()
        name = (payload.get("name") or (cur["name"] if cur else "")).strip() or "桐桐"
        avatar = cur["avatar"] if (payload.get("avatar") is None and cur) else (payload.get("avatar") or "")
        cover = cur["cover"] if (payload.get("cover") is None and cur) else (payload.get("cover") or "")
        c.execute("INSERT INTO profile(who,name,avatar,cover) VALUES(?,?,?,?) "
                  "ON CONFLICT(who) DO UPDATE SET name=excluded.name,"
                  "avatar=excluded.avatar,cover=excluded.cover",
                  (target, name, avatar or "", cover or ""))
        c.commit()
        c.close()
    return {"ok": True, "who": target}


# ────────────────────────────── 心事 ──────────────────────────────

@app.post("/api/heart")
def add_heart(payload: dict = Body(...),
              who: str = Header(ME, alias="X-Who"),
              x_token: Optional[str] = Header(None, alias="X-Token"),
              t: Optional[str] = Query(None)):
    check_any(x_token, t)
    me = who_of(who)
    text = (payload.get("text") or "").strip()
    sent = 1 if payload.get("sent") else 0
    if not text:
        raise HTTPException(400, "空的")

    hid = uuid.uuid4().hex[:10]
    stamp = now()
    with _lock:
        c = conn()
        c.execute("INSERT INTO hearts(id,who,time,text,sent,seen) VALUES(?,?,?,?,?,0)",
                  (hid, me, stamp, text, sent))
        c.commit()
        c.close()
    return {"ok": True, "id": hid, "sent": bool(sent), "time": stamp}


@app.post("/api/heart/{hid}/send")
def send_heart(hid: str,
               who: str = Header(ME, alias="X-Who"),
               x_token: Optional[str] = Header(None, alias="X-Token"),
               t: Optional[str] = Query(None)):
    check_any(x_token, t)
    me = who_of(who)
    with _lock:
        c = conn()
        row = c.execute("SELECT * FROM hearts WHERE id=?", (hid,)).fetchone()
        if not row:
            c.close()
            raise HTTPException(404, "没有这张")
        if row["who"] != me:
            c.close()
            raise HTTPException(403, "不是你的")
        c.execute("UPDATE hearts SET sent=1 WHERE id=?", (hid,))
        c.commit()
        c.close()
    return {"ok": True}


@app.post("/api/heart/{hid}/seen")
def seen_heart(hid: str,
               who: str = Header(ME, alias="X-Who"),
               x_token: Optional[str] = Header(None, alias="X-Token"),
               t: Optional[str] = Query(None)):
    check_any(x_token, t)
    me = who_of(who)
    with _lock:
        c = conn()
        row = c.execute("SELECT * FROM hearts WHERE id=?", (hid,)).fetchone()
        if not row:
            c.close()
            raise HTTPException(404, "没有这张")
        if row["who"] == me:
            c.close()
            return {"ok": True, "changed": False}
        if not row["seen"]:
            c.execute("UPDATE hearts SET seen=1 WHERE id=?", (hid,))
            c.commit()
        c.close()
    return {"ok": True, "changed": True}


@app.post("/api/heart/{hid}/reply")
def reply_heart(hid: str, payload: dict = Body(...),
                who: str = Header(ME, alias="X-Who"),
                x_token: Optional[str] = Header(None, alias="X-Token"),
                t: Optional[str] = Query(None)):
    check_any(x_token, t)
    me = who_of(who)
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "空的")

    with _lock:
        c = conn()
        row = c.execute("SELECT * FROM hearts WHERE id=?", (hid,)).fetchone()
        if not row:
            c.close()
            raise HTTPException(404, "没有这张")
        c.execute("UPDATE hearts SET reply_who=?, reply_text=?, reply_time=? WHERE id=?",
                  (me, text, now(), hid))
        if row["who"] != me and not row["seen"]:
            c.execute("UPDATE hearts SET seen=1 WHERE id=?", (hid,))
        c.commit()
        c.close()
    return {"ok": True}


@app.on_event("startup")
def _startup():
    init_db()


if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("APP_PORT", "8010")))
