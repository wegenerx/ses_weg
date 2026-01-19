import json
import ssl
import requests
import re
import math
import numpy as np
from PIL import Image as PILImage, ImageFilter, ImageEnhance, ImageOps
from io import BytesIO
import io

from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Bot
from nonebot_plugin_alconna.uniseg import Hyper, Image, MsgTarget, Reply, Text, UniMessage, UniMsg, MessageId

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="a002_heliemin",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

# 相当于先创建一个类型为on_keyword的事件响应器，再赋值给一个名为 word 的变量，使其成为一个事件响应器。
word = on_keyword(keywords={'对称', '镜像', '平移', '黑白', '模糊', '锐化', '边缘检测', '去噪', '放大镜', '凸透镜', '凹透镜', '老花镜'},
                  # permission='GROUP_OWNER', # 第二个是permission参数，这个参数负责传入能触发此事件响应器的消息发送者类型，也就是哪些人能触发这个响应器。一般来说重要的指令都会加上一些权限限制，诸如操作机器人后台的一些指令。常见的 permission 有 SUPERUSER(写在.env 文件中的超级用户)，GROUP_ADMIN(群管理员)和 GROUP_OWNER(群主)，这些是框架本身提供的。除此以外我们也可以自定义权限组，当然这个内容之后再谈。
                  priority=1,
                  )


def image_to_bytes(image: PILImage.Image, format: str = 'PNG') -> bytes:
    """
    将 PIL Image 对象转换为二进制数据。

    :param image: PIL Image 对象
    :param format: 图像格式，默认为 'PNG'
    :return: 二进制数据
    """
    # 创建一个 BytesIO 对象
    byte_stream = io.BytesIO()

    # 将图像保存到 BytesIO 对象中
    image.save(byte_stream, format=format)

    # 获取二进制数据
    byte_data = byte_stream.getvalue()

    # 关闭 BytesIO 对象
    byte_stream.close()

    return byte_data


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

def 拼接(input_img: PILImage) -> dict:
    """
    生成所有变换结果
    返回字典，包含：
    - 对称: 左、右、上、下
    - 镜像: 左、右、上、下  
    - 平移: 左、右、上、下
    """
    # 横向拼接
    def Horizontal_splicing(left_img, right_img):
        width1, height1 = left_img.size
        width2, height2 = right_img.size
        new_img = PILImage.new("RGB", (width1 + width2, max(height1, height2)))
        new_img.paste(left_img, (0, 0))
        new_img.paste(right_img, (width1, 0))
        return new_img

    # 纵向拼接
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

    # 制造半图像
    left_half = img.crop((0, 0, center_x, height))
    right_half = img.crop((center_x, 0, width, height))
    top_half = img.crop((0, 0, width, center_y))
    bottom_half = img.crop((0, center_y, width, height))

    result = {}
    
    # ===== 对称：将半部分翻转到另一半 =====
    # 对称左：左半边 + 左半边翻转（翻转到右）
    result['对称左'] = Horizontal_splicing(left_half, FLIP_LEFT_RIGHT(left_half))
    # 对称右：右半边翻转 + 右半边（翻转到左）
    result['对称右'] = Horizontal_splicing(FLIP_LEFT_RIGHT(right_half), right_half)
    # 对称上：上半边 + 上半边翻转（翻转到下）
    result['对称上'] = Longitudinal_splicing(top_half, FLIP_TOP_BOTTOM(top_half))
    # 对称下：下半边翻转 + 下半边（翻转到上）
    result['对称下'] = Longitudinal_splicing(FLIP_TOP_BOTTOM(bottom_half), bottom_half)

    # ===== 镜像：整图翻转后拼接，形成2倍大小 =====
    # 镜像左：原图 + 原图水平翻转（左右镜像）
    result['镜像左'] = Horizontal_splicing(img, FLIP_LEFT_RIGHT(img))
    # 镜像右：原图水平翻转 + 原图
    result['镜像右'] = Horizontal_splicing(FLIP_LEFT_RIGHT(img), img)
    # 镜像上：原图 + 原图垂直翻转（上下镜像）
    result['镜像上'] = Longitudinal_splicing(img, FLIP_TOP_BOTTOM(img))
    # 镜像下：原图垂直翻转 + 原图（往下翻转并拼接）
    result['镜像下'] = Longitudinal_splicing(FLIP_TOP_BOTTOM(img), img)

    # ===== 平移：半部分直接拼接，不翻转 =====
    # 平移左：左半边 + 左半边（不翻转）
    result['平移左'] = Horizontal_splicing(left_half, left_half)
    # 平移右：右半边 + 右半边（不翻转）
    result['平移右'] = Horizontal_splicing(right_half, right_half)
    # 平移上：上半边 + 上半边（不翻转）
    result['平移上'] = Longitudinal_splicing(top_half, top_half)
    # 平移下：下半边 + 下半边（不翻转）
    result['平移下'] = Longitudinal_splicing(bottom_half, bottom_half)

    return result


