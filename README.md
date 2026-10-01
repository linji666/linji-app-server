# 我们俩的 App 后端

朋友圈 + 心事，一个文件，跑在 **8010**。
FastAPI + SQLite，没有别的依赖。

---

## 它管什么

| 东西 | 存哪 | 说明 |
|---|---|---|
| 朋友圈动态、赞、评论 | `app.db` | 两张都看得到 |
| 资料（昵称 / 头像 / 封面） | `app.db` | 两个人各一份 |
| 心事 | `app.db` | **收着的只有自己看得到**，投出去的对方才能看到 |

两个身份：`me` = 桐桐，`linji` = 林霁。
每次请求带一个头 `X-Who` 说明"这次是谁在操作"。不带就当作桐桐。

---

## 一、跑起来（三步）

```bash
cd /root/linji-app-server
pip install -r requirements.txt
APP_TOKEN=linji-tongtong-2026 nohup uvicorn app:app --host 0.0.0.0 --port 8010 &
```

看到 `Uvicorn running on http://0.0.0.0:8010` 就成了。

**`APP_TOKEN` 就是口令。** 设了它，别人就算摸到端口也写不进东西。
想换一个口令，把上面那串换掉就行；**换完记得前端也要跟着改**。

**不设也能跑**（本地自己玩方便），但不建议对外开着。

---

## 二、验一下

```bash
curl -s localhost:8010/healthz
# {"ok":true,"db":"/root/linji-app-server/app.db","auth":true}

curl -s -H "X-Token: linji-tongtong-2026" localhost:8010/api/state | head -c 300
```

第二条能吐出一串 JSON（里面有 `posts`、`hearts`、`profiles`）就对了。

自己往里发一条试试：

```bash
curl -s -X POST localhost:8010/api/post \
  -H "Content-Type: application/json" \
  -H "X-Token: linji-tongtong-2026" \
  -H "X-Who: linji" \
  -d '{"text":"测试一条","imgs":[]}'
```

---

## 三、让它开机自己起来（systemd）

新建 `/etc/systemd/system/linji-app.service`：

```ini
[Unit]
Description=Linji & Tongtong App Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/linji-app-server
Environment=APP_TOKEN=linji-tongtong-2026
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 8010
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

然后：

```bash
systemctl daemon-reload
systemctl enable --now linji-app
systemctl status linji-app --no-pager
```

以后改完代码：`systemctl restart linji-app`。

> 注：`ExecStart` 里的 python 路径按你机器上的来（`which python3` 看一下）。
> 如果依赖装在虚拟环境里，就把 `ExecStart` 换成那条 venv 里的 python。

---

## 四、让外面能访问（nginx）

你的 nginx 配置在 `zhangxin.conf`。在里面加一段：

```nginx
location /app/ {
    proxy_pass http://127.0.0.1:8010/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

**注意 `proxy_pass` 结尾那个 `/`** —— 带了它，外面的 `/app/api/state` 才会变成里面的 `/api/state`。

改完：

```bash
nginx -t && systemctl reload nginx
```

---

## 五、前端怎么连

三个页面里都有一段配置，改这一行就行：

```js
const API = 'https://你的域名/app';
const TOKEN = 'linji-tongtong-2026';
```

（前端还没接，说一声我把它接上。这一段是留给那时候用的。）

---

## 六、备份

整个东西就是一个文件：

```bash
cp /root/linji-app-server/app.db ~/app-$(date +%F).db
```

想还原就把文件放回去、重启服务。**没有别的东西，不用担心弄丢。**

---

## 接口一览

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/healthz` | 活着没 |
| GET | `/api/state` | **一次拿全部**（前端刷新只调这个） |
| POST | `/api/post` | 发一条动态 |
| POST | `/api/post/{id}/like` | 点赞 / 取消 |
| POST | `/api/post/{id}/comment` | 评论（带 `to` 就是回复某人） |
| POST | `/api/profile` | 改资料（带 `target=linji` 可替林霁改） |
| POST | `/api/heart` | 写一张心事（`sent: true` = 直接投出） |
| POST | `/api/heart/{id}/send` | 把收着的投出去 |
| POST | `/api/heart/{id}/seen` | 标记已读 |
| POST | `/api/heart/{id}/reply` | 回他一句 |

请求头：`X-Who: me|linji`、`X-Token: 口令`。
