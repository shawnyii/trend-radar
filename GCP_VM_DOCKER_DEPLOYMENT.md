# GCP VM + Docker 部署教學

這份文件的目標是學會如何把 Trend Radar 從本機 Docker Compose 服務，部署到 Google Cloud Platform 的 Compute Engine VM 上。這不是正式 production 架構，而是用最低複雜度理解雲端部署的完整鏈路。

主流程使用 `GCP Console + SSH + Docker Compose`。`gcloud CLI` 只放在附錄，因為第一次學部署時，先看懂 VM、IP、firewall、port、Docker image、container 之間的關係，比一開始追求全指令自動化更重要。

## 1. 先理解部署鏈路

本機開發時，服務跑在你的電腦：

```text
Browser -> 127.0.0.1:8000 -> FastAPI app -> local SQLite or Docker PostgreSQL
```

部署到 GCP VM 後，服務跑在雲端 Linux 主機：

```text
Browser -> VM external IP:8000 -> GCP firewall -> VM -> Docker container -> FastAPI app -> PostgreSQL container
```

核心名詞：

- `VM`：Virtual Machine，雲端上的一台 Linux 電腦。你可以把它想成一台長時間開機的遠端主機。
- `SSH`：安全遠端登入方式。你用 SSH 從本機或瀏覽器登入 VM，進去後像操作 Linux terminal 一樣部署服務。
- `port`：服務對外開的門。Trend Radar 的 FastAPI server 對外使用 `8000`，所以網址會是 `http://VM_EXTERNAL_IP:8000`。
- `firewall`：GCP 的網路門禁。就算程式在 VM 上跑起來，如果 firewall 沒允許 `8000`，外部瀏覽器還是連不到。
- `Docker image`：把應用程式、Python 套件、啟動指令打包好的模板。
- `container`：由 image 啟動出來的實際執行環境。Trend Radar 會有 `web` container 和 `db` container。
- `Docker Compose`：用一份 `docker-compose.yml` 同時管理多個 container。這個專案用它啟動 FastAPI 與 PostgreSQL。

## 2. 成本與安全前提

Google Cloud Free Tier 目前包含 Compute Engine `e2-micro` VM、標準 persistent disk 與部分 outbound traffic，但有區域與用量限制。官方文件列出的免費 Compute Engine 區域包含 `us-west1`、`us-central1`、`us-east1`，並且免費額度是按時間與用量計算，不代表所有 VM 設定都免費。

建議：

- 建立 GCP Budget alert，避免意外費用。
- VM 選 `e2-micro` 與支援免費額度的美國區域。
- 磁碟先用標準 persistent disk，大小不要超過學習需求。
- 不使用 GPU、Load Balancer、Cloud SQL、Artifact Registry。
- 不要把 `DISCORD_WEBHOOK_URL` commit 到 GitHub。
- Dashboard 的 `8000` port 不要對全世界開放，建議只允許你的 IP。

參考：

- Google Cloud Free Program: https://cloud.google.com/free/docs/free-cloud-features
- GCP firewall rules: https://cloud.google.com/firewall/docs/firewalls
- Docker Engine on Ubuntu: https://docs.docker.com/engine/install/ubuntu/

## 3. 建立 GCP VM

在 GCP Console 操作：

1. 開啟 `Compute Engine` -> `VM instances`。
2. 點 `Create instance`。
3. 建議設定：
   - Name: `trend-radar-vm`
   - Region: `us-west1`、`us-central1` 或 `us-east1`
   - Machine type: `e2-micro`
   - Boot disk: `Ubuntu 24.04 LTS`
   - Disk type: Standard persistent disk
   - Disk size: 20 GB 到 30 GB
4. Firewall 的 `Allow HTTP traffic` 和 `Allow HTTPS traffic` 可以先不勾，因為本教學先用 `8000`。
5. Network tags 加上：

```text
trend-radar-dashboard
```

為什麼要加 network tag：之後 firewall rule 可以只套用到這台 VM，而不是套用到整個 VPC 內所有 VM。

建立後，記下 VM 的 `External IP`。

