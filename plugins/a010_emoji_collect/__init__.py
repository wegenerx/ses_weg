import time
import re
import asyncio
from datetime import datetime
import os
import json
import os
import ssl
import requests
from PIL import Image as PILImage, ImageSequence
from io import BytesIO
import io
from typing import Set

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

# 相当于先创建一个类型为on_keyword的事件响应器，再赋值给一个名为 word 的变量，使其成为一个事件响应器。
word = on_message(  # keywords={'对称', '平移'},
    # permission='GROUP_OWNER', # 第二个是permission参数，这个参数负责传入能触发此事件响应器的消息发送者类型，也就是哪些人能触发这个响应器。一般来说重要的指令都会加上一些权限限制，诸如操作机器人后台的一些指令。常见的 permission 有 SUPERUSER(写在.env 文件中的超级用户)，GROUP_ADMIN(群管理员)和 GROUP_OWNER(群主)，这些是框架本身提供的。除此以外我们也可以自定义权限组，当然这个内容之后再谈。
    priority=1,
    block=False
)


def image_to_bytes(image: PILImage.Image, format: str = "PNG") -> bytes:
    byte_stream = io.BytesIO()
    fmt = image.format or format
    image.save(byte_stream, format=fmt)
    data = byte_stream.getvalue()
    byte_stream.close()
    return data



def get_image_from_url(url: str) -> PILImage:
    '''

    :param url:
    :return:
    '''

    # 创建 SSL 上下文
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.set_ciphers('DEFAULT')
    SSL_CONTEXT.options |= ssl.OP_NO_SSLv2
    SSL_CONTEXT.options |= ssl.OP_NO_SSLv3
    SSL_CONTEXT.options |= ssl.OP_NO_TLSv1
    SSL_CONTEXT.options |= ssl.OP_NO_TLSv1_1
    SSL_CONTEXT.options |= ssl.OP_NO_COMPRESSION

    try:
        # 发送 HTTP 请求获取图片
        response = requests.get(url)  # , verify=SSL_CONTEXT)
        response.raise_for_status()  # 检查请求是否成功

        # 将响应内容加载为图片
        image = PILImage.open(BytesIO(response.content))

        return image

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
    except IOError as e:
        print(f"图片加载失败: {e}")


async def get_reply_content(bot: Bot, reply_msg_id: int) -> UniMsg:
    try:
        reply_content = await bot.get_msg(message_id=reply_msg_id)
        return UniMsg(reply_content)

    except Exception as e:
        from nonebot.log import logger
        logger.error(f"获取回复消息内容失败: {e}")
        return UniMsg()


def 拼接(input_img: PILImage) -> list[PILImage]:
    # 横向拼接
    def Horizontal_splicing(left_img, right_img):
        # 获取两个图片的尺寸
        width1, height1 = left_img.size
        width2, height2 = right_img.size

        # 创建一个新的空白图片，宽度为两个图片的宽度之和，高度为两个图片中较高的那个
        new_img = PILImage.new("RGB", (width1 + width2, max(height1, height2)))

        # 将两个图片粘贴到新的空白图片上
        new_img.paste(left_img, (0, 0))
        new_img.paste(right_img, (width1, 0))

        # 保存新的图片
        return new_img

    # 纵向拼接
    def Longitudinal_splicing(top_img, bottom_img):
        # 获取两个图片的尺寸
        width1, height1 = top_img.size
        width2, height2 = bottom_img.size

        # 创建一个新的空白图片，宽度为两个图片中较宽的那个，高度为两个图片的高度之和
        new_img = PILImage.new("RGB", (max(width1, width2), height1 + height2))

        # 将两个图片粘贴到新的空白图片上
        new_img.paste(top_img, (0, 0))
        new_img.paste(bottom_img, (0, height1))

        # 保存新的图片
        return new_img

    def FLIP_LEFT_RIGHT(image):
        return image.transpose(PILImage.FLIP_LEFT_RIGHT)

    def FLIP_TOP_BOTTOM(image):
        return image.transpose(PILImage.FLIP_TOP_BOTTOM)

    img = input_img
    width, height = img.size
    center_x = width // 2
    center_y = height // 2

    # 制造半图像
    left_half = img.crop((0, 0, center_x, height))
    right_half = img.crop((center_x, 0, width, height))
    top_half = img.crop((0, 0, width, center_y))
    bottom_half = img.crop((0, center_y, width, height))

    # 拼接半图像
    _2lefthalf = Horizontal_splicing(left_half, FLIP_LEFT_RIGHT(left_half))
    _2righthalf = Horizontal_splicing(FLIP_LEFT_RIGHT(right_half), right_half)
    _2tophalf = Longitudinal_splicing(top_half, FLIP_TOP_BOTTOM(top_half))
    _2bottomhalf = Longitudinal_splicing(FLIP_TOP_BOTTOM(bottom_half), bottom_half)

    # 拼接二图像
    _2left = Horizontal_splicing(img, FLIP_LEFT_RIGHT(img))
    _2right = Horizontal_splicing(FLIP_LEFT_RIGHT(img), img)
    _2top = Longitudinal_splicing(img, FLIP_TOP_BOTTOM(img))
    _2bottom = Longitudinal_splicing(FLIP_TOP_BOTTOM(img), img)

    return [_2lefthalf, _2righthalf, _2tophalf, _2bottomhalf, _2left, _2right, _2top, _2bottom]


