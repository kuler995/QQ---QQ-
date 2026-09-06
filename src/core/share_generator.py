# -*- coding: utf-8 -*-
"""
小青爱分享生成器
- 6 种类型：科普冷知识、生活小妙招、学习技巧、健康小贴士、校史趣闻、节气节日小知识
- 每天随机出 2 条（类型混搭，尽量不重复）
- 文案 150-250 字，阳光正能量 + 第一人称小青口吻
- 配图写实风，水印「小青爱分享」
"""

import json
import re
import random
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from src.api.agnes_ai import get_client
from src.core.content_generator import (
    ContentItem,
    _parse_candidates,
    _clean_tags,
)
from src.core.image_watermark import add_watermark, make_watermark_text
from src.config import CONFIG
from src.utils.logger import logger


_TYPE_CN = {
    "science":   "科普冷知识",
    "life":      "生活小妙招",
    "study":     "学习技巧",
    "health":    "健康小贴士",
    "campus":    "校史趣闻",
    "season":    "节气节日小知识",
}

_TYPE_TAG_HINT = {
    "science": ["#科普冷知识#", "#涨知识#", "#冷知识分享#", "#百科全书#"],
    "life":    ["#生活小妙招#", "#实用生活技巧#", "#生活小百科#", "#家居日常#"],
    "study":   ["#学习技巧#", "#大学生必备#", "#期末复习#", "#干货分享#"],
    "health":  ["#健康小贴士#", "#养生小知识#", "#日常保健#", "#生活健康#"],
    "campus":  ["#河南理工大学#", "#校史趣闻#", "#校园故事#", "#我的大学#"],
    "season":  ["#节气小知识#", "#传统节日#", "#今日是什么日子#", "#传统文化#"],
}

# 每种类型对应 1 套小红书风格的配图模板（写实风，不重复）
_STYLE_PACKS: Dict[str, Tuple[str, str]] = {
    "science": (
        "小青爱分享·创意科普风 AI 生成",
        "Realistic photography, xiaohongshu infographic aesthetic. "
        "A cute scientist desk with magnifying glass, beaker with blue liquid, "
        "DNA helix model, a chalkboard with scientific doodles in background, "
        "soft warm side light, bright and clean style. NO TEXT. Vertical 3:4."
    ),
    "life": (
        "小青爱分享·家居生活风 AI 生成",
        "Realistic photography, xiaohongshu cozy home life aesthetic. "
        "White marble countertop with lemon slices, bamboo cleaning brush, "
        "white ceramic bottle, linen cloth, warm window sunlight. "
        "Fresh bright pastel tone, shallow depth of field. NO TEXT. Vertical 3:4."
    ),
    "study": (
        "小青爱分享·学霸书桌风 AI 生成",
        "Realistic photography, xiaohongshu study inspiration aesthetic. "
        "Modern minimalist desk with open textbook, colorful highlight markers, "
        "headphones, cup of coffee, small succulent plant, "
        "warm natural side light, cozy and productive vibe. NO TEXT. Vertical 3:4."
    ),
    "health": (
        "小青爱分享·健康养生风 AI 生成",
        "Realistic photography, xiaohongshu wellness aesthetic. "
        "Yoga mat on wooden floor, fresh fruits on wooden plate, "
        "glass of green smoothie, white towel, small yoga blocks, "
        "soft natural light, bright and energetic. NO TEXT. Vertical 3:4."
    ),
    "campus": (
        "小青爱分享·理工校园风 AI 生成",
        "Realistic photography, xiaohongshu university campus aesthetic. "
        "Traditional Chinese arch gate (Henan Polytechnic style) with trees, "
        "students walking, red brick library building in background, "
        "sunny autumn afternoon, warm nostalgic tone. NO TEXT. Vertical 3:4."
    ),
    "season": (
        "小青爱分享·节气民俗风 AI 生成",
        "Realistic photography, xiaohongshu chinese tradition aesthetic. "
        "Bamboo mat with green tea cup, osmanthus flowers, "
        "paper lantern, traditional chinese window lattice with soft light, "
        "warm earthy tone, peaceful cultural vibe. NO TEXT. Vertical 3:4."
    ),
}


