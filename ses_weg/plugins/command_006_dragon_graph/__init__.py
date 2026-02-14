import json
import ssl
import requests
import re
import math
import numpy as np
from PIL import Image as PILImage, ImageFilter, ImageEnhance, ImageOps, ImageDraw, ImageFont
from io import BytesIO
import io
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass

import nonebot
from nonebot import get_plugin_config, on_command, on_message
from nonebot.plugin import PluginMetadata
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment, Bot, MessageEvent
from nonebot_plugin_alconna.uniseg import Hyper, Image, MsgTarget, Reply, Text, UniMessage, UniMsg, MessageId

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="command_006_dragon_graph",
    description="图像处理插件：对称、镜像、平移等变换，以及图片合并功能",
    usage="回复图片后输入变换命令（如：对称左、模糊[2.5]）或使用 \\merge 合并图片",
    config=Config,
)

config = get_plugin_config(Config)

# ===== 原有功能：图像变换 =====
word = on_keyword(keywords={'对称', '镜像', '平移', '黑白', '模糊', '锐化', '边缘检测', '去噪', '放大镜', '凸透镜', '凹透镜', '老花镜'},
                  priority=1,
                  )


def image_to_bytes(image: PILImage.Image, format: str = 'PNG') -> bytes:
    """将 PIL Image 对象转换为二进制数据"""
    byte_stream = io.BytesIO()
    image.save(byte_stream, format=format)
    byte_data = byte_stream.getvalue()
    byte_stream.close()
    return byte_data


def get_image_from_url(url: str) -> PILImage:
    """从URL获取图片"""
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.set_ciphers('DEFAULT')
    SSL_CONTEXT.options |= ssl.OP_NO_SSLv2
    SSL_CONTEXT.options |= ssl.OP_NO_SSLv3
    SSL_CONTEXT.options |= ssl.OP_NO_TLSv1
    SSL_CONTEXT.options |= ssl.OP_NO_TLSv1_1
    SSL_CONTEXT.options |= ssl.OP_NO_COMPRESSION

    try:
        response = requests.get(url)
        response.raise_for_status()
        image = PILImage.open(BytesIO(response.content))
        return image
    except requests.exceptions.RequestException as e:
        nonebot.logger.error(f"请求失败: {e}")
        return None
    except IOError as e:
        nonebot.logger.error(f"图片加载失败: {e}")
        return None


async def get_reply_content(bot: Bot, reply_msg_id: int) -> UniMsg:
    try:
        reply_content = await bot.get_msg(message_id=reply_msg_id)
        return UniMsg(reply_content)
    except Exception as e:
        nonebot.logger.error(f"获取回复消息内容失败: {e}")
        return UniMsg()


def 拼接(input_img: PILImage) -> dict:
    """生成所有变换结果"""
    def Horizontal_splicing(left_img, right_img):
        width1, height1 = left_img.size
        width2, height2 = right_img.size
        new_img = PILImage.new("RGB", (width1 + width2, max(height1, height2)))
        new_img.paste(left_img, (0, 0))
        new_img.paste(right_img, (width1, 0))
        return new_img

    def Longitudinal_splicing(top_img, bottom_img):
        width1, height1 = top_img.size
        width2, height2 = bottom_img.size
        new_img = PILImage.new("RGB", (max(width1, width2), height1 + height2))
        new_img.paste(top_img, (0, 0))
        new_img.paste(bottom_img, (0, height1))
        return new_img

    def FLIP_LEFT_RIGHT(image):
        return image.transpose(PILImage.FLIP_LEFT_RIGHT)

    def FLIP_TOP_BOTTOM(image):
        return image.transpose(PILImage.FLIP_TOP_BOTTOM)

    img = input_img
    width, height = img.size
    center_x = width // 2
    center_y = height // 2

    left_half = img.crop((0, 0, center_x, height))
    right_half = img.crop((center_x, 0, width, height))
    top_half = img.crop((0, 0, width, center_y))
    bottom_half = img.crop((0, center_y, width, height))

    result = {}
    result['对称左'] = Horizontal_splicing(left_half, FLIP_LEFT_RIGHT(left_half))
    result['对称右'] = Horizontal_splicing(FLIP_LEFT_RIGHT(right_half), right_half)
    result['对称上'] = Longitudinal_splicing(top_half, FLIP_TOP_BOTTOM(top_half))
    result['对称下'] = Longitudinal_splicing(FLIP_TOP_BOTTOM(bottom_half), bottom_half)
    result['镜像左'] = Horizontal_splicing(img, FLIP_LEFT_RIGHT(img))
    result['镜像右'] = Horizontal_splicing(FLIP_LEFT_RIGHT(img), img)
    result['镜像上'] = Longitudinal_splicing(img, FLIP_TOP_BOTTOM(img))
    result['镜像下'] = Longitudinal_splicing(FLIP_TOP_BOTTOM(img), img)
    result['平移左'] = Horizontal_splicing(left_half, left_half)
    result['平移右'] = Horizontal_splicing(right_half, right_half)
    result['平移上'] = Longitudinal_splicing(top_half, top_half)
    result['平移下'] = Longitudinal_splicing(bottom_half, bottom_half)

    return result


