from pydantic import BaseModel, Field
from typing import List, Set


class Config(BaseModel):
    """a014_maimai 表情包系统配置"""

    # MySQL 数据库（记录图片上传者、溯源等）
    meme_db_host: str = Field(default="127.0.0.1", description="数据库主机")
    meme_db_port: int = Field(default=3306, description="数据库端口")
    meme_db_user: str = Field(default="root", description="数据库用户")
    meme_db_password: str = Field(default="", description="数据库密码")
    meme_db_database: str = Field(default="meme_db", description="数据库名")

    # 管理员 QQ 号（除 superusers 外）
    admin_users: List[int] = Field(
        default=[3429630094, 3316413099, 2338680148],
        description="管理员 QQ 列表"
    )

    # 违禁文件夹名（禁止作为分类名）
    banned_words: List[str] = Field(
        default=["djb", "sb", "nm", "nmb"],
        description="违禁词，不可作为文件夹名"
    )

    # pic上传 时保存到 Mzk API 的本地路径
    api_root_dir: str = Field(
        default="",
        description="pic上传 保存路径，留空则禁用 pic上传 功能"
    )