def generate_share(count: int = 2, types: Optional[List[str]] = None) -> List[ContentItem]:
    """生成小青爱分享内容
    Args:
        count: 生成条数（默认 2，不重复类型混搭）
        types: 强制指定类型列表（不填则随机从 6 种里抽）
    """
    all_types = list(_TYPE_CN.keys())
    if types:
        chosen_types = [t for t in types if t in all_types]
    else:
        if count >= len(all_types):
            chosen_types = all_types
            random.shuffle(chosen_types)
        else:
            chosen_types = random.sample(all_types, count)
    logger.info(f"📚 今日小青爱分享选到的类型：{[ _TYPE_CN[t] for t in chosen_types ]}")

    # 1. 一次文案请求，一次出多条，扁平 JSON
    text_prompt = _build_text_prompt(chosen_types)
    client = get_client()
    ok, text_result = client.generate_text(text_prompt, temperature=0.92, max_tokens=2500)
    if not ok:
        logger.error(f"❌ 小青爱分享文案失败: {text_result}")
        # 全失败时，按类型逐条单独补，保证最终一定有 count 条
        items = []
        for t in chosen_types:
            ok2, entry = _repair_single_entry(t, {})
            if not ok2:
                items.append(ContentItem(
                    module="share", item_type=_TYPE_CN[t],
                    error=f"[小青爱分享·{_TYPE_CN[t]}] 文案失败: {text_result}"
                ))
            else:
                items.append(_make_item(t, entry))
        return items

    # 2. 解析（多层兜底）
    parsed = _parse_share_text(text_result, chosen_types)

    # 3. 不合格自动补全：正文 < 140 或 title 为空 → 单独再补
    for t in chosen_types:
        entry = parsed.get(t, {})
        if not entry.get("title") or len(entry.get("text", "")) < 140:
            logger.info(f"🔧 小青爱分享-{_TYPE_CN[t]} 不合格，单独补全")
            ok2, ent2 = _repair_single_entry(t, entry)
            if ok2:
                parsed[t] = ent2

    # 4. 为每条生成配图
    items = []
    for t in chosen_types:
        entry = parsed.get(t, {})
        if not entry.get("text"):
            # 实在没有文案，走单条补一次
            ok2, ent2 = _repair_single_entry(t, entry)
            entry = ent2 if ok2 else {"title": "", "text": "", "tags": _default_tags(t)}
        items.append(_make_item(t, entry))

    # 兜底 count
    while len(items) < count:
        items.append(ContentItem(
            module="share", item_type="分享",
            error="[小青爱分享] 生成不足"
        ))

    return items


def _make_item(type_key: str, entry: Dict) -> ContentItem:
    """组装单个分享条目：写正文+强制标题+画配图+水印"""
    cn = _TYPE_CN[type_key]
    title = entry.get("title", "")
    text = entry.get("text", "")
    tags = entry.get("tags") or _default_tags(type_key)
    source_note, img_prompt = _STYLE_PACKS[type_key]
    watermark = make_watermark_text("小青爱分享")

    # 标题开头强制加
    if title and title not in text:
        text = f"【{title}】{text}"

    item = ContentItem(
        text=text,
        tags=tags,
        module="share",
        item_type=cn,
        source_note=source_note
    )

    ok_img, img_bytes, img_url = get_client().generate_image(img_prompt, size="768x1024")
    if (not ok_img or not img_bytes):
        logger.info(f"🔄 小青爱分享-{cn} 配图失败，自动重试画图...")
        ok_img, img_bytes, img_url = get_client().generate_image(img_prompt, size="768x1024")

    if ok_img and img_bytes:
        item.image_bytes = add_watermark(img_bytes, watermark)
        item.image_url = img_url
        logger.info(f"✅ 小青爱分享-{cn} 完成（字数{len(text)}，{source_note}）")
    else:
        item.error = f"[小青爱分享·{cn}] 配图失败: {img_url or '返回空'}"
        logger.warning(f"⚠️ 小青爱分享-{cn} 配图失败: {img_url}")

    return item


