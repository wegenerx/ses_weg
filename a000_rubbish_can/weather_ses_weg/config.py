from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""


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