
---

# Hanime1 CLI · 交互式多线程高颜值版（V2）

> 一个基于 Python 的 hanime1 批量下载器：**交互式菜单 / 多线程 / 高颜值终端 UI / 原名抓取强化 / 懒加载全量抓取 / 智能冲突处理**。
> 仅用于学习研究，请遵守目标站点 ToS 及当地法律法规。

## ✨ 亮点特性（V2 新增）

* **一键交互菜单**：先列出**所有操作选项**（解析、下载当前/同系列/整列、读取 plan.json、设置、退出），支持**一行速用**：`4 https://hanime1.me/watch?v=123456`
* **多线程下载**：并行任务 + 错峰提交 + 可调延迟；配合**智能重试**，更稳更快
* **全量链接抓取**：**先把播放列表所有 `watch?v=xxxxx` 链接抓全**（滚动触发懒加载），再逐个进入**按原名**下载
* **标题统一**：标题一律从 `#shareBtn-title` 中取“原名”；解析失败再降级到 `og:title / <title>`
* **系列名/同系列识别**：自动标记同系列，支持只下同系列或整列
* **文件冲突友好**：同名文件**询问跳过/覆盖**；**10s 无操作默认跳过**；**跳过后自动继续下一个**
* **高颜值 CLI**：基于 `rich` 的全局/文件双进度，转速、ETA、速度、漂亮的表格/面板
* **Selenium 4 适配**：不再使用 `desired_capabilities`；统一用 `options.set_capability(...)`
* **抗风控**：自定义延迟、错峰、线程；请求头/UA/无头浏览器；（可选）解析阶段加载图片
* **传统子命令仍可用**：`analyze` / `download`，方便脚本化或与计划文件联动

> 参考与承袭自 V1 项目（MIT）：W-Ver/Hanime1\_downloader。([GitHub][1])

---

## 目录

