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
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment
from nonebot import on_keyword, on_message, on_fullmatch
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


class SingleKeywordMatcher:
    def __init__(self, type, priority, match_content, response_content, block=False, withdraw=True):
        if type == 'on_keyword':
            words = on_keyword(keywords=match_content,
                               priority=priority,
                               block=block)
        elif type == 'on_fullmatch':
            words = on_fullmatch(msg=match_content,
                                 priority=priority,
                                 block=block)

        @words.handle()
        async def reply(bot: Bot, origin_msg: UniMsg, event: MessageEvent):  # state: T_State):

            if Reply not in origin_msg:
                # create a unimsg to send
                # msgs = UniMessage()

                # # reply dealing
                # reply_msg = origin_msg[Reply, 0]  # print('reply_msg=', reply_msg)  # reply_msg= [reply] <class 'nonebot_plugin_alconna.uniseg.segment.Reply'>
                # reply_msg_id = reply_msg.id  # 获取回复的消息(消息 1) ID # reply_msg_id= 293890509
                # reply_msg_info = await bot.get_msg(message_id=reply_msg_id)  # print(json.dumps(reply_msg_info, indent=4))

                # origional msg dealing
                ori_msg_text = origin_msg.extract_plain_text()  # print('plaintext = ', ori_msg_text) # 蛾 对称

                # message to bytes
                # text: str = reply_msg_info['message'][0]['data']['text']  # extract url

                msg = response_content
                msg_id: dict = await words.send(msg)  # 发送消息并获取消息 ID

                # 假设需要在 30 秒后撤回消息
                if withdraw:
                    await asyncio.sleep(30)  # 等待 30 秒
                    await bot.delete_msg(message_id=msg_id["message_id"])  # 撤回消息


# maimai = SingleKeywordMatcher(type='on_keyword',
#                           priority=10,
#                           match_content={'舞萌',  'maimai', '地插', 'dx', 'DX',},
#                           response_content= \
#  \
#                               """
# 🟥🟥🟥🟥🟥🟥🟥🟥🟥
# 🌫🌫🌫🌈 📷 🌫🌫🌫🌈
# 🌫🌫🌫🌫      🌫🌫🌫🌫
#
#     🛑 🛑            🛑 🛑
# 🛑         🛑🎛🛑         🛑
# 🛑         🛑📲🛑         🛑
#     🛑 🛑            🛑 🛑
#                  💸
#
# ⬛️⬛️⬛️⬛️⬛️⬛️⬛️⬛️⬛️⬛️
# """,
#                           )

对吗 = SingleKeywordMatcher(type='on_keyword',
                          priority=10,
                          match_content={'对吗'},
                          response_content="""对的""",
                          )

好吗 = SingleKeywordMatcher(type='on_keyword',
                          priority=10,
                          match_content={'好吗'},
                          response_content="""好的""",
                          )

你好 = SingleKeywordMatcher(type='on_keyword',
                          priority=10,
                          match_content={'你好'},
                          response_content="""你坏""",
                          )

晚安 = SingleKeywordMatcher(type='on_keyword',
                          priority=10,
                          match_content={'晚安'},
                          response_content="""晚安""",
                          withdraw=False,
                          )

晚安捏 = SingleKeywordMatcher(type='on_keyword',
                          priority=10,
                          match_content={'众生睡觉'},
                          response_content="""晚安捏""",
                          withdraw=False,
                          )

# 水母
水母 = SingleKeywordMatcher(type='on_keyword',
                            match_content={'水母'},
                     priority=14,
                     response_content= \
                         '''蛰群友屁股
  ଳ~    ଳ~            ଳ~    ଳ~     ଳ~
      ଳ~             ଳ~            ଳ~
      ଳ~             ଳ~            ଳ~
  ଳ~    ଳ~       ଳ~         ଳ~     ଳ~
      ଳ~                  ଳ~       ଳ~
      ଳ~         ~ଳ                ଳ~        ~ଳ
  ଳ~    ଳ~            ଳ~    ଳ~     ଳ~          ଳ~                ~ଳ  
          ଳ~  ଳ~               ଳ~
   ଳ~           ଳ~          ଳ~          ଳ~                ଳ~        ଳ~
               ~ଳ      ଳ~   ଳ~
ଳ~  ଳ~               ଳ~               ଳ~                    ଳ~
                      ଳ~
                     ଳ~
ଳ~     ଳ~          ଳ~               
    ଳ~            ଳ~
ଳ~     ଳ~
    ଳ~                                 ଳ~     ଳ~
   ~ଳ             ~ଳ          ଳ~
ଳ~     ~ଳ''')

# 6
# 远离一个字的ip：6
# 远离两个字的ip：彩六
# 远离三个字的ip：r6s
# 远离四个字的ip：彩虹六号
# 远离五个字的ip：siege
# 远离六个字的ip：彩虹六号围攻
# _6p = KeywordsWords(keywords={'远离一个字的ip：6', '彩六', '彩6', 'r6s', '彩虹六号', 'siege', '围攻'},
#                          priority=17,
#                          returns= \
#                              """6p""")


def notations():
    '''
    # 相当于先创建一个类型为on_keyword的事件响应器，再赋值给一个名为 word 的变量，使其成为一个事件响应器。
    word = on_keyword(keywords={'日记', 'nikki', 'にっき', '日記'},
                      # permission='GROUP_OWNER', # 第二个是permission参数，这个参数负责传入能触发此事件响应器的消息发送者类型，也就是哪些人能触发这个响应器。一般来说重要的指令都会加上一些权限限制，诸如操作机器人后台的一些指令。常见的 permission 有 SUPERUSER(写在.env 文件中的超级用户)，GROUP_ADMIN(群管理员)和 GROUP_OWNER(群主)，这些是框架本身提供的。除此以外我们也可以自定义权限组，当然这个内容之后再谈。
                      priority=10,
                      block=False
                      )


    async def get_reply_content(bot: Bot, reply_msg_id: int) -> UniMsg:
        try:
            reply_content = await bot.get_msg(message_id=reply_msg_id)
            return UniMsg(reply_content)

        except Exception as e:
            from nonebot.log import logger
            logger.error(f"获取回复消息内容失败: {e}")
            return UniMsg()


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

            # 添加日记并发送消息
            append_to_me_mo(text)
            msg = '已加入日记：' + text
            msg_id: dict = await word.send(msg)  # 发送消息并获取消息 ID

            # 假设需要在 20 秒后撤回消息
            await asyncio.sleep(20)  # 等待 20 秒
            await bot.delete_msg(message_id=msg_id["message_id"])  # 撤回消息'''
