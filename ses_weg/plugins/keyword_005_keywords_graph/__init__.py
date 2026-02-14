# ===== 标准库 =====
import json
import os
import io
import re
import random
import asyncio
from datetime import datetime
from typing import Dict, Any, Iterable, Set
from pathlib import Path

# ===== 第三方库 =====
from PIL import Image as PILImage

# NoneBot 核心
from nonebot import get_plugin_config, on_keyword
from nonebot.plugin import PluginMetadata

# NoneBot OneBot v11 适配器
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment, GroupMessageEvent

# NoneBot Alconna 插件
from nonebot_plugin_alconna.uniseg import (
    Hyper, Image, MsgTarget, Reply, Text, UniMessage, UniMsg, MessageId
)

# ===== 本地模块 =====
from .config import Config

# ===== 注册 AVIF/HEIF 解码器 =====
try:
    import pillow_avif  # pip install pillow-avif-plugin
except Exception:
    try:
        import pillow_heif  # pip install pillow-heif
        pillow_heif.register_heif_opener()
    except Exception:
        pass


class KeywordsGraph():
    def __init__(
        self,
        keywords,
        path,
        priority: int = 10,
        temp: bool = False,
        probability: float = 0.9,
        withdraw: str = "60s",
        withdraw_max: int = 3600,
    ):
        self.keywords = keywords
        self.path = path
        self.priority = priority
        self.probability = probability
        self.withdraw = self.parse_withdraw(withdraw, withdraw_max)  # 秒 or None

        word = on_keyword(
            keywords=self.keywords,
            priority=self.priority,
            temp=temp
        )

        @word.handle()
        async def _(bot: Bot, event: MessageEvent, origin_msg: UniMsg):
            if random.random() < self.probability and Reply not in origin_msg:
                # 获取消息的纯文本内容
                msg_text = origin_msg.extract_plain_text().strip()
                
                # 过滤逻辑：检查消息中是否包含纯数字关键词或特定关键词
                # 将消息按逗号、空格等分隔符分割
                import re
                parts = re.split(r'[,\s]+', msg_text.lower())
                
                # 需要过滤的关键词列表（纯数字和特定关键词）
                filtered_keywords = {'single'}  # 特定关键词
                
                # 检查是否包含纯数字或特定关键词
                should_filter = False
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    # 检查是否是纯数字
                    if part.isdigit():
                        should_filter = True
                        break
                    # 检查是否是特定关键词
                    if part in filtered_keywords:
                        should_filter = True
                        break
                
                # 如果包含需要过滤的关键词，不发送图片
                if should_filter:
                    return

                unit = self.pick_unit()
                if not unit:
                    return

                if unit["type"] == "image":
                    out_msg = MessageSegment.image(unit["bytes"])
                else:
                    out_msg = unit["text"]

                res = await bot.send(event=event, message=out_msg)

                msg_id = None
                if isinstance(res, dict) and "message_id" in res:
                    msg_id = res["message_id"]
                elif hasattr(res, "message_id"):
                    msg_id = getattr(res, "message_id", None)

                # 记录发送日志
                self._log_send_record(
                    msg_type=unit["type"],
                    content_preview=unit.get("text", "")[:50] if unit["type"] == "text" else "[image]",
                    file_path=unit.get("file_path", ""),
                    line_number=unit.get("line_number", None),
                    group_id=getattr(event, "group_id", None),
                    user_id=getattr(event, "user_id", None),
                    msg_id=msg_id
                )

                if self.withdraw and msg_id is not None:
                    asyncio.create_task(self._delayed_withdraw(bot, msg_id, self.withdraw))

    # ===== 日志记录 =====
    @staticmethod
    def _log_send_record(
        msg_type: str,
        content_preview: str,
        file_path: str,
        line_number: int | None = None,
        group_id: int | None = None,
        user_id: int | None = None,
        msg_id: int | None = None
    ):
        """
        记录发送记录到 command_003_nsfw/location.txt
        格式：单行JSON，包含时间、类型、内容预览、文件路径等信息
        限制：保留最近1000行
        """
        try:
            # 获取插件目录的父目录（plugins目录）
            current_script_path = os.path.abspath(__file__)
            plugins_dir = os.path.dirname(os.path.dirname(current_script_path))
            command_003_nsfw_dir = os.path.join(plugins_dir, "command_003_nsfw")
            location_file = os.path.join(command_003_nsfw_dir, "location.txt")
            
            # 确保目录存在
            os.makedirs(command_003_nsfw_dir, exist_ok=True)
            
            # 构建记录
            record = {
                "timestamp": datetime.now().isoformat(),
                "type": msg_type,
                "content_preview": content_preview,
                "file_path": file_path,
                "line_number": line_number,
                "group_id": group_id,
                "user_id": user_id,
                "msg_id": msg_id
            }
            
            # 追加到文件
            with open(location_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
            # 限制文件大小：保留最近1000行
            try:
                with open(location_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                if len(lines) > 1000:
                    # 只保留最后1000行
                    with open(location_file, "w", encoding="utf-8") as f:
                        f.writelines(lines[-1000:])
            except Exception:
                pass  # 如果读取失败，不处理
            
        except Exception as e:
            # 记录失败不影响主流程
            print(f"[KeywordsGraph] log_send_record failed: {e}")

    # ===== 撤回相关 =====
    @staticmethod
    async def _delayed_withdraw(bot: Bot, message_id: int, delay_seconds: int):
        try:
            await asyncio.sleep(delay_seconds)
            await bot.delete_msg(message_id=message_id)
        except Exception as e:
            # 记录一下，不中断流程
            print(f"[KeywordsGraph] withdraw failed: {e}")

    @staticmethod
    def parse_withdraw(withdraw: str, withdraw_max: int) -> int | None:
        """
        解析 withdraw：支持 'false' / '0' / '0s' 关闭，
        支持 '30s' / '5m' / '1h'，并裁剪到 withdraw_max。
        返回：秒（int）或 None
        """
        if not withdraw or withdraw.strip().lower() in {"false", "0", "0s"}:
            return None

        m = re.match(r"^(\d+)([smh]?)$", withdraw.strip().lower())
        if not m:
            return None

        value, unit = m.groups()
        sec = int(value)
        if unit == "m":
            sec *= 60
        elif unit == "h":
            sec *= 3600
        # 其余情况默认秒

        return min(sec, withdraw_max)

    # ===== 图片读取 =====
    def graph_bit(self) -> bytes:
        directory = self.path
        candidates = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        random.shuffle(candidates)

        direct_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
        convert_exts = {".avif", ".heic", ".heif"}

        for name in candidates:
            file_path = os.path.join(directory, name)
            ext = os.path.splitext(name)[1].lower()
            try:
                if ext in convert_exts:
                    with PILImage.open(file_path) as img:
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        return buf.getvalue()

                if ext in direct_exts:
                    with open(file_path, "rb") as f:
                        return f.read()

                # 其它未知后缀：尝试 Pillow 打开并转 PNG
                with PILImage.open(file_path) as img:
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    return buf.getvalue()

            except Exception as e:
                print(f"[KeywordsGraph] convert failed: {file_path}, err={e}")
                try:
                    from PIL import features
                    print("features.check('avif')=" + str(features.check('avif')))
                except Exception:
                    pass
                continue

        # 没图或都失败
        return b""

    import json

    def _list_image_files(self, directory: str) -> list[str]:
        """列出目录下可作为图片发送的文件（排除 text.txt 等）"""
        candidates = []
        for name in os.listdir(directory):
            p = os.path.join(directory, name)
            if not os.path.isfile(p):
                continue
            if name.lower() == "text.txt":
                continue
            candidates.append(p)
        return candidates

    def _read_text_units(self, directory: str) -> list[dict[str, Any]]:
        """
        如果存在 text.txt，读取其中非空行作为可发送的文本单位。
        - UTF-8
        - 非空行：strip 后不为空
        - 兼容你之前写入的 JSONL：如果这一行能 json.loads 且含 text 字段，就取 text
        返回：list[{"text": str, "file_path": str, "line_number": int}]
        """
        txt_path = os.path.join(directory, "text.txt")
        if not os.path.exists(txt_path):
            return []

        units: list[dict[str, Any]] = []
        with open(txt_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                raw = line.rstrip("\n")
                if not raw.strip():
                    continue

                # 兼容 JSONL（你之前的 append_text_record 写法）
                s = raw.strip()
                if s.startswith("{") and s.endswith("}"):
                    try:
                        obj = json.loads(s)
                        if isinstance(obj, dict) and "text" in obj:
                            text_val = obj.get("text", "")
                            if isinstance(text_val, str) and text_val.strip():
                                units.append({
                                    "text": text_val,
                                    "file_path": txt_path,
                                    "line_number": line_num
                                })
                                continue
                    except Exception:
                        pass

                # 普通纯文本行
                units.append({
                    "text": raw,
                    "file_path": txt_path,
                    "line_number": line_num
                })

        return units

    def pick_unit(self) -> dict[str, Any] | None:
        """
        返回一个随机 unit：
          {"type": "image", "bytes": <...>, "file_path": <...>}   或
          {"type": "text",  "text":  <...>, "file_path": <...>, "line_number": <...>}

        若没有任何可用内容，返回 None
        """
        directory = self.path

        # 图片候选（按你原逻辑：支持直接读 bytes 或 Pillow 转 PNG）
        file_paths = self._list_image_files(directory)

        # 文本候选
        text_units = self._read_text_units(directory)

        # 构造 pool：每张图 / 每行文本都是一个 unit
        pool: list[tuple[str, Any]] = []
        pool += [("image_path", p) for p in file_paths]
        pool += [("text", t) for t in text_units]

        if not pool:
            return None

        kind, payload = random.choice(pool)

        if kind == "text":
            # payload 是一个字典，包含 text, file_path, line_number
            return {
                "type": "text",
                "text": payload["text"],
                "file_path": payload["file_path"],
                "line_number": payload["line_number"]
            }

        # kind == "image_path"
        file_path = payload
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower()

        direct_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
        convert_exts = {".avif", ".heic", ".heif"}

        try:
            if ext in direct_exts:
                with open(file_path, "rb") as f:
                    return {"type": "image", "bytes": f.read(), "file_path": file_path}

            if ext in convert_exts:
                with PILImage.open(file_path) as img:
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    return {"type": "image", "bytes": buf.getvalue(), "file_path": file_path}

            # 其它未知后缀：尝试 Pillow 打开并转 PNG
            with PILImage.open(file_path) as img:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return {"type": "image", "bytes": buf.getvalue(), "file_path": file_path}

        except Exception as e:
            print(f"[KeywordsGraph] pick_unit image convert failed: {file_path}, err={e}")
            return None

    # ===== 注意：你原文件中还有一个同名 parse_withdraw，这里保留以保持一致（先不优化） =====
    def parse_withdraw(self, withdraw: str, withdraw_max: int) -> int | None:
        """解析 withdraw 参数，支持 false / 30s / 5m / 1h，带上限"""
        if not withdraw or withdraw.lower() in {"false", "0", "0s"}:
            return None

        match = re.match(r"^(\d+)([smh]?)$", withdraw.strip().lower())
        if not match:
            return None

        value, unit = match.groups()
        value = int(value)

        if unit == "m":
            value *= 60
        elif unit == "h":
            value *= 3600
        # unit == "s" 或空，默认秒

        # 裁剪到上限
        return min(value, withdraw_max)


# =========================
#       工厂 & 配置
# =========================

DEFAULTS: Dict[str, Any] = {
    "priority": 10,
    "temp": False,
    "probability": 0.9,
    "withdraw": "60s",
    "withdraw_max": 3600,
}

def _ensure_set(x: Iterable[str] | Set[str]) -> Set[str]:
    return set(x) if not isinstance(x, set) else x

def _validate_item(name: str, item: Dict[str, Any]) -> None:
    required = ["keywords", "path"]
    missing = [k for k in required if k not in item]
    if missing:
        raise ValueError(f"[{name}] 缺少必要字段: {missing}")
    if not _ensure_set(item["keywords"]):
        raise ValueError(f"[{name}] keywords 不能为空")


def build_keywords_graphs(config_map: Dict[str, Dict[str, Any]]) -> Dict[str, "KeywordsGraph"]:
    """
    遍历配置字典，创建并返回 {name: KeywordsGraph实例} 的注册表。
    - 单项里写的值会覆盖 DEFAULTS
    - 支持 keywords 为 list/tuple/set
    """
    registry: Dict[str, "KeywordsGraph"] = {}

    for name, cfg in config_map.items():
        conf = {**DEFAULTS, **cfg}
        _validate_item(name, conf)
        conf["keywords"] = _ensure_set(conf["keywords"])

        allowed_keys = {"keywords", "path", "priority", "temp", "probability", "withdraw", "withdraw_max"}
        init_kwargs = {k: conf[k] for k in allowed_keys if k in conf}

        registry[name] = KeywordsGraph(**init_kwargs)

    return registry


# =========================
#         大字典
# =========================
def _abs_from_here(rel_or_abs: str) -> str:
    """把配置里的路径（相对/绝对）统一成基于本文件的绝对路径"""
    current_script_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_script_path)
    p = rel_or_abs
    if os.path.isabs(p):
        return os.path.normpath(p)
    return os.path.normpath(os.path.abspath(os.path.join(current_directory, p)))

def _is_serial_token(s: str) -> bool:
    return s.isdigit()

def extract_folder_order(folder_name: str) -> str | None:
    """
    从文件夹名中提取顺序标识 folder_order

    支持：
      a001_xxx           -> a001
      pjsk_002_xxx       -> pjsk_002
      animal_005_xxx     -> animal_005

    返回 None 表示无法识别
    """
    parts = folder_name.split("_")
    if not parts:
        return None

    # 情况 1：a001_xxx（a + 3 位数字粘在一起）
    if re.fullmatch(r"a\d{3}", parts[0]):
        return parts[0]

    # 情况 2：prefix_003_xxx
    if len(parts) >= 2 and re.fullmatch(r"\d{3}", parts[1]):
        return f"{parts[0]}_{parts[1]}"

    return None


def _extract_auto_keywords(folder_name: str) -> set[str]:
    """
    规则：
    - a093_xxx_yyy：首 token 若匹配 ^a\\d{3}$ 视为 (type+serial) 合并项，剔除该 token
    - pjsk_004_xxx：若第二 token 是 3 位数字，则剔除前两个 token (type,serial)
    - 剩余 token 中，剔除纯数字 token
    - 其余 token 全部作为 keyword（不做大小写归一，按你习惯保留）
    """
    parts = [p for p in folder_name.split("_") if p]
    if not parts:
        return set()

    # 情况1：a093_xxx...
    if re.fullmatch(r"a\d{3}", parts[0]):
        parts = parts[1:]
    # 情况2：pjsk_004_xxx...
    elif len(parts) >= 2 and re.fullmatch(r"\d{3}", parts[1]):
        parts = parts[2:]
    # 其它：不特殊处理

    # 剔除纯数字
    parts = [p for p in parts if not _is_serial_token(p)]
    return set(parts)

def _hit_blacklist(folder_name: str, folder_path_abs: str, blacklist_keyword_set: set[str], blacklist_path_set: set[str]) -> bool:
    # keyword 黑名单：只要文件夹名包含任意一个黑名单字符串，就跳过
    for bad in blacklist_keyword_set:
        if bad and bad in folder_name:
            return True

    # path 黑名单：建议用绝对路径统一比较
    norm_abs = os.path.normpath(folder_path_abs)
    norm_blk = {os.path.normpath(x) for x in blacklist_path_set}
    return norm_abs in norm_blk

def _hit_push_blacklist(folder_name: str, push_blacklist: list[str]) -> bool:
    """检查文件夹名是否包含推送黑名单中的关键词"""
    folder_name_lower = folder_name.lower()
    for keyword in push_blacklist:
        if keyword and keyword.lower() in folder_name_lower:
            return True
    return False

def _scan_keyword_folders(meta_keyword_folders: list[str]) -> list[tuple[str, str]]:
    """
    返回 [(folder_name, folder_path_abs), ...]
    只扫描每个 meta 目录的“一级子目录”（你的手牌库结构就是这样）
    """
    results: list[tuple[str, str]] = []
    for root in meta_keyword_folders:
        root_abs = _abs_from_here(root)
        if not os.path.exists(root_abs):
            continue
        for name in os.listdir(root_abs):
            p = os.path.join(root_abs, name)
            if os.path.isdir(p):
                results.append((name, os.path.normpath(p)))
    return results

def build_keywords_config_from_scan(config: "Config") -> dict[str, dict[str, Any]]:
    # ===== 1. 顶部集中取配置 =====
    meta_folders = list(config.meta_keyword_folders)
    manual_map = {k: set(v) for k, v in config.manual_keywords_map.items()}

    blacklist_kw = set(config.blacklist_keyword_set)
    blacklist_path = set(config.blacklist_path_set)

    # 默认值
    default_priority = config.graph_priority
    default_temp = config.graph_temp
    default_probability = config.graph_probability
    default_withdraw = config.graph_withdraw
    default_withdraw_max = config.graph_withdraw_max

    # override maps（手动值）
    priority_map = config.priority_map
    temp_map = config.temp_map
    probability_map = config.probability_map
    withdraw_map = config.withdraw_map

    config_map: dict[str, dict[str, Any]] = {}
    
    # 获取推送黑名单
    push_blacklist = list(config.push_blacklist)

    for folder_name, folder_path_abs in _scan_keyword_folders(meta_folders):
        if _hit_blacklist(folder_name, folder_path_abs, blacklist_kw, blacklist_path):
            continue
        
        # 检查推送黑名单：如果文件夹名包含 push_blacklist 中的关键词，跳过
        if _hit_push_blacklist(folder_name, push_blacklist):
            continue

        auto_keywords = _extract_auto_keywords(folder_name)
        extra_keywords = manual_map.get(folder_name, set())
        keywords = set(auto_keywords) | set(extra_keywords)

        if not keywords:
            continue

        folder_order = extract_folder_order(folder_name)
        if not folder_order:
            continue

        # ===== 2. 构建最小 config =====
        item: dict[str, Any] = {
            "keywords": keywords,
            "path": folder_path_abs,
            "withdraw_max": default_withdraw_max,
        }

        # ===== 3. 仅在“非默认”时覆盖 =====
        if folder_order in priority_map:
            item["priority"] = priority_map[folder_order]

        if folder_order in temp_map:
            item["temp"] = temp_map[folder_order]

        if folder_order in probability_map:
            item["probability"] = probability_map[folder_order]

        if folder_order in withdraw_map:
            item["withdraw"] = withdraw_map[folder_order]

        config_map[folder_order] = item

    return config_map



# =========================
#       构建 & 暴露
# =========================
plugin_config = get_plugin_config(Config)


# generate configmap
KEYWORDS_CONFIG = build_keywords_config_from_scan(plugin_config)
KEYWORD_GRAPHS = build_keywords_graphs(KEYWORDS_CONFIG)

globals().update(KEYWORD_GRAPHS)

