# -*- coding: utf-8 -*-
"""小青超推荐生成器
书籍 / 电影 / 纪录片 三种类型，每天各出一条
- 文案 150-250 字，第一人称"小青"口吻，阳光正能量
- 配图：小红书风格海报（书/电影/纪录片各对应一种视觉），768x1024 竖屏
- 文案末尾注明配图来源：📷 配图：小青超推荐 XX风 AI 生成
- 必带标签：#小青超推荐# #每日话题#
"""
import json
import re
from typing import List, Dict, Tuple

from src.api.agnes_ai import get_client
from src.core.content_generator import _parse_candidates, ContentItem, _clean_tags
from src.core.image_watermark import add_watermark, make_watermark_text
from src.config import CONFIG
from src.utils.logger import logger


# 三种类型的「配图来源说明 + 画图 Prompt」
_STYLE_PACKS: Dict[str, Tuple[str, str]] = {
    "book": (
        "小青超推荐·书香治愈风 AI 生成",
        "Realistic photography, cozy xiaohongshu bookstagram aesthetic. "
        "A beautifully designed hardcover book lying open on wooden table, "
        "beside a cup of hot latte with foam art, small green potted succulent, "
        "warm window sunlight, soft bokeh background, "
        "pastel warm color tone, shallow depth of field. "
        "NO TEXT, NO LOGOS on image. Vertical 3:4 composition."
    ),
    "movie": (
        "小青超推荐·电影海报风 AI 生成",
        "Xiaohongshu movie night poster aesthetic. "
        "Classic cinema scene: vintage film reel, clapperboard, popcorn in red-white box, "
        "warm amber cinema light, deep navy blue background with bokeh fairy lights, "
        "movie tickets beside, cinematic color grading. "
        "NO TEXT, NO LOGOS. Vertical 3:4."
    ),
    "doc": (
        "小青超推荐·纪录片自然风 AI 生成",
        "Realistic photography, xiaohongshu nature documentary aesthetic. "
        "Wide epic natural landscape: snow mountain with lake reflection, "
        "or old historical street with stone road, or milky way night sky over forest. "
        "Cinematic wide composition, golden hour light, earthy tone, "
        "wanderlust and inspiring vibe. "
        "NO TEXT, NO LOGOS. Vertical 3:4."
    ),
}

# 类型中文名
_TYPE_CN = {"book": "书籍", "movie": "电影", "doc": "纪录片"}


def generate_recommend(types: List[str] = None) -> List[ContentItem]:
    """生成小青超推荐（书籍+电影+纪录片各1条）
    Args:
        types: 要生成的类型子集，默认三种全出
    Returns:
        ContentItem 列表（按 book, movie, doc 顺序）
    """
    if types is None:
        types = ["book", "movie", "doc"]
    types = [t for t in types if t in _STYLE_PACKS]

    # 1. 一次文案请求，三种类型一起返回（省 API）——扁平 JSON，max_tokens 给足防截断
    text_prompt = _build_text_prompt(types)
    client = get_client()
    ok, text_result = client.generate_text(text_prompt, temperature=0.9, max_tokens=2500)
    if not ok:
        logger.error(f"❌ 推荐文案失败: {text_result}")
        return [ContentItem(module="recommend", item_type="推荐", error=f"文案失败: {text_result}")]

    # 2. 解析文案（三种类型分别解析）——多层兜底，保证拿到标题和足够字数的正文
    parsed = _parse_recommend_text(text_result, types)

    # 2.5 补全校验：某类型 title 缺失或正文<140 字，单独调一次补全
    for t in types:
        entry = parsed.get(t, {})
        title = entry.get("title", "")
        text = entry.get("text", "")
        if not title or len(text) < 140:
            logger.info(f"🔧 推荐-{_TYPE_CN[t]} 不合格(title={title[:10]}, len={len(text)})，单独补全")
            ok2, t2 = _repair_single_entry(t, entry)
            if ok2:
                parsed[t] = t2
                logger.info(f"✅ 补全完成: title={t2.get('title','')}, len={len(t2.get('text',''))}")

    # 3. 为每种类型生成配图 + 组装 ContentItem
    items = []
    for t in types:
        entry = parsed.get(t, {})
        title = entry.get("title", "")
        text = entry.get("text", "")
        tags = entry.get("tags") or _default_tags(t)
        source_note, img_prompt = _STYLE_PACKS[t]
        watermark = make_watermark_text("小青超推荐")

        # 如果文案里没有书名号形式的标题，强制加在最前面
        if title:
            titled = f"《{title}》"
            if titled not in text:
                text = f"{titled}——{text}"

        item = ContentItem(
            text=text,
            tags=tags,
            module="recommend",
            item_type=_TYPE_CN.get(t, t),
            source_note=source_note
        )

        ok_img, img_bytes, img_url = client.generate_image(img_prompt, size="768x1024")
        if ok_img and img_bytes:
            item.image_bytes = add_watermark(img_bytes, watermark)
            item.image_url = img_url
            logger.info(f"✅ 推荐-{_TYPE_CN[t]} 完成（{source_note}），字数{len(text)}")
        else:
            item.error = f"配图失败: {img_url}"
            logger.warning(f"⚠️ 推荐-{_TYPE_CN[t]} 配图失败: {img_url}")

        items.append(item)

    return items


