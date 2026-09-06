# -*- coding: utf-8 -*-
"""API 验证脚本 v2
用正确的 Agnes AI 国内端点（apihub.agnes-ai.cn/v1）重新测试。
和风天气需要用户提供专属 API Host，本脚本只做 Agnes AI 三项测试。

运行方式：
    .venv\\Scripts\\python.exe tests\\test_api.py
"""
import sys
import os
import json
import base64
import time
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import CONFIG
from src.utils.logger import logger


def test_agnes_text():
    """测试 1：Agnes AI 文案生成（国内站 .cn）"""
    print("\n" + "=" * 60)
    print("测试 1：Agnes AI 文案生成（agnes-2.0-flash）")
    print("=" * 60)

    cfg = CONFIG.get("agnes_ai", {})
    key = cfg.get("api_key", "")
    base_url = cfg.get("base_url", "https://apihub.agnes-ai.cn/v1").rstrip("/")
    model = cfg.get("text_model", "agnes-2.0-flash")

    # OpenAI 兼容格式：base_url + /chat/completions
    endpoint = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    test_prompt = """你是河南理工大学校园号运营者「小青」。
今天焦作天气：晴 26℃，东南风2级，湿度55%。
请写3条早安问候文案，每条10-20字，结尾带emoji。
严格输出JSON：{"candidates":[{"text":"文案","tags":["#早安理工#","#每日话题#"]}]}"""

    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": test_prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 800
    }

    print(f"端点: {endpoint}")
    print(f"API KEY: {key[:10]}***")
    print(f"文案模型: {model}")

    try:
        t0 = time.time()
        resp = requests.post(endpoint, headers=headers, json=body, timeout=30)
        elapsed = time.time() - t0
        print(f"\nHTTP 状态码: {resp.status_code} (耗时 {elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            print(f"返回结构 keys: {list(data.keys())}")

            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "")
                print(f"\n✅ 文案内容：")
                print(content)
                return True, content
            else:
                print(f"⚠️ 无 choices 字段，完整返回（前 500 字）:")
                print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                return False, None
        else:
            print(f"❌ HTTP {resp.status_code}")
            print(f"响应（前 500 字）: {resp.text[:500]}")
            return False, None
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {e}")
        return False, None


def test_agnes_image(size_str="1024x1024", label="方图"):
    """测试 2/3：Agnes AI 图片生成"""
    print("\n" + "=" * 60)
    print(f"测试：Agnes AI 图片生成（{label} {size_str}）")
    print("=" * 60)

    cfg = CONFIG.get("agnes_ai", {})
    key = cfg.get("api_key", "")
    base_url = cfg.get("base_url", "https://apihub.agnes-ai.cn/v1").rstrip("/")
    model = cfg.get("image_model", "agnes-image-2.1-flash")

    endpoint = f"{base_url}/images/generations"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        "prompt": "Realistic photography style, Chinese university campus morning, blue sky with white clouds, sunlight through phoenix tree leaves, warm tone, clean composition, NO WATERMARK OR TEXT on image",
        "n": 1,
        "size": size_str,
        "response_format": "b64_json"
    }

    print(f"端点: {endpoint}")
    print(f"画图模型: {model}")
    print(f"尺寸: {size_str}")

    try:
        t0 = time.time()
        resp = requests.post(endpoint, headers=headers, json=body, timeout=180)
        elapsed = time.time() - t0
        print(f"HTTP 状态码: {resp.status_code} (耗时 {elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            print(f"返回结构 keys: {list(data.keys())}")

            img_data = data.get("data", [])
            if img_data:
                item = img_data[0]
                print(f"图片项 keys: {list(item.keys())}")

                save_path = os.path.join(
                    os.path.dirname(__file__),
                    f"test_agnes_{label}_{size_str.replace('x', '_')}.png"
                )

                if "b64_json" in item:
                    img_bytes = base64.b64decode(item["b64_json"])
                    with open(save_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"✅ 图片已保存（base64）: {save_path} ({len(img_bytes)} bytes)")
                    return True, save_path
                elif "url" in item:
                    img_url = item["url"]
                    print(f"图片 URL: {img_url}")
                    r = requests.get(img_url, timeout=30)
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                    print(f"✅ 图片已保存（URL下载）: {save_path} ({len(r.content)} bytes)")
                    return True, save_path
                else:
                    print(f"⚠️ 未知图片字段: {list(item.keys())}")
                    return False, None
            else:
                print(f"⚠️ 无 data 字段，完整返回（前 500 字）:")
                print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                return False, None
        else:
            print(f"❌ HTTP {resp.status_code}")
            print(f"响应（前 500 字）: {resp.text[:500]}")
            return False, None
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {e}")
        return False, None


def main():
    print("=" * 60)
    print("🚀 自动早晚安小助手 - API 验证脚本 v2（Agnes AI 国内站）")
    print("=" * 60)
    print("说明：和风天气需用户提供专属 API Host，本脚本暂跳过")

    results = []

    # 测试 1：Agnes AI 文案
    ok, content = test_agnes_text()
    results.append(("Agnes 文案", ok))

    # 测试 2：Agnes AI 方图
    ok, path = test_agnes_image("1024x1024", "方图")
    results.append(("Agnes 方图", ok))

    # 测试 3：Agnes AI 竖图
    ok, path = test_agnes_image("768x1024", "竖图")
    results.append(("Agnes 竖图", ok))

    # 汇总
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    for name, ok in results:
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"{name}: {status}")

    all_ok = all(r[1] for r in results)
    if all_ok:
        print("\n🎉 Agnes AI 三项测试全部通过！可以写正式代码了")
        print("⚠️ 还需用户提供和风天气专属 API Host 才能测天气")
    else:
        print("\n⚠️ 有 Agnes AI 接口失败，请排查")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"API 测试脚本崩溃: {e}", exc_info=True)
        raise
