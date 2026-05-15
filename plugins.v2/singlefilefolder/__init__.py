"""
单文件种子自动创建文件夹插件
MoviePilot v2 Plugin - SingleFileFolder

功能：
- 监听下载添加事件，记录单文件种子信息
- 定时检查已完成的下载任务
- 对单文件种子：自动创建以电影中文名命名的文件夹，将文件移入
- 同步更新 qBittorrent 种子的保存位置，不影响做种
"""

import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType, MediaType, TorrentStatus


class SingleFileFolder(_PluginBase):
    """
    单文件种子自动创建文件夹插件
    """

    # 插件元数据
    plugin_name = "单文件种子自动创建文件夹"
    plugin_desc = "自动为单文件种子创建以电影名命名的文件夹并移入文件，不影响多文件种子"
    plugin_version = "1.0.0"
    plugin_author = "AutoClaw"
    plugin_level = 1
    plugin_icon = "FolderOpen"
    plugin_auth_level = 0
    plugin_order = 0
    plugin_history = {
        "1.0.0": "初始版本，支持单文件种子自动创建文件夹，优先使用中文标题"
    }

    # 视频文件扩展名
    _video_exts = {
        ".mp4", ".mkv", ".avi", ".wmv", ".flv", ".ts",
        ".m2ts", ".iso", ".rmvb", ".mov", ".webm",
        ".mpg", ".mpeg", ".vob",
    }

    def init_plugin(self, config: dict = None):
        self.config = config or {}
        self._enabled = self.config.get("enabled", False)
        self._force_chinese = self.config.get("force_chinese", False)
        # 缓存已添加的下载 hash
        self._processed_hashes: set = set()
        # 处理历史记录
        self._process_history: list = []

        if self._enabled:
            logger.info("【SingleFileFolder】插件已启动，监听下载添加与转移完成事件")

    def get_state(self) -> bool:
        return self._enabled

    def get_service(self) -> List[Dict[str, Any]]:
        """注册定时服务：每 30 秒轮询检查已完成下载"""
        if not self._enabled:
            return []
        return [{
            "id": "SingleFileFolder",
            "name": "单文件文件夹整理",
            "trigger": "interval",
            "func": self._check_completed_downloads,
            "kwargs": {"seconds": 30},
        }]

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_form(self) -> List[dict]:
        """插件配置表单（V2 兼容简化格式）"""
        return [
            {
                "component": "VSwitch",
                "props": {
                    "model": "enabled",
                    "label": "启用插件",
                    "description": "开启后自动监听并处理单文件种子"
                }
            },
            {
                "component": "VSwitch",
                "props": {
                    "model": "force_chinese",
                    "label": "强制使用中文名",
                    "description": "开启后，若识别不到中文标题则跳过该种子"
                }
            },
            {
                "component": "VAlert",
                "props": {
                    "type": "info",
                    "variant": "tonal",
                    "text": "仅处理单文件种子（只有一个视频文件）。自动创建电影名文件夹并移入文件，不影响多文件种子和做种。"
                }
            }
        ]

    def get_page(self) -> List[dict]:
        """插件详情页面 - 展示处理历史"""
        history_items = []
        for item in self._process_history[-20:]:
            icon = "✅" if item.get("success") else "❌"
            history_items.append({
                "component": "VListItem",
                "props": {"density": "compact"},
                "content": [
                    {
                        "component": "VListItemTitle",
                        "content": [
                            {"component": "span", "text": f"{icon} {item.get('time', '')} - {item.get('file', '')}"}
                        ],
                    },
                    {
                        "component": "VListItemSubtitle",
                        "content": [
                            {"component": "span", "text": f"→ {item.get('target', '') or item.get('reason', '')}"}
                        ],
                    },
                ],
            })

        return [
            {
                "component": "VContainer",
                "content": [
                    # 插件信息卡片
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VCard",
                                        "props": {"variant": "tonal"},
                                        "content": [
                                            {
                                                "component": "VCardTitle",
                                                "text": "插件信息",
                                            },
                                            {
                                                "component": "VCardText",
                                                "content": [
                                                    {
                                                        "component": "VRow",
                                                        "content": [
                                                            {
                                                                "component": "VCol",
                                                                "props": {"cols": 12, "md": 6},
                                                                "content": [
                                                                    {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": f"名称：{self.plugin_name}"}]},
                                                                    {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": f"版本：{self.plugin_version}"}]},
                                                                    {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": f"作者：{self.plugin_author}"}]},
                                                                ],
                                                            },
                                                            {
                                                                "component": "VCol",
                                                                "props": {"cols": 12, "md": 6},
                                                                "content": [
                                                                    {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": "轮询间隔：每 30 秒"}]},
                                                                    {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": f"状态：{'运行中' if self._enabled else '已停止'}"}]},
                                                                    {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": f"待处理种子：{len(self._processed_hashes)} 个"}]},
                                                                ],
                                                            },
                                                        ],
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                    # 处理记录卡片
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VCard",
                                        "content": [
                                            {
                                                "component": "VCardTitle",
                                                "text": "处理记录（最近 20 条）",
                                            },
                                            {
                                                "component": "VCardText",
                                                "content": history_items if history_items else [
                                                    {
                                                        "component": "VAlert",
                                                        "props": {"type": "info", "variant": "tonal", "text": "暂无处理记录"},
                                                    }
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                    # 使用说明卡片
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VCard",
                                        "content": [
                                            {
                                                "component": "VCardTitle",
                                                "text": "使用说明",
                                            },
                                            {
                                                "component": "VCardText",
                                                "content": [
                                                    {
                                                        "component": "VList",
                                                        "content": [
                                                            {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": "1️⃣ 插件监听新添加的下载任务，等待下载完成"}]},
                                                            {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": "2️⃣ 每 30 秒轮询检查已完成的下载任务"}]},
                                                            {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": "3️⃣ 仅处理单文件种子（只有一个视频文件）"}]},
                                                            {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": "4️⃣ 自动创建以电影中文名命名的文件夹"}]},
                                                            {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": "5️⃣ 移动视频文件及附属文件（nfo、字幕、海报等）"}]},
                                                            {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": "6️⃣ 自动更新 qBittorrent 种子保存位置，不影响做种"}]},
                                                            {"component": "VListItem", "content": [{"component": "VListItemTitle", "text": "📌 多文件种子（已有文件夹结构）不做处理"}]},
                                                        ],
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ]

    def stop_service(self):
        self._processed_hashes.clear()

    @eventmanager.register(EventType.DownloadAdded)
    def on_download_added(self, event: Event):
        """记录新添加的下载，等待下载完成后处理"""
        if not self._enabled:
            return
        event_data = event.event_data or {}
        download_hash = event_data.get("hash")
        if download_hash:
            self._processed_hashes.add(download_hash)
            logger.debug(f"【SingleFileFolder】记录新下载: hash={download_hash[:8]}...")

    @eventmanager.register(EventType.TransferComplete)
    def on_transfer_complete(self, event: Event):
        """转移完成后也检查一次源目录（兜底）"""
        if not self._enabled:
            return
        event_data = event.event_data or {}
        download_hash = event_data.get("download_hash")
        if download_hash:
            self._processed_hashes.add(download_hash)
        self._check_completed_downloads()

    def _check_completed_downloads(self):
        """定时任务：检查已完成的下载，处理单文件种子"""
        if not self._enabled or not self._processed_hashes:
            return

        try:
            torrents = self.list_torrents(status=TorrentStatus.TRANSFER)
            if not torrents:
                return
        except Exception as e:
            logger.warning(f"【SingleFileFolder】获取下载列表失败: {e}")
            return

        pending = [t for t in torrents if t.hash and t.hash in self._processed_hashes]
        if not pending:
            return

        for torrent in pending:
            try:
                self._process_torrent(torrent)
                self._processed_hashes.discard(torrent.hash)
            except Exception as e:
                logger.error(f"【SingleFileFolder】处理种子 {torrent.hash[:8]} 失败: {e}")

    def _process_torrent(self, torrent):
        """处理单个已完成下载任务"""
        torrent_path: Path = torrent.path
        if not torrent_path or not torrent_path.exists():
            logger.debug(f"【SingleFileFolder】种子路径不存在: {torrent_path}")
            return

        # 判断是否为单文件
        if torrent_path.is_file():
            if torrent_path.suffix.lower() not in self._video_exts:
                return
            video_file = torrent_path
            parent_dir = video_file.parent
        elif torrent_path.is_dir():
            video_files = [
                f for f in torrent_path.iterdir()
                if f.is_file() and f.suffix.lower() in self._video_exts
            ]
            if len(video_files) != 1:
                logger.debug(
                    f"【SingleFileFolder】{torrent_path.name} 下有 {len(video_files)} 个视频文件，跳过"
                )
                return
            video_file = video_files[0]
            parent_dir = torrent_path
            if self._is_already_organized(parent_dir, video_file):
                return
        else:
            return

        # 获取文件夹名称
        folder_name = self._get_folder_name(torrent, video_file)
        if not folder_name:
            logger.warning(f"【SingleFileFolder】无法确定文件夹名称，跳过: {video_file.name}")
            return

        target_folder = parent_dir / folder_name
        if target_folder.exists():
            logger.info(f"【SingleFileFolder】目标文件夹已存在: {target_folder}，跳过")
            return

        # 创建文件夹并移动文件
        try:
            target_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"【SingleFileFolder】创建文件夹: {target_folder}")

            new_path = target_folder / video_file.name
            shutil.move(str(video_file), str(new_path))
            logger.info(f"【SingleFileFolder】移动文件: {video_file.name} -> {target_folder}/")

            # 移动配套附属文件
            for sibling in parent_dir.iterdir():
                if sibling == video_file or sibling == target_folder:
                    continue
                if sibling.suffix.lower() in {
                    ".nfo", ".jpg", ".png", ".jpeg", ".srt", ".ass",
                    ".ssa", ".sub", ".idx", ".txt", ".smi", ".vtt",
                }:
                    try:
                        shutil.move(str(sibling), str(target_folder / sibling.name))
                    except Exception as e:
                        logger.warning(f"【SingleFileFolder】移动附属文件失败 {sibling.name}: {e}")

            # 更新下载器保存位置
            self._update_download_location(torrent.hash, str(target_folder))

            logger.info(f"【SingleFileFolder】✅ 整理完成: {video_file.name} -> {target_folder}")

            # 记录处理历史
            self._process_history.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file": video_file.name,
                "target": str(target_folder),
                "success": True,
            })

        except Exception as e:
            logger.error(f"【SingleFileFolder】处理文件失败: {e}")
            if target_folder.exists() and not video_file.exists():
                try:
                    shutil.move(str(target_folder / video_file.name), str(video_file))
                    shutil.rmtree(target_folder, ignore_errors=True)
                    logger.warning(f"【SingleFileFolder】已回滚移动操作")
                except Exception as rb:
                    logger.error(f"【SingleFileFolder】回滚失败: {rb}")

    def _get_folder_name(self, torrent, video_file: Path) -> Optional[str]:
        """获取文件夹名称，优先使用中文标题"""
        download_hash = getattr(torrent, "hash", None)
        if download_hash:
            downloadhis = self.downloadhis.get_by_hash(download_hash)
            if downloadhis:
                try:
                    mtype = MediaType(downloadhis.type)
                except (ValueError, AttributeError):
                    mtype = MediaType.MOVIE

                mediainfo = self.recognize_media(
                    mtype=mtype,
                    tmdbid=downloadhis.tmdbid,
                    doubanid=downloadhis.doubanid,
                )
                if mediainfo:
                    title = mediainfo.get("title") or mediainfo.title
                    year = mediainfo.get("year") or mediainfo.year
                    if title:
                        folder_name = f"{title} ({year})" if year else title
                        return self._clean_name(folder_name)
                    elif self._force_chinese:
                        return None

        # 回退：使用种子名称
        torrent_title = getattr(torrent, "title", None)
        if torrent_title:
            return self._clean_name(torrent_title)

        # 最后回退：使用视频文件名（去掉扩展名）
        return self._clean_name(video_file.stem)

    def _update_download_location(self, torrent_hash: str, new_path: str):
        """通知下载器更新种子保存位置"""
        try:
            self.run_module("set_torrents_save_path", hashs=[torrent_hash], save_path=new_path)
            logger.info(f"【SingleFileFolder】已通知下载器更新种子位置 -> {new_path}")
        except Exception as e:
            logger.warning(f"【SingleFileFolder】更新下载器位置失败: {e}")

    @staticmethod
    def _is_already_organized(parent_dir: Path, video_file: Path) -> bool:
        """判断目录是否已经是合理的整理结构"""
        dir_name = parent_dir.name.lower()
        file_stem = video_file.stem.lower()
        return dir_name in file_stem or file_stem in dir_name

    @staticmethod
    def _clean_name(name: str) -> str:
        """清理文件夹名称，移除非法字符"""
        name = re.sub(r'[\\/*?:"<>|\n\r\t]', "", name)
        name = name.strip(". ")
        if len(name) > 200:
            name = name[:200]
        return name or "Unknown"
