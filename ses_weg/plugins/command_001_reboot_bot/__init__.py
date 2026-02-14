# command_001_reboot_bot/__init__.py
from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.plugin import PluginMetadata

from ses_weg.services.restart import restart_process

__plugin_meta__ = PluginMetadata(
    name="reboot_bot",
    description="通过 \\reboot 指令重启 Bot",
    usage="\\reboot",
)

reboot_cmd = on_command(
    "reboot",
    # permission=SUPERUSER,
    priority=1,
    block=True,
)

@reboot_cmd.handle()
async def _(bot: Bot, event: Event):
    await reboot_cmd.send("♻️ 开始重启 Bot，请稍候…")
    await restart_process(delay=1.0, reason="manual reboot command")
