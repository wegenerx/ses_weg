# command_003_nsfw/__init__.py
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from nonebot import on_regex, get_driver
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="command_003_nsfw",
    description="归档 location.txt 中的记录",
    usage="\\remove [数字] [文件夹名] 或 \\nsfw [数字]",
)

# 权限约束器（暂时设为 False，所有人可用）
ENABLE_SUPERUSER_ONLY = False

# 图片预览（强模糊）
try:
    from PIL import Image as PILImage
    from PIL import ImageFilter
except Exception:  # Pillow 可能未安装
    PILImage = None
    ImageFilter = None

# 获取 location.txt 路径
def get_location_file_path() -> str:
    """获取 location.txt 的完整路径"""
    current_script_path = os.path.abspath(__file__)
    plugin_dir = os.path.dirname(current_script_path)
    return os.path.join(plugin_dir, "location.txt")


def parse_command(full_text: str, command_type: str) -> tuple[Optional[int], Optional[str]]:
    """
    解析命令参数
    参数:
        full_text: 完整的消息文本（包含命令头）
        command_type: 命令类型（"remove" 或 "nsfw"）
    返回: (index, folder_name)
    - index: 倒数第几条（1表示最后一条，2表示倒数第二条），None表示最后一条
    - folder_name: 目标文件夹名，None表示默认（remove 或 nsfw）
    
    支持的格式：
    - \remove -> (None, "remove")
    - \remove(2) -> (2, "remove")
    - \remove outdated -> (None, "outdated")
    - \remove(3) outdated -> (3, "outdated")
    - \remove nsfw -> (None, "nsfw")
    - \nsfw -> (None, "nsfw")
    - \nsfw(2) -> (2, "nsfw")
    - \nsfw outdated -> None (错误)
    """
    # 移除开头的反斜杠或正斜杠
    s = full_text.strip()
    if s.startswith("\\") or s.startswith("/"):
        s = s[1:].strip()
    
    # 默认文件夹名
    default_folder = "remove" if command_type == "remove" else "nsfw"
    
    # 检查命令中是否有 (数字)
    match = re.match(rf"^{re.escape(command_type)}\((\d+)\)", s, re.IGNORECASE)
    if match:
        index = int(match.group(1))
        # 移除命令部分，获取剩余参数
        remaining = s[len(match.group(0)):].strip()
        if remaining:
            folder_name = remaining.split()[0].lower()
            # 检查是否是错误用法（nsfw outdated）
            if command_type == "nsfw" and folder_name == "outdated":
                return None, None
        else:
            folder_name = default_folder
        return index, folder_name
    
    # 没有 (数字)，检查普通格式
    # 移除命令头
    remaining = s[len(command_type):].strip()
    
    # 检查是否是错误用法（nsfw outdated）
    if command_type == "nsfw" and remaining.lower() == "outdated":
        return None, None
    
    if not remaining:
        return None, default_folder
    
    # 分割参数
    parts = remaining.split(maxsplit=1)
    
    # 检查第一个参数是否是数字
    if parts[0].isdigit():
        index = int(parts[0])
        if len(parts) > 1:
            folder_name = parts[1].split()[0].lower()
        else:
            folder_name = default_folder
    else:
        index = None  # 没有指定数字，默认是最后一条
        folder_name = parts[0].lower()
    
    return index, folder_name


