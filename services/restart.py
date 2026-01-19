# ses_weg/services/restart.py
from __future__ import annotations

import os
import sys
import asyncio
from typing import Optional

async def restart_process(
    *,
    delay: float = 1.0,
    reason: str = "",
) -> None:
    """
    进程级重启：最稳（适用于 Windows / Linux）。
    - delay: 给消息/日志 flush 的时间
    - reason: 仅用于你自己记录/扩展（可接入日志）
    """
    if delay > 0:
        await asyncio.sleep(delay)

    python = sys.executable
    argv = [python] + sys.argv

    # 你后续想在这里加：
    # - 写入重启原因到文件
    # - 清理临时文件
    # - 关闭某些资源句柄
    # 都只改这一处即可

    os.execv(python, argv)