# ============= Prompt 构造 =============
def _build_text_prompt(types: List[str]) -> str:
    """扁平 JSON Prompt，每种类型一个 key"""
    required_tags = CONFIG.get("tags", {}).get("required", [])
    base_tags = [t for t in required_tags if "每日话题" in t]

    # 今天的节气 / 节日提示（方便 season 类型选相关主题）
    today = datetime.now()
    try:
        festivals = {
            (2, 14): "情人节", (3, 8): "女神节", (5, 4): "青年节", (6, 1): "儿童节",
            (9, 10): "教师节", (10, 1): "国庆节", (12, 25): "圣诞节", (1, 1): "元旦",
        }
        today_cn = festivals.get((today.month, today.day), "")
    except Exception:
        today_cn = ""

    today_line = f"今天是 {today.strftime('%Y年%m月%d日')}。"
    if today_cn:
        today_line += f" 今天是{today_cn}，可以结合节日主题。"

    # 每个类型的字段说明
    schema_parts = []
    for t in types:
        cn = _TYPE_CN[t]
        if t == "science":
            schema_parts.append(
                f'"{t}": {{"title":"知识点标题（短）","text":"正文180-250字：用小青第一人称讲一个有趣的科学冷知识，要让大学生觉得哇原来是这样的！分：引入→原理→生活应用→一句总结（必须≥180字）"}}'
            )
        elif t == "life":
            schema_parts.append(
                f'"{t}": {{"title":"小妙招名称（短）","text":"正文180-250字：用小青第一人称分享一个超实用的生活小妙招（比如去油污、收纳、清洁、省电等），分：场景痛点→步骤→为什么有效→一句暖心提醒（≥180字）"}}'
            )
        elif t == "study":
            schema_parts.append(
                f'"{t}": {{"title":"技巧名称（短）","text":"正文180-250字：用小青第一人称分享一个大学生超实用的学习技巧（比如背诵法、记笔记、复习、考试应对、论文等），分：为什么有用→具体步骤→真实感案例→推荐语（≥180字）"}}'
            )
        elif t == "health":
            schema_parts.append(
                f'"{t}": {{"title":"健康点（短）","text":"正文180-250字：用小青第一人称讲一个适合大学生的健康小贴士（比如久坐、颈椎、视力、饮食、睡眠、运动等），分：问题→原因→正确做法→一句鼓励（≥180字）"}}'
            )
        elif t == "campus":
            schema_parts.append(
                f'"{t}": {{"title":"校史小故事标题（短）","text":"正文180-250字：用小青第一人称讲一个河南理工大学相关的趣闻小知识（比如建校历史、知名校友、校园传说、知名建筑由来、校训来历等），要有真实感，不能瞎编。分：背景→故事→启发（≥180字）"}}'
            )
        elif t == "season":
            schema_parts.append(
                f'"{t}": {{"title":"节气/节日名+小标题","text":"正文180-250字：用小青第一人称讲一个贴近今天的节气或传统节日小知识（或今天所在季节的民俗），分：由来→传统习俗→当代年轻人可以怎么过→一句暖心祝福（≥180字）"}}'
            )

    body = ",\n  ".join(schema_parts)
    return f"""你是河南理工大学校园号运营者「小青」，阳光正能量，第一人称"小青"口吻，像和好朋友分享有趣小知识。

{today_line}
今天要分享【{'、'.join(_TYPE_CN[t] for t in types)}】这{len(types)}类内容。

📌 硬性要求（必须全部满足）：
1. 每个类型的「text」字段必须 ≥ 180 字，≤ 280 字，第一人称「小青」
2. 每个类型的「title」必须简短有力（8-15字）
3. 结构完整：引入 → 主体 → 实用小提醒/总结
4. 共用标签必须包含：{base_tags}，每个类型再灵活加自己相关的2-3个标签
5. 严格输出扁平 JSON，不要 candidates 数组，不要 ```json 代码块，不要任何解释文字：

{{
  {body},
  "tags": {base_tags}
}}

只输出 JSON，一条都不能少！"""