def read_location_records() -> list[dict]:
    """读取 location.txt 中的所有记录"""
    location_file = get_location_file_path()
    if not os.path.exists(location_file):
        return []
    
    records = []
    with open(location_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError:
                continue
    
    return records


def write_location_records(records: list[dict]):
    """将记录写回 location.txt"""
    location_file = get_location_file_path()
    with open(location_file, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _text_preview(record: dict) -> str:
    """
    文本预览：最多 10 字 + ...
    优先用 record.content_preview；否则尝试从 file_path + line_number 读取
    """
    s = (record.get("content_preview") or "").strip()
    if not s:
        file_path = record.get("file_path") or ""
        line_number = record.get("line_number")
        try:
            if file_path and os.path.exists(file_path) and isinstance(line_number, int) and line_number >= 1:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if 1 <= line_number <= len(lines):
                    s = (lines[line_number - 1] or "").strip()
        except Exception:
            s = ""
    if not s:
        return ""
    return (s[:10] + "...") if len(s) > 10 else s


def _blur_image_bytes(image_path: str) -> bytes | None:
    """
    重度马赛克（整张模糊）：先缩小再放大 + 高斯模糊
    返回 PNG bytes
    """
    if not PILImage:
        return None
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        from io import BytesIO

        with PILImage.open(image_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            small_w = max(8, w // 32)
            small_h = max(8, h // 32)
            img_small = img.resize((small_w, small_h), PILImage.Resampling.NEAREST)
            img_pix = img_small.resize((w, h), PILImage.Resampling.NEAREST)
            try:
                if ImageFilter:
                    img_pix = img_pix.filter(ImageFilter.GaussianBlur(radius=max(8, min(w, h) // 40)))
            except Exception:
                pass
            buf = BytesIO()
            img_pix.save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        return None


def _build_success_message_with_preview(record: dict, base_message: str) -> Message:
    """
    在同一条成功消息里附带预览：
    - text: 增加“预览: xxx...”
    - image: 增加模糊图
    """
    msg_type = (record.get("type") or "").lower()
    m = Message()
    m += MessageSegment.text(f"✅ {base_message}")

    if msg_type == "text":
        pv = _text_preview(record)
        if pv:
            m += MessageSegment.text(f"\n预览: {pv}")
        return m

    if msg_type == "image":
        # 注意：archive_record 会移动图片，所以必须在归档前生成预览
        file_path = record.get("file_path") or ""
        img_bytes = _blur_image_bytes(file_path)
        if img_bytes:
            m += MessageSegment.text("\n预览: ")
            m += MessageSegment.image(img_bytes)
        return m

    return m


def archive_record(record: dict, target_folder: str) -> tuple[bool, str]:
    """
    归档一条记录
    返回: (success, message)
    """
    try:
        file_path = record.get("file_path", "")
        msg_type = record.get("type", "")
        line_number = record.get("line_number")
        
        if not file_path or not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"
        
        # 获取文件所在目录（图片的根目录）
        # 根目录是指包含该文件的文件夹
        # 例如：如果文件在 plugins/keyword_005_keywords_graph/a001_all_graph/a044_meme/xxx.jpg
        # 那么根目录就是 a044_meme 文件夹
        file_dir = os.path.dirname(file_path)
        
        # 在文件所在目录下创建目标文件夹
        target_dir = os.path.join(file_dir, target_folder)
        os.makedirs(target_dir, exist_ok=True)
        
        if msg_type == "image":
            # 图片：直接移动文件
            file_name = os.path.basename(file_path)
            target_file = os.path.join(target_dir, file_name)
            # 如果目标文件已存在，添加序号
            counter = 1
            base_name, ext = os.path.splitext(file_name)
            while os.path.exists(target_file):
                target_file = os.path.join(target_dir, f"{base_name}_{counter}{ext}")
                counter += 1
            
            shutil.move(file_path, target_file)
            return True, f"图片已归档到 {target_folder}/{os.path.basename(target_file)}"
        
        elif msg_type == "text":
            # 文本：删除该行（留空），然后追加到目标文件夹的 text.txt
            txt_path = file_path
            if not os.path.exists(txt_path):
                return False, f"文本文件不存在: {txt_path}"
            
            # 读取原文件内容
            with open(txt_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 检查行号是否有效
            if line_number is None or line_number < 1 or line_number > len(lines):
                return False, f"无效的行号: {line_number}"
            
            # 获取原内容（索引从0开始）
            original_content = lines[line_number - 1].rstrip("\n")
            
            # 将该行留空
            lines[line_number - 1] = "\n"
            
            # 写回文件
            with open(txt_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            # 追加到目标文件夹的 text.txt
            target_text_file = os.path.join(target_dir, "text.txt")
            with open(target_text_file, "a", encoding="utf-8") as f:
                f.write(original_content + "\n")
            
            return True, f"文本已归档到 {target_folder}/text.txt"
        
        else:
            return False, f"未知的消息类型: {msg_type}"
    
    except Exception as e:
        return False, f"归档失败: {str(e)}"


# 创建命令处理器
# 使用正则匹配支持 remove(2) 这种格式
# 匹配 \remove 或 /remove，可选带 (数字) 和参数
remove_pattern = r"^[/\\]?remove(?:\(\d+\))?(?:\s+.*)?$"
# 匹配 \nsfw 或 /nsfw，可选带 (数字)，但不能跟 outdated
nsfw_pattern = r"^[/\\]?nsfw(?:\(\d+\))?(?:\s+(?!outdated).*)?$"

remove_cmd = on_regex(
    remove_pattern,
    permission=SUPERUSER if ENABLE_SUPERUSER_ONLY else None,
    priority=1,
    block=True,
)

nsfw_cmd = on_regex(
    nsfw_pattern,
    permission=SUPERUSER if ENABLE_SUPERUSER_ONLY else None,
    priority=1,
    block=True,
)


@remove_cmd.handle()
async def handle_remove(bot: Bot, event: MessageEvent):
    """处理 remove 命令"""
    full_text = event.get_plaintext().strip()
    
    # 解析命令参数
    index, folder_name = parse_command(full_text, "remove")
    
    if folder_name is None:
        await remove_cmd.finish("❌ 命令格式错误")
        return
    
    # 读取记录
    records = read_location_records()
    if not records:
        await remove_cmd.finish("❌ location.txt 中没有记录")
        return
    
    # 确定要归档的记录索引（倒数第几条）
    if index is None:
        target_index = -1  # 最后一条
    else:
        if index > len(records):
            await remove_cmd.finish(f"❌ 记录数量不足，只有 {len(records)} 条")
            return
        target_index = -index  # 倒数第 index 条
    
    # 获取要归档的记录
    target_record = records[target_index]
    
    # 归档
    success, message = archive_record(target_record, folder_name)
    
    if success:
        # 从 records 中移除该记录
        records.pop(target_index)
        # 写回文件
        write_location_records(records)
        await remove_cmd.finish(_build_success_message_with_preview(target_record, message))
    else:
        await remove_cmd.finish(f"❌ {message}")


@nsfw_cmd.handle()
async def handle_nsfw(bot: Bot, event: MessageEvent):
    """处理 nsfw 命令（便捷命令，等同于 remove nsfw）"""
    full_text = event.get_plaintext().strip()
    
    # 解析命令参数
    index, folder_name = parse_command(full_text, "nsfw")
    
    # 检查是否是错误用法（nsfw outdated）
    if folder_name is None:
        await nsfw_cmd.finish("❌ 不能使用 'nsfw outdated'，请使用 'remove outdated'")
        return
    
    # nsfw 命令固定归档到 nsfw 文件夹
    folder_name = "nsfw"
    
    # 读取记录
    records = read_location_records()
    if not records:
        await nsfw_cmd.finish("❌ location.txt 中没有记录")
        return
    
    # 确定要归档的记录索引（倒数第几条）
    if index is None:
        target_index = -1  # 最后一条
    else:
        if index > len(records):
            await nsfw_cmd.finish(f"❌ 记录数量不足，只有 {len(records)} 条")
            return
        target_index = -index  # 倒数第 index 条
    
    # 获取要归档的记录
    target_record = records[target_index]
    
    # 归档
    success, message = archive_record(target_record, folder_name)
    
    if success:
        # 从 records 中移除该记录
        records.pop(target_index)
        # 写回文件
        write_location_records(records)
        await nsfw_cmd.finish(_build_success_message_with_preview(target_record, message))
    else:
        await nsfw_cmd.finish(f"❌ {message}")
