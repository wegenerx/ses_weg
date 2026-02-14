import contextlib
import time
from collections import deque
from contextvars import ContextVar
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
    """Bot发言频率限制器 - 支持多个时间窗口限制"""
    
    def __init__(self, rate_limit_rules: Dict[int, int]):
        """
        Args:
            rate_limit_rules: 频率限制规则字典，格式：{时间窗口（秒）: 最大发送次数}
                例如：{5: 1, 15: 2, 60: 3} 表示：
                    - 5秒内最多1条
                    - 15秒内最多2条
                    - 60秒内最多3条
        """
        # 按时间窗口从小到大排序，便于检查
        self.rate_limit_rules = dict(sorted(rate_limit_rules.items()))
        # 获取最大时间窗口，用于清理过期记录
        self.max_window_seconds = max(self.rate_limit_rules.keys()) if self.rate_limit_rules else 60
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
        # 移除超过最大时间窗口的记录
        while queue and (now - queue[0]) > self.max_window_seconds:
            queue.popleft()
        
        # 如果队列为空，删除该作用域的记录
        if not queue:
            del self.records[scope]
    
    def check_and_record(self, group_id: int = None, user_id: int = None) -> bool:
        """
        检查是否允许发送消息，如果允许则记录时间戳
        检查所有时间窗口限制，只要有一个超过限制就阻止发送
        
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
        
        # 检查所有时间窗口限制
        for window_seconds, max_count in self.rate_limit_rules.items():
            # 计算该时间窗口内的消息数量
            count_in_window = sum(1 for timestamp in queue if (now - timestamp) <= window_seconds)
            
            # 如果超过该窗口的限制，阻止发送
            if count_in_window >= max_count:
                return False
        
        # 所有限制都通过，记录当前时间戳
        queue.append(now)
        return True
    
    def get_remaining_count(self, group_id: int = None, user_id: int = None) -> int:
        """获取剩余可发送次数（返回最严格的限制）"""
        scope = self._get_scope(group_id, user_id)
        now = time.time()
        self._clean_expired(scope, now)
        
        if scope not in self.records:
            # 返回最小的限制值
            return min(self.rate_limit_rules.values()) if self.rate_limit_rules else 0
        
        queue = self.records[scope]
        
        # 计算所有时间窗口的剩余次数，返回最小值
        remaining_counts = []
        for window_seconds, max_count in self.rate_limit_rules.items():
            count_in_window = sum(1 for timestamp in queue if (now - timestamp) <= window_seconds)
            remaining_counts.append(max(0, max_count - count_in_window))
        
        return min(remaining_counts) if remaining_counts else 0
    
    def get_violated_rule(self, group_id: int = None, user_id: int = None) -> tuple[int, int] | None:
        """
        获取违反的规则（如果有）
        
        Returns:
            (window_seconds, max_count) 或 None
        """
        scope = self._get_scope(group_id, user_id)
        now = time.time()
        self._clean_expired(scope, now)
        
        if scope not in self.records:
            return None
        
        queue = self.records[scope]
        
        # 检查所有时间窗口限制
        for window_seconds, max_count in self.rate_limit_rules.items():
            count_in_window = sum(1 for timestamp in queue if (now - timestamp) <= window_seconds)
            if count_in_window >= max_count:
                return (window_seconds, max_count)
        
        return None


# 创建全局频率限制器实例（使用配置中的规则）
rate_limiter = BotRateLimiter(rate_limit_rules=config.rate_limit_rules)

# 限制生效的群组ID
RATE_LIMIT_GROUP_ID = 937786461

# 豁免标记：被设为 True 时跳过频率限制（供 auto_003_llmchat 等插件使用）
_rate_limit_exempt: ContextVar[bool] = ContextVar("rate_limit_exempt", default=False)


@contextlib.contextmanager
def exempt_rate_limit():
    """在此上下文中发送的消息不受频率限制"""
    token = _rate_limit_exempt.set(True)
    try:
        yield
    finally:
        _rate_limit_exempt.reset(token)


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
        # 豁免标记为 True 时跳过限制
        if _rate_limit_exempt.get():
            return await original_send_group_msg(group_id=group_id, message=message, **kwargs)
        # 只对指定群组生效
        if group_id == RATE_LIMIT_GROUP_ID:
            # 检查频率限制
            if not rate_limiter.check_and_record(group_id=group_id):
                # 超过限制，阻止发送
                remaining = rate_limiter.get_remaining_count(group_id=group_id)
                violated = rate_limiter.get_violated_rule(group_id=group_id)
                rule_desc = f"{violated[0]}秒内超过{violated[1]}次" if violated else "频率限制"
                nonebot.logger.warning(
                    f"[RateLimit] 群组 {group_id} Bot发言频率超限，"
                    f"剩余可发送次数: {remaining}，本次发送被阻止（{rule_desc}）"
                )
                # 抛出异常阻止发送
                raise RuntimeError(
                    f"Bot发言频率超限（{rule_desc}）"
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
        # 豁免标记为 True 时跳过限制
        if _rate_limit_exempt.get():
            return await original_send(event=event, message=message, **kwargs)
        # 只处理群消息
        if isinstance(event, GroupMessageEvent):
            # 只对指定群组生效
            if event.group_id == RATE_LIMIT_GROUP_ID:
                # 检查频率限制
                if not rate_limiter.check_and_record(group_id=event.group_id):
                    # 超过限制，阻止发送
                    remaining = rate_limiter.get_remaining_count(group_id=event.group_id)
                    violated = rate_limiter.get_violated_rule(group_id=event.group_id)
                    rule_desc = f"{violated[0]}秒内超过{violated[1]}次" if violated else "频率限制"
                    nonebot.logger.warning(
                        f"[RateLimit] 群组 {event.group_id} Bot发言频率超限，"
                        f"剩余可发送次数: {remaining}，本次发送被阻止（{rule_desc}）"
                    )
                    # 抛出异常阻止发送
                    raise RuntimeError(
                        f"Bot发言频率超限（{rule_desc}）"
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