* [安装](#安装)
* [快速开始](#快速开始)
* [交互式菜单](#交互式菜单)
* [一行速用](#一行速用)
* [传统 CLI 子命令](#传统-cli-子命令)
* [设置项](#设置项)
* [命名与抓取策略](#命名与抓取策略)
* [文件冲突策略](#文件冲突策略)
* [故障排除](#故障排除)
* [与 V1 的差异](#与-v1-的差异)
* [Roadmap](#roadmap)
* [许可 & 致谢](#许可--致谢)

---

## 安装

**环境需求**

* Python 3.8+
* **Chrome** 与匹配版本 **ChromeDriver**（加入 PATH）
* （推荐）`ffmpeg`：更稳地处理 `.m3u8` 下载
* 依赖：`requests`、`selenium`、（可选）`rich`

**安装命令**

```bash
pip install -U requests selenium rich
# 可选：安装 ffmpeg（Windows 请到官网下载解压后加入 PATH）
```

> V1 中也依赖 Chrome/ChromeDriver 与 ffmpeg，保持一致。([GitHub][1])

---

## 快速开始

```bash
# 方式一：进入交互菜单（推荐）
python hanime1_cli_交互式多线程高颜值版.py

# 方式二：一行速用（无需进入菜单）
python hanime1_cli_交互式多线程高颜值版.py 4 https://hanime1.me/watch?v=123456

# 方式三：传统子命令
python hanime1_cli_交互式多线程高颜值版.py analyze "https://hanime1.me/watch?v=123456" --json
python hanime1_cli_交互式多线程高颜值版.py download --url "https://hanime1.me/watch?v=123456" --all --threads 3
```

---

## 交互式菜单

运行后会显示一个表格菜单（`rich` 样式）。**你可以输入编号**，或**直接一行速用**（编号+链接/文件路径）：

* 1 解析页面（仅查看）：展示标题/系列/画质；可**保存 plan.json**
* 2 下载当前视频
* 3 下载同系列
* 4 下载播放列表全部（**先抓全量链接，再逐个按原名下载**）
* 5 使用计划文件下载（读取 `plan.json`）
* 6 设置选项（目录/重试/延迟/错峰/线程/画质/headless/解析图片/标题策略）
* 7 退出

---

## 一行速用

```bash
# 下载播放列表全部
python hanime1_cli_交互式多线程高颜值版.py 4 https://hanime1.me/watch?v=97494

# 用计划文件下载
python hanime1_cli_交互式多线程高颜值版.py 5 D:\plan.json
```

---

## 传统 CLI 子命令

**analyze**

```bash
python ... analyze "https://hanime1.me/watch?v=123456" --json --save-plan plan.json
```

**download**

```bash
# 下载整列
python ... download --url "https://hanime1.me/watch?v=123456" --all --threads 3 --retry 3 --delay 2

# 仅同系列
python ... download --url "..." --series-only

# 指定编号（来自 analyze 的顺序）
python ... download --url "..." --ids "1,3,5"

# 从 plan.json 下载
python ... download --plan plan.json --all
```

**全局参数（节选）**

* `--threads` 并发线程数（默认 3）
* `--stagger` 任务错峰（默认 0.8 秒）
* `--priority` 画质策略：`highest` / `balanced` / `fastest`
* `--title-mode` 标题策略：`original`（默认）/ `as_shown`
* `--headless` / `--no-headless` 启/禁无头
* `--parse-images` / `--no-parse-images` 解析阶段启/禁图片加载

---

## 设置项

在菜单 6 中可交互修改并立即生效：

* 下载目录、失败重试、同线程延迟、任务错峰、并发线程
* 画质优先级（最高/平衡/最快）
* **标题策略**（`original` 优先从 `#shareBtn-title`、`og:title`、`<title>` 原名抓取；`as_shown` 使用卡片显示名）
* 无头模式、解析阶段加载图片

---

## 命名与抓取策略

* **标题来源统一**：优先从页面

  ```html
  <h3 id="shareBtn-title" class="video-details-wrapper">原名</h3>
  ```

  获取**原名**；失败则回退到 `og:title` 或 `<title>` 去尾部站点名
* **播放列表策略**：先滚动列表容器触发懒加载，**把所有 `watch?v=xxxxx` 链接抓全**；然后逐个页**重新解析原名**并下载（避免混入翻译后的卡片名）
* **同系列识别**：基于原名提取“系列名”进行标记与过滤

---

## 文件冲突策略

* 若目标目录存在同名文件：弹出**覆盖/跳过**选择
* **10 秒**内无应答默认**跳过**
* **跳过后自动继续下一个**任务（不会回主菜单中断）

---

## 故障排除

* **`net_error -100` / 证书握手失败**：已启用 `acceptInsecureCerts`、忽略证书参数；若网络波动，可**降低线程**、**增大延迟/错峰**重试
* **Selenium 报 `WebDriver.__init__() ... desired_capabilities`**：V2 已用 **Selenium 4** 的 `options.set_capability(...)` 适配
* **Rich 进度条 `unsupported format string passed to NoneType.__format__`**：V2 已改为对未知 total 使用通用占位，不做数值格式化
* **GPU/WebGL 警告**：已默认 `--disable-gpu`；必要时可在本地自行追加 `--enable-unsafe-swiftshader`
* **`ffmpeg` 未找到**：请安装并加入 `PATH`（V1 也使用 ffmpeg 处理 m3u8）([GitHub][1])
* **ChromeDriver 版本不匹配**：请更新与本机 Chrome 一致的版本（V1 README 同样提示）([GitHub][1])

---

## 与 V1 的差异

对比 \[W-Ver/Hanime1\_downloader（V1）]（功能：系列识别、原名提取、画质优先、批量操作、进度 UI、依赖 ChromeDriver 与 ffmpeg 等）([GitHub][1])，V2 主要变化：

* ✅ 交互式菜单 + 一行速用
* ✅ **多线程** + 错峰 + 延迟 + 智能重试
* ✅ \*\*统一“原名”\*\*抓取（`#shareBtn-title` → `og:title` → `<title>`）
* ✅ **先抓全量链接**→再逐个按原名下载（避免标题语言不一致）
* ✅ **文件冲突** 10s 默认跳过 + 连续下载不中断
* ✅ 修复 Selenium 4 兼容问题与 Rich 进度条格式化异常
* ✅ 更加美观的 `rich` 终端 UI

---

## Roadmap

* [ ] 失败任务自动回收与重试队列
* [ ] 断点续传更精细的 `.mp4` 直传（`Range`/校验）
* [ ] 站内更多页面结构兼容（移动端/镜像）
* [ ] 任务导出/导入（CSV/JSON 多格式）

---

## 许可 & 致谢

* **License**：MIT
* **V1 项目**：W-Ver / Hanime1\_downloader（MIT）— 作为本项目的最初来源与灵感。([GitHub][1])

感谢这些优秀项目/工具：Selenium、FFmpeg、Rich……以及 V1 的思路与脚手架。([GitHub][1])

---

### 附：典型命令速查

```bash
# 解析并保存计划
python ... analyze "https://hanime1.me/watch?v=123456" --save-plan plan.json

# 下载整列（多线程）
python ... download --url "https://hanime1.me/watch?v=123456" --all --threads 3 --retry 3 --delay 2

# 仅下载同系列（按“原名”识别）
python ... download --url "..." --series-only

# 从计划文件挑选编号下载
python ... download --plan plan.json --ids "1,3,5"
```

---


[1]: https://github.com/W-Ver/Hanime1_downloader "GitHub - W-Ver/Hanime1_downloader: 一款基于Python的由Claude辅助了999%的hanime1批量下载工具/A Python-based hanime1 batch downloader, 99.9% powered by Claude."
