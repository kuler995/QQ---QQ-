# -*- coding: utf-8 -*-
"""内容生成器
组装「天气查询 → Prompt 构造 → Agnes 文案 → Agnes 画图 → 水印」的完整流程

按需求文档：
- 早晚安文案：10-20字，阳光正能量，第一人称小青，融入天气
- 配图：小红书风格（治愈花系/手绘/唯美夜景/小王子），竖屏，水印不挡画面
- 标签：#早安理工# #每日话题# #晚安理工# 必须有
- 每张图文案注明来源：📷 配图：XX风 AI 生成
"""
import json
import re
import random
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from src.api.agnes_ai import get_client
from src.api.weather import get_weather, weather_to_text
from src.core.image_watermark import add_watermark, make_watermark_text
from src.config import CONFIG
from src.utils.logger import logger


class ContentItem:
    """一条内容（文案 + 图片）"""

    def __init__(self, text: str = "", tags: List[str] = None,
                 image_bytes: bytes = None, image_url: str = "",
                 module: str = "", item_type: str = "",
                 error: str = "", source_note: str = "",
                 saved: bool = False):
        self.text = text                    # 文案正文
        self.tags = tags or []              # 标签列表
        self.image_bytes = image_bytes      # 图片字节（加水印后）
        self.image_url = image_url          # 原图 URL
        self.module = module                # 模块：morning/night/recommend/share
        self.item_type = item_type          # 类型：如 book/movie/doc/knowledge
        self.saved = saved                  # 用户是否点过保存
        self.error = error                  # 错误信息（生成失败时）
        self.source_note = source_note      # 图片来源说明（如"小红书风格AI生成"）

    @property
    def full_text(self) -> str:
        """文案 + 来源说明 + 标签（用于复制到 QQ 动态）
        格式：
          文案正文
          📷 配图：小红书治愈花系 AI 生成
          #早安理工# #每日话题#
        """
        if self.text:
            lines = [self.text]
            # 如果有配图，加来源说明
            if self.image_bytes and self.source_note:
                lines.append(f"📷 配图：{self.source_note}")
            tag_str = " ".join(self.tags) if self.tags else ""
            if tag_str:
                lines.append(tag_str)
            return "\n".join(lines)
        return ""


def generate_morning_content(count: int = 2) -> List[ContentItem]:
    """生成早安理工内容（2条，从8种小红书风格中随机挑选不重复）"""
    # 8 种早安风格，只有 1 种花系，其余都是生活/风景/静物，避免千篇一律
    styles = [
        ("小红书治愈花系 AI 生成",
         "Realistic photography, xiaohongshu aesthetic morning. "
         "Clear glass vase with white roses and eucalyptus, "
         "soft ocean-blue bokeh background, warm window sunlight, "
         "shallow depth of field, pastel tone. NO TEXT. Vertical 3:4."),
        ("小红书手绘郁金香 AI 生成",
         "Hand drawn watercolor illustration, cream paper texture. "
         "Pink tulips in small glass milk bottle with red ribbon, "
         "striped placemat, washi tape, doodles: stars, heart, sparkles. "
         "NO TEXT on image. Vertical 3:4."),
        ("小红书咖啡早餐风 AI 生成",
         "Realistic photography, xiaohongshu weekend brunch aesthetic. "
         "Ceramic latte cup with latte art heart, croissant on wood plate, "
         "warm morning sunlight through window, long shadows on oak table, "
         "soft bokeh. NO TEXT. Vertical 3:4."),
        ("小红书猫咪窗台风 AI 生成",
         "Realistic photography, xiaohongshu cozy home aesthetic. "
         "Fluffy ginger cat sleeping peacefully on white sheer curtain windowsill, "
         "morning golden sunlight, soft dappled shadows, small green succulent beside, "
         "warm cozy vibe. NO TEXT. Vertical 3:4."),
        ("小红书绿植书桌风 AI 生成",
         "Realistic photography, xiaohongshu study inspiration aesthetic. "
         "Fiddle-leaf fig green plant on clean white desk, "
         "open notebook with fountain pen, small potted succulent, "
         "warm soft natural morning light, minimalist. NO TEXT. Vertical 3:4."),
        ("小红书海边日出风 AI 生成",
         "Realistic photography, cinematic xiaohongshu wanderlust aesthetic. "
         "Golden sunrise over calm ocean, gentle waves on sandy beach, "
         "silhouette of seagulls flying, pink and orange sky. "
         "NO TEXT. Vertical 3:4 composition."),
        ("小红书日式抹茶风 AI 生成",
         "Realistic photography, xiaohongshu Japanese zen morning. "
         "Matcha green tea in chawan bowl with wagashi sweet next to it, "
         "soft light through shoji paper screen, tatami mat, "
         "calm peaceful vibe. NO TEXT. Vertical 3:4."),
        ("小红书温暖厨房风 AI 生成",
         "Realistic photography, xiaohongshu home baking aesthetic. "
         "Rustic ceramic basket full of fresh bread and sliced baguette, "
         "glass of milk, linen cloth, soft morning sunlight through kitchen window, "
         "warm earthy tone. NO TEXT. Vertical 3:4."),
    ]
    return _generate_greeting(
        module="morning",
        greeting_type="早安",
        prefix="早安理工",
        weather_keyword="早安",
        style_packs=styles,
        count=count
    )


