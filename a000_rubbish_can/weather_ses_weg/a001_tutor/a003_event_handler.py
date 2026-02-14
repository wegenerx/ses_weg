# --------------- basic info --------------- *
# auther: wegener 
# time & date: 2024/11/13, 20:54
# project: a002_编译.py, PyCharm, a003_event_management 
iii = 0


# --------------- debug-func --------------- *
def aa():
    print("a try\n")


def bb():
    global iii
    print("try order %d \n" % (iii))
    iii = iii + 1


# --------------- information if it's copied--------------- *

# * website of the project:  https://nonebot.dev/docs/tutorial/handler
# * name of the original author(can be LLM):

# ------------------------------end predefine------------------------------

# start import --- *
import math
# end import ----- *

import nonebot
from nonebot.rule import to_me
from nonebot.plugin import on_command

nonebot.init()

weather = on_command("天气",
                     rule=to_me(),
                     aliases={"weather", "查天气"},
                     priority=10,
                     block=True)


@weather.handle()
async def handle_function():
    # await weather.send("天气是...")
    await weather.finish("天气是...")


nonebot.run()