import re
from typing import Optional

def 解析参数(关键字: str, 关键词: str) -> Optional[float]:
    """
    支持格式：
      关键词参数
      关键词 参数
      关键词    参数

    示例：
      模糊0.8
      模糊 0.8
      模糊    -1.2
      模糊 1e-3
    """
    pattern = rf"""
        (?<!\S)                         # 关键词前是行首或空白
        {re.escape(关键词)}
        \s*                             # 任意空格
        ([+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)  # 浮点数 / 科学计数法
        (?!\S)                          # 参数后是行尾或空白
    """

    match = re.search(pattern, 关键字, re.IGNORECASE | re.VERBOSE)
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None



def 黑白(image: PILImage) -> PILImage:
    """将图片转化为黑白图片"""
    return image.convert('L').convert('RGB')


def 模糊(image: PILImage, radius: float) -> PILImage:
    """
    模糊处理
    radius: 模糊半径，建议范围 0.5-10
    """
    # 限制参数范围
    radius = max(0.5, min(10.0, abs(radius)))
    # PIL的GaussianBlur需要整数半径，我们使用ImageFilter.GaussianBlur
    # 但PIL的半径是整数，所以我们需要自己实现或近似
    if radius < 1:
        radius = 1
    return image.filter(ImageFilter.GaussianBlur(radius=int(radius)))


def 锐化(image: PILImage, factor: float) -> PILImage:
    """
    锐化处理
    factor: 锐化强度，建议范围 0.5-5.0
    """
    factor = max(0.5, min(5.0, abs(factor)))
    enhancer = ImageEnhance.Sharpness(image)
    return enhancer.enhance(1.0 + factor * 0.5)


def 边缘检测(image: PILImage) -> PILImage:
    """边缘检测处理"""
    # 转换为灰度图
    gray = image.convert('L')
    # 使用FIND_EDGES滤镜
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # 转换回RGB
    return edges.convert('RGB')


def 去噪(image: PILImage, strength: float) -> PILImage:
    """
    去噪处理（使用中值滤波和平滑滤波）
    strength: 去噪强度，建议范围 0.5-3.0
    """
    strength = max(0.5, min(3.0, abs(strength)))
    
    # 根据强度选择不同的处理方式
    if strength < 1.0:
        # 轻度去噪：使用SMOOTH
        result = image.filter(ImageFilter.SMOOTH)
    elif strength < 2.0:
        # 中度去噪：使用MedianFilter（固定3x3）
        result = image.filter(ImageFilter.MedianFilter())
    else:
        # 重度去噪：多次应用中值滤波
        result = image.filter(ImageFilter.MedianFilter())
        result = result.filter(ImageFilter.MedianFilter())
    
    return result


import math
import numpy as np
from PIL import Image as PILImage