def 解析参数(关键字: str, 关键词: str) -> Optional[float]:
    """解析参数"""
    pattern = rf"(?<!\S){re.escape(关键词)}\s*([+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)(?!\S)"
    match = re.search(pattern, 关键字, re.IGNORECASE | re.VERBOSE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def 黑白(image: PILImage) -> PILImage:
    return image.convert('L').convert('RGB')


def 模糊(image: PILImage, radius: float) -> PILImage:
    radius = max(0.5, min(10.0, abs(radius)))
    if radius < 1:
        radius = 1
    return image.filter(ImageFilter.GaussianBlur(radius=int(radius)))


def 锐化(image: PILImage, factor: float) -> PILImage:
    factor = max(0.5, min(5.0, abs(factor)))
    enhancer = ImageEnhance.Sharpness(image)
    return enhancer.enhance(1.0 + factor * 0.5)


def 边缘检测(image: PILImage) -> PILImage:
    gray = image.convert('L')
    edges = gray.filter(ImageFilter.FIND_EDGES)
    return edges.convert('RGB')


def 去噪(image: PILImage, strength: float) -> PILImage:
    strength = max(0.5, min(3.0, abs(strength)))
    if strength < 1.0:
        result = image.filter(ImageFilter.SMOOTH)
    elif strength < 2.0:
        result = image.filter(ImageFilter.MedianFilter())
    else:
        result = image.filter(ImageFilter.MedianFilter())
        result = result.filter(ImageFilter.MedianFilter())
    return result


def 球形畸变(image: PILImage, strength: float) -> PILImage:
    """球形畸变效果"""
    if strength is None or not np.isfinite(strength):
        strength = 1.0
    strength = abs(float(strength))
    strength = max(1e-6, min(1e6, strength))

    if image.mode != "RGB":
        image = image.convert("RGB")

    width, height = image.size
    if width <= 1 or height <= 1:
        return image

    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    max_radius = math.hypot(cx, cy)
    if max_radius <= 1e-12:
        return image

    src = np.asarray(image, dtype=np.uint8)
    if src.ndim != 3 or src.shape[2] != 3:
        image = image.convert("RGB")
        src = np.asarray(image, dtype=np.uint8)

    if abs(strength - 1.0) < 1e-12:
        gamma = 1.0
    elif strength < 1.0:
        k = 1.0
        gamma = math.exp(-k * (1.0 / strength - 1.0))
        gamma = max(1e-6, min(1.0, gamma))
    else:
        a = 1.0
        gamma = 1.0 + a * math.log1p(strength - 1.0)
        gamma = max(1.0, min(1e6, gamma))

    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    dx = x - cx
    dy = y - cy
    r_out = np.sqrt(dx * dx + dy * dy)
    d_out = np.clip(r_out / max_radius, 0.0, 1.0)
    d_in = np.power(d_out, gamma, dtype=np.float32)
    r_in = d_in * max_radius

    eps = 1e-8
    scale = r_in / (r_out + eps)
    scale = np.where(r_out < eps, 0.0, scale).astype(np.float32)

    src_x = cx + dx * scale
    src_y = cy + dy * scale
    src_x = np.clip(src_x, 0.0, width - 1.0)
    src_y = np.clip(src_y, 0.0, height - 1.0)

    x0 = np.floor(src_x).astype(np.int32)
    y0 = np.floor(src_y).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, width - 1)
    y1 = np.clip(y0 + 1, 0, height - 1)

    wx = (src_x - x0).astype(np.float32)
    wy = (src_y - y0).astype(np.float32)

    Ia = src[y0, x0].astype(np.float32)
    Ib = src[y0, x1].astype(np.float32)
    Ic = src[y1, x0].astype(np.float32)
    Id = src[y1, x1].astype(np.float32)

    wa = (1.0 - wx) * (1.0 - wy)
    wb = wx * (1.0 - wy)
    wc = (1.0 - wx) * wy
    wd = wx * wy

    out = (Ia * wa[..., None] + Ib * wb[..., None] + Ic * wc[..., None] + Id * wd[..., None])
    out = np.clip(out + 0.5, 0, 255).astype(np.uint8)
    return PILImage.fromarray(out, mode="RGB")


def 对称(image: PILImage, 关键字: str) -> PILImage:
    """根据关键字返回对应的变换图像"""
    if '黑白' in 关键字:
        return 黑白(image)
    if '模糊' in 关键字:
        param = 解析参数(关键字, '模糊')
        return 模糊(image, param if param is not None else 2.0)
    if '锐化' in 关键字:
        param = 解析参数(关键字, '锐化')
        return 锐化(image, param if param is not None else 2.0)
    if '边缘检测' in 关键字:
        return 边缘检测(image)
    if '去噪' in 关键字:
        param = 解析参数(关键字, '去噪')
        return 去噪(image, param if param is not None else 1.5)
    
    lens_keywords = ['放大镜', '凸透镜', '凹透镜', '老花镜']
    for lens_keyword in lens_keywords:
        if lens_keyword in 关键字:
            param = 解析参数(关键字, lens_keyword)
            return 球形畸变(image, param if param is not None else 1.5)
    
    transform_dict = 拼接(image)
    方向 = None
    if '左' in 关键字:
        方向 = '左'
    elif '右' in 关键字:
        方向 = '右'
    elif '上' in 关键字:
        方向 = '上'
    elif '下' in 关键字:
        方向 = '下'
    
    类型 = None
    if '对称' in 关键字:
        类型 = '对称'
    elif '镜像' in 关键字:
        类型 = '镜像'
    elif '平移' in 关键字:
        类型 = '平移'
    
    if 类型 and 方向:
        key = f"{类型}{方向}"
        if key in transform_dict:
            return transform_dict[key]
    
    return image


@word.handle()
async def reply(bot: Bot, origin_msg: UniMsg):
    """原有功能：图像变换处理"""
    if Reply in origin_msg:
        reply_msg = origin_msg[Reply, 0]
        reply_msg_id = reply_msg.id
        reply_msg_info = await bot.get_msg(message_id=reply_msg_id)
        ori_msg_text = origin_msg.extract_plain_text()
        url = reply_msg_info['message'][0]['data']['url']
        PILImage_ = get_image_from_url(url)
        if PILImage_ is None:
            return
        PILImage_ = 对称(image=PILImage_, 关键字=ori_msg_text)
        image_byte = image_to_bytes(PILImage_)
        await word.send(MessageSegment.image(image_byte))


# ===== 新增功能：图片合并 =====

