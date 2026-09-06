# -*- coding: utf-8 -*-
"""Agnes AI 画图专项测试 v3
修正参数：return_base64 / extra_body.response_format / size 用 1K+ratio
端点用 .com（文档标准）

运行方式：
    .venv\\Scripts\\python.exe tests\\test_image.py
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


def test_image(size_str, ratio, label, use_cn=False, use_base64_param="return_base64"):
    """画图测试
    Args:
        size_str: "1K" / "2K" / "1024x1024"
        ratio: "1:1" / "3:4" / "9:16"
        label: 标签
        use_cn: True=用.cn / False=用.com
        use_base64_param: "return_base64" / "extra_body" / "none"
    """
    print("\n" + "=" * 60)
    print(f"画图测试：{label} | size={size_str} ratio={ratio} | 端点={'cn' if use_cn else 'com'} | base64方式={use_base64_param}")
    print("=" * 60)

    cfg = CONFIG.get("agnes_ai", {})
    key = cfg.get("api_key", "")
    model = cfg.get("image_model", "agnes-image-2.1-flash")

    # 选端点
    if use_cn:
        base_url = "https://apihub.agnes-ai.cn/v1"
    else:
        base_url = "https://apihub.agnes-ai.com/v1"
    endpoint = f"{base_url}/images/generations"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        "prompt": "Realistic photography style, Chinese university campus morning, blue sky with white clouds, sunlight through phoenix tree leaves, warm tone, clean composition",
        "size": size_str,
    }

    # 2.1 flash 支持 ratio
    if ratio and ratio != "1:1":
        body["ratio"] = ratio

    # base64 返回方式
    if use_base64_param == "return_base64":
        body["return_base64"] = True
    elif use_base64_param == "extra_body":
        body["extra_body"] = {"response_format": "b64_json"}
    # none = 默认返回 URL

    print(f"端点: {endpoint}")
    print(f"模型: {model}")
    print(f"请求体: {json.dumps(body, ensure_ascii=False)}")

    try:
        t0 = time.time()
        resp = requests.post(endpoint, headers=headers, json=body, timeout=300)
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
                    f"test_img_{label.replace(' ','_')}.png"
                )

                if "b64_json" in item:
                    img_bytes = base64.b64decode(item["b64_json"])
                    with open(save_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"✅ 图片已保存（base64）: {save_path} ({len(img_bytes)} bytes)")
                    return True
                elif "url" in item:
                    img_url = item["url"]
                    print(f"图片 URL: {img_url[:100]}...")
                    r = requests.get(img_url, timeout=60)
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                    print(f"✅ 图片已保存（URL下载）: {save_path} ({len(r.content)} bytes)")
                    return True
                else:
                    print(f"⚠️ 未知图片字段: {list(item.keys())}")
                    print(f"完整返回（前 500 字）: {json.dumps(data, ensure_ascii=False)[:500]}")
                    return False
            else:
                print(f"⚠️ 无 data 字段，完整返回（前 500 字）:")
                print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                return False
        else:
            print(f"❌ HTTP {resp.status_code}")
            print(f"响应（前 500 字）: {resp.text[:500]}")
            return False
    except requests.exceptions.ReadTimeout:
        print(f"❌ 超时（300秒）")
        return False
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 Agnes AI 画图专项测试 v3")
    print("=" * 60)

    results = []

    # 测试 1：.com 端点 + 1K + 1:1 + return_base64（最标准）
    ok = test_image("1K", "1:1", "com_1K_11", use_cn=False, use_base64_param="return_base64")
    results.append(("com+1K+return_base64", ok))

    # 测试 2：.com 端点 + 1K + 3:4 竖图 + return_base64
    ok = test_image("1K", "3:4", "com_1K_34", use_cn=False, use_base64_param="return_base64")
    results.append(("com+1K+3:4+return_base64", ok))

    # 测试 3：.cn 端点 + 1K + 1:1 + return_base64（看 cn 行不行）
    ok = test_image("1K", "1:1", "cn_1K_11", use_cn=True, use_base64_param="return_base64")
    results.append(("cn+1K+return_base64", ok))

    # 汇总
    print("\n" + "=" * 60)
    print("📊 画图测试汇总")
    print("=" * 60)
    for name, ok in results:
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"{name}: {status}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"画图测试崩溃: {e}", exc_info=True)
        raise
