# WangVer H-Downloader

专为 **hanime1.me** 定制的自动化视频下载工具。通过真实浏览器配合半人工过 Cloudflare，再用多线程引擎下载，支持单集、批量与**同作者/同播放列表**一键抓取。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| **智能链接解析** | 单集 / 批量 .txt / 列表页 URL，自动提取直链（mp4/m3u8）与标题，支持 360p～1080p 画质选择 |
| **CF 半自动绕过** | Playwright 真实浏览器、持久化用户数据；遇 CF 时挂起并提示手动验证，通过后自动提取 Cookies/UA 给下载引擎 |
| **同列表精准解析** | 列表页仅解析「当前播放列表」内视频（`#video-playlist-wrapper` 内 overlay 链接），不混入推荐/其他作者 |
| **多任务与分块下载** | 可配置最大并行任务数、单任务分块数，下载默认走系统/环境代理 |
| **断点续传** | 使用 `.part` 临时文件，中断后可从断点继续 |
| **文件名清洗** | 自动去掉标题中的站点水印（如「H動漫裏番線上看」「Hanime1.me」），并剔除非法字符，便于媒体库刮削 |

---

## 环境要求

- **Python** 3.10+
- **Chrome 或 Chromium**（Playwright 会优先使用系统 Chrome）

---

## 安装

```bash
cd "WangVer H-Downloader"
pip install -r requirements.txt
playwright install chromium
```

---

## 使用方式

### 交互式主菜单（推荐）

无参数运行即可进入主菜单：

```bash
python run.py
# 或
python -m wangver_h_downloader.cli
```

| 选项 | 说明 |
|------|------|
| **1** | 单链接下载 — 输入一集视频页 URL |
| **2** | 批量下载 — 输入 .txt 路径（每行一个 URL） |
| **3** | 列表页下载 — 输入任意视频页 URL，自动抓取**该页右侧播放列表**内全部视频 |
| **4** | 设置 — 输出目录、最大并行数、分块线程数、画质（360p/480p/720p/1080p） |
| **0** | 退出 |

列表页下载说明：若输入的是单集链接（如 `https://hanime1.me/watch?v=xxx`），会解析该页**右侧同一作者/同一播放列表**中的视频并批量下载，不会混入「更多推荐」等其它列表。

### 命令行直连

```bash
# 单集
python -m wangver_h_downloader.cli "https://hanime1.me/watch?v=xxx" -o ./downloads

# 批量（.txt 每行一个链接）
python -m wangver_h_downloader.cli -b urls.txt -o ./downloads

# 列表页（同主菜单逻辑：解析当前页播放列表）
python -m wangver_h_downloader.cli "https://hanime1.me/watch?v=xxx" -o ./downloads
```

### 常用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output` | 下载输出目录 | `./downloads` |
| `--max-tasks` | 最大并行下载任务数 | 3 |
| `--chunk-threads` | 单任务分块并发数 | 8 |
| `--quality` | 优先画质 | 1080p |
| `--user-data-dir` | 浏览器用户数据目录（持久化 Cookie） | `./browser_user_data` |
| `--headless` | 无头模式（不推荐，CF 易拦截） | 关 |
| `--no-ui` | 无 URL 时仅显示帮助、不进入菜单 | 关 |

---

## 首次使用与 CF 验证

1. 首次运行会弹出**带界面的浏览器**；若出现 Cloudflare 验证页，终端会提示：
   - **「触发 Cloudflare 拦截，请在弹出的浏览器窗口中手动完成验证！」**
2. 在浏览器中完成验证后，回到终端按 **Enter** 继续。
3. 验证通过后，Cookies 会保存到 `--user-data-dir`，后续同站访问可减少重复验证。

---

## 代理与下载

- 下载请求**默认使用系统/环境代理**（`trust_env=True`），会读取 `HTTP_PROXY` / `HTTPS_PROXY` 及系统代理设置。
- 若下载无速度，可检查代理是否生效；也可在设置中适当调高「单任务分块线程数」或调低以适配代理限速。

---

## 输出与断点续传

- 文件先写入 `{标题}.mp4.part`（或 `.m3u8.part`），完成后自动重命名为 `{标题}.mp4`。
- 标题会**自动去掉**站点水印（如「 - H動漫裏番線上看 - Hanime1.me」），仅保留视频名。
- 中断后再次下载同一视频时，会识别已有 `.part` 并从断点续传。

---

## 项目结构

```
WangVer H-Downloader/
├── .gitignore         # 忽略 downloads/、browser_user_data/、*.part、__pycache__ 等
├── requirements.txt
├── run.py
├── README.md
└── wangver_h_downloader/
    ├── __init__.py
    ├── config.py          # 输出目录、并发、画质、CF 特征等
    ├── parser.py          # 链接解析、直链提取、标题/水印清洗、播放列表提取
    ├── browser_cf.py      # 浏览器启动、CF 检测与挂起、凭证提取
    ├── downloader.py      # 分块并发下载、断点续传（直链做 html.unescape）
    ├── file_manager.py    # 文件名清洗、.part 查找
    ├── ui_theme.py        # 界面主题常量
    └── cli.py             # Rich 交互式菜单、进度条、结果表格
```

---

## 扩展说明（PRD 预留）

- **Telegram 通知**：在 `browser_cf.py` 的 `on_cf_triggered` 中可接入 Telegram Bot，便于 VPS 上通过 VNC/RDP 完成验证。
- **aria2 RPC**：可在 `downloader.py` 中增加 aria2c RPC，沿用浏览器提供的 Cookies/UA 做下载。

---

## 免责声明

本工具仅供学习与个人备份使用，请遵守目标站点服务条款与当地法律法规。
