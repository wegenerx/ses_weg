# command_004_help/config.py
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Help 插件配置"""
    
    help_content: str = Field(
        default="""🤖 Bot 功能简介

══════════════


🔧 系统命令：
• \\reboot - 重启 Bot
• \\ban_list - 黑名单管理
  - \\ban_list add <词1> <词2> ... - 添加黑名单
  - \\ban_list rm <词1> <词2> ... - 移除黑名单
  - \\ban_list ls - 查看黑名单列表

📦 内容管理：
• \\remove [数字] [文件夹名] - 归档内容
  - \\remove - 归档最后一条记录到 remove 文件夹
  - \\remove(2) - 归档倒数第二条记录
  - \\remove outdated - 归档到 outdated 文件夹
  - \\remove(3) outdated - 归档倒数第三条到 outdated

📢 信息查询：
• \\release [数量] - 查看更新日志
  - \\release - 查看最近1次更新
  - \\release 3 - 查看最近3次更新
• \\help - 查看本帮助信息

══════════════

🖼️ 图片处理功能

回复图片消息使用以下命令：

几何变换：
• 对称左/右/上/下 - 将半部分翻转到另一半
• 镜像左/右/上/下 - 整图翻转后拼接（2倍大小）
• 平移左/右/上/下 - 半部分直接拼接

图像特效：
• 黑白 - 转为灰度图
• 模糊[参数] - 高斯模糊（参数：0.5-10）
• 锐化[参数] - 锐化增强（参数：0.5-5.0）
• 边缘检测 - 边缘检测效果
• 去噪[参数] - 中值滤波去噪（参数：0.5-3.0）
• 放大镜/凸透镜/凹透镜/老花镜[参数] - 球形畸变
  - 参数 < 1：向中心挤压（凹透镜）
  - 参数 > 1：中间放大（凸透镜）

══════════════

📥 消息收集功能

• 回复消息自动收集
  - 回复图片：自动保存到对应文件夹
  - 回复文本：自动保存到对应文件夹
  - 回复合并转发：批量收集所有子消息
• 创建新文件夹：add <prefix> <token1> [token2] ...


══════════════

• 基于 NoneBot2 框架 https://github.com/wegenerx/ses_weg

"""
    )