def _repair_single_entry(type_key: str, broken: dict) -> Tuple[bool, dict]:
    """单条推荐不合格时，单独发一次 Agnes 补全标题和正文长度
    Returns: (成功?, 修复后的 entry dict)
    """
    cn = _TYPE_CN[type_key]
    prompt_tpl = {
        "book": "你是校园号小青，今天给大学生推荐一本真实存在的好书。直接输出 JSON：{\"title\":\"书名\",\"author\":\"作者\",\"text\":\"180字推荐理由，第一人称小青口吻，含：核心观点+作者背景+为什么适合大学生+推荐语结尾\"}。不要多余文字。text 必须不少于 180 字。",
        "movie": "你是校园号小青，今天给大学生推荐一部真实的好电影。直接输出 JSON：{\"title\":\"片名\",\"type\":\"类型\",\"text\":\"180字推荐理由，第一人称小青口吻，含：一句话看点+剧情简介不剧透+为什么适合学生群体+推荐语结尾\"}。不要多余文字。text 必须不少于 180 字。",
        "doc": "你是校园号小青，今天给大学生推荐一部真实的纪录片。直接输出 JSON：{\"title\":\"纪录片名\",\"theme\":\"主题\",\"text\":\"180字推荐理由，第一人称小青口吻，含：核心看点+内容简介+看完收获+推荐语结尾\"}。不要多余文字。text 必须不少于 180 字。",
    }
    ok, raw = get_client().generate_text(prompt_tpl[type_key], temperature=0.9, max_tokens=1200)
    if not ok:
        return False, broken
    entry = _parse_one_subjson(raw, type_key)
    if entry.get("text") and len(entry["text"]) >= 140:
        entry.setdefault("tags", _default_tags(type_key))
        return True, entry
    return False, broken


