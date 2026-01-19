import time

import asyncio
from datetime import datetime
import os
import json
import os
import ssl
import requests
from PIL import Image as PILImage
from io import BytesIO
import io

import nonebot
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment
from nonebot import on_keyword, on_message
from nonebot.adapters.onebot.v11 import Bot
from nonebot_plugin_alconna.uniseg import Hyper, Image, MsgTarget, Reply, Text, UniMessage, UniMsg, MessageId

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="a010_heliemin",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

from nonebot import get_driver
from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent

driver = get_driver()
cfg = driver.config

# 从 .env 读取（JSON 列表会被解析成 list/set 之类）
GROUP_WHITELIST = set(getattr(cfg, "bot_group_whitelist", []) or [])
SUPERUSERS = set(str(x) for x in getattr(cfg, "superusers", []) or [])

@event_preprocessor
async def _(event):
    # 1) 群消息：只允许白名单群
    if isinstance(event, GroupMessageEvent):
        if GROUP_WHITELIST and event.group_id not in GROUP_WHITELIST:
            raise IgnoredException("group not allowed")
        return

    # 2) 私聊：默认全部忽略；如果你希望超级用户私聊可用，就放行
    if isinstance(event, PrivateMessageEvent):
        if str(event.user_id) not in SUPERUSERS:
            raise IgnoredException("private not allowed")
