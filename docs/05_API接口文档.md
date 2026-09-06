# 05 - API 接口文档

> 本文档详细说明项目用到的两个外部 API：和风天气（天气查询）、Agnes AI（文案生成 + 图片生成）。
> 包含接口地址、请求参数、返回示例、错误处理方式。
> **调用前请先查阅官方文档验证最新参数，不要硬猜字段名。**

---

## 一、和风天气 API（免费版）

### 1.1 官方文档
- 首页：https://dev.qweather.com/
- 实时天气接口：https://dev.qweather.com/docs/api/weather/weather-now/
- 城市 ID 查询：https://geoapi.qweather.com/v2/city/lookup?location=焦作&key=YOUR_KEY

### 1.2 基本信息

| 项目 | 内容 |
|------|------|
| 接口名 | 实时天气（Weather Now） |
| 免费版地址 | `https://devapi.qweather.com/v7/weather/now` |
| 付费版地址 | `https://api.qweather.com/v7/weather/now` |
| 请求方式 | GET |
| 返回格式 | JSON |
| 免费额度 | 每天 1000 次（足够用，一天只查 1-2 次就行） |

### 1.3 请求参数

| 参数 | 必填 | 类型 | 示例值 | 说明 |
|------|------|------|--------|------|
| key | 是 | string | f3967f30ced34e54a417acc145065d67 | 用户提供的 API KEY |
| location | 是 | string | 101181101 | 城市 ID（焦作的 ID 是 101181101，也可以写「焦作」但建议用 ID 更准） |
| lang | 否 | string | zh | 语言，中文用 zh |
| unit | 否 | string | m | 温度单位：m=摄氏度（默认），i=华氏度 |

### 1.4 调用示例
```python
import requests

url = "https://devapi.qweather.com/v7/weather/now"
params = {
    "key": "f3967f30ced34e54a417acc145065d67",
    "location": "101181101",  # 焦作
    "lang": "zh",
    "unit": "m"
}
resp = requests.get(url, params=params, timeout=10)
data = resp.json()
```

### 1.5 成功返回示例
```json
{
  "code": "200",
  "updateTime": "2026-08-29T10:30+08:00",
  "fxLink": "https://www.qweather.com/weather/jiaozuo-101181101.html",
  "now": {
    "obsTime": "2026-08-29T10:25+08:00",
    "temp": "26",
    "feelsLike": "28",
    "icon": "100",
    "text": "晴",
    "wind360": "135",
    "windDir": "东南风",
    "windScale": "2",
    "windSpeed": "11",
    "humidity": "55",
    "precip": "0.0",
    "pressure": "1005",
    "vis": "15",
    "cloud": "10",
    "dew": "18"
  },
  "refer": {
    "sources": ["QWeather"],
    "license": ["CC BY-SA 4.0"]
  }
}
```

### 1.6 我们需要提取的字段

| 字段 | 路径 | 说明 | 示例 |
|------|------|------|------|
| 状态码 | `code` | 200=成功，其他都是失败 | 200 |
| 更新时间 | `updateTime` | 天气数据更新时间（转成 YYYY-MM-DD HH:mm 展示） | 2026-08-29 10:30 |
| 当前温度 | `now.temp` | 摄氏度，整数 | 26 |
| 体感温度 | `now.feelsLike` | 摄氏度（可选，文案里可以提「体感 28 度」） | 28 |
| 天气状况 | `now.text` | 晴/多云/阴/小雨/雷阵雨等 | 晴 |
| 风向 | `now.windDir` | 东南风/西北风等 | 东南风 |
| 风力等级 | `now.windScale` | 1-12 级，文案里写「2 级微风」 | 2 |
| 湿度 | `now.humidity` | 百分比，文案里写「湿度 55%」 | 55 |

### 1.7 错误码（部分）

| code | 说明 | 处理方式 |
|------|------|----------|
| 200 | 成功 | 正常解析 |
| 204 | 请求成功，但无数据 | 弹提示「暂无天气数据，请稍后重试」 |
| 401 | 认证失败 / KEY 错误 | 弹提示「和风天气 API KEY 无效，请去设置页检查」 |
| 402 | 免费次数用完 | 弹提示「今天天气查询额度用完啦，明天再试吧」 |
| 403 | 无访问权限（KEY 被禁用） | 弹提示「和风天气 KEY 被禁用，请更换 KEY」 |
| 404 | 城市不存在 | 弹提示「城市参数错误」 |
| 500 | 服务器内部错误 | 弹提示「和风天气服务器出问题了，稍后重试」 |

---

## 二、Agnes AI API（文案 + 图片生成）

