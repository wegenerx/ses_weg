# command_005_release/__init__.py
import json
import os
import asyncio
from typing import Optional

import nonebot
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg
from nonebot.adapters import Message

__plugin_meta__ = PluginMetadata(
    name="command_005_release",
    description="发送更新日志",
    usage="\\release [数量] - 发送最近N次更新（默认1次）",
)

# 获取 release.txt 路径
def get_release_file_path() -> str:
    """获取 release.txt 的完整路径"""
    current_script_path = os.path.abspath(__file__)
    plugin_dir = os.path.dirname(current_script_path)
    return os.path.join(plugin_dir, "release.txt")


def read_release_records() -> list[dict]:
    """读取 release.txt 中的所有记录（从新到旧）"""
    release_file = get_release_file_path()
    if not os.path.exists(release_file):
        return []
    
    records = []
    with open(release_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError:
                continue
    
    # 返回从新到旧的记录（最后一行是最新的）
    return records


def format_release_message(records: list[dict]) -> str:
    """格式化 release 记录为消息文本"""
    if not records:
        return "暂无更新记录"
    
    lines = []
    for i, record in enumerate(records, 1):
        date = record.get("date", "未知日期")
        version = record.get("version", "")
        content = record.get("content", "")
        github = record.get("github", "")
        website = record.get("website", "")
        
        # 构建单条记录
        record_lines = [f"📅 {date}"]
        if version:
            record_lines.append(f"🏷️ 版本: {version}")
        record_lines.append(f"📝 {content}")
        if github:
            record_lines.append(f"🔗 GitHub: {github}")
        if website:
            record_lines.append(f"🌐 网站: {website}")
        
        # 如果不是最后一条，添加分隔符
        formatted_record = "\n".join(record_lines)
        if i < len(records):
            formatted_record += "\n" + "-" * 30
        
        lines.append(formatted_record)
    
    return "\n\n".join(lines)


async def withdraw_message(bot: Bot, message_id: int, delay_seconds: int = 300):
    """延迟撤回消息"""
    try:
        await asyncio.sleep(delay_seconds)
        await bot.delete_msg(message_id=message_id)
    except Exception as e:
        nonebot.logger.error(f"[Release] 撤回消息失败: {e}")


# 创建命令处理器
release_cmd = on_command(
    "release",
    priority=1,
    block=True,
)


@release_cmd.handle()
async def handle_release(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    """处理 release 命令"""
    # 解析参数
    plain_text = arg.extract_plain_text().strip()
    
    # 确定要发送的记录数量
    count = 1  # 默认1次
    if plain_text:
        try:
            count = int(plain_text)
            if count < 1:
                count = 1
        except ValueError:
            await release_cmd.finish("❌ 参数错误，请输入数字")
            return
    
    # 读取记录
    records = read_release_records()
    if not records:
        await release_cmd.finish("❌ 暂无更新记录")
        return
    
    # 获取最近的 N 条记录（从新到旧）
    recent_records = records[-count:] if count <= len(records) else records
    
    # 格式化消息
    message_text = format_release_message(recent_records)
    
    # 发送消息
    try:
        res = await release_cmd.send(message_text)
        
        # 获取消息ID
        msg_id = None
        if isinstance(res, dict) and "message_id" in res:
            msg_id = res["message_id"]
        elif hasattr(res, "message_id"):
            msg_id = getattr(res, "message_id", None)
        
        # 自动撤回已禁用
        # if msg_id:
        #     asyncio.create_task(withdraw_message(bot, msg_id, 300))
    except Exception as e:
        nonebot.logger.error(f"[Release] 发送消息失败: {e}")
        await release_cmd.finish(f"❌ 发送失败: {e}")
