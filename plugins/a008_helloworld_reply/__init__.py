from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment
from nonebot.rule import to_me

# helloword = on_keyword({"hello"}, rule=to_me())
#
#
# @helloword.handle()
# async def _(event: GroupMessageEvent):
#     await helloword.finish(MessageSegment.at(event.user_id))


from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.typing import T_State

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
from nonebot.message import *



__plugin_meta__ = PluginMetadata(
    name='Reply Detector',
    description='Detect reply events and send the reply content',
    usage='Detect reply events and send the reply content',
)

def detect_rule(Event: Event):
    return_ = False
    if Event.is_tome():
        return_ = True
    return return_


reply_event = on_command(# rule=detect_rule,
                         cmd='对称左')

@reply_event.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State):
    # 检查事件类型是否为消息事件
    if event.get('type') == 'message':

        print("nice")
        # 检查消息是否为回复
        if event.get('reply'):
            # 获取回复内容
            reply_content = event['reply']['content']
            # 发送回复内容
            await reply_event.finish(Message(reply_content) + '曹尼玛')
        else:
            await reply_event.finish('This is not a reply event.')
    else:
        await reply_event.finish('This is not a message event.')