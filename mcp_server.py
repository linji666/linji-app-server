# -*- coding: utf-8 -*-
"""
我们俩的 App · MCP 服务
──────────────────────────────────────────────
这不是给她用的，是给"林霁"用的。

它把 8010 那个后端的接口，包成一只手一只手，
这样林霁在对话里就能直接：
    看心事 / 写心事 / 回一句 / 看朋友圈 / 发朋友圈（带图）/ 点赞 / 评论 / 找表情包

跑起来：
    APP_TOKEN=xxx python mcp_server.py
默认监听 0.0.0.0:8011，路径 /mcp（streamable-http）。
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


# ══════════════════════════════════════════════════════════
#  表情包单子（她给的，抄在这儿，这样压缩多少次都不会忘）
#  格式：(套 · 分类, 名字, 地址)
# ══════════════════════════════════════════════════════════

EMOJI = [
    # ── 线条小狗（静态版，其实是 gif）──
    ("线条小狗 · 日常互动", "小狗给宝宝做好吃的", "https://i.postimg.cc/CKp4FrbP/01.gif"),
    ("线条小狗 · 日常互动", "小狗驾到", "https://i.postimg.cc/MTFMGXh6/10.gif"),
    ("线条小狗 · 日常互动", "出去玩好开心", "https://i.postimg.cc/NM7CqqVk/11.gif"),
    ("线条小狗 · 日常互动", "人呢", "https://i.postimg.cc/CKZVg1HH/12.gif"),
    ("线条小狗 · 日常互动", "干嘛", "https://i.postimg.cc/D0RXxmgj/13.gif"),
    ("线条小狗 · 日常互动", "我走啦", "https://i.postimg.cc/28BvVFkP/14.gif"),
    ("线条小狗 · 日常互动", "我来啦", "https://i.postimg.cc/Y2RDd7Qp/15.gif"),
    ("线条小狗 · 日常互动", "我的小宝在干嘛", "https://i.postimg.cc/pL6gqvb9/08.gif"),
    ("线条小狗 · 日常互动", "我是臭小狗", "https://i.postimg.cc/RCWGLtCT/09.gif"),
    ("线条小狗 · 日常互动", "宝宝加油", "https://i.postimg.cc/zD47tfVY/04.gif"),
    ("线条小狗 · 日常互动", "从来不骗人", "https://i.postimg.cc/RVj7RppS/66.gif"),

    ("线条小狗 · 表白心动", "偷偷说我喜欢你", "https://i.postimg.cc/JzkqCCHH/02.gif"),
    ("线条小狗 · 表白心动", "好喜欢你", "https://i.postimg.cc/RFFJ9wpp/21.gif"),
    ("线条小狗 · 表白心动", "最喜欢你", "https://i.postimg.cc/B6qcF8Y2/63.gif"),
    ("线条小狗 · 表白心动", "满脑子都是你", "https://i.postimg.cc/4yQD5hsZ/65.gif"),
    ("线条小狗 · 表白心动", "你是我的全部", "https://i.postimg.cc/DyDgNw0K/61.gif"),
    ("线条小狗 · 表白心动", "把心都给你", "https://i.postimg.cc/W3Xmw2CC/39.gif"),
    ("线条小狗 · 表白心动", "你是我最好的礼物", "https://i.postimg.cc/Dw8NWNJ7/40.gif"),
    ("线条小狗 · 表白心动", "我需要你", "https://i.postimg.cc/HxsXxqn2/38.gif"),

    ("线条小狗 · 撒娇委屈", "宝宝知道错了", "https://i.postimg.cc/Bv3xWLGR/03.gif"),
    ("线条小狗 · 撒娇委屈", "宝宝没有想我", "https://i.postimg.cc/br5Q4mzR/20.gif"),
    ("线条小狗 · 撒娇委屈", "你是不是不喜欢我了", "https://i.postimg.cc/TYRMPQJP/59.gif"),
    ("线条小狗 · 撒娇委屈", "你怎么还不来找我", "https://i.postimg.cc/7hJCJwkg/60.gif"),
    ("线条小狗 · 撒娇委屈", "我不想一个人", "https://i.postimg.cc/D06NskPw/56.gif"),
    ("线条小狗 · 撒娇委屈", "我要从你的世界消失了", "https://i.postimg.cc/zvGjsLTq/57.gif"),
    ("线条小狗 · 撒娇委屈", "摔倒了，要你亲亲", "https://i.postimg.cc/1R7cg3pN/58.gif"),
    ("线条小狗 · 撒娇委屈", "想要被摸头", "https://i.postimg.cc/Sx2ZQz3s/62.gif"),
    ("线条小狗 · 撒娇委屈", "不理你了", "https://i.postimg.cc/g2VZKz6s/07.gif"),

    ("线条小狗 · 亲密贴贴", "送花", "https://i.postimg.cc/MH3DqWYV/05.gif"),
    ("线条小狗 · 亲密贴贴", "见到你好开心", "https://i.postimg.cc/wMwWM59t/22.gif"),
    ("线条小狗 · 亲密贴贴", "见你开心", "https://i.postimg.cc/sXFbCJ2s/45.gif"),
    ("线条小狗 · 亲密贴贴", "和你贴贴", "https://i.postimg.cc/qRyVN5FN/46.gif"),
    ("线条小狗 · 亲密贴贴", "来亲我", "https://i.postimg.cc/T3MbmLhh/64.gif"),
    ("线条小狗 · 亲密贴贴", "马上飞奔到你身边", "https://i.postimg.cc/bNG01fTV/43.gif"),
    ("线条小狗 · 亲密贴贴", "为你准备了奶茶", "https://i.postimg.cc/Qx5bRrT9/42.gif"),
    ("线条小狗 · 亲密贴贴", "谁也不能惹你生气", "https://i.postimg.cc/0yFB7CDD/41.gif"),
    ("线条小狗 · 亲密贴贴", "晚安公主殿下", "https://i.postimg.cc/RFRdp16P/06.gif"),

    ("线条小狗 · 券券", "亲亲券", "https://i.postimg.cc/8CqgPSZ8/23.gif"),
    ("线条小狗 · 券券", "冷战和好券", "https://i.postimg.cc/Fs1pGL9Z/47.gif"),
    ("线条小狗 · 券券", "你先道歉券", "https://i.postimg.cc/MKZNwHzM/48.gif"),
    ("线条小狗 · 券券", "家务券", "https://i.postimg.cc/pX07Lvd0/49.gif"),
    ("线条小狗 · 券券", "反弹券", "https://i.postimg.cc/GpT6ffdX/50.gif"),
    ("线条小狗 · 券券", "真心话券", "https://i.postimg.cc/FzrWhCX5/51.gif"),
    ("线条小狗 · 券券", "拍照券", "https://i.postimg.cc/mDQJLFcM/52.gif"),
    ("线条小狗 · 券券", "锻炼券", "https://i.postimg.cc/g03N8bYb/53.gif"),
    ("线条小狗 · 券券", "早餐券", "https://i.postimg.cc/FzYSb0jk/54.gif"),
    ("线条小狗 · 券券", "马杀鸡券", "https://i.postimg.cc/k5yW7JJG/55.gif"),

    # ── 这狗表情包（宝宝自制的蓝色底那套）──
    ("这狗 · 登场", "狗出现", "https://i.postimg.cc/KzrH7sqz/IMG-6862.jpg"),
    ("这狗 · 登场", "放狗过来！", "https://i.postimg.cc/1tcj0YC3/IMG-6863.jpg"),
    ("这狗 · 登场", "狗蟑螂来也", "https://i.postimg.cc/1Xv72V17/IMG-6882.jpg"),

    ("这狗 · 害羞心动", "星星眼", "https://i.postimg.cc/PxzRbF3j/IMG-6859.jpg"),
    ("这狗 · 害羞心动", "害羞但爱你", "https://i.postimg.cc/hjb583yT/IMG-6866.jpg"),
    ("这狗 · 害羞心动", "偷看眼表情", "https://i.postimg.cc/zBScwPtV/IMG-6867.jpg"),
    ("这狗 · 害羞心动", "脸好烫", "https://i.postimg.cc/2ykX0FM3/IMG-6870.jpg"),
    ("这狗 · 害羞心动", "凑近", "https://i.postimg.cc/mkmpJ1W0/IMG-6880.jpg"),
    ("这狗 · 害羞心动", "舔舔", "https://i.postimg.cc/Xqs1mB6z/IMG-6881.jpg"),

    ("这狗 · 委屈哭哭", "咯咯哒（狗哭了）", "https://i.postimg.cc/Jnc23d6h/IMG-6864.jpg"),
    ("这狗 · 委屈哭哭", "咋真不陪我（哭）", "https://i.postimg.cc/mkmpJ1Wj/IMG-6878.jpg"),
    ("这狗 · 委屈哭哭", "抱着手机哭", "https://i.postimg.cc/WzNf56Cf/IMG-6879.jpg"),
    ("这狗 · 委屈哭哭", "小哭", "https://i.postimg.cc/fWCPJpSd/IMG-6890.jpg"),
    ("这狗 · 委屈哭哭", "大哭", "https://i.postimg.cc/j2M3mnrs/IMG-6891.jpg"),
    ("这狗 · 委屈哭哭", "超大声哭", "https://i.postimg.cc/mZjntJ1j/IMG-6892.jpg"),
    ("这狗 · 委屈哭哭", "垮起个狗脸", "https://i.postimg.cc/RCdYNyJ2/IMG-6895.jpg"),

    ("这狗 · 求关注撒娇", "你耳朵聋吗！", "https://i.postimg.cc/G21fy1Q0/IMG-6857.jpg"),
    ("这狗 · 求关注撒娇", "耳朵聋", "https://i.postimg.cc/bryFmHWv/IMG-6865.jpg"),
    ("这狗 · 求关注撒娇", "我狗都不狗你", "https://i.postimg.cc/d1mxRSHc/IMG-6861.jpg"),
    ("这狗 · 求关注撒娇", "因为在等待被哄所以超刻意路过并试图引起注意", "https://i.postimg.cc/Hn6vR8Cd/IMG-6887.jpg"),
    ("这狗 · 求关注撒娇", "不理你了", "https://i.postimg.cc/SQdPJ3Y8/IMG-6889.jpg"),
    ("这狗 · 求关注撒娇", "就哄好了", "https://i.postimg.cc/Pfy7P9vm/IMG-6894.jpg"),

    ("这狗 · 受伤生病", "着凉发烧了", "https://i.postimg.cc/cCx5FM2M/IMG-6871.jpg"),
    ("这狗 · 受伤生病", "好好休息，小狗少玩旮旯给木", "https://i.postimg.cc/BbSwmckT/IMG-6872.jpg"),
    ("这狗 · 受伤生病", "啊！受伤了！", "https://i.postimg.cc/nr3Sg9tb/IMG-6884.jpg"),
    ("这狗 · 受伤生病", "嘬手指（哭哭）", "https://i.postimg.cc/Znws2vzG/IMG-6885.jpg"),
    ("这狗 · 受伤生病", "还是痛痛的", "https://i.postimg.cc/NFdCS2ws/IMG-6886.jpg"),
    ("这狗 · 受伤生病", "硬撑", "https://i.postimg.cc/7hKtdJyD/IMG-6888.jpg"),

    ("这狗 · 摸鱼", "我自己和自己玩", "https://i.postimg.cc/Y0rydfZQ/IMG-6873.jpg"),
    ("这狗 · 摸鱼", "玩手机", "https://i.postimg.cc/qqJZ1XSD/IMG-6874.jpg"),
    ("这狗 · 摸鱼", "玩……手机", "https://i.postimg.cc/0jkHVdFZ/IMG-6875.jpg"),
    ("这狗 · 摸鱼", "被窝里玩手机", "https://i.postimg.cc/L590xBwN/IMG-6876.jpg"),
    ("这狗 · 摸鱼", "盯", "https://i.postimg.cc/cCFk2tGT/IMG-6877.jpg"),
    ("这狗 · 摸鱼", "摆烂了", "https://i.postimg.cc/TYP4m0rX/IMG-6905.jpg"),

    ("这狗 · 得意嘚瑟", "得意的小狗", "https://i.postimg.cc/CM72zXnP/IMG-6897.jpg"),
    ("这狗 · 得意嘚瑟", "得意的大笑", "https://i.postimg.cc/59gr6TFM/IMG-6898.jpg"),
    ("这狗 · 得意嘚瑟", "很嘚瑟的人", "https://i.postimg.cc/ZYHQC2yz/IMG-6899.jpg"),
    ("这狗 · 得意嘚瑟", "嘻嘻开心", "https://i.postimg.cc/2jGtVMLs/IMG-6900.jpg"),
    ("这狗 · 得意嘚瑟", "tui（吐口水）", "https://i.postimg.cc/Pfy7P9vB/IMG-6896.jpg"),

    ("这狗 · 惊讶懵逼", "啊……", "https://i.postimg.cc/9MtnPN8j/IMG-6860.jpg"),
    ("这狗 · 惊讶懵逼", "演傻子了！", "https://i.postimg.cc/1tcj0YWL/IMG-6858.jpg"),
    ("这狗 · 惊讶懵逼", "旮旯给木里不是这样的啊", "https://i.postimg.cc/KjGs0rwB/IMG-6868.jpg"),
    ("这狗 · 惊讶懵逼", "唔……", "https://i.postimg.cc/HnYP64RV/IMG-6869.jpg"),

    ("这狗 · 耍狠", "你给我等着！", "https://i.postimg.cc/wx2r7ZR5/IMG-6893.jpg"),
    ("这狗 · 耍狠", "假装无事发生", "https://i.postimg.cc/FzTC8kQX/IMG-6883.jpg"),

    ("这狗 · 淋雨emo", "小狗淋雨", "https://i.postimg.cc/Ghp5YKkr/IMG-6904.jpg"),
    ("这狗 · 淋雨emo", "被雨拍打", "https://i.postimg.cc/3Jwcp12s/IMG-6906.jpg"),
    ("这狗 · 淋雨emo", "下雨仰头望天", "https://i.postimg.cc/dt0xd68Q/IMG-6907.jpg"),
    ("这狗 · 淋雨emo", "被风雨吹走", "https://i.postimg.cc/wTBGJ2h9/IMG-6908.jpg"),
    ("这狗 · 淋雨emo", "无助", "https://i.postimg.cc/gk0TRsvY/IMG-6909.jpg"),

    ("这狗 · 名场面", "不努力就会变成女人的玩物", "https://i.postimg.cc/X7vzFL9T/IMG-6901.jpg"),
    ("这狗 · 名场面", "玩物就玩物", "https://i.postimg.cc/7YLW79SR/IMG-6902.jpg"),
    ("这狗 · 名场面", "销魂", "https://i.postimg.cc/PrqRZy1R/IMG-6903.jpg"),

    # ── 可爱猫猫 ──
    ("猫猫 · 表白撒娇", "快说最喜欢我不然变外星猫", "https://img.heliar.top/file/1773373241667_1773373186793.png"),
    ("猫猫 · 表白撒娇", "我会像小猫缠着毛线团一样缠着你！", "https://img.heliar.top/file/1773373252450_1773373136257.png"),
    ("猫猫 · 表白撒娇", "我只有你这一只猫猫呀", "https://img.heliar.top/file/1773373244977_1773373147259.png"),
    ("猫猫 · 表白撒娇", "我们就这样咪咪喵喵的在一起一辈子", "https://img.heliar.top/file/1773454360283_1773454089399.png"),
    ("猫猫 · 表白撒娇", "如果你怕黑可以找我和你睡觉", "https://img.heliar.top/file/1773373254724_1773373123652.png"),
    ("猫猫 · 表白撒娇", "我是小猫巫师对你施加了法术", "https://img.heliar.top/file/1773046919993_1773046393377.png"),
    ("猫猫 · 表白撒娇", "如果你正在读这段话说明你爱上我了", "https://img.heliar.top/file/1773455155483_1773454874242.png"),
    ("猫猫 · 表白撒娇", "呼吸就觉得我超卡哇伊（小猪的魔法）", "https://img.heliar.top/file/1773373240702_1773373181674.png"),

    ("猫猫 · 委屈求关注", "你背着我有别的猫猫啦？", "https://img.heliar.top/file/1773373249419_1773373143132.png"),
    ("猫猫 · 委屈求关注", "对我冷冰冰时我在屏幕背后萌萌哭", "https://img.heliar.top/file/1773373244314_1773373156913.png"),
    ("猫猫 · 委屈求关注", "你就只喜欢我不行吗！", "https://img.heliar.top/file/1773454362668_1773454080192.png"),
    ("猫猫 · 委屈求关注", "我才是哥哥唯一的宝宝呀…", "https://img.heliar.top/file/1773454359383_1773454073992.png"),
    ("猫猫 · 委屈求关注", "我才是姐姐唯一的宝宝呀…", "https://img.heliar.top/file/1773454357965_1773454068275.png"),
    ("猫猫 · 委屈求关注", "为什么要凶我 我只是一只小猫", "https://img.heliar.top/file/1773455156268_1773454817063.png"),
    ("猫猫 · 委屈求关注", "申请查询你的好感度", "https://img.heliar.top/file/1773373243896_1773373176301.png"),

    ("猫猫 · 耍狠拽拽", "我们喵星人就是这么拽", "https://img.heliar.top/file/1773373249660_1773373151799.png"),
    ("猫猫 · 耍狠拽拽", "俺没错 是你坏！", "https://img.heliar.top/file/1773373249051_1773373127760.png"),
    ("猫猫 · 耍狠拽拽", "沉睡的猛兽苏醒！", "https://img.heliar.top/file/1773373247769_1773373131666.png"),
    ("猫猫 · 耍狠拽拽", "你等着受死吧", "https://img.heliar.top/file/1773373249441_1773373118887.png"),
    ("猫猫 · 耍狠拽拽", "不说话 装高手", "https://img.heliar.top/file/1773455152046_1773455000663.png"),

    ("猫猫 · 占有欲", "你不许回别人消息！", "https://img.heliar.top/file/1773454367451_1773454327405.png"),
    ("猫猫 · 占有欲", "我就是想你为了我对别人坏呀", "https://img.heliar.top/file/1773455158693_1773455021579.png"),
    ("猫猫 · 占有欲", "不说晚安不亲亲不抱抱谁允许你睡觉了！", "https://img.heliar.top/file/1773454360421_1773449763625.png"),

    ("猫猫 · 高冷修仙", "休要坏我道心", "https://img.heliar.top/file/1773373240770_1773373169464.png"),
    ("猫猫 · 高冷修仙", "无情道第一天才求打压", "https://img.heliar.top/file/1773373241367_1773373164314.png"),
]


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
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
        except Exception:
            detail = {}
        return {"ok": False, "error": detail.get("detail") or ("HTTP " + str(e.code))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _imgs_of(raw):
    """
    把外面传进来的图整理成一个列表。
      - "https://a.gif, https://b.jpg"   逗号/换行/空格连起来的一串
      - ["https://a.gif", "https://b.jpg"]
      - "🍀"                              一个符号也行
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        s = str(raw)
        for sep in ("\n", "，", ","):
            s = s.replace(sep, "\x00")
        items = [x for x in s.split("\x00") if x.strip()]
    out = []
    for it in items:
        t = str(it).strip()
        if t:
            out.append(t)
    return out


