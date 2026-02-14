import multiprocessing
import nonebot
# import nonebot_plugin_AutoRepeater
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
import time
import os
import sys
from pathlib import Path

# import nonebot_plugin_mute

# 设置日志级别为DEBUG
nonebot.init(log_level="DEBUG")

# 配置日志：保存DEBUG到文件，控制台过滤PreProcessors日志
from nonebot.log import logger, default_format, logger_id

# 移除默认处理器
logger.remove(logger_id)

# 确保logs目录存在
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# 添加控制台处理器（INFO级别，过滤PreProcessors日志）
logger.add(
    sys.stdout,
    level="INFO",
    format=default_format,
    filter=lambda record: "PreProcessors" not in str(record.get("message", ""))
)

# 添加文件处理器（DEBUG级别，保存所有日志到文件）
logger.add(
    str(logs_dir / "debug.log"),
    level="DEBUG",
    format=default_format,
    rotation="1 week",  # 每周轮转一次
    retention="4 weeks",  # 保留4周的日志
    encoding="utf-8"
)


def rubbish_can():
    ''
    # "haruka_bot", # B站 up 主动态
    # "haruka_bot_red",  # B站 up 主动态


def load_plugin_and_sleep(plugin_names: list[str]):
    for plugin_name in plugin_names:
        nonebot.load_plugin(plugin_name)  # nb plugin install haruka_bot_red
        time.sleep(0.05)


driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

# 第三方插件列表（加载在 main 中执行）
_THIRD_PARTY_PLUGINS = [
    "nonebot_plugin_status",  # 戳一戳
    "nonebot_plugin_remake",  # 人生重开模拟器

    # "nonebot_plugin_longtu")    # 随机龙图
    "nonebot_plugin_setu_now",  # 另一个色图插件
    "nonebot_plugin_ottohzys",

    # "nonebot_plugin_arcaeabot",  # arcaea bot
    "nonebot_plugin_lxns_maimai",  # maimai score bot
    # "nonebot_plugin_maimai",  # maimai bot - Pydantic Config 兼容性报错
    # "nonebot_plugin_plus_one",      # +1
    "nonebot_plugin_bilichat",  # 需先执行: pip install -r requirements-bilichat.txt（降级 httpx<0.28）
    # 'nonebot_plugin_AutoRepeater',      # +1
    # 'nonebot_plugin_capoo',
    'nonebot_plugin_jm',        #禁漫
    'nonebot_plugin_zxreport',              # 真寻日报
    'nonebot_plugin_multi_source_daily',     # 多来源日报
    'nonebot_plugin_nmcweather',     # 天气预报
    'nonebot_plugin_arcaea_sticker',  # maimai score bot
    # "nonebot_plugin_pjsekaihelper"    # pjsekai helper
]

_PLUGIN_BLACKLIST = {"a004_1_nonebot_plugin_plus_one", "__pycache__", "a001_longtu"}


def _load_all_plugins():
    nonebot.load_builtin_plugins("echo")
    load_plugin_and_sleep(_THIRD_PARTY_PLUGINS)
    plugin_dir = "ses_weg/plugins"
    path_list = next(os.walk(plugin_dir))[1]
    for dir in path_list:
        if dir not in _PLUGIN_BLACKLIST:
            plugin_path = f"ses_weg.plugins.{dir}"
            print(plugin_path)
            nonebot.load_plugin(plugin_path)
            print(f"Loaded plugin: {plugin_path}")
            time.sleep(0.05)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    # 仅主进程加载插件并启动，避免 hipporag 的 multiprocessing.Manager spawn 子进程时重复执行
    if multiprocessing.current_process().name == "MainProcess":
        _load_all_plugins()
        nonebot.run()