class MergeMode(Enum):
    """合并模式"""
    HORIZONTAL = "水平"  # 水平拼接
    VERTICAL = "垂直"    # 垂直拼接
    OVERLAP = "重叠"     # 重叠合成
    GRID = "网格"        # 网格拼接
    CIRCLE = "圆形"      # 圆形/环形排列
    NINE_GRID = "九宫格"  # 3x3网格
    DIAGONAL = "对角线"   # 对角线拼接
    BLEND = "混合"       # 混合模式（叠加、柔光等）
    GIF = "动画"         # 动画GIF
    TEMPLATE = "模板"    # 模板布局


class PixelMode(Enum):
    """像素模式"""
    HIGHEST = "最高像素"  # 以最高像素为基准
    LOWEST = "最低像素"   # 以最低像素为基准


class BlendMode(Enum):
    """混合模式"""
    NORMAL = "正常"      # 正常（等透明度）
    MULTIPLY = "叠加"    # 叠加
    SCREEN = "柔光"      # 柔光
    OVERLAY = "强光"     # 强光
    SOFT_LIGHT = "软光"  # 软光
    HARD_LIGHT = "硬光"  # 硬光


class ScaleMode(Enum):
    """缩放模式"""
    KEEP_RATIO = "等比例"  # 等比例缩放
    FILL = "填充"         # 填充
    CROP = "裁剪"         # 裁剪


class SortMode(Enum):
    """排序模式"""
    SIZE = "尺寸"         # 按尺寸排序
    NONE = "不排序"       # 不排序


class MergeState(Enum):
    """合并状态"""
    IDLE = "idle"                    # 空闲
    WAIT_MODE = "wait_mode"          # 等待选择合并方式
    COLLECT_IMAGES = "collect_images"  # 收集图片
    WAIT_PIXEL = "wait_pixel"        # 等待选择像素模式
    WAIT_GRID_SIZE = "wait_grid_size"  # 等待网格尺寸（行x列）
    WAIT_BLEND_MODE = "wait_blend_mode"  # 等待混合模式
    WAIT_BACKGROUND = "wait_background"  # 等待背景色
    WAIT_SPACING = "wait_spacing"    # 等待间距/边距
    WAIT_OPTIONS = "wait_options"    # 等待其他选项（边框、圆角等）


# 全局状态管理：{user_id: {state, mode, images, pixel_mode, ...}}
merge_sessions: Dict[str, Dict] = {}

MAX_IMAGES = 20  # 增加最大图片数量以支持更多功能


def extract_image_from_message(msg_info: dict) -> Optional[PILImage]:
    """从消息中提取图片"""
    try:
        message = msg_info.get("message", [])
        for seg in message:
            if seg.get("type") == "image":
                url = seg.get("data", {}).get("url")
                if url:
                    return get_image_from_url(url)
    except Exception as e:
        nonebot.logger.error(f"提取图片失败: {e}")
    return None


def extract_image_from_unimsg(msg: UniMsg) -> Optional[PILImage]:
    """从UniMsg中提取图片"""
    try:
        if Image in msg:
            img_seg = msg[Image, 0]
            url = img_seg.url if hasattr(img_seg, 'url') else None
            if url:
                return get_image_from_url(url)
    except Exception as e:
        nonebot.logger.error(f"从UniMsg提取图片失败: {e}")
    return None


def resize_keep_ratio(img: PILImage, target_size: tuple) -> PILImage:
    """等比例缩放图片到目标尺寸"""
    img.thumbnail(target_size, PILImage.Resampling.LANCZOS)
    return img


def merge_horizontal(images: List[PILImage], pixel_mode: PixelMode) -> PILImage:
    """水平拼接：从左到右，等比例缩放到高度相等"""
    if not images:
        return None
    
    # 确定基准高度
    heights = [img.height for img in images]
    if pixel_mode == PixelMode.HIGHEST:
        target_height = max(heights)
    else:
        target_height = min(heights)
    
    # 等比例缩放所有图片到目标高度
    resized_images = []
    total_width = 0
    for img in images:
        ratio = target_height / img.height
        new_width = int(img.width * ratio)
        resized = img.resize((new_width, target_height), PILImage.Resampling.LANCZOS)
        resized_images.append(resized)
        total_width += new_width
    
    # 创建新图片
    result = PILImage.new("RGB", (total_width, target_height))
    x_offset = 0
    for resized in resized_images:
        result.paste(resized, (x_offset, 0))
        x_offset += resized.width
    
    return result


def merge_vertical(images: List[PILImage], pixel_mode: PixelMode) -> PILImage:
    """垂直拼接：从上到下，等比例缩放到宽度相等"""
    if not images:
        return None
    
    # 确定基准宽度
    widths = [img.width for img in images]
    if pixel_mode == PixelMode.HIGHEST:
        target_width = max(widths)
    else:
        target_width = min(widths)
    
    # 等比例缩放所有图片到目标宽度
    resized_images = []
    total_height = 0
    for img in images:
        ratio = target_width / img.width
        new_height = int(img.height * ratio)
        resized = img.resize((target_width, new_height), PILImage.Resampling.LANCZOS)
        resized_images.append(resized)
        total_height += new_height
    
    # 创建新图片
    result = PILImage.new("RGB", (target_width, total_height))
    y_offset = 0
    for resized in resized_images:
        result.paste(resized, (0, y_offset))
        y_offset += resized.height
    
    return result


