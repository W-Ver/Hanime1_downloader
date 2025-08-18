# Hanime1_-
一款基于Python的由Claude辅助了999%的hanime1批量下载工具/A Python-based hanime1 batch downloader, 99.9% powered by Claude.
```markdown
# 视频智能下载器 🎬

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com)

> 🚀 一款功能强大的智能视频批量下载工具，支持系列识别、防风控下载、自动重试，配备精美的毛玻璃UI界面

## ✨ 核心特性

### 🎯 智能识别
- **系列自动识别** - 智能识别同系列视频，一键批量下载
- **原始标题提取** - 自动获取视频原始标题，无需手动重命名
- **画质智能选择** - 自动选择最高画质（1080p > 720p > 480p）
- **播放列表解析** - 自动解析播放列表，区分当前/系列视频

### 🛡️ 防风控设计
- **单线程顺序下载** - 避免并发请求触发风控
- **自定义下载间隔** - 支持1-30秒间隔设置
- **智能重试机制** - 失败自动重试，最多5次
- **静音爬取** - 后台静默运行，无声音干扰

### 💎 界面设计
- **毛玻璃UI** - 现代化glassmorphism设计风格
- **双层进度条** - 总进度和当前文件进度分离显示
- **队列可视化** - 实时查看下载队列状态
- **响应式布局** - 自适应不同屏幕尺寸

### 🔧 高级功能
- **批量操作** - 全选/取消/选择系列/选择高清
- **自定义设置** - 下载目录/重试次数/画质优先级
- **实时统计** - 显示总数/系列/已选/高清/预计大小
- **错误恢复** - 失败文件记录，支持断点续传

## 📦 安装指南

### 环境要求
- Python 3.8 或更高版本
- Chrome 浏览器（最新版本）
- 操作系统：Windows 10/11、macOS 10.15+、Linux

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/video-downloader.git
cd video-downloader
```

### 2. 安装Python依赖
```bash
pip install -r requirements.txt
```

或手动安装：
```bash
pip install flask flask-cors selenium requests
```

### 3. 安装ChromeDriver