def 对称(image: PILImage, 关键字: str, ) -> PILImage:
    # init
    chaos_img: list = 拼接(image)
    # cycle

    if '对称' in 关键字:
        if '左' in 关键字:
            PILImage = chaos_img[0]
        elif '右' in 关键字:
            PILImage = chaos_img[1]
        elif '上' in 关键字:
            PILImage = chaos_img[2]
        elif '下' in 关键字:
            PILImage = chaos_img[3]
    elif '平移' in 关键字:
        if '左' in 关键字:
            PILImage = chaos_img[4]
        elif '右' in 关键字:
            PILImage = chaos_img[5]
        elif '上' in 关键字:
            PILImage = chaos_img[6]
        elif '下' in 关键字:
            PILImage = chaos_img[7]

    return PILImage


def uni_msg_annotation():
    ''
    # reply = Reply(id=origin_msg.get_message_id())
    # msgs.append(reply)  # self_iduser_idtimemessage_idmessage_seqreal_idmessage_typesenderraw_messagefontsub_typemessagemessage_formatpost_typegroup_id[image]
    # msgs.append(reply_msg)
    # msgs.append(Text(url))
    # print(type(Text('success')))  # <class 'nonebot_plugin_alconna.uniseg.segment.Text'>
    # msgs.append(Text(str(origin_msg))) [reply]对称
    # msgs.append(Text(str(origin_msg.reply()))) # error
    # msgs.append(Text(str(origin_msg.get_message_id())))
    # await word.finish(str(bot.self_id))
    # await word.finish('success')
    # await msgs.send()

    # 消息一：希望对称的图片消息
    # 消息二：对称 str
    # 消息三：bot发送的对称图片


def find_folder(keyword):
    if keyword == '':
        return False

    import os

    # 现在用一个列表来装所有目标目录（相对路径）
    target_directories = [
        r"..\keyword_005_keywords_graph\a001_all_graph",
        r"..\auto_001_bad_morning",
        r"..\keyword_005_keywords_graph\a001_all_graph\folder_001_collect",
        r"..\keyword_005_keywords_graph\a001_all_graph\folder_002_音游"
        # 你以后可以继续加更多路径
        # r"..\xxx",
    ]

    # 获取当前脚本所在目录（绝对路径）
    current_script_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_script_path)

    # 将所有相对路径转为绝对路径
    abs_directories = [
        os.path.abspath(os.path.join(current_directory, d))
        for d in target_directories
    ]

    # 按顺序遍历每一个目录
    for directory in abs_directories:
        if not os.path.exists(directory):
            print(f"目录 {directory} 不存在")
            continue

        for folder_name in os.listdir(directory):
            folder_path = os.path.join(directory, folder_name)
            if os.path.isdir(folder_path) and keyword in folder_name:
                return folder_path, folder_name  # 找到就返回

    return False

def _abs_keywords_graph_root() -> str:
    """返回 ..\\keyword_005_keywords_graph 的绝对路径"""
    current_script_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_script_path)
    return os.path.abspath(os.path.join(current_directory, r"..\keyword_005_keywords_graph\a001_all_graph"))