def generate_night_content(count: int = 2) -> List[ContentItem]:
    """生成晚安理工内容（2条，从8种晚安风格中随机挑选）"""
    styles = [
        ("小红书月牙湖夜景 AI 生成",
         "Realistic photography, cinematic xiaohongshu dreamy night scene. "
         "Large glowing crescent moon reflection on calm lake, small wooden cabin, "
         "pine trees with warm interior light, dark blue sky with tiny stars. "
         "NO TEXT. Vertical 3:4."),
        ("小红书小王子手绘风 AI 生成",
         "Hand drawn watercolor illustration, cream paper background. "
         "Little Prince in green outfit orange scarf holding glowing star, "
         "red rose beside his feet, inside warm yellow translucent bubble. "
         "Cozy dreamy vibe. NO TEXT on image. Vertical 3:4."),
        ("小红书中式灯笼夜市 AI 生成",
         "Realistic photography, xiaohongshu chinese street night aesthetic. "
         "Traditional red lanterns hanging above stone old street, "
         "warm amber bokeh lights, small stalls with food steam, "
         "cinematic warm color grading. NO TEXT. Vertical 3:4."),
        ("小红书城市夜色 AI 生成",
         "Realistic photography, cinematic xiaohongshu city night aesthetic. "
         "Light trails from cars on bridge, glowing office windows in skyline, "
         "dark blue night sky, bokeh neon lights, urban dreamy feel. "
         "NO TEXT. Vertical 3:4."),
        ("小红书深夜书房风 AI 生成",
         "Realistic photography, xiaohongshu cozy night reading aesthetic. "
         "Brass banker table lamp lighting up open book with fountain pen, "
         "old wooden desk, pile of books, city light through window at night, "
         "warm amber glow, peaceful vibe. NO TEXT. Vertical 3:4."),
        ("小红书风铃卧室 AI 生成",
         "Realistic photography, xiaohongshu cozy bedroom night aesthetic. "
         "Glass wind chime hanging, warm fairy star string lights on white wall, "
         "city lights blur outside window, soft pillow on bed, "
         "calm sleepy vibe. NO TEXT. Vertical 3:4."),
        ("小红书深夜热茶 AI 生成",
         "Realistic photography, xiaohongshu rainy night aesthetic. "
         "White ceramic mug of hot herbal tea with steam rising, "
         "rain droplets on window, soft warm desk lamp glow, "
         "cozy and calm vibe. NO TEXT. Vertical 3:4."),
        ("小红书橘猫夜沙发 AI 生成",
         "Realistic photography, xiaohongshu warm home aesthetic. "
         "Ginger cat curled up sleeping on fabric sofa, "
         "warm yellow floor lamp beside, knitted blanket draped, "
         "peaceful cozy night vibe. NO TEXT. Vertical 3:4."),
    ]
    return _generate_greeting(
        module="night",
        greeting_type="晚安",
        prefix="晚安理工",
        weather_keyword="晚安",
        style_packs=styles,
        count=count
    )