def merge_overlap(images: List[PILImage], pixel_mode: PixelMode) -> PILImage:
    """重叠合成：非等比例拉伸到基准尺寸，等透明度合成"""
    if not images:
        return None
    
    # 确定基准尺寸
    sizes = [(img.width, img.height) for img in images]
    if pixel_mode == PixelMode.HIGHEST:
        target_size = max(sizes, key=lambda s: s[0] * s[1])
    else:
        target_size = min(sizes, key=lambda s: s[0] * s[1])
    
    target_width, target_height = target_size
    
    # 将所有图片拉伸到基准尺寸（非等比例）
    stretched_images = []
    for img in images:
        stretched = img.resize((target_width, target_height), PILImage.Resampling.LANCZOS)
        # 转换为RGBA以支持透明度
        if stretched.mode != "RGBA":
            stretched = stretched.convert("RGBA")
        stretched_images.append(stretched)
    
    # 等透明度合成（每张图片透明度 = 1 / 图片数量）
    alpha = 1.0 / len(stretched_images)
    
    # 创建结果图片
    result = PILImage.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    
    for img in stretched_images:
        # 创建带透明度的图片
        alpha_img = PILImage.new("RGBA", (target_width, target_height))
        alpha_data = []
        for pixel in img.getdata():
            r, g, b, a = pixel
            alpha_data.append((r, g, b, int(a * alpha * 255)))
        alpha_img.putdata(alpha_data)
        result = PILImage.alpha_composite(result, alpha_img)
    
    # 转换回RGB
    result = result.convert("RGB")
    return result


# ===== 扩展功能实现 =====

def parse_color(color_str: str) -> Optional[Tuple[int, int, int]]:
    """解析颜色字符串，支持 hex (#RRGGBB) 和 rgb(r,g,b)"""
    color_str = color_str.strip().lower()
    # 尝试解析 hex
    if color_str.startswith('#'):
        try:
            hex_color = color_str[1:]
            if len(hex_color) == 6:
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            pass
    # 尝试解析 rgb
    if color_str.startswith('rgb'):
        try:
            match = re.search(r'rgb\((\d+),(\d+),(\d+)\)', color_str)
            if match:
                return tuple(int(match.group(i)) for i in range(1, 4))
        except:
            pass
    # 默认颜色
    color_map = {
        'white': (255, 255, 255), 'black': (0, 0, 0), 'red': (255, 0, 0),
        'green': (0, 255, 0), 'blue': (0, 0, 255), 'yellow': (255, 255, 0),
        'cyan': (0, 255, 255), 'magenta': (255, 0, 255), 'gray': (128, 128, 128),
        '白色': (255, 255, 255), '黑色': (0, 0, 0), '红色': (255, 0, 0),
        '绿色': (0, 255, 0), '蓝色': (0, 0, 255), '黄色': (255, 255, 0),
        '青色': (0, 255, 255), '洋红': (255, 0, 255), '灰色': (128, 128, 128)
    }
    return color_map.get(color_str, (255, 255, 255))


def add_border(img: PILImage, border_width: int, border_color: Tuple[int, int, int]) -> PILImage:
    """为图片添加边框"""
    if border_width <= 0:
        return img
    new_img = PILImage.new("RGB", 
                          (img.width + border_width * 2, img.height + border_width * 2),
                          border_color)
    new_img.paste(img, (border_width, border_width))
    return new_img


def add_rounded_corners(img: PILImage, radius: int) -> PILImage:
    """为图片添加圆角"""
    if radius <= 0:
        return img
    mask = PILImage.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius, fill=255)
    result = PILImage.new("RGBA", img.size, (255, 255, 255, 0))
    if img.mode == "RGBA":
        result.paste(img, (0, 0), mask)
    else:
        result.paste(img, (0, 0))
        alpha = mask.split()[0]
        result.putalpha(alpha)
    return result


def apply_filter(img: PILImage, filter_name: str) -> PILImage:
    """应用滤镜"""
    filter_map = {
        'blur': ImageFilter.BLUR,
        'contour': ImageFilter.CONTOUR,
        'detail': ImageFilter.DETAIL,
        'edge_enhance': ImageFilter.EDGE_ENHANCE,
        'emboss': ImageFilter.EMBOSS,
        'smooth': ImageFilter.SMOOTH,
        'sharpen': ImageFilter.SHARPEN,
        '模糊': ImageFilter.BLUR,
        '轮廓': ImageFilter.CONTOUR,
        '细节': ImageFilter.DETAIL,
        '边缘增强': ImageFilter.EDGE_ENHANCE,
        '浮雕': ImageFilter.EMBOSS,
        '平滑': ImageFilter.SMOOTH,
        '锐化': ImageFilter.SHARPEN
    }
    filter_obj = filter_map.get(filter_name.lower())
    if filter_obj:
        return img.filter(filter_obj)
    return img


def blend_images(base: PILImage, overlay: PILImage, mode: BlendMode, alpha: float = 0.5) -> PILImage:
    """混合两张图片"""
    if base.mode != "RGB":
        base = base.convert("RGB")
    if overlay.mode != "RGBA":
        overlay = overlay.convert("RGBA")
    
    base_array = np.array(base, dtype=np.float32)
    overlay_array = np.array(overlay, dtype=np.float32)
    overlay_alpha = overlay_array[:, :, 3:4] / 255.0 * alpha
    
    if mode == BlendMode.MULTIPLY:
        result = base_array * (overlay_array[:, :, :3] / 255.0)
    elif mode == BlendMode.SCREEN:
        result = 1.0 - (1.0 - base_array / 255.0) * (1.0 - overlay_array[:, :, :3] / 255.0)
        result = result * 255.0
    elif mode == BlendMode.OVERLAY:
        base_norm = base_array / 255.0
        overlay_norm = overlay_array[:, :, :3] / 255.0
        mask = base_norm < 0.5
        result = np.where(mask, 2 * base_norm * overlay_norm * 255.0,
                          (1.0 - 2 * (1.0 - base_norm) * (1.0 - overlay_norm)) * 255.0)
    elif mode == BlendMode.SOFT_LIGHT:
        base_norm = base_array / 255.0
        overlay_norm = overlay_array[:, :, :3] / 255.0
        result = (base_norm + (2 * overlay_norm - 1) * (base_norm - base_norm * base_norm)) * 255.0
    elif mode == BlendMode.HARD_LIGHT:
        base_norm = base_array / 255.0
        overlay_norm = overlay_array[:, :, :3] / 255.0
        mask = overlay_norm < 0.5
        result = np.where(mask, 2 * base_norm * overlay_norm * 255.0,
                          (1.0 - 2 * (1.0 - base_norm) * (1.0 - overlay_norm)) * 255.0)
    else:  # NORMAL
        result = base_array * (1.0 - overlay_alpha) + overlay_array[:, :, :3] * overlay_alpha
    
    result = np.clip(result, 0, 255).astype(np.uint8)
    return PILImage.fromarray(result, mode="RGB")