## 4. 用 SSH 進入 VM

最簡單方式：

1. 在 `Compute Engine` -> `VM instances` 找到 `trend-radar-vm`。
2. 點該列的 `SSH`。
3. 瀏覽器會開一個 terminal。

進入後先確認系統：

```bash
uname -a
lsb_release -a
```

如果你能看到 Ubuntu 資訊，代表你已經登入雲端 VM。

## 5. 在 VM 安裝 Docker

以下使用 Docker 官方 Ubuntu apt repository 安裝方式。

先更新套件並安裝必要工具：

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
```

加入 Docker 官方 GPG key：

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

加入 Docker apt repository：

```bash
echo "Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc" | sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null
```

安裝 Docker Engine 與 Docker Compose plugin：

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

確認 Docker 正常：

```bash
sudo systemctl status docker
sudo docker run hello-world
```

為了之後不用每次加 `sudo`，把目前使用者加入 `docker` 群組：

```bash
sudo usermod -aG docker $USER
newgrp docker
docker version
docker compose version
```

如果 `docker version` 和 `docker compose version` 都有輸出，Docker 已可使用。

## 6. 把專案放到 VM

在 VM 上 clone GitHub repo：

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

如果 repo 是 private，你需要先設定 GitHub SSH key 或使用 GitHub CLI / personal access token。學習部署時，建議先用 public repo，流程最單純。

確認部署檔案存在：

```bash
ls Dockerfile docker-compose.yml .env.example
```

## 7. 設定環境變數

建立 VM 上的 `.env`：

```bash
cp .env.example .env
nano .env
```

至少確認：

```env
TIMEZONE=Asia/Taipei
DISCORD_WEBHOOK_URL=你的 Discord webhook URL
DAILY_SUMMARY_HOUR=1
DAILY_SUMMARY_MINUTE=52
```

重要：目前 `docker-compose.yml` 已經直接在 `web` service 設定 PostgreSQL 的 `DATABASE_URL`，所以 `.env` 裡的 SQLite 預設值不會影響 Docker 部署的資料庫連線。

若要讓 Discord webhook 與排程設定確實進入 container，建議在 VM 建立一個不 commit 的 `docker-compose.override.yml`：

```bash
nano docker-compose.override.yml
```

內容：

```yaml
services:
  web:
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+psycopg://trend_radar:trend_radar@db:5432/trend_radar
```

原因：Docker Compose 會自動合併 `docker-compose.yml` 與 `docker-compose.override.yml`。這樣可以保留 repo 內的預設 compose 設定，同時在 VM 上安全地注入 Discord webhook。

## 8. 啟動服務

在 repo 目錄執行：

```bash
docker compose up --build -d
```

確認 container 狀態：

```bash
docker compose ps
```

你應該看到類似：

```text
NAME               SERVICE   STATUS
project-db-1       db        running
project-web-1      web       running
```

查看 log：

```bash
docker compose logs -f web
```

如果看到 Uvicorn 啟動並監聽 `0.0.0.0:8000`，代表 FastAPI 已在 container 內啟動。

## 9. 設定 GCP firewall 開放 Dashboard

目前服務在 VM 上跑起來，但外部瀏覽器還不能保證連得到，因為 GCP firewall 需要允許 `8000`。

先查自己的 public IP：

```bash
curl ifconfig.me
```

假設查到：

```text
203.0.113.10
```

在 GCP Console 建立 firewall rule：

1. 到 `VPC network` -> `Firewall`。
2. 點 `Create firewall rule`。
3. 設定：
   - Name: `allow-trend-radar-dashboard`
   - Direction: `Ingress`
   - Action: `Allow`
   - Targets: `Specified target tags`
   - Target tags: `trend-radar-dashboard`
   - Source IPv4 ranges: `你的 IP/32`
   - Protocols and ports: `tcp:8000`

範例：

```text
Source IPv4 ranges: 203.0.113.10/32
Protocols and ports: tcp:8000
```

為什麼用 `/32`：代表只允許單一 IP 連入，比 `0.0.0.0/0` 安全很多。

## 10. 從瀏覽器確認 Dashboard

打開：

```text
http://VM_EXTERNAL_IP:8000
```

如果打得開，代表：

- VM 正在運行
- Docker container 正在運行
- FastAPI server 正在 listening
- Docker port mapping `8000:8000` 正常
- GCP firewall 允許你的 IP 連入

如果打不開，依序檢查：

```bash
docker compose ps
docker compose logs web
curl http://127.0.0.1:8000/health
```

判斷方式：

- VM 內 `curl http://127.0.0.1:8000/health` 成功，但外部瀏覽器失敗：通常是 firewall 或 external IP 問題。
- VM 內 curl 也失敗：通常是 container 沒起來、app crash、port mapping 錯誤。
- `db` unhealthy：通常是 PostgreSQL 還沒 ready、volume 權限或資源不足。