def 球形畸变(image: PILImage, strength: float) -> PILImage:
    """
    球形畸变效果（放大镜/凸透镜/凹透镜/老花镜）

    strength:
      - strength = 1: 无变化
      - 0 < strength < 1: 凹透镜（中心缩小/向中心挤压），且越接近 0 强度指数级增强
      - strength > 1: 凸透镜（中心放大），且越接近 +inf 放大强度对数级增长

    实现：
      - 使用径向幂映射 d_in = d_out ** gamma
      - gamma(strength)：
          strength<1:  gamma = exp(-k*(1/strength - 1))    -> strength→0 时 gamma→0（指数级变强）
          strength>1:  gamma = 1 + a*log1p(strength-1)      -> strength→+inf 时 gamma~log(strength)（对数级变强）
      - 采样使用双线性插值，避免锯齿
    """
    # ---------- 参数清洗 ----------
    if strength is None or not np.isfinite(strength):
        strength = 1.0
    strength = abs(float(strength))

    # 强制限制，避免 1/strength 溢出
    strength = max(1e-6, min(1e6, strength))

    # ---------- 图像格式 ----------
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
        # 极端情况下兜底
        image = image.convert("RGB")
        src = np.asarray(image, dtype=np.uint8)

    # ---------- strength -> gamma 非线性映射 ----------
    if abs(strength - 1.0) < 1e-12:
        gamma = 1.0
    elif strength < 1.0:
        # 越接近 0，指数级缩小（强凹透镜）
        k = 1.0  # 可调：越大越“猛”
        gamma = math.exp(-k * (1.0 / strength - 1.0))  # (0,1]
        gamma = max(1e-6, min(1.0, gamma))
    else:
        # 越接近 +inf，按对数级增长（慢慢变强的凸透镜）
        a = 1.0  # 可调：越大越“猛”
        gamma = 1.0 + a * math.log1p(strength - 1.0)
        gamma = max(1.0, min(1e6, gamma))

    # ---------- 构造输出网格 ----------
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    dx = x - cx
    dy = y - cy

    r_out = np.sqrt(dx * dx + dy * dy)  # 输出半径（像素）
    d_out = np.clip(r_out / max_radius, 0.0, 1.0)  # 归一化半径 [0,1]

    # 径向幂映射：d_in = d_out ** gamma
    d_in = np.power(d_out, gamma, dtype=np.float32)
    r_in = d_in * max_radius

    # 计算缩放系数，把 (dx,dy) 缩放到输入位置
    eps = 1e-8
    scale = r_in / (r_out + eps)
    # 中心点 r_out=0 时应采样中心
    scale = np.where(r_out < eps, 0.0, scale).astype(np.float32)

    src_x = cx + dx * scale
    src_y = cy + dy * scale

    # ---------- 双线性采样 ----------
    # clip 到有效范围
    src_x = np.clip(src_x, 0.0, width - 1.0)
    src_y = np.clip(src_y, 0.0, height - 1.0)

    x0 = np.floor(src_x).astype(np.int32)
    y0 = np.floor(src_y).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, width - 1)
    y1 = np.clip(y0 + 1, 0, height - 1)

    wx = (src_x - x0).astype(np.float32)
    wy = (src_y - y0).astype(np.float32)

    # 四个角
    Ia = src[y0, x0].astype(np.float32)
    Ib = src[y0, x1].astype(np.float32)
    Ic = src[y1, x0].astype(np.float32)
    Id = src[y1, x1].astype(np.float32)

    wa = (1.0 - wx) * (1.0 - wy)
    wb = wx * (1.0 - wy)
    wc = (1.0 - wx) * wy
    wd = wx * wy

    out = (Ia * wa[..., None] +
           Ib * wb[..., None] +
           Ic * wc[..., None] +
           Id * wd[..., None])

    out = np.clip(out + 0.5, 0, 255).astype(np.uint8)
    return PILImage.fromarray(out, mode="RGB")



