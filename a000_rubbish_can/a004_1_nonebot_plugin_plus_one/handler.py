from nonebot.plugin import on_message
from nonebot.rule import regex
from nonebot.adapters import Event, Message, Bot

from nonebot_plugin_session import extract_session, SessionIdType
from nonebot_plugin_alconna.uniseg import Hyper, Image, MsgTarget, Reply, Text, UniMessage, UniMsg, MessageId

from .config import config

plus = on_message(rule=regex(""), priority=config.plus_one_priority, block=False)
msg_dict = {}


# judge if they're equal
def is_equal(msg1: Message, msg2: Message, ori_msg: UniMsg):
    """判断是否相等"""
    if len(msg1) == len(msg2) == 1 and msg1[0].type == msg2[0].type == "image":
        if msg1[0].data["file_size"] == msg2[0].data["file_size"]:
            # ban True 'cause of bugs
            ''  # return True
    if msg1 == msg2 and msg1[0].type != "image" and msg2[0].type != "image" and Image not in ori_msg:
        print(ori_msg)
        return True

    return False




@plus.handle()
async def plush_handler(bot: Bot, event: Event, ori_msg: UniMsg):
    global msg_dict

    session = extract_session(bot, event)
    group_id = session.get_id(SessionIdType.GROUP).split("_")[-1]
    if group_id not in config.plus_one_white_list:
        return

    # 获取群聊记录
    text_list = msg_dict.get(group_id, None)
    if not text_list:
        text_list = []
        msg_dict[group_id] = text_list

    # 获取当前信息
    msg = event.get_message()   # nonebot.adapters.Message
    print(type(msg))
    print(1)

    try:
        if not is_equal(text_list[-1], msg, ori_msg):
            text_list = []
            msg_dict[group_id] = text_list
    except IndexError:
        pass

    text_list.append(msg)

    # if repeated, send
    if len(text_list) > 1:
        await plus.send(msg)
