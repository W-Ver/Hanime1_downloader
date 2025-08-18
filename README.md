# 🎬 Hanime1 Downloader

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com)

> 🚀 一个 **基于 Python 的 hanime1 批量下载工具**，支持系列识别、防风控下载、自动重试，配备毛玻璃风格 UI。  
> A **Python-based hanime1 batch downloader**, featuring series recognition, anti-blocking, auto-retry, and glassmorphism UI.  
> (99.9% powered by Claude 🤖)

---

## 🌟 背景 / Background

煮波在下载 hanime1 视频时觉得手动操作太麻烦，  
翻遍 GitHub 发现同类项目基本都失效了，  
于是决定借助 AI 的力量写了这个下载器。  
<img width="3072" height="1601" alt="image" src="https://github.com/user-attachments/assets/1e6e6846-3378-4501-8aee-387ffb868fbd" />
虽然工具很简陋，但能用就行 ✔️。  
You just need to install dependencies and run the Python script.

---

## ✨ 功能特性 / Features

### 🎯 智能识别
- **系列自动识别**：一键下载同系列视频  
- **原始标题提取**：自动获取视频原名  
- **画质优先选择**：自动选择最高可用画质（1080p > 720p > 480p）  
- **播放列表解析**：支持区分当前视频与系列视频  

### 🛡️ 防风控设计
- **单线程顺序下载**：降低触发风险  
- **自定义间隔**：支持 1-30 秒间隔设置  
- **智能重试**：失败自动重试（最多 5 次）  
- **静默模式**：后台静音运行  

### 💎 界面设计
- **毛玻璃 UI**：现代 glassmorphism 风格  
- **双层进度条**：总进度 + 文件进度分离显示  
- **实时队列**：直观查看任务列表  
- **响应式布局**：适配不同分辨率  

### 🔧 高级功能
- **批量操作**：全选 / 取消 / 系列 / 高清  
- **自定义配置**：目录 / 重试次数 / 画质策略  
- **实时统计**：数量 / 系列 / 高清 / 预计大小  
- **错误恢复**：支持断点续传、失败记录  

---

## 📦 安装指南 / Installation

### 环境需求
- Python 3.8+  
- Chrome 浏览器（最新版）  
- 操作系统：Windows / macOS / Linux  

### 步骤
1. 克隆项目
```bash
git clone https://github.com/W-Ver/Hanime1_downloader.git
cd Hanime1_downloader
````

2. 安装依赖

```bash
pip install flask flask-cors selenium requests
```

3. 安装 ChromeDriver

   * [下载地址](https://chromedriver.chromium.org/) 并放入 PATH
   * macOS: `brew install chromedriver`
   * Linux: `sudo apt-get install chromium-chromedriver`

4. 安装 FFmpeg（处理 m3u8 视频）

   * Windows: [FFmpeg 官网](https://ffmpeg.org/download.html)，解压并加入 PATH
   * macOS: `brew install ffmpeg`
   * Linux: `sudo apt-get install ffmpeg`

---

## 🚀 使用方法 / Quick Start

运行程序：

```bash
python hanime1下载器.py
```

程序会：

1. 启动本地服务器（端口 5000）
2. 自动打开浏览器
3. 显示下载界面

使用流程：

1. 输入视频链接 (`https://hanime1.me/watch?v=xxxxx`)
2. 点击 **🔍 分析视频**
3. 选择视频（全选 / 系列 / 高清 / 手动勾选）
4. 配置下载参数
5. 点击 **🚀 开始下载**

---

## ⚙️ 配置说明 / Settings

| 设置项   | 默认值                 | 范围     | 说明      |
| ----- | ------------------- | ------ | ------- |
| 下载间隔  | 3 秒                 | 1-30 秒 | 防风控延迟时间 |
| 重试次数  | 3 次                 | 0-5 次  | 自动重试次数  |
| 画质优先级 | 最高画质                | -      | 下载画质策略  |
| 下载目录  | \~/Downloads/Videos | -      | 文件保存路径  |

画质策略：

* **最高画质**：1080p > 720p > 480p
* **平衡模式**：720p > 1080p > 480p
* **最快速度**：480p > 360p > 720p

---

## 📝 注意事项 / Notes

1. **仅供学习研究**，请合法使用
2. **禁止商业用途**，尊重版权
3. **网络需稳定**，否则易中断
4. **建议设置合理间隔**，避免触发风控

---

## 🛠️ 故障排除 / Troubleshooting

* **ffmpeg 未安装**：确认已加入 PATH
* **ChromeDriver 版本不匹配**：请更新到对应版本
* **速度慢或失败**：增大间隔，切换画质
* **无法访问界面**：检查端口 5000 或防火墙设置，手动访问 [http://localhost:5000](http://localhost:5000)

---

## 🤝 贡献 / Contributing

欢迎提交 Issue & PR！

* 提交 Issue 时请附带日志、环境信息
* PR 流程：Fork → 新建分支 → 修改 → 提交

---

## 📄 开源协议 / License

本项目基于 [MIT License](LICENSE) 开源。

---

## 👨‍💻 作者 / Author

* GitHub: [@W-Ver](https://github.com/W-Ver)

---

## 🙏 致谢 / Thanks

* [Flask](https://flask.palletsprojects.com/)
* [Selenium](https://www.selenium.dev/)
* [FFmpeg](https://ffmpeg.org/)

---

⭐ 如果这个项目对你有帮助，别忘了点个 Star！