# ============= 解析 =============
def _parse_share_text(raw: str, types: List[str]) -> Dict[str, Dict]:
    """6 层兜底解析，保证每个类型拿到 title+text"""
    result = {}
    text = raw.strip()

    # 0. 剥 ```json
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            code = parts[1].strip()
            lines = code.split("\n")
            if lines and lines[0].strip().lower() == "json":
                lines = lines[1:]
            text = "\n".join(lines).strip()

    # 1. 扁平顶级 JSON（最新结构优先）
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

    # 2. 最大 JSON 块解析（兼容 {items:[{type,title,text,...}]}）
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            data = json.loads(text[s:e + 1])
            if isinstance(data, dict):
                pool = data.get("items") or data.get("candidates") or [data]
                if isinstance(pool, list):
                    for node in pool:
                        if not isinstance(node, dict):
                            continue
                        # 扁平结构
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
                        # 列表结构 {type:"science", title:"", text:""}
                        t = node.get("type") or node.get("key") or ""
                        if t in types and t not in result and node.get("text"):
                            result[t] = {
                                "title": str(node.get("title", "")).strip(),
                                "text": str(node.get("text", "")).strip(),
                                "tags": _clean_tags(node.get("tags") or _default_tags(t))
                            }
            if all(t in result for t in types):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. 按类型正则切子对象（括号配对，同 recommend 解析）
    for t in types:
        if t in result and result[t]["title"] and len(result[t]["text"]) >= 140:
            continue
        entry = _extract_typed_block_via_regex(text, t)
        if entry:
            result[t] = entry

    # 4. 终极兜底：从全文中按 type 找 【标题】或 《标题》+ 正文
    for t in types:
        if t in result and result[t].get("text"):
            continue
        title = ""
        m = re.search(r"【([^【】]{2,30})】", text) or re.search(r"《([^《》]{2,30})》", text)
        if m:
            title = m.group(1)
        body = _fallback_text_cleanup(text)
        result[t] = {"title": title, "text": body, "tags": _default_tags(t)}

    return result


def _extract_typed_block_via_regex(text: str, type_key: str) -> Optional[Dict]:
    """定位"type_key"关键字后的 {…} 对象，单独解析"""
    needle = f'"{type_key}"'
    pos = text.find(needle)
    if pos == -1:
        # 也允许 "type": "type_key" 后面紧跟对象
        m = re.search(rf'"type"\s*:\s*"{type_key}".*?(\{{)', text, flags=re.DOTALL)
        if m:
            brace_start = m.start(1)
        else:
            return None
    else:
        brace_start = text.find("{", pos)
        if brace_start == -1:
            return None

    depth = 0
    in_str = False
    esc = False
    brace_end = -1
    for i in range(brace_start, len(text)):
        ch = text[i]
        if esc:
            esc = False; continue
        if ch == "\\":
            esc = True; continue
        if ch == '"':
            in_str = not in_str; continue
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

    title = ""
    mt = re.search(r'"title"\s*:\s*"([^"]{2,30})"', chunk)
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


# ============= 单条补全 =============
def _repair_single_entry(type_key: str, broken: Dict) -> Tuple[bool, Dict]:
    """单条不合格时，单独调一次 Agnes 补全"""
    cn = _TYPE_CN[type_key]
    today_line = f"今天是 {datetime.now().strftime('%Y年%m月%d日')}。"

    prompt_tpl = {
        "science": f"{today_line} 你是校园号小青，今天给大学生讲一个有趣的科学冷知识。输出JSON：{{\"title\":\"8-15字短标题\",\"text\":\"180-250字正文，第一人称小青口吻。分：引入→科学原理→生活应用→一句总结。必须≥180字\"}}。不要多余文字。",
        "life":    f"{today_line} 你是校园号小青，今天分享一个超实用生活小妙招。输出JSON：{{\"title\":\"8-15字短标题\",\"text\":\"180-250字正文，第一人称小青口吻。分：场景痛点→步骤→为什么有效→暖心提醒。必须≥180字\"}}。不要多余文字。",
        "study":   f"{today_line} 你是校园号小青，今天给河南理工的同学分享一个超实用学习技巧。输出JSON：{{\"title\":\"8-15字短标题\",\"text\":\"180-250字正文，第一人称小青口吻。分：为什么有用→具体步骤→真实例子→推荐。必须≥180字\"}}。不要多余文字。",
        "health":  f"{today_line} 你是校园号小青，今天讲一个适合大学生的健康小贴士。输出JSON：{{\"title\":\"8-15字短标题\",\"text\":\"180-250字正文，第一人称小青口吻。分：问题→原因→正确做法→鼓励。必须≥180字\"}}。不要多余文字。",
        "campus":  f"{today_line} 你是校园号小青，今天讲一个河南理工大学校史趣闻或校园小故事。输出JSON：{{\"title\":\"8-15字短标题\",\"text\":\"180-250字正文，第一人称小青口吻。分：背景→故事→启发。内容要有真实感，不能瞎编。必须≥180字\"}}。不要多余文字。",
        "season":  f"{today_line} 你是校园号小青，今天分享一个节气/传统节日小知识（尽量结合今天所在季节或临近的节日）。输出JSON：{{\"title\":\"8-15字短标题\",\"text\":\"180-250字正文，第一人称小青口吻。分：由来→传统习俗→年轻人可以怎么过→祝福。必须≥180字\"}}。不要多余文字。",
    }
    ok, raw = get_client().generate_text(prompt_tpl[type_key], temperature=0.9, max_tokens=1200)
    if not ok:
        return False, broken
    entry = _parse_one_subjson(raw, type_key)
    if entry.get("text") and len(entry["text"]) >= 140:
        return True, entry
    return False, broken