#### Windows
1. 下载 [ChromeDriver](https://chromedriver.chromium.org/)
2. 解压到系统PATH目录或项目目录

#### macOS
```bash
brew install chromedriver
```

#### Linux
```bash
sudo apt-get install chromium-chromedriver
```

### 4. 安装FFmpeg（用于m3u8视频）

#### Windows
1. 下载 [FFmpeg](https://ffmpeg.org/download.html)
2. 解压并添加到系统PATH

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

## 🚀 快速开始

### 运行程序
```bash
python 本体.py
```

程序会自动：
1. 启动本地服务器（端口5000）
2. 打开默认浏览器
3. 显示下载界面

### 使用流程

#### 1️⃣ 输入视频URL
在输入框中粘贴视频链接，格式：`https://hanime1.me/watch?v=xxxxx`

#### 2️⃣ 分析视频
点击"🔍 分析视频"按钮，等待系统分析

#### 3️⃣ 选择视频
- **全选** - 选择所有视频
- **选择系列** - 只选择同系列视频
- **选择高清** - 只选择1080p视频
- **手动勾选** - 点击单个视频选择

#### 4️⃣ 配置设置
- **下载间隔** - 防风控延迟（建议3-5秒）
- **重试次数** - 失败重试次数（建议3次）
- **画质优先级** - 最高画质/平衡/最快速度
- **下载目录** - 点击"📁 更改"选择保存位置

#### 5️⃣ 开始下载
点击"🚀 开始下载"，查看实时进度

## 📊 界面说明

### 主界面
```
┌─────────────────────────────────────┐
│         🎬 视频下载器 Pro           │
│   单线程防风控 · 智能重试 · 毛玻璃界面  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  [输入URL]           [🔍 分析视频]   │
│                                     │
│  ⚙️ 设置面板                        │
│  ├─ 下载间隔: [3] 秒               │
│  ├─ 画质优先级: [最高画质优先 ▼]    │
│  ├─ 下载目录: [~/Downloads/Videos]  │
│  └─ 失败重试: [3] 次               │
└─────────────────────────────────────┘
```

### 视频列表
```
┌─────────────────────────────────────┐
│  📊 视频分析结果                     │
│                                     │
│  统计: 总数[5] 系列[3] 已选[3]      │
│        高清[2] 预计[2.3GB]          │
│                                     │
│  [✅全选] [📂系列] [🎬高清] [🚀下载] │
│                                     │
│  ☑ 视频1 [当前][系列][HD] 1080p    │
│  ☑ 视频2 [系列] 720p               │
│  ☐ 视频3 480p                      │
└─────────────────────────────────────┘
```

### 下载进度
```
┌─────────────────────────────────────┐
│  📥 下载进度                         │
│                                     │
│  总进度                             │
│  [████████████░░░░] 60%            │
│  3/5  ⏳下载中  剩余: 02:35        │
│                                     │
│  当前文件: video_name.mp4           │
│  [██████░░░░░░░░] 35%              │
│  速度: 2.5MB/s  150/430MB  重试:0/3 │
│                                     │
│  📋 下载队列                        │
│  ✅ 视频1 - 完成                   │
│  ✅ 视频2 - 完成                   │
│  📥 视频3 - 下载中...              │
│  ⏳ 视频4 - 等待                   │
│  ⏳ 视频5 - 等待                   │
└─────────────────────────────────────┘
```

## ⚙️ 配置说明

### 下载设置
| 设置项 | 默认值 | 范围 | 说明 |
|-------|--------|------|------|
| 下载间隔 | 3秒 | 1-30秒 | 防风控延迟时间 |
| 重试次数 | 3次 | 0-5次 | 失败后重试次数 |
| 画质优先级 | 最高画质 | - | 优先下载的画质 |
| 下载目录 | ~/Downloads/Videos | - | 视频保存位置 |

### 画质优先级说明
- **最高画质优先** - 1080p > 720p > 480p > 360p > 240p
- **平衡模式** - 720p > 1080p > 480p > 360p > 240p
- **最快速度** - 480p > 360p > 720p > 240p > 1080p

## 🔧 高级配置

### 修改默认端口
编辑 `本体.py` 最后一行：
```python
app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
```

### 修改默认下载目录
编辑 `本体.py` 中的默认设置：
```python
download_settings = {
    'download_dir': str(Path.home() / 'Downloads' / 'Videos'),
    # ...
}
```

### 添加代理支持
在 `get_chrome_driver()` 函数中添加：
```python
chrome_options.add_argument('--proxy-server=http://your-proxy:port')
```

## 📝 注意事项

### ⚠️ 使用须知
1. **合法使用** - 请遵守相关法律法规，仅用于个人学习研究
2. **尊重版权** - 下载的内容请勿用于商业用途
3. **网络要求** - 需要稳定的网络连接
4. **风控限制** - 建议设置合理的下载间隔

### 🐛 常见问题

#### Q: 提示"ffmpeg未安装"
A: 请按照安装指南安装ffmpeg，并确保添加到系统PATH

#### Q: 提示"ChromeDriver版本不匹配"
A: 下载与Chrome浏览器版本对应的ChromeDriver

#### Q: 下载失败或速度慢
A: 
- 增加下载间隔时间
- 增加重试次数
- 检查网络连接
- 尝试更换画质

#### Q: 无法打开网页界面
A: 
- 检查5000端口是否被占用
- 手动访问 http://localhost:5000
- 检查防火墙设置

## 🛠️ 故障排除

### 查看日志
程序运行时会在控制台输出详细日志：
```
[分析] 访问: https://...
[分析] 找到 5 个视频
[下载] 开始顺序下载，间隔 3 秒
[1/5] 处理: 视频名称
[成功] 下载完成: video.mp4
```

### 调试模式
修改启动参数开启调试：
```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

## 📈 性能优化

### 内存优化
- 使用无头浏览器模式
- 禁用图片加载
- 及时关闭浏览器实例

### 下载优化
- 使用Session保持连接
- 合理设置chunk_size
- 支持断点续传

### 并发限制
- 单线程顺序下载
- 自定义下载间隔
- 智能重试机制

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 提交Issue
- 描述问题的详细信息
- 提供错误日志
- 说明操作系统和Python版本

### 提交PR
1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

## 📄 开源协议

本项目采用 MIT 协议 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👨‍💻 作者

- GitHub: [@yourusername](https://github.com/yourusername)

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Selenium](https://www.selenium.dev/) - 自动化测试工具
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理工具

## 📊 项目状态

![Stars](https://img.shields.io/github/stars/yourusername/video-downloader)
![Forks](https://img.shields.io/github/forks/yourusername/video-downloader)
![Issues](https://img.shields.io/github/issues/yourusername/video-downloader)

---

⭐ 如果这个项目对你有帮助，请给一个Star支持一下！
```
