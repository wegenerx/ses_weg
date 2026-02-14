from __future__ import annotations

import os
from pathlib import Path

import nonebot
from nonebot import get_plugin_config, on_command
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="command_007_show_num",
    description="展示手牌库数量",
    usage="\\show 或 /show - 查看当前手牌数量",
    config=Config,
)

config = get_plugin_config(Config)

show_cmd = on_command("show", aliases={"\\show", "/show"}, priority=1, block=True)


def _count_files_recursive(root: Path) -> int:
    if not root.exists():
        return 0
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过缓存目录
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn == ".DS_Store":
                continue
            # 忽略插件源码文件（只统计素材库）
            if fn.endswith(".py") or fn.endswith(".pyc"):
                continue
            count += 1
    return count


@show_cmd.handle()
async def handle_show(bot: Bot, event: MessageEvent):
    try:
        plugins_dir = Path(__file__).resolve().parents[1]
        keyword_005_dir = plugins_dir / "keyword_005_keywords_graph" / "a001_all_graph"
        n = _count_files_recursive(keyword_005_dir)
        await show_cmd.finish(f"keyword_005文件夹内的文件数量：{n}\n目前手牌数量：{n}")
    except Exception as e:
        nonebot.logger.error(f"[show_num] 统计失败: {e}")
        await show_cmd.finish(f"统计失败：{e}")