### 2.1 官方信息

| 项目 | 内容 |
|------|------|
| 官网 | https://agnes-ai.com/ |
| API 文档地址 | **【必须先查！】** https://agnes-ai.com/docs 或开发者控制台文档页 |
| Base URL（假设，以官方为准） | `https://agnes-ai.com/api/v1` |
| API KEY | sk-zGDHQw8eYMi7nzSQ37t4p2ahhQipnoJBD9FMWNdOutXOtYQP（用户提供） |
| 认证方式 | HTTP Header: `Authorization: Bearer {API_KEY}` |
| 图片模型 | `agnes-image-2.1-flash`（用户指定） |
| 文案模型 | 需要查官方文档选最新的中文对话模型（如 `agnes-text-2.0` / `agnes-turbo` 等，以官方为准） |

> ⚠️ **重要**：Agnes AI 的具体 API 端点、参数名、请求格式必须**在阶段3开发前打开官网文档核对**！下面是基于常见 OpenAI 兼容格式的推测，实际调用以 Agnes 官方文档为准。

### 2.2 文案生成接口（Chat Completions）

#### 推测请求格式（OpenAI 兼容风格，以官方为准）
```
POST https://agnes-ai.com/api/v1/chat/completions
Headers:
  Authorization: Bearer sk-zGDHQw8eYMi7nzSQ37t4p2ahhQipnoJBD9FMWNdOutXOtYQP
  Content-Type: application/json

Body:
{
  "model": "agnes-text-latest",        ← 换成官方实际模型名
  "messages": [
    {"role": "system", "content": "你是河南理工大学校园号的运营者「小青」，阳光正能量..."},
    {"role": "user", "content": "今天焦作天气：晴 26℃，东南风2级，湿度55%。请写3条早安理工文案..."}
  ],
  "temperature": 0.8,                  ← 0.7-0.9 有创意但不胡扯
  "max_tokens": 1000,
  "response_format": {"type": "json_object"}   ← 要求返回 JSON 数组
}
```

#### 要求 AI 返回的 JSON 格式（必须在 Prompt 里明确要求）
```json
{
  "candidates": [
    {
      "text": "今天晴 26℃，微风正好，早安理工 ☀️",
      "tags": ["#早安理工#", "#每日话题#"]
    },
    {
      "text": "阳光洒进校园，26度的清晨刚刚好，早安！",
      "tags": ["#早安理工#", "#每日话题#"]
    }
  ]
}
```

#### 常用 Prompt 模板（集中写在 content_generator.py 顶部）
```python
# ===== 通用 System Prompt =====
SYSTEM_PROMPT = """
你是河南理工大学校园号的运营者「小青」，阳光开朗、正能量满满的学长/学姐人设。
你说话温暖亲切，称呼同学们为「小栗子们」或「理工学子们」。
所有输出必须严格遵守用户给的长度要求，绝不超字数。
"""

# ===== 早安文案 Prompt 模板 =====
MORNING_PROMPT = """
【任务】写 {count} 条早安问候文案，给河南理工大学的同学们。
【今天天气】{weather_text}（{temp}℃，{wind}，湿度{humidity}%）
【要求】
1. 每条 10-20 个字，超短一句话，结尾带 1-2 个合适的 emoji
2. 风格阳光、治愈、正能量，第一人称「小青」口吻
3. 把天气信息自然融入句子（不用硬写所有数据，挑1-2个重点就行）
4. 必须包含必须标签：#早安理工# #每日话题#
5. 输出严格 JSON 格式，不要任何多余文字：
{{
  "candidates": [
    {{"text": "文案正文（不含标签）", "tags": ["#早安理工#", "#每日话题#", "...其他标签"]}}
  ]
}}
"""

# ===== 晚安文案 Prompt 模板（类似，改标签和氛围）
# ===== 推荐类 Prompt（150-250字，第一人称小青推荐）
# ===== 分享类 Prompt（150-250字，知识点类）
```

### 2.3 图片生成接口

#### 推测请求格式（以 Agnes 官方文档为准）
```
POST https://agnes-ai.com/api/v1/images/generations
Headers:
  Authorization: Bearer sk-zGDHQw8eYMi7nzSQ37t4p2ahhQipnoJBD9FMWNdOutXOtYQP
  Content-Type: application/json

Body:
{
  "model": "agnes-image-2.1-flash",       ← 用户指定的模型，不要改
  "prompt": "Realistic photography style, Chinese university campus morning, blue sky with white clouds, sunlight through phoenix tree leaves, warm tone, clean composition, vertical 3:4 ratio, NO WATERMARK OR TEXT on image",
  "n": 1,
  "size": "1024x1536"   ← 查官方支持的尺寸：常见有 512x512, 1024x1024(1:1), 1024x1536(2:3竖), 1536x1024(横)
}
```

