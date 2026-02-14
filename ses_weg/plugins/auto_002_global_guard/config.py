from pydantic import BaseModel, Field
from typing import Dict


class Config(BaseModel):
    """Plugin Config Here"""
    
    # 频率限制配置：{时间窗口（秒）: 最大发送次数}
    # 例如：{5: 1, 15: 2, 60: 3} 表示：
    #   - 5秒内最多发送1条
    #   - 15秒内最多发送2条
    #   - 60秒内最多发送3条
    rate_limit_rules: Dict[int, int] = Field(
        default={
            5: 1,   # 5秒内最多1条
            15: 2,  # 15秒内最多2条
            60: 3   # 60秒内最多3条
        },
        description="频率限制规则字典，格式：{时间窗口（秒）: 最大发送次数}"
    )