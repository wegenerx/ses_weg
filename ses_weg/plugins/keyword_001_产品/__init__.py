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

def graph_bit():
    # 定义文件路径
    directory = r'ses_weg\plugins\keyword_001_产品\a001_graph'

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
word = on_keyword(keywords={'产品'},
                  # permission='GROUP_OWNER', # 第二个是permission参数，这个参数负责传入能触发此事件响应器的消息发送者类型，也就是哪些人能触发这个响应器。一般来说重要的指令都会加上一些权限限制，诸如操作机器人后台的一些指令。常见的 permission 有 SUPERUSER(写在.env 文件中的超级用户)，GROUP_ADMIN(群管理员)和 GROUP_OWNER(群主)，这些是框架本身提供的。除此以外我们也可以自定义权限组，当然这个内容之后再谈。
                  priority=1
                  )


@word.handle()
async def _(bot: Bot):
    # await word.finish(str(bot.self_id))
    await word.send(MessageSegment.image(graph_bit()))