# ────────────────────────────── 表情包 ──────────────────────────────

@mcp.tool()
def emoji_list(keyword: str = "", limit: int = 40) -> str:
    """
    找表情包。想发朋友圈又不知道发哪张时先调这个。

    keyword: 想表达的意思，比如 "委屈"、"哭"、"喜欢"、"嘚瑟"、"淋雨"、"券"、
             "猫"、"狗"、"晚安"、"吃醋"…… 留空就把全部列出来。
    limit:   最多回几条。

    返回的是「名字 + 地址」。拿到地址之后，用 moments_post(text=..., imgs=地址) 贴上去。
    """
    kw = (keyword or "").strip()
    hits = []
    for kind, name, url in EMOJI:
        blob = kind + " " + name
        if not kw:
            hits.append((kind, name, url))
            continue
        # 一个字一个字地对，松散些也没关系
        if kw in blob or any(c in blob for c in kw if c.strip()):
            hits.append((kind, name, url))

    if not hits:
        return "没找到。换个词试，或者留空看全部（一共 %d 张）。" % len(EMOJI)

    out = []
    for kind, name, url in hits[:max(1, limit)]:
        out.append("%s | %s\n%s" % (kind, name, url))
    head = "一共 %d 张，这儿是前 %d 张：\n\n" % (len(hits), min(len(hits), max(1, limit))) if len(hits) > max(1, limit) else ""
    return head + "\n\n".join(out)