def _sanitize_part(s: str) -> str:
    """清理不可作为 Windows 文件名的字符，并去掉多余空白"""
    s = s.strip()
    # Windows 禁止：\ / : * ? " < > |
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    # 把连续空白压成一个下划线（可选）
    s = re.sub(r"\s+", "_", s)
    return s

def _next_index_for_prefix_fill_gaps(root: str, prefix: str) -> int:
    """
    从 001 开始找最小未占用序号：
      - prefix == "a":   a001_xxx
      - 其他:            {prefix}_001_xxx
    """
    if not os.path.exists(root):
        return 1

    if prefix == "a":
        # a001_... 或 a001（后面可能无下划线）
        pat = re.compile(r"^a(\d{3})(?:\b|_)")
    else:
        p = re.escape(prefix)
        pat = re.compile(rf"^{p}_(\d{{3}})(?:\b|_)")

    used: Set[int] = set()
    for name in os.listdir(root):
        full = os.path.join(root, name)
        if not os.path.isdir(full):
            continue
        m = pat.match(name)
        if not m:
            continue
        try:
            used.add(int(m.group(1)))
        except Exception:
            pass

    i = 1
    while i in used:
        i += 1
    return i

def _build_folder_name(prefix: str, idx: int, key: str, en: str, cn: str) -> str:
    key = _sanitize_part(key)
    en = _sanitize_part(en)
    cn = _sanitize_part(cn)

    if prefix == "a":
        head = f"a{idx:03d}"
    else:
        head = f"{_sanitize_part(prefix)}_{idx:03d}"

    return f"{head}_{key}_{en}_{cn}"

def parse_add_command(text: str):
    """
    支持：
      add <prefix> <token1> [token2 token3 ...]
    最少 2 个参数（prefix + 至少 1 个 token）
    返回：(prefix, tokens:list[str]) 或 None
    """
    t = text.strip()
    if not t.lower().startswith("add "):
        return None

    parts = t.split()
    # parts[0] = add
    if len(parts) < 3:
        return None

    prefix = parts[1]
    tokens = parts[2:]
    return prefix, tokens



# return absolute path
def get_current_script_path():
    # 获取当前脚本的绝对路径
    return os.path.abspath(__file__)


def save_image(path, image_byte):
    # 检查路径是否存在，如果不存在则创建
    if not os.path.exists(path):
        os.makedirs(path)

    # 获取当前时间戳（精确到秒）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 判断图片是否为动图（GIF）
    # GIF 文件头通常是 b'\x47\x49\x46\x38\x39\x61' 或 b'\x47\x49\x46\x38\x37\x61'
    gif_header = image_byte[:6]
    if gif_header in [b'\x47\x49\x46\x38\x39\x61', b'\x47\x49\x46\x38\x37\x61']:
        file_extension = "gif"
    else:
        file_extension = "png"  # 默认保存为 PNG 格式

    # 构造文件名
    file_name = f"{timestamp}.{file_extension}"
    file_path = os.path.join(path, file_name)

    # 将二进制图片数据写入文件
    with open(file_path, "wb") as file:
        file.write(image_byte)

    print(f"图片已保存到: {file_path}")


def save_PIL(path, PILImage_: PILImage):
    """
    保存 PIL 图像对象到指定路径。

    参数:
        path (str): 图像保存的目录路径。
        PILImage_ (PIL.Image.Image): 要保存的 PIL 图像对象。
    """
    # 检查路径是否存在，如果不存在则创建
    if not os.path.exists(path):
        os.makedirs(path)

    # 获取当前时间戳（精确到秒）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 获取图像的格式（如果图像有格式信息，否则默认为 PNG）
    file_extension = PILImage_.format.lower() if PILImage_.format else "png"

    # 构造文件名
    file_name = f"{timestamp}.{file_extension}"
    file_path = os.path.join(path, file_name)

    if file_extension == "gif":
        frames = [frame.copy() for frame in ImageSequence.Iterator(PILImage_)]

        duration = PILImage_.info.get("duration", 80)  # 兜底
        loop = PILImage_.info.get("loop", 0)

        frames[0].save(
            file_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=loop,
            disposal=2,  # 保留也行，不保留也行 # https://usage.imagemagick.org/anim_basics/#none https://chenjiehua.me/python/pil-patch-gif-disposal.html https://blog.csdn.net/qq_40878431/article/details/82939733
        )

    else:
        # 保存普通图像
        PILImage_.save(file_path)

    print(f"图片已保存到: {file_path}")