def _generate_greeting(module: str, greeting_type: str, prefix: str,
                       weather_keyword: str,
                       style_packs: List[Tuple[str, str]],
                       count: int = 2) -> List[ContentItem]:
    """早晚安内容生成内部函数
    健壮性：文案失败自动重试 1 次；条数不够补全；图片失败自动重试 1 次；失败信息前缀加模块名
    """
    err_tag = f"[{prefix}]"  # 统一错误前缀，让用户一眼知道早安还是晚安失败

    # 1. 查天气
    ok_w, weather, msg_w = get_weather()
    weather_text = weather_to_text(weather) if ok_w else "天气晴朗温暖"
    weather_scene = _weather_to_scene(weather)

    # 2. 构造文案 Prompt
    required_tags = CONFIG.get("tags", {}).get("required", [])
    base_tags = [t for t in required_tags if greeting_type in t or "每日话题" in t]

    def _build_prompt(num: int) -> str:
        return f"""你是河南理工大学校园号运营者「小青」，风格阳光正能量。

今天{weather_text}。

请写{num}条{greeting_type}问候文案，要求：
1. 每条10-20字（不含标签）
2. 第一人称"小青"口吻，活泼阳光
3. 自然融入天气信息（可以直白写也可以藏在句子里）
4. 结尾带一个emoji

严格输出JSON格式，不要其他内容：
{{"candidates":[
  {{"text":"文案正文","tags":{base_tags}}}
]}}

只输出{num}条候选，一条都不能少！"""

    client = get_client()

    # ===== 3. 文案生成 + 失败重试 + 解析兜底 =====
    def _fetch_candidates(num: int, temp: float) -> List[Dict]:
        ok, raw = client.generate_text(_build_prompt(num), temperature=temp, max_tokens=500)
        if not ok or not raw.strip():
            return []
        cands = _parse_candidates(raw)
        if not cands and raw.strip():
            # 解析失败时，拿原文前 50 字当一条兜底
            cands = [{"text": raw.strip()[:50], "tags": base_tags}]
        return cands

    candidates = _fetch_candidates(count, 0.85)
    if len(candidates) < count:
        # 第一次不够 count → 重试一次（温度稍高，避免又卡住）
        logger.info(f"🔄 {err_tag} 文案不够{count}条，拿到{len(candidates)}条，自动重试...")
        retry = _fetch_candidates(count, 0.95)
        # 合并，不足的部分用 retry 补
        if retry:
            for c in retry:
                if len(candidates) >= count:
                    break
                candidates.append(c)

    # 最终还是不够 count → 再单独写 count 次保证数量（每次单独写1条）
    if len(candidates) < count:
        logger.warning(f"⚠️ {err_tag} 合并后仍然只有{len(candidates)}条，单独补写到{count}条...")
        need = count - len(candidates)
        for _ in range(need):
            single = _fetch_candidates(1, 0.98)
            if single:
                candidates.append(single[0])
            else:
                # 最坏情况：写一个固定兜底文案
                candidates.append({
                    "text": f"小青祝大家{greeting_type}，愿今天有好事发生 🌈",
                    "tags": base_tags
                })

    # 4. 风格打乱 + 逐条画图（图片失败也重试 1 次）
    style_order = list(range(len(style_packs)))
    random.shuffle(style_order)
    watermark = make_watermark_text(prefix)

    items = []
    for i in range(count):
        cand = candidates[i] if i < len(candidates) else candidates[-1]
        src_note, img_prompt_tpl = style_packs[style_order[i % len(style_packs)]]

        # tags 兜底：空列表 / None / 缺省 都用 base_tags
        cand_tags = cand.get("tags") or base_tags
        if not cand_tags:
            cand_tags = base_tags
        item = ContentItem(
            text=cand.get("text", ""),
            tags=cand_tags,
            module=module,
            item_type=greeting_type,
            source_note=src_note
        )

        img_prompt = img_prompt_tpl
        if weather_scene:
            img_prompt += f" The weather is {weather_scene}."

        # 画图 + 重试 1 次
        ok_img, img_bytes, img_url = client.generate_image(img_prompt, size="768x1024")
        if (not ok_img or not img_bytes):
            logger.info(f"🔄 {err_tag} 第{i+1}张图失败，自动重试画图...")
            ok_img, img_bytes, img_url = client.generate_image(img_prompt, size="768x1024")

        if ok_img and img_bytes:
            item.image_bytes = add_watermark(img_bytes, watermark)
            item.image_url = img_url
            logger.info(f"✅ {err_tag} 第{i+1}条完成（{src_note}）")
        else:
            item.error = f"{err_tag} 配图失败: {img_url or 'Agnes返回空'}"
            logger.warning(f"⚠️ {err_tag} 第{i+1}条配图重试后仍失败: {img_url}")

        items.append(item)

    # 保证最终一定返回 count 条（极端情况下，用占位 error 项补满）
    while len(items) < count:
        items.append(ContentItem(
            module=module, item_type=greeting_type,
            error=f"{err_tag} 生成失败：返回条目不足"
        ))

    return items


