# SingleFileFolder — 单文件种子自动创建文件夹插件

## 功能简介

自动为 **单文件种子** 创建以电影中文名命名的文件夹，并将视频文件及附属文件（nfo、字幕、海报等）移入其中，同时更新 qBittorrent 种子保存位置，**不影响继续做种**。

### 效果示例

```
下载前：
/downloads/
└── Project.Hail.Mary.2026.1080p.BluRay.x264.mkv

下载后（自动整理）：
/downloads/
└── 挽救计划 (2026)/
    ├── 挽救计划.2026.1080p.BluRay.x264.mkv
    ├── 挽救计划.nfo
    ├── poster.jpg
    └── 挽救计划.zh.srt
```

---

## 使用说明

### 安装方式

#### 方式一：通过 MoviePilot 插件市场安装

1. 打开 MoviePilot → 设置 → 插件 → 插件源
2. 添加自定义插件源：
   ```
   https://raw.githubusercontent.com/Dragon525/MoviePilot-Custom-Plugins/main/package.v2.json
   ```
3. 刷新插件市场，搜索 **"SingleFileFolder"** 安装

#### 方式二：手动安装

将 `plugins.v2/singlefilefolder` 文件夹整体拷贝到 MoviePilot 宿主机的 `app/plugins/` 目录下：

```bash
# Docker 环境示例
docker cp singlefilefolder moviepilot-v2:/moviepilot/app/plugins/

# 或直接映射到 NAS 上的 config/plugins 目录
cp -r singlefilefolder /path/to/MoviePilot/config/plugins/
```

重启 MoviePilot 后在插件管理中启用。

---

### 工作流程

```
添加下载 → 记录种子 Hash → 等待下载完成 → 检测单文件种子
                                                    ↓
                                        ┌───────────┴───────────┐
                                        ↓                       ↓
                                是多文件种子            是单文件种子
                                （跳过不处理）          ↓
                                            识别电影信息（TMDB/豆瓣）
                                                    ↓
                                        ┌───────────┴───────────┐
                                        ↓                       ↓
                                  识别成功                识别失败
                                使用中文标题              回退到种子名/文件名
                                        ↓
                                  创建文件夹 → 移动视频文件 + 附属文件
                                        ↓
                                  更新 qBittorrent 保存位置
                                        ↓
                                  ✅ 完成（记录日志）
```

---

### 配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| **启用插件** | 开关 | 关 | 开启后开始监听和处理 |
| **强制使用中文名** | 开关 | 关 | 开启后，如果识别不到中文标题则跳过该种子（不会回退到种子名） |

---

### 支持的场景

#### ✅ 会处理的场景

| 场景 | 示例 | 结果 |
|------|------|------|
| 单文件 MKV | `/downloads/Movie.2024.1080p.mkv` | 创建文件夹并移入 |
| 单文件 MP4 | `/downloads/Movie.2024.1080p.mp4` | 创建文件夹并移入 |
| 单文件 + 字幕 | `/downloads/Movie.mkv` + `Movie.zh.srt` | 文件和字幕一起移入 |
| 单文件 + nfo/海报 | `/downloads/Movie.mkv` + `Movie.nfo` + `poster.jpg` | 所有附属文件一起移入 |

#### ❌ 不会处理的场景

| 场景 | 原因 |
|------|------|
| 多文件种子（已有文件夹） | 种子内包含多个文件或已有文件夹结构 |
| 文件夹下有多个视频文件 | 判定为多文件种子或已整理 |
| 非视频文件 | 不是 .mp4/.mkv 等视频格式 |
| 目标文件夹已存在 | 避免覆盖已有文件 |
| 路径不存在 | 下载器中的路径已失效 |

---

### 文件夹命名规则

优先级从高到低：

1. **TMDB/豆瓣 中文标题**（如能识别到）
   - 格式：`电影名 (年份)`，例如 `挽救计划 (2026)`
2. **种子名称**（TMDB 识别失败时回退）
   - 例如 `Project Hail Mary 2026`
3. **视频文件名**（去掉扩展名）
   - 例如 `Project.Hail.Mary.2026.1080p`

> 所有名称会自动清理非法字符（`\/:*?"<>|` 等）。

---

### 做种兼容性

插件通过调用 qBittorrent 的 **设置位置（set location）** 功能更新种子的保存路径，因此：

- ✅ 种子可以继续做种，不会中断
- ✅ 做种比例不会丢失
- ✅ 下载器能正确找到文件位置

---

### 日志查看

在 MoviePilot 日志中搜索 `【SingleFileFolder】` 即可查看插件运行日志。

常见日志示例：
```
【SingleFileFolder】插件已启动，监听下载添加与转移完成事件
【SingleFileFolder】记录新下载: hash=abc12345...
【SingleFileFolder】创建文件夹: /downloads/挽救计划 (2026)
【SingleFileFolder】移动文件: Movie.2024.1080p.mkv -> /downloads/挽救计划 (2026)/
【SingleFileFolder】已通知下载器更新种子位置 -> /downloads/挽救计划 (2026)
【SingleFileFolder】✅ 整理完成: Movie.2024.1080p.mkv -> /downloads/挽救计划 (2026)
```

---

## 注意事项

1. **定时轮询**：插件每 30 秒检查一次已完成的下载任务，所以整理操作可能有最多 30 秒的延迟。
2. **首次识别**：如果 TMDB/豆瓣 识别较慢，文件夹命名可能会回退到种子名。可以在详情页查看处理记录确认。
3. **回滚机制**：如果移动文件后更新下载器位置失败，插件会自动将文件移回原位置，确保数据安全。
4. **多下载器**：目前仅适配 qBittorrent，使用 Transmission 的用户可能需要手动调整。

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-05-15 | 初始版本，支持单文件种子自动创建文件夹，优先使用中文标题 |