def extract_first_image_url(reply_msg_info: dict) -> str | bool | None:
    """
    返回规则：
    - 有 image        -> 返回 image 的 url (str)
    - 纯 text         -> 返回 False
    - 其他（无 image 且含非 text） -> 返回 None
    """
    segments = reply_msg_info.get("message", [])
    if not segments:
        return None

    has_text = False

    for seg in segments:
        seg_type = seg.get("type")

        if seg_type == "image":
            data = seg.get("data", {})
            url = data.get("url")
            if url:
                return url

        elif seg_type == "text":
            # 标记存在纯文本
            if seg.get("data", {}).get("text", "").strip():
                has_text = True

        else:
            # 出现非 text / image 的 segment
            has_text = False  # 直接打断“纯文字”可能
            break

    # 循环结束仍未 return，说明没有 image
    if has_text:
        return False  # 纯文字
    return None      # 其他情况


from pathlib import Path
import json
from datetime import datetime

def extract_all_text(reply_msg_info: dict) -> str:
    """把消息里所有 text 段按顺序拼起来（保留原始换行/空格）"""
    parts = []
    for seg in reply_msg_info.get("message", []):
        if seg.get("type") == "text":
            parts.append(seg.get("data", {}).get("text", ""))
    return "".join(parts)

def append_text_record(folder_path: str, text: str) -> None:
    """
    追加写入 folder_path/text.txt
    - UTF-8
    - 追加模式
    - 不存在就新建
    - 每条记录一行（JSON），多行文本会被无失真压成一行
    """
    Path(folder_path).mkdir(parents=True, exist_ok=True)
    txt_file = Path(folder_path) / "text.txt"

    record = {
        "ts": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "text": text,  # 这里保持原始文本（可含多行）
    }

    # ensure_ascii=False 保留中文；json 会把换行编码为 \n，保证单行
    line = json.dumps(record, ensure_ascii=False)

    with txt_file.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")

import unicodedata

def is_single_punct(text: str) -> bool:
    """
    True: 只有一个字符，且该字符是 Unicode 标点（类别 P*）
    False: 例如 '⑨' (No)、'A'、'9'、'。' 以外的情况
    """
    s = (text or "").strip()
    if len(s) != 1:
        return False
    ch = s
    return unicodedata.category(ch).startswith("P")  # P* 全部标点


