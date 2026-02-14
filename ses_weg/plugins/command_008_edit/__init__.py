# command_008_edit/__init__.py
"""
编辑 keyword_005_keywords_graph/a001_all_graph 内的文件夹名称
命令: \\edit 或 /edit 关键词 -> 搜索 -> 用户输入新名称 -> 重命名
非 superuser 专用，过滤含 collect 的文件夹
"""
import os
import re

import nonebot
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="command_008_edit",
    description="编辑 a001_all_graph 内文件夹名称",
    usage="\\edit 关键词 -> 输入新名称（如 a op oi）重命名",
)

# 仅搜索 a001_all_graph
A001_ROOT_KEY = "a001_all_graph"

# 推送黑名单：含这些词的文件夹不参与搜索
PUSH_BLACKLIST = ["collect", "collection"]

# 会话: {user_id: {"state": "wait_name", "folder_path": ..., "folder_name": ..., "keyword": ...}}
edit_sessions: dict = {}

edit_cmd = on_command("edit", aliases={"\\edit", "/edit"}, priority=2, block=True)


def _abs_a001_root() -> str:
    p = os.path.abspath(__file__)
    plug_dir = os.path.dirname(p)
    return os.path.normpath(os.path.join(plug_dir, "..", "keyword_005_keywords_graph", A001_ROOT_KEY))


def _sanitize_part(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r"\s+", "_", s)
    return s


def _hit_push_blacklist(folder_name: str) -> bool:
    fn = folder_name.lower()
    for kw in PUSH_BLACKLIST:
        if kw and kw.lower() in fn:
            return True
    return False


def find_first_folder_by_keyword(keyword: str) -> tuple[str, str] | None:
    """
    在 a001_all_graph 下搜索第一个包含 keyword 的文件夹（不含 collect）
    返回 (folder_path, folder_name) 或 None
    """
    if not keyword or not keyword.strip():
        return None
    kw = keyword.strip()
    root = _abs_a001_root()
    if not os.path.isdir(root):
        return None
    for name in os.listdir(root):
        if kw not in name:
            continue
        if _hit_push_blacklist(name):
            continue
        full = os.path.join(root, name)
        if os.path.isdir(full):
            return (os.path.normpath(full), name)
    return None


def parse_rename_tokens(text: str) -> list[str]:
    """解析用户输入为新名称的 tokens，如 'a op oi' -> ['a','op','oi']"""
    parts = (text or "").strip().split()
    return [_sanitize_part(p) for p in parts if p.strip()]


def extract_head_from_folder_name(folder_name: str) -> str:
    """
    从文件夹名提取前缀头，如 a044_xxx_yyy -> a044, pjsk_005_zzz -> pjsk_005
    """
    parts = folder_name.split("_")
    if not parts:
        return ""
    # a044 / pjsk_005 等
    if re.match(r"^a\d{3}$", parts[0], re.I):
        return parts[0]
    if len(parts) >= 2 and re.match(r"^\d{3}$", parts[1]):
        return f"{parts[0]}_{parts[1]}"
    return parts[0] if parts else ""


@edit_cmd.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    arg = arg.extract_plain_text().strip()
    if not arg:
        await edit_cmd.finish("用法：\\edit 关键词")
        return

    found = find_first_folder_by_keyword(arg)
    if not found:
        await edit_cmd.finish(f"未找到包含「{arg}」的文件夹（已排除含 collect 的文件夹）")
        return

    folder_path, folder_name = found
    user_id = str(event.user_id)
    edit_sessions[user_id] = {
        "state": "wait_name",
        "folder_path": folder_path,
        "folder_name": folder_name,
        "keyword": arg,
    }
    await edit_cmd.send(f"找到文件夹：{folder_name}\n请发送新名称（如 a op oi），将重命名为 a0**_op_oi 格式。发送 取消 放弃。")


edit_listener = on_message(priority=3, block=False)


@edit_listener.handle()
async def _listen(bot: Bot, event: MessageEvent):
    user_id = str(event.user_id)
    if user_id not in edit_sessions:
        return
    ses = edit_sessions[user_id]
    if ses.get("state") != "wait_name":
        return

    text = event.get_plaintext().strip()
    if "取消" in text:
        del edit_sessions[user_id]
        await edit_listener.finish("已取消")
        return

    tokens = parse_rename_tokens(text)
    if not tokens:
        await edit_listener.send("至少需要一个有效字符，或发送 取消")
        return

    folder_path = ses["folder_path"]
    folder_name = ses["folder_name"]
    head = extract_head_from_folder_name(folder_name)
    if not head:
        del edit_sessions[user_id]
        await edit_listener.finish("无法解析文件夹前缀")
        return

    new_name = head + "_" + "_".join(tokens)
    parent = os.path.dirname(folder_path)
    new_path = os.path.join(parent, new_name)
    if os.path.exists(new_path):
        await edit_listener.send(f"目标名称已存在：{new_name}，请重新发送或 取消")
        return

    try:
        os.rename(folder_path, new_path)
        del edit_sessions[user_id]
        await edit_listener.finish(f"重命名成功：{folder_name} -> {new_name}")
    except Exception as e:
        nonebot.logger.error(f"[edit] rename failed: {e}")
        await edit_listener.finish(f"重命名失败：{e}")