def _weather_to_scene(weather: Dict) -> str:
    """天气转成画图场景描述"""
    text = weather.get("text", "晴")
    if "雨" in text:
        return "light rain with wet campus roads, reflections on puddles"
    elif "雪" in text:
        return "snowy campus, white covered trees and buildings"
    elif "阴" in text or "云" in text:
        return "cloudy sky, soft diffused light"
    elif "雾" in text or "霾" in text:
        return "foggy morning, misty atmosphere"
    else:
        return "clear blue sky, bright sunshine"


def _parse_candidates(text: str) -> List[Dict]:
    """从AI返回的文本里解析出 candidates JSON 数组
    支持情况：
    1. 完整 JSON：{"candidates": [{"text":"xxx","tags":[...]}, ...]}
    2. ```json ... ``` markdown 包裹的 JSON
    3. AI 截断导致 JSON 结构不完整 → 正则兜底提取每段 text 内容和标签
    """
    if not text:
        return []

    original = text
    text = text.strip()

    # ---------- 步骤 1：剥离 markdown 代码块包裹（```json 或 ```） ----------
    if "```" in text:
        # 找第一对 ``` 之间的内容
        parts = text.split("```")
        # parts[0] 是 ``` 前的内容（可能空或有提示词）
        # parts[1] 是第一个代码块里的内容（可能是 "json\n{...}"）
        if len(parts) >= 2:
            code_content = parts[1].strip()
            # 去掉开头的 "json" 或 "JSON" 标识（第一行如果是就删）
            code_lines = code_content.split("\n")
            if code_lines and code_lines[0].strip().lower() in ("json", "```json"):
                code_lines = code_lines[1:]
            text = "\n".join(code_lines).strip()
            # 如果剥离后 text 是空（代码块里全是标识），就用回 original
            if not text:
                text = original

    # ---------- 步骤 2：尝试直接解析完整 JSON ----------
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            cands = data.get("candidates")
            if isinstance(cands, list) and cands:
                return _normalize_candidates(cands)
            # 如果不是 candidates 结构但有 text 字段，兜底包一层
            if "text" in data:
                return [{"text": str(data["text"]), "tags": data.get("tags", [])}]
    except (json.JSONDecodeError, ValueError):
        pass

    # ---------- 步骤 3：提取 JSON 块（AI 可能前后加了中文说明） ----------
    # 找第一个 { 到最后一个 } 之间的内容
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = text[start:end + 1]
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                cands = data.get("candidates")
                if isinstance(cands, list) and cands:
                    return _normalize_candidates(cands)
                if "text" in data:
                    return [{"text": str(data["text"]), "tags": data.get("tags", [])}]
        except (json.JSONDecodeError, ValueError):
            pass

    # ---------- 步骤 4：正则兜底（AI 截断、JSON 不完整时用） ----------
    # 按行扫描，提取 "text":"..." 的内容，和末尾的标签
    candidates = []

    # 提取所有 "text":"xxx" 段（支持转义引号）
    text_matches = re.findall(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    tag_matches = re.findall(r'"tags"\s*:\s*\[([^\]]*)\]', text)

    # 为每条 text 找对应的 tags
    default_tags = _extract_hashtags_from_text(text)

    for i, t in enumerate(text_matches):
        tags = default_tags
        if i < len(tag_matches):
            tags = _parse_tag_array(tag_matches[i]) or default_tags
        # 去掉可能的转义符
        t = t.replace('\\"', '"').replace("\\n", " ").strip()
        # 过滤掉混入的 JSON 结构字符（JSON 截断导致的脏数据）
        if t and ("{" in t or "[" in t or '"text"' in t):
            body, more_tags = _split_body_and_hashtags(t)
            t = body
            tags = _clean_tags(tags + more_tags)
        if t:
            candidates.append({"text": t, "tags": tags})

    # 如果正则兜底提取出来的内容有脏字（JSON 结构残留），清空，走步骤5终极兜底
    def _looks_dirty(txt: str) -> bool:
        return any(k in txt for k in ["candidates", "text", "{", "}", "[", "]"])

    if candidates and not any(_looks_dirty(c["text"]) for c in candidates):
        return candidates

    # ---------- 步骤 5：终极兜底（完全没结构，把非标签正文当一条） ----------
    # 处理用户截图场景：截断的 JSON + 换行 + 裸标签
    body, tags = _split_body_and_hashtags(text)
    if body:
        # 再次清洗 body 里的 JSON 残留
        if _looks_dirty(body):
            body = _extract_last_readable_sentence(body)
        if body:
            return [{"text": body, "tags": tags or default_tags}]

    return []


def _normalize_candidates(raw_cands: List) -> List[Dict]:
    """标准化 candidates 数组，确保每项是 {text, tags}"""
    result = []
    default_tags = []
    for c in raw_cands:
        if isinstance(c, dict):
            text = str(c.get("text", "")).strip()
            tags = c.get("tags", [])
            if text:
                result.append({
                    "text": text,
                    "tags": _clean_tags(tags) or default_tags
                })
    return result


def _parse_tag_array(tag_str: str) -> List[str]:
    """从 '"#早安理工#","#每日话题#' 或 '#早安理工# #每日话题#' 解析标签列表"""
    if not tag_str:
        return []
    # 先找所有 #xxx# 段（支持中英文标签，排除引号、逗号、空白）
    tags = re.findall(r"#[^#\s\"',]+#?", tag_str)
    return _clean_tags(tags)


def _extract_hashtags_from_text(text: str) -> List[str]:
    """从任意文本里提取所有 #xxx# 标签"""
    tags = re.findall(r'#[^#\s]+(?:#|$)', text)
    # 有些标签末尾不带 #，也要识别（如 #早安理工 后跟换行或空格）
    tags2 = re.findall(r'#[^#\s]{2,}', text)
    merged = list(dict.fromkeys(tags + tags2))  # 去重保序
    return _clean_tags(merged)


def _clean_tags(tags) -> List[str]:
    """清洗标签，确保是 #xxx# 形式"""
    if not tags:
        return []
    cleaned = []
    for t in tags:
        if isinstance(t, str):
            t = t.strip().strip('"').strip("'").strip(",")
            if not t:
                continue
            # 确保以 # 开头
            if not t.startswith("#"):
                t = "#" + t
            # 确保标签内容完整（如果结尾是字母/文字，补个#）
            if not t.endswith("#") and not re.search(r'[^\w\u4e00-\u9fff]', t[-1:]):
                # 简短处理：如果结尾不是 #，并且之前没有配对的 # 出现在中间，则补 #
                inner = t[1:]
                if "#" not in inner:
                    t = t + "#"
            cleaned.append(t)
    # 去重保序
    return list(dict.fromkeys(cleaned))


def _split_body_and_hashtags(text: str) -> Tuple[str, List[str]]:
    """把正文和标签拆开（标签一般在末尾）"""
    lines = text.strip().split("\n")
    body_lines = []
    all_tags = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        line_tags = _extract_hashtags_from_text(line)
        # 如果整行基本都是标签，就不算正文
        stripped = line
        for t in line_tags:
            stripped = stripped.replace(t, "")
        stripped = stripped.strip()
        if stripped and len(stripped) > 2:
            body_lines.append(stripped)
        if line_tags:
            all_tags.extend(line_tags)
    body = " ".join(body_lines).strip()
    return body, _clean_tags(all_tags)


def _extract_last_readable_sentence(messy: str) -> str:
    """从混杂了 JSON 结构的文本里提取最后一段中文可读句子
    场景：用户截图里的 ``'{"candidates":[{"text":"晴好26℃，阳光正暖，小青喊你'``
    需要从中提取 ``'晴好26℃，阳光正暖，小青喊你'``
    """
    # 方法：找所有中文/数字/标点连续的片段（>=4字符），取最后一个
    matches = re.findall(r'[\u4e00-\u9fff\d℃，。！？、…“”：；\s]{4,}', messy)
    if matches:
        # 从后往前找一个不是纯标点的
        for m in reversed(matches):
            cleaned = m.strip().strip("，。！？、…：； ")
            if len(cleaned) >= 4:
                return cleaned
    # 退而求其次：找最后一次出现的 "text":"xxx" 的 xxx 部分（即使没闭合引号）
    m = re.search(r'"text"\s*:\s*"([^"]{4,})', messy)
    if m:
        return m.group(1).strip()
    return ""