def merge_grid(images: List[PILImage], rows: int, cols: int, pixel_mode: PixelMode,
               spacing: int = 0, background: Optional[Tuple[int, int, int]] = None,
               border: int = 0, border_color: Tuple[int, int, int] = (0, 0, 0),
               rounded: int = 0) -> PILImage:
    """网格拼接：按行列数排列图片"""
    if not images or rows <= 0 or cols <= 0:
        return None
    
    # 确定每张图片的目标尺寸
    cell_widths = [img.width for img in images[:rows*cols]]
    cell_heights = [img.height for img in images[:rows*cols]]
    
    if pixel_mode == PixelMode.HIGHEST:
        target_cell_w = max(cell_widths) if cell_widths else 200
        target_cell_h = max(cell_heights) if cell_heights else 200
    else:
        target_cell_w = min(cell_widths) if cell_widths else 200
        target_cell_h = min(cell_heights) if cell_heights else 200
    
    # 处理图片
    processed_images = []
    for i, img in enumerate(images[:rows*cols]):
        # 等比例缩放
        ratio = min(target_cell_w / img.width, target_cell_h / img.height)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        resized = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
        
        # 居中放置
        cell_img = PILImage.new("RGB", (target_cell_w, target_cell_h), 
                               background or (255, 255, 255))
        x_offset = (target_cell_w - new_w) // 2
        y_offset = (target_cell_h - new_h) // 2
        cell_img.paste(resized, (x_offset, y_offset))
        
        # 添加边框和圆角
        if border > 0:
            cell_img = add_border(cell_img, border, border_color)
        if rounded > 0:
            cell_img = add_rounded_corners(cell_img, rounded)
        
        processed_images.append(cell_img)
    
    # 创建网格
    total_w = cols * target_cell_w + (cols - 1) * spacing
    total_h = rows * target_cell_h + (rows - 1) * spacing
    result = PILImage.new("RGB", (total_w, total_h), background or (255, 255, 255))
    
    for row in range(rows):
        for col in range(cols):
            idx = row * cols + col
            if idx < len(processed_images):
                x = col * (target_cell_w + spacing)
                y = row * (target_cell_h + spacing)
                result.paste(processed_images[idx], (x, y))
    
    return result


