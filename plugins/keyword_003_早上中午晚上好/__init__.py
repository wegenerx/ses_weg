import os
import random

from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="a003_heliemin_graph",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment

def print_current_path():
    # 获取当前工作目录的绝对路径
    current_path = os.path.abspath('.')
    print(f"当前的绝对路径是: {current_path}")



def graph_bit(directory):
    # 获取目录中所有文件的列表
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    # 检查目录是否为空
    if files:
        # 随机选择一个文件
        file_path = os.path.join(directory, random.choice(files))
        # print(file_path)

    # 使用 open 函数以二进制模式读取文件内容
    with open(file_path, 'rb') as file:
        file_bytes = file.read()

    # file_bytes 现在包含了文件的二进制数据
    # print(type(file_bytes))  # 输出: <class 'bytes'>

    return file_bytes


# 相当于先创建一个类型为on_keyword的事件响应器，再赋值给一个名为 word 的变量，使其成为一个事件响应器。
word_morning = on_keyword(keywords={'早上好'}, priority=1)

# 相当于先创建一个类型为on_keyword的事件响应器，再赋值给一个名为 word 的变量，使其成为一个事件响应器。
word_afternoon = on_keyword(keywords={'中午好'}, priority=1)

# 相当于先创建一个类型为on_keyword的事件响应器，再赋值给一个名为 word 的变量，使其成为一个事件响应器。
word_evening = on_keyword(keywords={'晚上好'}, priority=1)


@word_morning.handle()
async def _(bot: Bot):  # await word.finish(str(bot.self_id))
    # 调用函数
    print_current_path()
    await word_morning.send(MessageSegment.image(graph_bit(r'ses_weg\plugins\keyword_003_早上中午晚上好\a001_graph'))) # 当前的绝对路径是: C:\Users\dell\ses_weg


@word_afternoon.handle()
async def _(bot: Bot):  # await word.finish(str(bot.self_id))
    await word_afternoon.send(MessageSegment.image(graph_bit(r'ses_weg\plugins\keyword_003_早上中午晚上好\a002_graph')))


@word_evening.handle()
async def _(bot: Bot):  # await word.finish(str(bot.self_id))
    await word_evening.send(MessageSegment.image(graph_bit(r'ses_weg\plugins\keyword_003_早上中午晚上好\a003_graph')))
