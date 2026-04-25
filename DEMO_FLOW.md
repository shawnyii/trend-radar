# Trend Radar Demo Flow

## 目的

這份文件用來快速展示 Trend Radar MVP 的核心能力：

- 啟動系統
- 驗證資料來源可連通
- 手動抓取一次熱門關鍵字
- 檢查資料是否入庫
- 開啟 Dashboard
- 驗證 Discord webhook 推播

## Demo 前準備

### 1. 啟用虛擬環境

```bash
source .venv/bin/activate
```

### 2. 確認 `.env` 存在

如果你還沒有 `.env`：

```bash
cp .env.example .env
```

### 3. 設定 Discord Webhook

打開 `.env`，找到這一行：

```env
DISCORD_WEBHOOK_URL=
```

把它改成：

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/你的_webhook_id/你的_webhook_token
```

### 4. 如何取得 Discord Webhook URL

在 Discord：

1. 進入你要接收通知的伺服器頻道
2. 點 `Edit Channel`
3. 找 `Integrations`
4. 建立 `Webhook`
5. 複製 `Webhook URL`
6. 貼到 `.env` 的 `DISCORD_WEBHOOK_URL`

## 驗證資料來源是否可連通

### 1. 驗證 Google Trends Taiwan RSS

```bash
curl -I "https://trends.google.com/trending/rss?geo=TW"
```

正常情況應看到 `HTTP/1.1 200 OK` 或 `HTTP/2 200`。

也可以直接看前幾行內容：

```bash
curl -s "https://trends.google.com/trending/rss?geo=TW" | head -20
```

如果成功，應該會看到 RSS / XML 內容。

### 2. 驗證 Google News RSS

```bash
curl -I "https://news.google.com/rss/search?q=AI&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
```

也可以直接看內容：

```bash
curl -s "https://news.google.com/rss/search?q=AI&hl=zh-TW&gl=TW&ceid=TW:zh-Hant" | head -20
```

如果成功，應該會看到 RSS / XML。

### 3. 若驗證失敗

可能原因：

- 公司網路或學校網路阻擋 Google
- VPN / Proxy 干擾
- DNS 問題
- 當下網路暫時不穩

可先檢查：

```bash
curl -I https://www.google.com
```

如果這也失敗，通常不是程式問題，而是你目前的網路環境無法正常連 Google。

## Demo 流程一：本機 SQLite 模式

### 1. 初始化資料庫

```bash
.venv/bin/python -m app.cli init-db
```

### 2. 手動抓取一次資料

```bash
.venv/bin/python -m app.cli collect-now
```

成功時會輸出類似：

```json
{"snapshot_id":1,"observation_count":20,"news_count":12,"alerts_count":2,"sent_alerts_count":2}
```

### 3. 手動送出每日摘要

```bash
.venv/bin/python -m app.cli send-summary
```

成功時會輸出：

```json
{"sent": true}
```

如果 `.env` 沒填 `DISCORD_WEBHOOK_URL`，可能會看到：

```json
{"sent": false}
```

### 4. 啟動 Dashboard

```bash
uvicorn app.main:app --reload
```

開啟：

```text
http://127.0.0.1:8000
```

### 5. Demo 時建議展示的頁面

- Dashboard 首頁
- 最新熱門關鍵字
- 最近警報
- 單一 keyword 詳情頁
- keyword 歷史圖表
- 相關新聞連結

## Demo 流程二：Docker PostgreSQL 模式

### 1. 啟動 stack

```bash
docker compose up --build
```

### 2. 檢查健康狀態

```bash
curl -s http://127.0.0.1:8000/health
```

應回傳：

```json
{"status":"ok"}
```

### 3. 打開 Dashboard

```text
http://127.0.0.1:8000
```

### 4. 結束

```bash
docker compose down
```

## 建議的實際展示順序

1. 先展示 `.env` 已填 Discord webhook
2. 用 `curl` 驗證 Google Trends / Google News 可連通
3. 執行 `collect-now`
4. 展示 Discord 是否收到 alert / summary
5. 開 Dashboard 展示最新資料
6. 點進單一 keyword 查看歷史圖表與新聞

## 快速排錯

### `collect-now` 沒抓到資料

先跑：

```bash
curl -s "https://trends.google.com/trending/rss?geo=TW" | head
```

如果沒有 XML，先排查網路。

### `send-summary` 沒送成功

先檢查 `.env`：

```bash
grep DISCORD_WEBHOOK_URL .env
```

如果是空值，就不會送。

### Dashboard 開得起來但沒資料

代表 app 正常，但你還沒跑：

```bash
.venv/bin/python -m app.cli collect-now
```

### Docker 起來但頁面沒回應

先看：

```bash
docker compose ps
docker compose logs web --tail=50
docker compose logs db --tail=50
```
