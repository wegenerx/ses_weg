# a013_jm/__init__.py
"""
解析 JM 类网页（如 18comic.vip/album/xxx），归档参数和内容到本地
发链接自动触发，不登录版本
"""
import json
import os
import re

import nonebot
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.plugin import PluginMetadata

try:
    import httpx
except ImportError:
    httpx = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

__plugin_meta__ = PluginMetadata(
    name="a013_jm",
    description="解析 JM 网页并归档到本地",
    usage="发送 18comic.vip/album/xxx 等链接自动解析归档",
)

# JM 链接匹配：18comic.vip/album/数字，支持 https 和多种域名变体
JM_ALBUM_PATTERN = re.compile(
    r"https?://(?:[a-zA-Z0-9.-]*\.)?(?:18comic|jmcomic)\.(?:vip|org|cc|one)/album/(\d+)",
    re.I,
)

# 存档根目录（插件目录下的 archive）
def _archive_root() -> str:
    p = os.path.abspath(__file__)
    return os.path.normpath(os.path.join(os.path.dirname(p), "archive"))


def _ensure_archive():
    root = _archive_root()
    os.makedirs(root, exist_ok=True)
    return root


async def _fetch_page(url: str) -> str | None:
    """获取页面 HTML"""
    if not httpx:
        nonebot.logger.error("[a013_jm] 需要安装 httpx: pip install httpx")
        return None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return r.text
    except Exception as e:
        nonebot.logger.error(f"[a013_jm] 请求失败: {e}")
        return None


def _parse_album_page(html: str, album_id: str, url: str) -> dict:
    """
    解析专辑页，提取 title、author、tags、cover、chapters 等
    无 cookie 版本，仅解析公开可见内容
    """
    if not BeautifulSoup:
        nonebot.logger.error("[a013_jm] 需要安装 beautifulsoup4: pip install beautifulsoup4")
        return {"album_id": album_id, "url": url, "error": "bs4 not installed"}

    soup = BeautifulSoup(html, "html.parser")
    data = {
        "album_id": album_id,
        "url": url,
        "title": "",
        "author": "",
        "tags": [],
        "description": "",
        "cover": "",
        "chapters": [],
        "raw_links": [],
    }

    # 通用选择器，按常见结构尝试
    # 标题
    for sel in ("h1", ".album-title", ".title", '[class*="album"] h1', '[class*="title"]'):
        try:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                data["title"] = el.get_text(strip=True)
                break
        except Exception:
            pass

    # 作者
    for sel in ('a[href*="author"]', '.author', '[class*="author"]', 'span[class*="artist"]'):
        try:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                data["author"] = el.get_text(strip=True)
                break
        except Exception:
            pass

    # 标签
    for sel in ('a[href*="tag"]', '.tag', '[class*="tag"]', '.genre a'):
        try:
            for el in soup.select(sel):
                t = el.get_text(strip=True)
                if t and len(t) < 30:
                    data["tags"].append(t)
        except Exception:
            pass
    data["tags"] = list(dict.fromkeys(data["tags"]))[:30]

    # 封面
    for sel in ('.thumbnail img', '.cover img', 'img[class*="cover"]', '.album-cover img', 'article img'):
        try:
            el = soup.select_one(sel)
            if el and el.get("src"):
                src = el.get("src") or el.get("data-src")
                if src and src.startswith(("http", "//")):
                    data["cover"] = src if src.startswith("http") else "https:" + src
                    break
        except Exception:
            pass

    # 章节列表
    for sel in ('a[href*="/photo/"]', 'a[href*="/chapter/"]', '.episode a', '[class*="chapter"] a'):
        try:
            for el in soup.select(sel):
                href = el.get("href")
                text = el.get_text(strip=True)
                if href and ("/photo/" in href or "/chapter/" in href):
                    if not href.startswith("http"):
                        href = "https://18comic.vip" + href if href.startswith("/") else url.rsplit("/", 1)[0] + "/" + href
                    data["chapters"].append({"title": text or href, "url": href})
                    data["raw_links"].append(href)
        except Exception:
            pass
    data["chapters"] = data["chapters"][:200]
    data["raw_links"] = list(dict.fromkeys(data["raw_links"]))[:200]

    # 描述
    for sel in ('.description', '.summary', '[class*="desc"]', '[class*="summary"]'):
        try:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                data["description"] = el.get_text(strip=True)[:500]
                break
        except Exception:
            pass

    return data


def _save_archive(album_id: str, data: dict) -> str:
    """保存到 archive/{album_id}/"""
    root = _ensure_archive()
    folder = os.path.join(root, str(album_id))
    os.makedirs(folder, exist_ok=True)
    meta_path = os.path.join(folder, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return folder


jm_matcher = on_message(priority=5, block=False)


@jm_matcher.handle()
async def _(bot: Bot, event: MessageEvent):
    text = event.get_plaintext().strip()
    m = JM_ALBUM_PATTERN.search(text)
    if not m:
        return

    album_id = m.group(1)
    url = m.group(0)

    if not httpx or not BeautifulSoup:
        await jm_matcher.send("[a013_jm] 缺少依赖: pip install httpx beautifulsoup4")
        return

    await jm_matcher.send(f"正在解析：{url}")

    html = await _fetch_page(url)
    if not html:
        await jm_matcher.send("解析失败：无法获取页面")
        return

    data = _parse_album_page(html, album_id, url)
    folder = _save_archive(album_id, data)

    title = data.get("title") or f"album_{album_id}"
    info = f"标题: {title}\n作者: {data.get('author', '-')}\n标签: {', '.join(data.get('tags', [])[:10]) or '-'}"
    await jm_matcher.send(f"已归档到 {folder}\n{info}")
