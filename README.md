

# Hanime1_-  
一款基于 Python 的 hanime1 批量下载工具 / A Python-based hanime1 batch downloader (99.9% powered by Claude)

---

# 🎬 视频智能下载器

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com)

> 🚀 功能强大的智能视频批量下载工具，支持系列识别、防风控下载、自动重试，配备精美的毛玻璃 UI 界面

---

## ✨ 核心特性

### 🎯 智能识别
- **系列自动识别**：一键批量下载同系列视频  
- **原始标题提取**：自动获取视频原始标题，无需手动重命名  
- **画质智能选择**：自动选择最高画质（1080p > 720p > 480p）  
- **播放列表解析**：区分当前视频与系列视频  

### 🛡️ 防风控设计
- **单线程顺序下载**：避免并发触发风控  
- **自定义下载间隔**：支持 1-30 秒间隔  
- **智能重试机制**：失败自动重试（最多 5 次）  
- **静音爬取**：后台静默运行  

### 💎 界面设计
- **毛玻璃 UI**：现代 glassmorphism 风格  
- **双层进度条**：总进度 & 当前文件进度分离显示  
- **队列可视化**：实时查看下载队列  
- **响应式布局**：自适应不同屏幕尺寸  

### 🔧 高级功能
- **批量操作**：全选 / 取消 / 系列 / 高清  
- **自定义设置**：下载目录 / 重试次数 / 画质优先级  
- **实时统计**：显示总数 / 系列 / 已选 / 高清 / 预计大小  
- **错误恢复**：失败文件记录，支持断点续传  

---

## 📦 安装指南

### 环境要求
- Python 3.8 或更高版本  
- Chrome 浏览器（最新版本）  
- 操作系统：Windows 10/11、macOS 10.15+、Linux  


### 1. 克隆项目
```bash
git clone https://github.com/yourusername/video-downloader.git
cd video-downloader
````

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install flask flask-cors selenium requests
```

### 3. 安装 ChromeDriver

* **Windows**：下载 [ChromeDriver](https://chromedriver.chromium.org/) 并放入 PATH
* **macOS**：

  ```bash
  brew install chromedriver
  ```
* **Linux**：

  ```bash
  sudo apt-get install chromium-chromedriver
  ```

### 4. 安装 FFmpeg（用于 m3u8 视频）

* **Windows**：下载 [FFmpeg](https://ffmpeg.org/download.html)，解压并加入 PATH
* **macOS**：

  ```bash
  brew install ffmpeg
  ```
* **Linux**：

  ```bash
  sudo apt-get update && sudo apt-get install ffmpeg
  ```

---

## 🚀 快速开始

运行程序：

```bash
python hanime1下载器.py
```

启动后程序会：

1. 启动本地服务器（端口 5000）
2. 自动打开默认浏览器
3. 显示下载界面

使用流程：

1. 输入视频 URL（如 `https://hanime1.me/watch?v=xxxxx`）
2. 点击 **🔍 分析视频**
3. 选择视频（全选 / 系列 / 高清 / 手动勾选）
4. 配置下载间隔、重试次数、画质优先级、下载目录
5. 点击 **🚀 开始下载**

---

## ⚙️ 配置说明

| 设置项   | 默认值                 | 范围     | 说明        |
| ----- | ------------------- | ------ | --------- |
| 下载间隔  | 3 秒                 | 1-30 秒 | 防风控延迟时间   |
| 重试次数  | 3 次                 | 0-5 次  | 失败后自动重试次数 |
| 画质优先级 | 最高画质                | -      | 画质选择策略    |
| 下载目录  | \~/Downloads/Videos | -      | 保存路径      |

**画质优先级模式：**

* 最高画质：1080p > 720p > 480p
* 平衡模式：720p > 1080p > 480p
* 最快速度：480p > 360p > 720p

---

## 📝 注意事项

1. **合法使用**：仅限个人学习研究
2. **尊重版权**：禁止商业用途
3. **网络要求**：需稳定网络
4. **风控提醒**：建议设置合理的下载间隔

---

## 🛠️ 故障排除

* **ffmpeg 未安装**：请安装并加入 PATH
* **ChromeDriver 版本不匹配**：请下载与 Chrome 版本对应的驱动
* **下载失败 / 速度慢**：尝试加大间隔、增加重试、切换画质
* **无法访问界面**：检查 5000 端口、防火墙、手动访问 [http://localhost:5000](http://localhost:5000)

---

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

* Issue：请附带日志、环境信息
* PR：Fork → 新建分支 → 修改提交 → 提交 PR

---

## 📄 开源协议

本项目使用 [MIT License](LICENSE)

---

## 👨‍💻 作者

* GitHub: [@W-Ver](https://github.com/W-Ver)

---

## 🙏 致谢

* [Flask](https://flask.palletsprojects.com/)
* [Selenium](https://www.selenium.dev/)
* [FFmpeg](https://ffmpeg.org/)

---

⭐ 如果这个项目对你有帮助，请给一个 Star！

```

---

要不要我再帮你做一个**英文简化版 README**（只保留核心安装 + 使用流程），放在项目里给国际用户？
```