## 11. 驗證資料抓取與 Discord 推播

手動抓取真實資料：

```bash
docker compose exec web python -m app.cli collect-now
```

手動發送 daily summary：

```bash
docker compose exec web python -m app.cli send-summary
```

如果 Discord 沒收到：

```bash
docker compose exec web env | grep DISCORD
docker compose logs web
```

若 `DISCORD_WEBHOOK_URL` 沒出現，代表環境變數沒有被傳進 container，請回到第 7 步確認 `docker-compose.override.yml`。

## 12. 確認自動排程

Trend Radar 的排程是在 FastAPI app 啟動時由 APScheduler 啟動。

目前預設：

- 每 `60` 分鐘抓取一次 Google Trends
- 每天 `01:52` 發送 daily summary
- 時區：`Asia/Taipei`

確認 container 持續運行：

```bash
docker compose ps
docker compose logs -f web
```

如果你要讓 VM 放著跑一整天，至少確認：

- VM 沒有被手動 stop
- `web` container 沒有 crash
- `db` container 正常
- `.env` 裡的 webhook 正確
- GCP 沒有超出免費額度或被停用

## 13. 更新部署

之後 GitHub repo 有新版本時，在 VM 上：

```bash
git pull
docker compose up --build -d
docker compose ps
docker compose logs -f web
```

原因：

- `git pull` 取得最新程式碼
- `--build` 重新建立 Docker image
- `-d` 讓 container 在背景執行
- `ps` 和 `logs` 確認新版本有正常啟動

## 14. 停止服務或關閉 VM

只停止 container：

```bash
docker compose down
```

停止 container 但保留 PostgreSQL volume。下次 `docker compose up -d` 後資料還在。

如果要連資料也清掉：

```bash
docker compose down -v
```

注意：`-v` 會刪除 PostgreSQL volume，歷史資料會消失。

如果短期不使用，建議到 GCP Console stop VM，避免不必要的費用。但 VM 停止後，排程與 Dashboard 都會停止。

## 15. gcloud CLI 對照附錄

第一次學習建議用 Console。理解後，可以用 CLI 對照同樣概念。

建立 VM 的概念指令：

```bash
gcloud compute instances create trend-radar-vm \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --tags=trend-radar-dashboard
```

建立 firewall rule 的概念指令：

```bash
gcloud compute firewall-rules create allow-trend-radar-dashboard \
  --allow=tcp:8000 \
  --direction=INGRESS \
  --source-ranges=YOUR_PUBLIC_IP/32 \
  --target-tags=trend-radar-dashboard
```

SSH 進 VM：

```bash
gcloud compute ssh trend-radar-vm --zone=us-central1-a
```

這些 CLI 指令對應到 Console 中的 VM 設定、network tag、firewall rule 和 SSH。

## 16. 這個學習版部署先不做什麼

為了保持學習焦點，這份教學暫時不做：

- 不設定 HTTPS
- 不買網域
- 不用 Load Balancer
- 不用 Cloud SQL
- 不用 Artifact Registry
- 不用 Kubernetes
- 不做多人登入與權限管理
- 不做 GitHub Actions 自動部署

這些都可以是未來進階題，但目前的學習目標是先看懂一台 VM 如何承載一個 Docker Compose app。
