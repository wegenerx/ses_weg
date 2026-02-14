from pydantic import BaseModel


class Config(BaseModel):
    repeater_config_path: str = "./data/repeater_config/"
    repeat_interval: int = 300

    class Config:
        extra = "ignore"








