# --------------- basic info --------------- *
# auther: wegener 
# time & date: 2024/11/13, 20:48
# project: a002_编译.py, PyCharm, a001_tutor 
iii = 0


# --------------- debug-func --------------- *
def aa():
    print("a try\n")


def bb():
    global iii
    print("try order %d \n" % (iii))
    iii = iii + 1


# --------------- information if it's copied--------------- *

# * website of the project:  https://nonebot.dev/docs/tutorial/create-plugin
# * name of the original author(can be LLM):

# ------------------------------end predefine------------------------------

# start import --- *
import math
# end import ----- *


import nonebot




from pathlib import Path
nonebot.init()

# 加载插件
nonebot.load_plugins("src/plugins", "path/to/your/plugins")
# nonebot.load_plugin("path.to.your.plugin")  # 加载第三方插件
nonebot.load_plugin(Path("./path/to/your/plugin.py"))  # 加载项目插件

nonebot.run()

