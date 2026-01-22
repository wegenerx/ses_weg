import time
from collections import deque
from typing import Dict, Deque

import nonebot
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot import get_plugin_config, get_driver
from nonebot.plugin import PluginMetadata
from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="auto_002_global_guard",
    description="全局守卫 - 控制机器人的访问权限和发言频率",
    usage="通过环境变量配置群组白名单和超级用户",
    config=Config,
)

config = get_plugin_config(Config)

driver = get_driver()
cfg = driver.config

# 从 .env 读取（JSON 列表会被解析成 list/set 之类）
GROUP_WHITELIST = set(getattr(cfg, "bot_group_whitelist", []) or [])
SUPERUSERS = set(str(x) for x in getattr(cfg, "superusers", []) or [])

# ============================================
# 发言频率限制器
# ============================================
class BotRateLimiter:
    """Bot发言频率限制器"""
    
    def __init__(self, max_count: int = 3, window_seconds: int = 60):
        """
        Args:
            max_count: 时间窗口内允许的最大发言次数
            window_seconds: 时间窗口大小（秒）
        """
        self.max_count = max_count
        self.window_seconds = window_seconds
        # 存储每个群组/私聊的发言时间戳队列
        # key: "group_{group_id}" 或 "private_{user_id}"
        self.records: Dict[str, Deque[float]] = {}
    
    def _get_scope(self, group_id: int = None, user_id: int = None) -> str:
        """获取作用域标识"""
        if group_id is not None:
            return f"group_{group_id}"
        elif user_id is not None:
            return f"private_{user_id}"
        return "global"
    
    def _clean_expired(self, scope: str, now: float):
        """清理过期的时间戳记录"""
        if scope not in self.records:
            return
        
        queue = self.records[scope]
        # 移除超过时间窗口的记录
        while queue and (now - queue[0]) > self.window_seconds:
            queue.popleft()
        
        # 如果队列为空，删除该作用域的记录
        if not queue:
            del self.records[scope]
    
    def check_and_record(self, group_id: int = None, user_id: int = None) -> bool:
        """
        检查是否允许发送消息，如果允许则记录时间戳
        
        Returns:
            True: 允许发送
            False: 超过限制，不允许发送
        """
        scope = self._get_scope(group_id, user_id)
        now = time.time()
        
        # 清理过期记录
        self._clean_expired(scope, now)
        
        # 获取或创建队列
        if scope not in self.records:
            self.records[scope] = deque()
        
        queue = self.records[scope]
        
        # 检查是否超过限制
        if len(queue) >= self.max_count:
            return False
        
        # 记录当前时间戳
        queue.append(now)
        return True
    
    def get_remaining_count(self, group_id: int = None, user_id: int = None) -> int:
        """获取剩余可发送次数"""
        scope = self._get_scope(group_id, user_id)
        now = time.time()
        self._clean_expired(scope, now)
        
        if scope not in self.records:
            return self.max_count
        
        return max(0, self.max_count - len(self.records[scope]))


# 创建全局频率限制器实例
rate_limiter = BotRateLimiter(max_count=3, window_seconds=60)

# 限制生效的群组ID
RATE_LIMIT_GROUP_ID = 937786461


# ============================================
# Bot Hook: 拦截消息发送
# ============================================
@driver.on_bot_connect
async def register_rate_limit_hook(bot: Bot):
    """注册Bot连接时的hook，拦截消息发送"""
    
    # 保存原始的 send_group_msg 方法
    original_send_group_msg = bot.send_group_msg
    
    async def rate_limited_send_group_msg(
        group_id: int,
        message,
        **kwargs
    ):
        """
        包装 send_group_msg 方法，添加频率限制
        只对指定群组生效
        """
        # 只对指定群组生效
        if group_id == RATE_LIMIT_GROUP_ID:
            # 检查频率限制
            if not rate_limiter.check_and_record(group_id=group_id):
                # 超过限制，阻止发送
                remaining = rate_limiter.get_remaining_count(group_id=group_id)
                nonebot.logger.warning(
                    f"[RateLimit] 群组 {group_id} Bot发言频率超限，"
                    f"剩余可发送次数: {remaining}，本次发送被阻止"
                )
                # 抛出异常阻止发送
                raise RuntimeError(
                    f"Bot发言频率超限（1分钟内超过{rate_limiter.max_count}次）"
                )
        
        # 允许发送，调用原始方法
        return await original_send_group_msg(group_id=group_id, message=message, **kwargs)
    
    # 替换 bot 的 send_group_msg 方法
    bot.send_group_msg = rate_limited_send_group_msg
    
    # 同时拦截 bot.send 方法（当传入 GroupMessageEvent 时）
    original_send = bot.send
    
    async def rate_limited_send(event: MessageEvent, message, **kwargs):
        """
        包装 send 方法，添加频率限制
        只对指定群组生效
        """
        # 只处理群消息
        if isinstance(event, GroupMessageEvent):
            # 只对指定群组生效
            if event.group_id == RATE_LIMIT_GROUP_ID:
                # 检查频率限制
                if not rate_limiter.check_and_record(group_id=event.group_id):
                    # 超过限制，阻止发送
                    remaining = rate_limiter.get_remaining_count(group_id=event.group_id)
                    nonebot.logger.warning(
                        f"[RateLimit] 群组 {event.group_id} Bot发言频率超限，"
                        f"剩余可发送次数: {remaining}，本次发送被阻止"
                    )
                    # 抛出异常阻止发送
                    raise RuntimeError(
                        f"Bot发言频率超限（1分钟内超过{rate_limiter.max_count}次）"
                    )
        
        # 允许发送，调用原始方法
        return await original_send(event=event, message=message, **kwargs)
    
    # 替换 bot 的 send 方法
    bot.send = rate_limited_send


# ============================================
# 事件预处理器：访问权限控制
# ============================================
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