def 对称(image: PILImage, 关键字: str) -> PILImage:
    """
    根据关键字返回对应的变换图像
    支持：
    - 对称、镜像、平移 + 方向（左、右、上、下）
    - 黑白
    - 模糊[参数]、锐化[参数]、去噪[参数]
    - 边缘检测
    - 放大镜/凸透镜/凹透镜/老花镜[参数]
    """
    # ===== 1. 黑白处理 =====
    if '黑白' in 关键字:
        return 黑白(image)
    
    # ===== 2. 模糊处理 =====
    if '模糊' in 关键字:
        param = 解析参数(关键字, '模糊')
        if param is not None:
            return 模糊(image, param)
        else:
            # 默认模糊半径
            return 模糊(image, 2.0)
    
    # ===== 3. 锐化处理 =====
    if '锐化' in 关键字:
        param = 解析参数(关键字, '锐化')
        if param is not None:
            return 锐化(image, param)
        else:
            # 默认锐化强度
            return 锐化(image, 2.0)
    
    # ===== 4. 边缘检测 =====
    if '边缘检测' in 关键字:
        return 边缘检测(image)
    
    # ===== 5. 去噪处理 =====
    if '去噪' in 关键字:
        param = 解析参数(关键字, '去噪')
        if param is not None:
            return 去噪(image, param)
        else:
            # 默认去噪强度
            return 去噪(image, 1.5)
    
    # ===== 6. 球形畸变（放大镜/凸透镜/凹透镜/老花镜） =====
    lens_keywords = ['放大镜', '凸透镜', '凹透镜', '老花镜']
    for lens_keyword in lens_keywords:
        if lens_keyword in 关键字:
            param = 解析参数(关键字, lens_keyword)
            if param is not None:
                return 球形畸变(image, param)
            else:
                # 默认强度
                return 球形畸变(image, 1.5)
    
    # ===== 7. 对称、镜像、平移处理 =====
    # 获取所有变换结果
    transform_dict = 拼接(image)
    
    # 提取方向和类型
    方向 = None
    if '左' in 关键字:
        方向 = '左'
    elif '右' in 关键字:
        方向 = '右'
    elif '上' in 关键字:
        方向 = '上'
    elif '下' in 关键字:
        方向 = '下'
    
    # 确定变换类型
    类型 = None
    if '对称' in 关键字:
        类型 = '对称'
    elif '镜像' in 关键字:
        类型 = '镜像'
    elif '平移' in 关键字:
        类型 = '平移'
    
    # 组合键名
    if 类型 and 方向:
        key = f"{类型}{方向}"
        if key in transform_dict:
            return transform_dict[key]
    
    # 如果没有匹配到，默认返回原图
    return image


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


@word.handle()
async def reply(bot: Bot, origin_msg: UniMsg, ):  # state: T_State):
    if Reply in origin_msg:

        # create a unimsg to send
        # msgs = UniMessage()

        # reply dealing
        reply_msg = origin_msg[Reply, 0]  # print('reply_msg=', reply_msg)  # reply_msg= [reply] <class 'nonebot_plugin_alconna.uniseg.segment.Reply'>
        reply_msg_id = reply_msg.id  # 获取回复的消息(消息 1) ID # reply_msg_id= 293890509
        reply_msg_info = await bot.get_msg(message_id=reply_msg_id) # print(json.dumps(reply_msg_info, indent=4))

        # origional msg dealing
        ori_msg_text = origin_msg.extract_plain_text()  # print('plaintext = ', ori_msg_text) # 蛾 对称

        # get url
        url = reply_msg_info['message'][0]['data']['url']  # extract url

        # url to PIL_image
        PILImage_ = get_image_from_url(url)

        # 对称
        PILImage_ = 对称(image=PILImage_, 关键字=ori_msg_text)

        # PIL_image to bytes
        image_byte = image_to_bytes(PILImage_)

        await word.send(MessageSegment.image(image_byte))
