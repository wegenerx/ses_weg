# command_004_help/__init__.py
import asyncio

import nonebot
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg
from nonebot.adapters import Message

__plugin_meta__ = PluginMetadata(
    name="command_004_help",
    description="Bot 功能帮助",
    usage="\\help 或 /help - 查看 Bot 所有功能简介",
)

# 帮助内容字典
HELP_CONTENT = {
    "photo": """🖼️ 图像处理插件功能

回复图片消息使用以下命令：

几何变换：
• 对称左/右/上/下 - 将半部分翻转到另一半
• 镜像左/右/上/下 - 整图翻转后拼接（2倍大小）
• 平移左/右/上/下 - 半部分直接拼接

图像特效：
• 黑白 - 转为灰度图
• 模糊[参数] - 高斯模糊（参数：0.5-10）
• 锐化[参数] - 锐化增强（参数：0.5-5.0）
• 边缘检测 - 边缘检测效果
• 去噪[参数] - 中值滤波去噪（参数：0.5-3.0）
• 放大镜/凸透镜/凹透镜/老花镜[参数] - 球形畸变
  - 参数 < 1：向中心挤压（凹透镜）
  - 参数 > 1：中间放大（凸透镜）
  - 参数范围：0.1-5.0

使用方法：回复图片消息，输入变换命令（如：对称左、模糊[2.5]）""",
    
    "reply": """📥 回复数据库相关功能

消息收集功能：
• 回复消息自动收集
  - 回复图片：自动保存到对应文件夹
  - 回复文本：自动保存到对应文件夹
  - 回复合并转发：批量收集所有子消息

使用方法：
• 回复消息，输入关键词（可多个，空格分隔）
  例如：回复图片后输入 "猫 狗"
• 回复消息，输入 "add 关键词1 关键词2"
  例如：回复图片后输入 "add 猫 狗"

创建新文件夹：
• add <prefix> <token1> [token2] ...
  例如：add a 新文件夹 测试""",
    
    "reboot": """🔄 重启功能

命令：\\reboot 或 /reboot

功能：重启 Bot 服务

注意：重启后需要重新连接，可能需要几秒钟时间""",
    
    "ban_list": """🚫 黑名单管理

命令格式：
• \\ban_list add <词1> <词2> ... - 添加黑名单
• \\ban_list rm <词1> <词2> ... - 移除黑名单
• \\ban_list ls - 查看黑名单列表

示例：
• \\ban_list add 垃圾 广告
• \\ban_list rm 垃圾
• \\ban_list ls""",
    
    "remove": """📦 归档内容功能

命令格式：
• \\remove - 归档最后一条记录到 remove 文件夹
• \\remove(2) - 归档倒数第二条记录
• \\remove outdated - 归档到 outdated 文件夹
• \\remove(3) outdated - 归档倒数第三条到 outdated 文件夹

说明：
• 归档会将记录从 location.txt 移动到指定文件夹
• 支持归档到 remove、nsfw、outdated 等文件夹""",
    
    "release": """📢 更新日志

命令格式：
• \\release - 查看最近1次更新
• \\release 3 - 查看最近3次更新

功能：查看 Bot 的版本更新历史记录""",
    
    "help": """❓ 帮助信息

命令格式：
• \\help - 查看所有功能列表
• \\help <功能名> - 查看具体功能帮助

可用功能：
• \\help photo - 图像处理插件功能
• \\help reply - 回复数据库相关功能
• \\help reboot - 重启功能
• \\help ban_list - 黑名单管理
• \\help remove - 归档内容功能
• \\help release - 更新日志"""
}

# 默认帮助列表
DEFAULT_HELP_LIST = """🤖 Bot 功能帮助

使用 \\help <功能名> 查看详细帮助

可用功能：
• \\help photo - 图像处理插件功能
• \\help reply - 回复数据库相关功能
• \\help reboot - 重启功能
• \\help ban_list - 黑名单管理
• \\help remove - 归档内容功能
• \\help release - 更新日志

══════════════

• 基于 NoneBot2 框架 https://github.com/wegenerx/ses_weg
"""


# 创建命令处理器
help_cmd = on_command(
    "help",
    priority=1,
    block=True,
)


@help_cmd.handle()
async def handle_help(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    """处理 help 命令"""
    # 解析参数
    plain_text = arg.extract_plain_text().strip().lower()
    
    # 如果没有参数，显示默认帮助列表
    if not plain_text:
        help_text = DEFAULT_HELP_LIST
    else:
        # 查找对应的帮助内容
        help_text = HELP_CONTENT.get(plain_text)
        if help_text is None:
            # 如果找不到，显示默认帮助列表
            help_text = f"❌ 未找到功能 '{plain_text}' 的帮助信息\n\n{DEFAULT_HELP_LIST}"
    
    try:
        # 发送消息
        await help_cmd.send(help_text)
    except Exception as e:
        nonebot.logger.error(f"[Help] 发送消息失败: {e}")
        await help_cmd.finish(f"❌ 发送失败: {e}")
