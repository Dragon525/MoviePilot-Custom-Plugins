# MoviePilot 自定义插件仓库

> 为 MoviePilot v2 提供的自定义插件集合

## 插件列表

| 插件 | 版本 | 说明 |
|------|------|------|
| [SingleFileFolder](./plugins.v2/singlefilefolder/) | 1.0.0 | 单文件种子自动创建文件夹，下载完成后为单文件种子创建以电影名命名的文件夹 |

---

## 使用方法

### 1. 添加插件源

打开 MoviePilot → **设置 → 插件 → 插件源**，添加以下 URL：

```
https://raw.githubusercontent.com/Dragon525/MoviePilot-Custom-Plugins/main/package.v2.json
```

### 2. 安装插件

刷新插件市场，搜索 **"SingleFileFolder"** 即可看到并安装。

### 3. 启用插件

安装完成后，在插件管理中启用插件并根据需要调整配置选项。

---

## 插件详情

### SingleFileFolder — 单文件种子自动创建文件夹

#### 功能

自动为 **单文件种子** 创建以电影中文名命名的文件夹，将视频文件及附属文件（nfo、字幕、海报等）移入其中，同时更新 qBittorrent 种子保存位置，**不影响继续做种**。

#### 效果示例

```
下载前：
/downloads/
└── Project.Hail.Mary.2026.1080p.BluRay.x264.mkv

下载后：
/downloads/
└── 挽救计划 (2026)/
    ├── 挽救计划.2026.1080p.BluRay.x264.mkv
    ├── 挽救计划.nfo
    ├── poster.jpg
    └── 挽救计划.zh.srt
```

#### 特性

- ✅ 优先使用 TMDB/豆瓣 中文标题命名文件夹
- ✅ 自动移动视频文件 + 附属文件（nfo、字幕、海报等）
- ✅ 自动更新下载器保存位置，不影响做种
- ✅ 失败自动回滚，确保数据安全
- ✅ 仅处理单文件种子，多文件种子自动跳过
- ✅ 详细的处理记录日志

[查看详细文档 →](./plugins.v2/singlefilefolder/README.md)

---

## 目录结构

```
.
├── README.md                     # 仓库说明
├── package.v2.json               # V2 插件索引
└── plugins.v2/
    └── singlefilefolder/
        ├── __init__.py           # 插件主代码
        └── README.md             # 插件使用文档
```

---

## 更新插件

如果本地安装了新版本，推送到 GitHub 即可：

```bash
cd MP-Plugins
git add -A
git commit -m "更新 SingleFileFolder 到 vX.X.X"
git push upstream main
```

> 由于网络问题导致 HTTPS 推送失败时，可以使用 GitHub API 上传。

---

## 许可证

MIT License