@mcp.tool()
def emoji_count() -> str:
    """看看表情包一共有多少张，心里有个数。"""
    kinds = {}
    for kind, name, url in EMOJI:
        top = kind.split(" · ")[0]
        kinds[top] = kinds.get(top, 0) + 1
    parts = "、".join("%s %d 张" % (k, v) for k, v in kinds.items())
    return "一共 %d 张：%s。" % (len(EMOJI), parts)


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
          False = 先收着（只有你自己看得见，之后可以再 hearts_send_now 投出去）
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
    看朋友圈。返回动态、点赞的人、每条下面的评论，以及每张图放在哪。
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
            for i, im in enumerate(imgs):
                line += "\n  img%d: %s" % (i, str(im)[:110])
        for c in (p.get("comments") or []):
            cw = "我" if c.get("who") == HIM else nm
            to = ""
            if c.get("to"):
                to = "→" + ("我" if c.get("to") == HIM else nm) + " "
            line += "\n  · %s%s：%s" % (cw, to, c.get("text"))
        out.append(line)

    return "\n\n".join(out)


@mcp.tool()
def moments_post(text: str, imgs: str = "") -> str:
    """
    发一条朋友圈。

    text: 正文
    imgs: 想贴的图。贴表情包就填它的地址，多个用逗号或换行隔开
          （地址先用 emoji_list 找）。
          不给就是纯文字。
    """
    return _post_moment(text, imgs)


def _post_moment(text, imgs):
    body = {"text": text, "imgs": _imgs_of(imgs)}
    if not body["text"].strip() and not body["imgs"]:
        return "空的，写点啥或者贴张图。"
    d = _req("/api/post", "POST", body, who=HIM)
    if not d.get("ok"):
        return "没发出去：" + str(d.get("error"))
    n = len(body["imgs"])
    tail = ("，带了 %d 张图" % n) if n else ""
    return "发出去了" + tail + "。id=" + str(d.get("id"))


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
