import time

import asyncio
from datetime import datetime
import os
import json
import os
import ssl
import requests
from PIL import Image as PILImage
from io import BytesIO
import io

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
word = on_keyword(keywords={'撤回'},
                  # permission='GROUP_OWNER', # 第二个是permission参数，这个参数负责传入能触发此事件响应器的消息发送者类型，也就是哪些人能触发这个响应器。一般来说重要的指令都会加上一些权限限制，诸如操作机器人后台的一些指令。常见的 permission 有 SUPERUSER(写在.env 文件中的超级用户)，GROUP_ADMIN(群管理员)和 GROUP_OWNER(群主)，这些是框架本身提供的。除此以外我们也可以自定义权限组，当然这个内容之后再谈。
                  priority=10,
                  block=False
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
    image.save(byte_stream, format=image.format)

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
    # 定义目标目录的相对路径
    target_directory = r"..\keyword_005_keywords_graph"

    # 获取当前脚本的绝对路径
    current_script_path = os.path.abspath(__file__)
    # 获取当前脚本所在的目录
    current_directory = os.path.dirname(current_script_path)
    # 计算目标目录的绝对路径
    target_directory = os.path.abspath(os.path.join(current_directory, target_directory))

    # 检查目标目录是否存在
    if not os.path.exists(target_directory):
        print(f"目标目录 {target_directory} 不存在")
        return False

    # 遍历目标目录下的所有文件夹
    for folder_name in os.listdir(target_directory):
        folder_path = os.path.join(target_directory, folder_name)
        if os.path.isdir(folder_path) and keyword in folder_name:
            return folder_path  # 找到匹配的文件夹，返回路径

    # 如果没有找到匹配的文件夹，返回 False
    return False


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


def append_to_me_mo(content):
    def nikki_now():
        from datetime import datetime

        # 获取当前时间
        now = datetime.now()

        # 将时间格式化为字符串
        # 这里使用 '%Y-%m-%d %H:%M:%S' 格式，表示 年-月-日 时:分:秒
        from datetime import datetime
        import calendar

        # 获取当前日期
        now = datetime.now()

        # 获取今天是星期几（0代表星期一，1代表星期二，...，6代表星期日）
        weekday_number = now.weekday()

        # 使用calendar.day_name获取星期几的字符串（注意列表的索引是从0开始的）
        weekday_str = calendar.day_name[weekday_number]
        time_str = now.strftime('%Y-%m-%d ') + weekday_str + now.strftime(' %H:%M:%S')

        return time_str

    # lineEdit 6
    text_in_lineEdit = content
    text_in_lineEdit = text_in_lineEdit.replace('\n', '').strip()

    # lineEdit 不为空才写入me_mo，同时判断列头的类型
    if text_in_lineEdit != '':
        text_in_lineEdit = text_in_lineEdit + ' - ' + nikki_now()
        text_to_diary = '- ' + text_in_lineEdit

        # 打开文件以追加模式（'a'）写入，如果文件不存在则创建
        with open(r"D:\Libraries\projects\python\ownproject\011 ++本地门户网站\文本\a002_日记.md",
                  'a',
                  encoding='utf-8') as file:
            # 确保新文本之前有一个换行符，以便它出现在新的一行
            file.write('\n' + text_to_diary)


@word.handle()
async def reply(bot: Bot, origin_msg: UniMsg, event: MessageEvent):  # state: T_State):

    if Reply in origin_msg:
        # create a unimsg to send
        # msgs = UniMessage()

        # reply dealing
        reply_msg = origin_msg[Reply, 0]  # print('reply_msg=', reply_msg)  # reply_msg= [reply] <class 'nonebot_plugin_alconna.uniseg.segment.Reply'>
        reply_msg_id = reply_msg.id  # 获取回复的消息(消息 1) ID # reply_msg_id= 293890509
        reply_msg_info = await bot.get_msg(message_id=reply_msg_id)  # print(json.dumps(reply_msg_info, indent=4))

        # origional msg dealing
        ori_msg_text = origin_msg.extract_plain_text()  # print('plaintext = ', ori_msg_text) # 蛾 对称

        # message to bytes
        text: str = reply_msg_info['message'][0]['data']['text']  # extract url

        # delete message
        try:
            await bot.delete_msg(message_id=reply_msg_id)  # delete replied message
            time.sleep(0.5)
            await bot.delete_msg(message_id=origin_msg.get_message_id())  # delete reply message

        except Exception as e:
            nonebot.logger.error(f"复读自动跟随撤回失败||{e}")

            # 发送消息
            msg_fail = '撤回失败：' + text
            msg_fail_id: dict = await word.send(msg_fail)  # 发送消息并获取消息 ID

            # 假设需要在 20 秒后撤回消息
            await asyncio.sleep(20)  # 等待 20 秒
            await bot.delete_msg(message_id=msg_fail_id["message_id"])  # 撤回消息

        # 发送消息
        msg = '已尝试撤回：' + text
        msg_id: dict = await word.send(msg)  # 发送消息并获取消息 ID

        # 假设需要在 20 秒后撤回消息
        await asyncio.sleep(20)  # 等待 20 秒
        await bot.delete_msg(message_id=msg_id["message_id"])  # 撤回消息