def _parse_one_subjson(raw: str, type_key: str) -> Dict:
    """单条补全专用解析"""
    s, e = raw.find("{"), raw.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            d = json.loads(raw[s:e + 1])
            if isinstance(d, dict) and d.get("text"):
                return {
                    "title": str(d.get("title", "")).strip(),
                    "text": str(d["text"]).strip(),
                    "tags": _clean_tags(d.get("tags") or _default_tags(type_key))
                }
        except (json.JSONDecodeError, ValueError):
            pass
    m = re.search(r"《([^《》]{2,40})》", raw) or re.search(r"【([^【】]{2,40})】", raw)
    title = m.group(1) if m else ""
    body = raw
    for junk in ["title", "text", "tags", "{", "}", "\"", "\\n", "science", "life", "study", "health", "campus", "season"]:
        body = body.replace(junk, " ")
    body = re.sub(r"#[^#\s]+#?", "", body)
    body = re.sub(r"\s+", " ", body).strip()[:350]
    return {"title": title, "text": body, "tags": _default_tags(type_key)}


# ============= 工具函数 =============
def _default_tags(type_key: str) -> List[str]:
    required = CONFIG.get("tags", {}).get("required", [])
    base = [t for t in required if "每日话题" in t]
    return base + _TYPE_TAG_HINT.get(type_key, [])[:3]


def _clean_tags(tags) -> List[str]:
    result = []
    if isinstance(tags, list):
        for t in tags:
            ts = str(t).strip()
            if not ts:
                continue
            if not ts.startswith("#"):
                ts = "#" + ts
            if not ts.endswith("#"):
                ts = ts + "#"
            result.append(ts)
    elif isinstance(tags, str):
        for part in re.split(r"\s+", tags.strip()):
            if part.startswith("#"):
                result.append(part if part.endswith("#") else part + "#")
    # 去重保序
    seen = set()
    out = []
    for t in result:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _fallback_text_cleanup(raw: str) -> str:
    """终极兜底：从原始文本中清出正文（150-300 字）"""
    body = raw
    # 剥 JSON
    body = re.sub(r"\{.*?\}", " ", body, flags=re.DOTALL)
    body = re.sub(r"\[.*?\]", " ", body, flags=re.DOTALL)
    body = body.replace("```json", "").replace("```", "")
    body = re.sub(r'"(text|title|tags|candidates|type|science|life|study|health|campus|season)"\s*:?', " ", body)
    # 去标签
    body = re.sub(r"#[^#\s]+#?", " ", body)
    # 去多余空白
    body = re.sub(r"\s+", " ", body).strip()
    # 去掉尾部多余标点
    body = body.rstrip(" ,;:|/-")
    if len(body) > 320:
        # 找最近的句号/问号/感叹号/换行截断，不在句子中间切断
        cut = body[:320].rfind("。")
        if cut < 200:
            cut = body[:320].rfind("！")
        if cut < 200:
            cut = body[:320].rfind("？")
        if cut < 200:
            cut = 300
        body = body[:cut + 1]
    return body


def generate_single_share(type_key: str) -> ContentItem:
    """[单条换一条专用] 强制指定类型生成 1 条分享"""
    if type_key not in _TYPE_CN:
        # 没命中的话，降级为 1 条随机
        items = generate_share(count=1)
        return items[0] if items else ContentItem(module="share", error="[小青爱分享] 类型无效")
    items = generate_share(count=1, types=[type_key])
    return items[0] if items else ContentItem(
        module="share", item_type=_TYPE_CN[type_key], error="[小青爱分享] 生成失败"
    )