def merge_circle(images: List[PILImage], pixel_mode: PixelMode,
                 background: Optional[Tuple[int, int, int]] = None,
                 border: int = 0, border_color: Tuple[int, int, int] = (0, 0, 0),
                 rounded: int = 0) -> PILImage:
    """圆形/环形排列：围绕中心排列"""
    if not images:
        return None
    
    # 确定每张图片的尺寸
    sizes = [(img.width, img.height) for img in images]
    if pixel_mode == PixelMode.HIGHEST:
        target_size = max(sizes, key=lambda s: s[0] * s[1])
    else:
        target_size = min(sizes, key=lambda s: s[0] * s[1])
    
    target_w, target_h = target_size
    radius = max(target_w, target_h) * len(images) // 2
    
    # 处理图片
    processed_images = []
    for img in images:
        resized = img.resize((target_w, target_h), PILImage.Resampling.LANCZOS)
        if border > 0:
            resized = add_border(resized, border, border_color)
        if rounded > 0:
            resized = add_rounded_corners(resized, rounded)
        processed_images.append(resized)
    
    # 计算画布大小
    canvas_size = int(radius * 2.5)
    result = PILImage.new("RGB", (canvas_size, canvas_size), background or (255, 255, 255))
    center_x, center_y = canvas_size // 2, canvas_size // 2
    
    # 排列图片
    angle_step = 2 * math.pi / len(processed_images)
    for i, img in enumerate(processed_images):
        angle = i * angle_step
        x = int(center_x + radius * math.cos(angle) - img.width // 2)
        y = int(center_y + radius * math.sin(angle) - img.height // 2)
        result.paste(img, (x, y))
    
    return result


def merge_nine_grid(images: List[PILImage], pixel_mode: PixelMode,
                    spacing: int = 0, background: Optional[Tuple[int, int, int]] = None,
                    border: int = 0, border_color: Tuple[int, int, int] = (0, 0, 0),
                    rounded: int = 0) -> PILImage:
    """九宫格：3x3网格"""
    return merge_grid(images, 3, 3, pixel_mode, spacing, background, border, border_color, rounded)


def merge_diagonal(images: List[PILImage], pixel_mode: PixelMode,
                   background: Optional[Tuple[int, int, int]] = None,
                   border: int = 0, border_color: Tuple[int, int, int] = (0, 0, 0),
                   rounded: int = 0) -> PILImage:
    """对角线拼接：沿对角线排列"""
    if not images:
        return None
    
    # 确定每张图片的尺寸
    sizes = [(img.width, img.height) for img in images]
    if pixel_mode == PixelMode.HIGHEST:
        target_size = max(sizes, key=lambda s: s[0] * s[1])
    else:
        target_size = min(sizes, key=lambda s: s[0] * s[1])
    
    target_w, target_h = target_size
    
    # 处理图片
    processed_images = []
    for img in images:
        resized = img.resize((target_w, target_h), PILImage.Resampling.LANCZOS)
        if border > 0:
            resized = add_border(resized, border, border_color)
        if rounded > 0:
            resized = add_rounded_corners(resized, rounded)
        processed_images.append(resized)
    
    # 计算画布大小（对角线排列）
    total_w = target_w * len(processed_images)
    total_h = target_h * len(processed_images)
    result = PILImage.new("RGB", (total_w, total_h), background or (255, 255, 255))
    
    # 沿对角线排列
    for i, img in enumerate(processed_images):
        x = i * target_w
        y = i * target_h
        result.paste(img, (x, y))
    
    return result


def merge_blend(images: List[PILImage], blend_mode: BlendMode, pixel_mode: PixelMode) -> PILImage:
    """混合模式：支持叠加、柔光、强光等"""
    if not images:
        return None
    
    # 确定基准尺寸
    sizes = [(img.width, img.height) for img in images]
    if pixel_mode == PixelMode.HIGHEST:
        target_size = max(sizes, key=lambda s: s[0] * s[1])
    else:
        target_size = min(sizes, key=lambda s: s[0] * s[1])
    
    target_width, target_height = target_size
    
    # 将所有图片调整到基准尺寸
    processed_images = []
    for img in images:
        resized = img.resize((target_width, target_height), PILImage.Resampling.LANCZOS)
        if resized.mode != "RGBA":
            resized = resized.convert("RGBA")
        processed_images.append(resized)
    
    # 混合所有图片
    result = processed_images[0].convert("RGB")
    alpha = 1.0 / len(processed_images)
    
    for overlay in processed_images[1:]:
        result = blend_images(result, overlay, blend_mode, alpha)
    
    return result


def merge_template(images: List[PILImage], template_name: str, pixel_mode: PixelMode,
                   background: Optional[Tuple[int, int, int]] = None) -> PILImage:
    """模板布局：预设布局模板"""
    templates = {
        'instagram': (3, 3),  # Instagram 九宫格
        'puzzle': (2, 2),     # 拼图
        'collage': (2, 3),    # 拼贴
        'instagram九宫格': (3, 3),
        '拼图': (2, 2),
        '拼贴': (2, 3)
    }
    
    rows, cols = templates.get(template_name.lower(), (3, 3))
    return merge_grid(images, rows, cols, pixel_mode, spacing=5, background=background)


def create_gif(images: List[PILImage], duration: int = 500) -> bytes:
    """创建GIF动画"""
    if not images:
        return None
    
    # 统一尺寸
    sizes = [(img.width, img.height) for img in images]
    target_size = max(sizes, key=lambda s: s[0] * s[1])
    target_w, target_h = target_size
    
    processed_images = []
    for img in images:
        resized = img.resize((target_w, target_h), PILImage.Resampling.LANCZOS)
        if resized.mode != "RGB":
            resized = resized.convert("RGB")
        processed_images.append(resized)
    
    # 创建GIF
    gif_bytes = io.BytesIO()
    processed_images[0].save(
        gif_bytes,
        format='GIF',
        save_all=True,
        append_images=processed_images[1:],
        duration=duration,
        loop=0
    )
    return gif_bytes.getvalue()


merge_cmd = on_command("merge", aliases={"\\merge", "/merge"}, priority=2, block=True)


@merge_cmd.handle()
async def handle_merge_start(bot: Bot, event: MessageEvent):
    """处理 \\merge 命令开始"""
    user_id = str(event.user_id)
    
    # 初始化会话
    merge_sessions[user_id] = {
        "state": MergeState.WAIT_MODE,
        "mode": None,
        "images": [],
        "pixel_mode": None,
        "blend_mode": None,
        "grid_rows": None,
        "grid_cols": None,
        "spacing": 0,
        "background": None,
        "border": 0,
        "border_color": (0, 0, 0),
        "rounded": 0,
        "filter_name": None,
        "sort_mode": SortMode.NONE
    }
    
    help_text = """请发送merge方式：
基础模式：垂直/水平/重叠
扩展模式：网格/圆形/九宫格/对角线/混合/动画/模板
或发送：取消"""
    await merge_cmd.send(help_text)


# 监听消息以收集图片
merge_listener = on_message(priority=3, block=False)


@merge_listener.handle()
async def handle_merge_collect(bot: Bot, event: MessageEvent, origin_msg: UniMsg = None):
    """处理合并方式选择、图片收集和像素模式选择"""
    user_id = str(event.user_id)
    
    if user_id not in merge_sessions:
        return
    
    session = merge_sessions[user_id]
    
    # 检查是否是文本消息
    text = origin_msg.extract_plain_text().strip() if origin_msg else ""
    
    # ===== 处理合并方式选择 =====
    if session["state"] == MergeState.WAIT_MODE:
        # 解析合并方式
        mode_text = text.strip()
        
        if "取消" in mode_text:
            del merge_sessions[user_id]
            await merge_listener.finish("已取消合并")
            return
        
        # 基础模式
        if "水平" in mode_text:
            session["mode"] = MergeMode.HORIZONTAL
            session["state"] = MergeState.COLLECT_IMAGES
            await merge_listener.send(f"请发送第{len(session['images']) + 1}张图片/end/取消")
            return
        elif "垂直" in mode_text:
            session["mode"] = MergeMode.VERTICAL
            session["state"] = MergeState.COLLECT_IMAGES
            await merge_listener.send(f"请发送第{len(session['images']) + 1}张图片/end/取消")
            return
        elif "重叠" in mode_text:
            session["mode"] = MergeMode.OVERLAP
            session["state"] = MergeState.COLLECT_IMAGES
            await merge_listener.send(f"请发送第{len(session['images']) + 1}张图片/end/取消")
            return
        # 扩展模式
        elif "网格" in mode_text:
            session["mode"] = MergeMode.GRID
            session["state"] = MergeState.WAIT_GRID_SIZE
            await merge_listener.send("请发送网格尺寸（格式：行x列，如 2x3）")
            return
        elif "圆形" in mode_text or "环形" in mode_text:
            session["mode"] = MergeMode.CIRCLE
            session["state"] = MergeState.COLLECT_IMAGES
            await merge_listener.send(f"请发送第{len(session['images']) + 1}张图片/end/取消")
            return
        elif "九宫格" in mode_text:
            session["mode"] = MergeMode.NINE_GRID
            session["state"] = MergeState.COLLECT_IMAGES
            await merge_listener.send(f"请发送第{len(session['images']) + 1}张图片/end/取消（最多9张）")
            return
        elif "对角线" in mode_text:
            session["mode"] = MergeMode.DIAGONAL
            session["state"] = MergeState.COLLECT_IMAGES
            await merge_listener.send(f"请发送第{len(session['images']) + 1}张图片/end/取消")
            return
        elif "混合" in mode_text:
            session["mode"] = MergeMode.BLEND
            session["state"] = MergeState.WAIT_BLEND_MODE
            await merge_listener.send("请发送混合模式：正常/叠加/柔光/强光/软光/硬光")
            return
        elif "动画" in mode_text or "gif" in mode_text.lower():
            session["mode"] = MergeMode.GIF
            session["state"] = MergeState.COLLECT_IMAGES
            await merge_listener.send(f"请发送第{len(session['images']) + 1}张图片/end/取消")
            return
        elif "模板" in mode_text:
            session["mode"] = MergeMode.TEMPLATE
            # 尝试从文本中提取模板名称
            template_map = {
                'instagram': 'instagram',
                '拼图': 'puzzle',
                '拼贴': 'collage',
                'puzzle': 'puzzle',
                'collage': 'collage'
            }
            template_name = None
            for key, value in template_map.items():
                if key in mode_text.lower():
                    template_name = value
                    break
            if template_name:
                session["template_name"] = template_name
                session["state"] = MergeState.COLLECT_IMAGES
                await merge_listener.send(f"模板：{template_name}，请发送第{len(session['images']) + 1}张图片/end/取消")
            else:
                session["state"] = MergeState.COLLECT_IMAGES
                await merge_listener.send("请发送第1张图片/end/取消（默认使用instagram模板）")
            return
        else:
            await merge_listener.send("无效的合并方式，请重新发送")
            return
    
    # ===== 处理网格尺寸 =====
    if session["state"] == MergeState.WAIT_GRID_SIZE:
        if "取消" in text:
            del merge_sessions[user_id]
            await merge_listener.finish("已取消合并")
            return
        
        # 解析网格尺寸（格式：2x3 或 2 3）
        match = re.search(r'(\d+)[xX\s]+(\d+)', text)
        if match:
            rows = int(match.group(1))
            cols = int(match.group(2))
            if rows > 0 and cols > 0:
                session["grid_rows"] = rows
                session["grid_cols"] = cols
                session["state"] = MergeState.COLLECT_IMAGES
                await merge_listener.send(f"网格尺寸：{rows}x{cols}，请发送第{len(session['images']) + 1}张图片/end/取消")
                return
        
        await merge_listener.send("格式错误，请发送：行x列（如 2x3）")
        return
    
    # ===== 处理混合模式选择 =====
    if session["state"] == MergeState.WAIT_BLEND_MODE:
        if "取消" in text:
            del merge_sessions[user_id]
            await merge_listener.finish("已取消合并")
            return
        
        if "正常" in text or "等透明度" in text:
            session["blend_mode"] = BlendMode.NORMAL
        elif "叠加" in text:
            session["blend_mode"] = BlendMode.MULTIPLY
        elif "柔光" in text:
            session["blend_mode"] = BlendMode.SCREEN
        elif "强光" in text:
            session["blend_mode"] = BlendMode.OVERLAY
        elif "软光" in text:
            session["blend_mode"] = BlendMode.SOFT_LIGHT
        elif "硬光" in text:
            session["blend_mode"] = BlendMode.HARD_LIGHT
        else:
            await merge_listener.send("无效的混合模式，请发送：正常/叠加/柔光/强光/软光/硬光")
            return
        
        session["state"] = MergeState.COLLECT_IMAGES
        await merge_listener.send(f"混合模式已设置，请发送第{len(session['images']) + 1}张图片/end/取消")
        return
    
    # ===== 处理像素模式选择 =====
    if session["state"] == MergeState.WAIT_PIXEL:
        # 解析像素模式
        mode_text = text.strip()
        
        if "取消" in mode_text:
            del merge_sessions[user_id]
            await merge_listener.finish("已取消合并")
            return
        
        if "最高" in mode_text or "最高像素" in mode_text:
            session["pixel_mode"] = PixelMode.HIGHEST
        elif "最低" in mode_text or "最低像素" in mode_text:
            session["pixel_mode"] = PixelMode.LOWEST
        else:
            await merge_listener.send("无效的像素模式，请发送：最高像素/最低像素")
            return
        
        # 执行合并
        images = session["images"]
        mode = session["mode"]
        pixel = session["pixel_mode"]
        
        try:
            result = None
            
            # 基础模式
            if mode == MergeMode.HORIZONTAL:
                result = merge_horizontal(images, pixel)
            elif mode == MergeMode.VERTICAL:
                result = merge_vertical(images, pixel)
            elif mode == MergeMode.OVERLAP:
                result = merge_overlap(images, pixel)
            # 扩展模式
            elif mode == MergeMode.GRID:
                rows = session.get("grid_rows", 2)
                cols = session.get("grid_cols", 2)
                spacing = session.get("spacing", 0)
                background = session.get("background")
                border = session.get("border", 0)
                border_color = session.get("border_color", (0, 0, 0))
                rounded = session.get("rounded", 0)
                result = merge_grid(images, rows, cols, pixel, spacing, background, border, border_color, rounded)
            elif mode == MergeMode.CIRCLE:
                background = session.get("background")
                border = session.get("border", 0)
                border_color = session.get("border_color", (0, 0, 0))
                rounded = session.get("rounded", 0)
                result = merge_circle(images, pixel, background, border, border_color, rounded)
            elif mode == MergeMode.NINE_GRID:
                spacing = session.get("spacing", 0)
                background = session.get("background")
                border = session.get("border", 0)
                border_color = session.get("border_color", (0, 0, 0))
                rounded = session.get("rounded", 0)
                result = merge_nine_grid(images, pixel, spacing, background, border, border_color, rounded)
            elif mode == MergeMode.DIAGONAL:
                background = session.get("background")
                border = session.get("border", 0)
                border_color = session.get("border_color", (0, 0, 0))
                rounded = session.get("rounded", 0)
                result = merge_diagonal(images, pixel, background, border, border_color, rounded)
            elif mode == MergeMode.BLEND:
                blend_mode = session.get("blend_mode", BlendMode.NORMAL)
                result = merge_blend(images, blend_mode, pixel)
            elif mode == MergeMode.GIF:
                gif_bytes = create_gif(images)
                if gif_bytes:
                    await merge_listener.send(MessageSegment.image(gif_bytes))
                    del merge_sessions[user_id]
                    return
                else:
                    await merge_listener.finish("GIF创建失败")
                    return
            elif mode == MergeMode.TEMPLATE:
                template_name = session.get("template_name", "instagram")
                background = session.get("background")
                result = merge_template(images, template_name, pixel, background)
                if result is None:
                    # 如果模板失败，使用默认
                    result = merge_template(images, "instagram", pixel, background)
            else:
                await merge_listener.finish("合并模式错误")
                return
            
            if result is None:
                await merge_listener.finish("合并失败")
                return
            
            # 发送结果
            image_byte = image_to_bytes(result)
            await merge_listener.send(MessageSegment.image(image_byte))
            
            # 清理会话
            del merge_sessions[user_id]
            
        except Exception as e:
            nonebot.logger.error(f"合并图片失败: {e}")
            await merge_listener.finish(f"合并失败: {e}")
            if user_id in merge_sessions:
                del merge_sessions[user_id]
        return
    
    # ===== 处理图片收集 =====
    if session["state"] != MergeState.COLLECT_IMAGES:
        return
    
    if "取消" in text:
        del merge_sessions[user_id]
        await merge_listener.finish("已取消合并")
        return
    
    if "end" in text.lower():
        if len(session["images"]) < 2:
            await merge_listener.send("至少需要2张图片，请继续发送图片或发送'取消'")
            return
        
        # 根据模式决定下一步
        mode = session["mode"]
        if mode in [MergeMode.HORIZONTAL, MergeMode.VERTICAL, MergeMode.OVERLAP, MergeMode.CIRCLE, 
                    MergeMode.DIAGONAL, MergeMode.BLEND]:
            session["state"] = MergeState.WAIT_PIXEL
            await merge_listener.send("请发送：最高像素/最低像素")
        elif mode == MergeMode.NINE_GRID:
            if len(session["images"]) > 9:
                await merge_listener.send("九宫格最多9张图片，已自动截取前9张")
                session["images"] = session["images"][:9]
            session["state"] = MergeState.WAIT_PIXEL
            await merge_listener.send("请发送：最高像素/最低像素")
        elif mode == MergeMode.GRID:
            rows = session.get("grid_rows", 2)
            cols = session.get("grid_cols", 2)
            max_images = rows * cols
            if len(session["images"]) > max_images:
                await merge_listener.send(f"网格最多{max_images}张图片，已自动截取前{max_images}张")
                session["images"] = session["images"][:max_images]
            session["state"] = MergeState.WAIT_PIXEL
            await merge_listener.send("请发送：最高像素/最低像素")
        elif mode == MergeMode.GIF:
            # GIF直接处理，不需要像素模式
            session["state"] = MergeState.WAIT_PIXEL
            await merge_listener.send("请发送：最高像素/最低像素（用于统一尺寸）")
        elif mode == MergeMode.TEMPLATE:
            session["state"] = MergeState.WAIT_PIXEL
            await merge_listener.send("请发送：最高像素/最低像素")
        return
    
    # 尝试提取图片
    img = None
    
    # 尝试从UniMsg提取
    if origin_msg:
        img = extract_image_from_unimsg(origin_msg)
    
    # 如果失败，尝试从消息ID获取
    if img is None:
        try:
            msg_info = await bot.get_msg(message_id=event.message_id)
            img = extract_image_from_message(msg_info)
        except:
            pass
    
    if img is None:
        # 非法文本：已发送图片阶段，重新尝试
        if len(session["images"]) > 0:
            await merge_listener.send(f"未检测到图片，请重新发送第{len(session['images']) + 1}张图片/end/取消")
        else:
            # 未发送图片阶段，结束会话
            del merge_sessions[user_id]
            await merge_listener.finish("未检测到图片，合并已取消")
        return
    
    # 添加图片
    session["images"].append(img)
    
    # 根据模式限制图片数量
    mode = session.get("mode")
    max_for_mode = 20  # MAX_IMAGES
    if mode == MergeMode.NINE_GRID:
        max_for_mode = 9
    elif mode == MergeMode.GRID:
        rows = session.get("grid_rows", 2)
        cols = session.get("grid_cols", 2)
        max_for_mode = rows * cols
    
    if len(session["images"]) >= max_for_mode:
        session["state"] = MergeState.WAIT_PIXEL
        await merge_listener.send(f"已收集{max_for_mode}张图片（达到上限），请发送：最高像素/最低像素")
        return
    
    await merge_listener.send(f"已接收第{len(session['images'])}张图片，请发送第{len(session['images']) + 1}张图片/end/取消")