#### 图片 Prompt 编写规范
1. **必须用英文写**（绝大多数画图模型英文效果比中文好太多）
2. **开头固定写实风格关键词**：`Realistic photography style, professional DSLR photo, high detail, 8k quality`
3. **主体内容描述**（中文先想好再翻英文）：
   - 早安校园：Chinese university campus morning, blue sky, sunlight through leaves, warm morning glow
   - 晚安校园：Campus night scene, moon through window, soft warm lamp light, quiet dormitory, dreamy
   - 书籍推荐：Open book on wooden desk, campus library background, warm natural light, cozy reading atmosphere
   - 电影推荐：Cinematic poster style, ...（根据电影类型具体描述）
   - 科普冷知识：Scientific visualization, futuristic lab style, clean infographic feel...
4. **画面比例说明**：
   - 竖屏 3:4 → `vertical composition, 3:4 aspect ratio`，size 用 `768x1024` 或 `1024x1536`
   - 正方形 1:1 → `square composition, 1:1 aspect ratio`，size 用 `1024x1024`
5. **结尾固定 Negative**：`, NO text, NO watermark, NO logo, NO signature`（**很重要！** 禁止模型自己画文字和水印，因为我们要后期自己加）

#### 成功返回示例（推测，以官方为准）
```json
{
  "created": 1724900000,
  "data": [
    {
      "url": "https://agnes-ai.com/output/xxx.jpg",   ← 可能返回公网 URL
      "b64_json": "..."                                 ← 或直接返回 base64 编码的图片数据
    }
  ]
}
```

#### 图片保存流程
1. 如果返回 `b64_json`：直接 `base64.b64decode()` → bytes → Pillow 打开 → 转 RGB → 加水印 → 存 JPG
2. 如果返回 `url`：`requests.get(url, timeout=30)` → bytes → 同上处理
3. 统一保存格式：JPG，质量 85（可在设置改）

### 2.4 错误处理（通用）

| HTTP 状态码 | 可能原因 | 处理方式 |
|-------------|----------|----------|
| 200 | 成功 | 正常解析 |
| 400 | 参数错误（模型名错、Prompt 太长等） | 日志记录详情，弹提示「请求参数错误，请联系开发者」 |
| 401 | API KEY 无效 | 弹提示「Agnes AI API KEY 无效，请去设置页检查」 |
| 403 | 权限不足 / 账号封禁 | 弹提示「Agnes AI 账号无访问权限，请更换 KEY」 |
| 429 | 请求太频繁 / 额度用完 | 弹提示「Agnes AI 调用太频繁或额度用完，稍后再试」，加 30 秒冷却再让点按钮 |
| 500 | 服务器出错 | 弹提示「Agnes AI 服务器出问题了，点换一条再试试」 |
| 超时 | 网络慢 / 画图慢（尤其是画图可能 30s+） | 超时时间设 120 秒，超时后弹提示「生成超时了，点换一条重试」 |

---

## 三、开发前必须做的 API 验证

**在阶段 3 开始写代码前，必须先写一个独立的 test_api.py 脚本，手工跑通以下 4 个调用，确认接口格式和字段没问题再写正式代码：**

```python
# test_api.py（一次性验证脚本，验证完删掉或放到 tests/ 目录）
import requests, json

# ========== 1. 和风天气 ==========
print("=== 测试和风天气 ===")
# ... 调用 + 打印返回，确认关键字段存在

# ========== 2. Agnes AI 文案生成 ==========
print("\n=== 测试 Agnes AI 文案生成 ===")
# ... 调用 + 打印，确认能拿到 JSON 数组格式的 3 条候选

# ========== 3. Agnes AI 图片生成（方图） ==========
print("\n=== 测试 Agnes AI 图片生成（方图） ===")
# ... 调用 + 存成 test_square.jpg，确认能打开、没有模型自带的水印文字

# ========== 4. Agnes AI 图片生成（竖图） ==========
print("\n=== 测试 Agnes AI 图片生成（竖图） ===")
# ... 调用 + 存成 test_vertical.jpg，同上

print("\n✅ 全部 API 测试通过！")
```

> **注意**：Agnes AI 的实际接口端点和参数，一定要以官方文档最新内容为准！如果和本文档推测的不一样，以官方为准，不用来问我（毕竟我也看不到 Agnes 的实时文档）。