@word.handle()
async def reply(bot: Bot, origin_msg: UniMsg, event: MessageEvent):  # state: T_State):
    # ===== group routing config =====
    group_white_list = ['937786461']     # 在这里的群：会撤回（维持你原逻辑）
    log_group_chat = '872057585'         # 其他群：把提示发到这里，不撤回

    src_group_id = str(getattr(event, "group_id", ""))  # 非群消息会是 ""
    # 在白名单里：不撤回任何消息
    should_withdraw = (src_group_id not in group_white_list)

    async def send_notice(msg: str):
        """
        白名单群：提示发在原群，不撤回
        非白名单群：提示发到日志群，不撤回
        """
        try:
            if src_group_id in group_white_list:
                await word.send(msg)
            else:
                await bot.send_group_msg(
                    group_id=int(log_group_chat),
                    message=msg
                )
        except Exception as e:
            nonebot.logger.error(f"发送提示失败||{e}")

    # ========= 新增：add 创建手牌文件夹（不撤回）=========
    plain = origin_msg.extract_plain_text().strip()
    parsed = parse_add_command(plain)
    if parsed is not None:
        prefix, tokens = parsed

        root = _abs_keywords_graph_root()
        idx = _next_index_for_prefix_fill_gaps(root, prefix)

        # 清理 token（防 Windows 非法字符）
        safe_tokens = [_sanitize_part(t) for t in tokens if t.strip()]
        if not safe_tokens:
            await word.finish("参数不足，至少需要一个名称")

        # 构建目录名
        if prefix == "a":
            head = f"a{idx:03d}"
        else:
            head = f"{_sanitize_part(prefix)}_{idx:03d}"

        # 白名单 whitelist
        # if prefix not in {"a", "pjsk"}:
        #     await word.finish(f"不支持的前缀：{prefix}")

        folder_name = "_".join([head] + safe_tokens)
        folder_path = os.path.join(root, folder_name)

        if os.path.exists(folder_path):
            await word.finish(f"目录已存在：{folder_name}")

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # 不撤回
        await word.finish(f"已添加牌组：{folder_name}")
    # ===================================================

    if Reply in origin_msg:
        # create a unimsg to send
        # msgs = UniMessage()

        # reply dealing
        reply_msg = origin_msg[Reply, 0]  # print('reply_msg=', reply_msg)  # reply_msg= [reply] <class 'nonebot_plugin_alconna.uniseg.segment.Reply'>
        reply_msg_id = reply_msg.id  # 获取回复的消息(消息 1) ID # reply_msg_id= 293890509
        reply_msg_info = await bot.get_msg(message_id=reply_msg_id)  # print(json.dumps(reply_msg_info, indent=4))

        # original msg dealing
        ori_msg_text = origin_msg.extract_plain_text().strip()  # print('plaintext = ', ori_msg_text) # 蛾 对称
        from ses_weg.services import ban_list as banlist_svc
        BAN_SET = banlist_svc.load_set()
        # group_white_list = ['937786461']
        # log_group_chat = '872057585'

        # find folder
        found = find_folder(ori_msg_text)
        if ori_msg_text not in BAN_SET and not is_single_punct(ori_msg_text) and found:
            path, folder_name = found

            # message to bytes
            url = extract_first_image_url(reply_msg_info)

            # 1) 纯文字：先 pass（不做任何处理）
            if url is False:
                # 纯文字：写入 path/text.txt（一行一条，JSON，无失真）
                text = extract_all_text(reply_msg_info).strip()
                if text:
                    append_text_record(path, text)
                else:
                    await word.finish("回复内容是空文本")

                # 可选：是否也撤回消息（和图片逻辑一致的话就保留）
                # 仅白名单群撤回
                if should_withdraw:
                    try:
                        await bot.delete_msg(message_id=reply_msg_id)
                    except Exception as e:
                        nonebot.logger.error(f"复读自动跟随撤回失败||{e}")

                    await asyncio.sleep(0.5)

                    try:
                        await bot.delete_msg(message_id=origin_msg.get_message_id())
                    except Exception as e:
                        nonebot.logger.error(f"复读自动跟随撤回失败||{e}")

                # 提示：白名单群在原群发并撤回；非白名单发到日志群不撤回
                await send_notice(
                    f"已记录文本：{ori_msg_text} ( {folder_name if 'collect' not in folder_name else 'null'} ) "
                )


            # 2) 其他：回复不包含可用内容（并结束本次 handler）
            elif url is None:
                await word.finish("回复内容不包含可用内容")

            # 3) 图片：按目前情况处理
            else:
                PILImage_: PILImage = get_image_from_url(url)
                if PILImage_ is None:
                    await word.finish("图片下载或解析失败")

                # await word.send(str(PILImage_.format) + ' ' + str(PILImage_.is_animated))
                image_byte = image_to_bytes(PILImage_)  # PIL_image to bytes

                # save
                # save_image(path, image_byte)
                save_PIL(path, PILImage_)

                # delete message
                # 仅白名单群撤回
                if should_withdraw:
                    try:
                        await bot.delete_msg(message_id=reply_msg_id)
                    except Exception as e:
                        nonebot.logger.error(f"复读自动跟随撤回失败||{e}")

                    await asyncio.sleep(0.5)

                    try:
                        await bot.delete_msg(message_id=origin_msg.get_message_id())
                    except Exception as e:
                        nonebot.logger.error(f"复读自动跟随撤回失败||{e}")

                # 组织提示文案
                if 'collect' in folder_name:
                    msg = f"已加入手牌：{ori_msg_text} ( null ) "
                else:
                    msg = f"已加入手牌：{ori_msg_text} ( {folder_name} ) "

                # 提示路由：白名单原群且撤回；非白名单发日志群不撤回
                await send_notice(msg)