def _parse_one_subjson(raw: str, type_key: str) -> dict:
    """从一段可能脏的文本里拿出 {title,text}，补全时专用"""
    # 方法 1：全量 JSON（扁平 {title,author,type,theme,text,...}）
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            d = json.loads(raw[start:end + 1])
            if isinstance(d, dict) and d.get("text"):
                return {"title": d.get("title", ""),
                        "text": str(d["text"]).strip(),
                        "tags": _clean_tags(d.get("tags") or _default_tags(type_key))}
        except (json.JSONDecodeError, ValueError):
            pass
    # 方法 2：书名号取标题 + 全量非 JSON 正文
    m = re.search(r"《([^《》]{2,40})》", raw)
    title = m.group(1) if m else ""
    body = raw
    for junk in ["title", "author", "type", "theme", "text", "tags", "{", "}", "\"", "\\n", "candidates", "book", "movie", "doc"]:
        body = body.replace(junk, " ")
    body = re.sub(r"#[^#\s]+#?", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    body = body[:350]
    return {"title": title, "text": body, "tags": _default_tags(type_key)}


def _build_text_prompt(types: List[str]) -> str:
    """构造文案 Prompt（扁平 JSON，避免 candidates 嵌套，AI 更容易输出正确）"""
    required_tags = CONFIG.get("tags", {}).get("required", [])
    base_tags = [t for t in required_tags if "小青超推荐" in t or "每日话题" in t]

    schemas = {
        "book": f'"book": {{"title": "书籍全名（真实存在）", "author": "作者", '
                f'"text": "正文180-250字：《书名》开篇+核心观点+为什么适合河南理工大学学生读+暖心推荐语（必须不少于180字）"}}',
        "movie": f'"movie": {{"title": "电影全名（真实存在）", "type": "类型", '
                 f'"text": "正文180-250字：一句话核心看点+不剧透的剧情简介+为什么值得周末看+暖心推荐语结尾（必须不少于180字）"}}',
        "doc": f'"doc": {{"title": "纪录片全名（真实存在）", "theme": "主题", '
               f'"text": "正文180-250字：核心看点+内容概览+看完能学到什么+暖心推荐语结尾（必须不少于180字）"}}',
    }
    body_parts = [schemas[t] for t in types]
    body = ",\n  ".join(body_parts)

    return f"""你是河南理工大学校园号运营者「小青」，阳光正能量，第一人称口吻，像和好朋友分享好东西。

今天一次性推荐【{'、'.join(_TYPE_CN[t] for t in types)}】。

📌 硬性要求（必须全部满足）：
1. 每个「text」字段的正文必须 ≥ 180 字，≤ 280 字，第一人称"小青"
2. 每个「title」必须是真实存在、口碑较好的作品名（要写全名，不能瞎编）
3. 文案结构完整：引入 → 内容介绍 → 为什么适合大学生看 → 推荐语
4. 所有推荐共用标签必须包含：{base_tags}，每个类型可以再加自己相关的2-3个标签（如#豆瓣高分# #周末电影# #纪录片推荐# #大学生书单#等）
5. 严格输出扁平 JSON，不要 candidates 外层数组，不要 ```json 代码块，不要任何解释文字：

{{
  {body},
  "tags": {base_tags}
}}

只输出 JSON。"""


def _parse_recommend_text(raw: str, types: List[str]) -> Dict[str, Dict]:
    """解析推荐文案：6 层兜底，保证每个类型拿到 title + 180 字正文，绝不三条共用同一段！
    """
    result = {}

    # ===== 0. 剥 ```json =====
    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            code = parts[1].strip()
            lines = code.split("\n")
            if lines and lines[0].strip().lower() == "json":
                lines = lines[1:]
            text = "\n".join(lines).strip()

    # ===== 1. 扁平顶级 JSON（最新 Prompt 结构，优先走这个）=====
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            common_tags = data.get("tags") or []
            for t in types:
                if t in data and isinstance(data[t], dict):
                    entry = data[t]
                    result[t] = {
                        "title": str(entry.get("title", "")).strip(),
                        "text": str(entry.get("text", "")).strip(),
                        "tags": _clean_tags(
                            entry.get("tags") or common_tags or _default_tags(t)
                        )
                    }
            if all(t in result for t in types):
                return result
    except (json.JSONDecodeError, ValueError):
        pass

    # ===== 2. 找最大 JSON 块再解析（兼容 candidates 或不完整结构）=====
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            data = json.loads(text[s:e + 1])
            if isinstance(data, dict):
                # 可能是扁平 {book:{...}, movie:{...}} 或 {candidates:[{book:...}]}
                pool = []
                if "candidates" in data and isinstance(data["candidates"], list):
                    pool = data["candidates"]
                else:
                    pool = [data]
                for node in pool:
                    if not isinstance(node, dict):
                        continue
                    for t in types:
                        if t in node and isinstance(node[t], dict) and t not in result:
                            entry = node[t]
                            result[t] = {
                                "title": str(entry.get("title", "")).strip(),
                                "text": str(entry.get("text", "")).strip(),
                                "tags": _clean_tags(
                                    entry.get("tags") or node.get("tags") or _default_tags(t)
                                )
                            }
            if all(t in result for t in types):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # ===== 3. 为每个类型分别从原文中切「子 JSON 块」（最关键修复：避免三条共用一份 text）=====
    for t in types:
        if t in result and result[t]["title"] and len(result[t]["text"]) >= 140:
            continue  # 已合格，跳过
        entry = _extract_typed_block_via_regex(text, t)
        if entry:
            result[t] = entry

    # ===== 4. 最终兜底：还缺的类型，用《书名号》+ 整段非标签文字（这是最坏情况，随后会被 _repair_single_entry 再补）=====
    for t in types:
        if t not in result or not result[t].get("text"):
            title = _regex_extract_title_after_label(text, _TYPE_CN[t])
            body = _fallback_text_cleanup(text)
            result[t] = {"title": title, "text": body, "tags": _default_tags(t)}

    return result


def _extract_typed_block_via_regex(text: str, type_key: str) -> Optional[Dict]:
    """按类型定位 JSON 片段：找 '"type_key"' 后面的第一个 {…} 对象，单独解析 title/text"""
    # 1) 定位 "\"book\"" / "\"movie\"" / "\"doc\"" 的位置
    needle = f'"{type_key}"'
    pos = text.find(needle)
    if pos == -1:
        return None

    # 2) 从该位置往后找第一个 "{"
    brace_start = text.find("{", pos)
    if brace_start == -1:
        return None

    # 3) 括号配对找结束的 "}"
    depth = 0
    in_str = False
    esc = False
    brace_end = -1
    for i in range(brace_start, len(text)):
        ch = text[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                brace_end = i
                break
    if brace_end == -1:
        return None

    chunk = text[brace_start:brace_end + 1]
    try:
        d = json.loads(chunk)
        if isinstance(d, dict) and d.get("text"):
            return {
                "title": str(d.get("title", "")).strip(),
                "text": str(d["text"]).strip(),
                "tags": _clean_tags(d.get("tags") or _default_tags(type_key))
            }
    except (json.JSONDecodeError, ValueError):
        pass

    # 4) JSON 解析坏掉，从 chunk 里用正则拿 "title":"…" 和 "text":"…"
    title = ""
    mt = re.search(r'"title"\s*:\s*"([^"]{2,40})"', chunk)
    if mt:
        title = mt.group(1)
    body = ""
    mb = re.search(r'"text"\s*:\s*"((?:[^"\\]|\\.){80,})"', chunk)
    if mb:
        body = mb.group(1).replace('\\"', '"').replace("\\n", "\n").strip()
    if title or body:
        return {
            "title": title,
            "text": body or _fallback_text_cleanup(chunk),
            "tags": _default_tags(type_key)
        }
    return None



def _default_tags(type_key: str) -> List[str]:
    required = CONFIG.get("tags", {}).get("required", [])
    tags = [t for t in required if "小青超推荐" in t or "每日话题" in t]
    extras = {
        "book": ["#大学生书单#", "#豆瓣高分#"],
        "movie": ["#电影推荐#", "#周末片单#"],
        "doc": ["#纪录片推荐#", "#涨知识#"],
    }
    tags.extend(extras.get(type_key, []))
    return _clean_tags(tags)


def _regex_get(text: str, path) -> str:
    """简易从 JSON 文本中按路径拿第一个字符串值（失败回空）"""
    return ""  # 下面用更鲁棒的专用函数


def _regex_extract_title_after_label(text: str, type_cn: str) -> str:
    """从文本里找「书籍：XXX」或书名号《XXX》里的标题"""
    # 找中文书名号
    m = re.search(r"《([^《》]{1,40})》", text)
    if m:
        return m.group(1).strip()
    # 找 「类型：标题」模式
    m = re.search(rf"{type_cn}\s*[:：]\s*《?([^《》\n，。]{{2,40}})》?", text)
    if m:
        return m.group(1).strip()
    return ""


def _regex_extract_body(text: str, keywords) -> str:
    """从文本里提取推荐正文（找 text 字段的字符串）"""
    # 优先 "text": "xxx"
    m = re.search(r'"text"\s*:\s*"((?:[^"\\]|\\.){50,})"', text)
    if m:
        body = m.group(1).replace('\\"', '"').replace("\\n", "\n")
        return body.strip()
    return ""


def _fallback_text_cleanup(text: str) -> str:
    """兜底：从乱的文本里剔掉 JSON 结构和标签，保留正文"""
    # 剔标签
    for tag in re.findall(r"#[^#\s]+#?", text):
        text = text.replace(tag, "")
    # 剔 JSON 关键字
    for junk in ["candidates", "title", "author", "type", "theme", "text", "tags",
                 "book", "movie", "doc", "{", "}", "[", "]", "\""]:
        text = text.replace(junk, " ")
    # 合并空格
    text = re.sub(r"\s+", " ", text).strip(" ,，:：")
    # 取前 300 字
    return text[:300]


def _extract_tags_from_full_text(text: str, type_key: str) -> List[str]:
    tags = re.findall(r"#[^#\s]{2,}#?", text)
    if not tags:
        tags = _default_tags(type_key)
    return _clean_tags(tags)


_CN_TO_KEY = {"书籍": "book", "电影": "movie", "纪录片": "doc", "book": "book", "movie": "movie", "doc": "doc"}


def generate_single_recommend(type_name: str) -> ContentItem:
    """[单条换一条专用] 强制指定类型生成 1 条推荐
    type_name 接受中文（书籍/电影/纪录片）或 key（book/movie/doc）
    """
    type_key = _CN_TO_KEY.get(str(type_name).strip())
    if not type_key:
        items = generate_recommend(types=["book"])
        return items[0] if items else ContentItem(module="recommend", error="[小青超推荐] 类型无效")
    items = generate_recommend(types=[type_key])
    if not items:
        return ContentItem(
            module="recommend", item_type=_TYPE_CN[type_key],
            error="[小青超推荐] 单条生成失败"
        )
    return items[0]
