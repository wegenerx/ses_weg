from pydantic import BaseModel, Field
from typing import List


class Config(BaseModel):
    """Plugin Config Here"""

    # 推送黑名单（文件夹名含这些子串会跳过图片推送和添加）
    push_blacklist: List[str] = Field(
        default=["collect", "collection"],
        description="推送黑名单：文件夹名包含这些关键词时，不会推送图片也不会添加图片"
    )

    # 图片下载超时（秒），大图可适当延长
    image_fetch_timeout: int = Field(
        default=90,
        description="单张图片下载超时时间（秒），处理多张大图时可延长"
    )

    # 超过此数量时先发“正在处理”以维持连接
    many_images_ack_threshold: int = Field(
        default=5,
        description="图片数量超过此值时，先发送「正在处理」再开始下载，避免 WebSocket 超时"
    )
