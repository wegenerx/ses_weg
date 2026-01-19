# ses_weg/plugins/a015_banlist_admin/__init__.py
from __future__ import annotations

from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot, Event

from ses_weg.services import ban_list as banlist_svc
from ses_weg.services.restart import restart_process

ban_cmd = on_command("ban_list", permission=SUPERUSER, priority=1, block=True)


def _parse_op_and_tokens(plain: str) -> tuple[str | None, list[str]]:
    """
    支持：
      \\ban_list add 词1 词2 词3
      \\ban_list rm  词1 词2
      \\ban_list ls
    解析结果：
      (op, tokens)
    """
    s = (plain or "").strip()

    # 兼容消息里前面可能带反斜杠
    if s.startswith("\\"):
        s = s[1:].lstrip()

    parts = s.split()
    if len(parts) < 2:
        return None, []

    op = parts[1].lower()
    tokens = parts[2:]  # add/rm 后面按空格分成多个词
    return op, tokens


@ban_cmd.handle()
async def _(bot: Bot, event: Event):
    plain = event.get_plaintext().strip()

    op, tokens = _parse_op_and_tokens(plain)
    if op is None:
        await ban_cmd.finish("用法：\\ban_list add <词...> | \\ban_list rm <词...> | \\ban_list ls")

    if op in {"ls", "list"}:
        s = sorted(banlist_svc.load_set())
        preview = "，".join(s[:50])
        more = "" if len(s) <= 50 else f"\n... 还有 {len(s) - 50} 个"
        await ban_cmd.finish(f"ban_list 共 {len(s)} 个：\n{preview}{more}")

    if op == "add":
        if not tokens:
            await ban_cmd.finish("用法：\\ban_list add <词...>")

        added, total = banlist_svc.add(tokens)
        await ban_cmd.send(
            "已添加 {added} 个 ban_word：{words}\n当前共 {total} 个 ban_word。准备重启…".format(
                added=added,
                words=" | ".join(tokens),
                total=total,
            )
        )
        await restart_process(delay=1.0, reason="ban_list add")

    if op in {"rm", "remove", "del"}:
        if not tokens:
            await ban_cmd.finish("用法：\\ban_list rm <词...>")

        removed, total = banlist_svc.remove(tokens)
        await ban_cmd.send(
            "已删除 {removed} 个 ban_word：{words}\n当前共 {total} 个 ban_word。准备重启…".format(
                removed=removed,
                words=" | ".join(tokens),
                total=total,
            )
        )
        await restart_process(delay=1.0, reason="ban_list remove")

    await ban_cmd.finish("未知操作：add/rm/ls")
