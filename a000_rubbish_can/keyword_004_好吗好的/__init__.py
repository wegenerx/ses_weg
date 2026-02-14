from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="a002_heliemin",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Bot


class KeywordsWords():
    def __init__(self,
                 keywords,
                 # path,
                 priority,
                 returns):
        # init param
        self.keywords = keywords
        # self.path = path
        self.priority = priority
        self.returns = returns

        # 相当于先创建一个类型为on_keyword的事件响应器，再赋值给一个名为 word 的变量，使其成为一个事件响应器。
        word = on_keyword(keywords=self.keywords,
                          # permission='GROUP_OWNER', # 第二个是permission参数，这个参数负责传入能触发此事件响应器的消息发送者类型，也就是哪些人能触发这个响应器。一般来说重要的指令都会加上一些权限限制，诸如操作机器人后台的一些指令。常见的 permission 有 SUPERUSER(写在.env 文件中的超级用户)，GROUP_ADMIN(群管理员)和 GROUP_OWNER(群主)，这些是框架本身提供的。除此以外我们也可以自定义权限组，当然这个内容之后再谈。
                          priority=self.priority
                          )

        dx = self.returns

        @word.handle()
        async def _(bot: Bot):
            # await word.finish(str(bot.self_id))
            await word.finish(dx)


# # 好吗好的
# 好吗好的 = KeywordsWords(keywords={'好吗'},
#                          priority=11,
#                          returns= \
#                              """好的""")

# 你好
你好 = KeywordsWords(keywords={'你好'},
                     priority=12,
                     returns= \
                         """你坏""")




# 晚安
晚安 = KeywordsWords(keywords={'晚安', },
                     priority=15,
                     returns= \
                         """晚安""")

# 众生睡觉
众生睡觉 = KeywordsWords(keywords={'众生睡觉', },
                         priority=16,
                         returns= \
                             """晚安捏""")


