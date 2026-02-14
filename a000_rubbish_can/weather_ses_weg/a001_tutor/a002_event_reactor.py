# --------------- basic info --------------- *
# auther: wegener 
# time & date: 2024/11/13, 20:51
# project: a002_编译.py, PyCharm, a002_event_reactor 
iii = 0


# --------------- debug-func --------------- *
def aa():
    print("a try\n")


def bb():
    global iii
    print("try order %d \n" % (iii))
    iii = iii + 1


# --------------- information if it's copied--------------- *

# * website of the project:  https://nonebot.dev/docs/tutorial/matcher
# * name of the original author(can be LLM):

# ------------------------------end predefine------------------------------

# start import --- *
import math
# end import ----- *
import nonebot
from nonebot import on_command
nonebot.init()

# ver.1
# weather = on_command("天气")

# ver.2
from nonebot.rule import to_me
weather = on_command("天气",
                     rule=to_me(),
                     aliases={"weather", "查天气"},
                     priority=10,
                     block=True)


# 这样，我们就获得了一个可以响应 天气、weather、查天气 三个命令的响应规则，
# 需要私聊或 @bot 时才会响应，优先级为 10（越小越优先），
# 阻断事件向后续优先级传播的事件响应器了。这些内容的意义和使用方法将会在后续的章节中一一介绍。









