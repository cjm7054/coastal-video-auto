"""2단계: 장면별 이미지 생성 (Gemini 또는 OpenAI). 실패 시 재시도 후 직전 이미지로 대체."""
import os, time, base64, io
from pathlib import Path
from PIL import Image
from .common import load_config, ROOT, log


def _gemini(prompt: str, cfg: dict) -> bytes:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=cfg["images"]["gemini_model"],
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"],
                                           image_config=types.ImageConfig(aspect_ratio="16:9")),
    )
    for part in resp.candidates[0].content.parts:
        if part.inline_data:
            return part.inline_data.data
    raise RuntimeError("이미지 파트 없음 (안전 필터?)")


def _openai(prompt: str, cfg: dict) -> bytes:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = client.images.generate(model=cfg["images"]["openai_model"], prompt=prompt,
                               size="1792x1024", quality="standard", response_format="b64_json")
    return base64.b64decode(r.data[0].b64_json)


def _fit(data: bytes, w: int, h: int) -> Image.Image:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    ratio = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def _draw_fallback_image(prompt: str, sid: str | int, w: int, h: int) -> Image.Image:
    """API 크레딧 소진 또는 실패 시 테스트용 깔끔한 도면/일러스트 이미지 자동 생성"""
    from PIL import ImageDraw, ImageFont
    im = Image.new("RGB", (w, h), color=(18, 30, 49))
    draw = ImageDraw.Draw(im)

    # 배경 그라데이션 및 바다/지반 가이드라인
    for y in range(h):
        r = int(12 + (y / h) * 15)
        g = int(24 + (y / h) * 35)
        b = int(42 + (y / h) * 45)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 수면선 & 해저 지반 드로잉
    water_y = int(h * 0.45)
    seabed_y = int(h * 0.75)
    draw.rectangle([0, water_y, w, seabed_y], fill=(16, 68, 105, 120))
    draw.rectangle([0, seabed_y, w, h], fill=(35, 48, 55))

    # 그리드 선
    for x in range(0, w, 120):
        draw.line([(x, 0), (x, h)], fill=(40, 70, 95), width=1)
    for y in range(0, h, 120):
        draw.line([(0, y), (w, y)], fill=(40, 70, 95), width=1)

    # 라벨 박스 및 정보 텍스트
    draw.rectangle([80, 80, w - 80, h - 80], outline=(60, 160, 220), width=3)
    font = None
    font_path = ROOT / "assets/fonts/NotoSansCJK-Bold.ttc"
    if font_path.exists():
        try:
            font = ImageFont.truetype(str(font_path), 36)
        except Exception:
            pass

    title_text = f"[TEST MODE / 시뮬레이션 단면도] Scene {sid}"
    desc_text = (prompt[:140] + "...") if len(prompt) > 140 else prompt
    if font:
        draw.text((120, 120), title_text, fill=(240, 245, 255), font=font)
        draw.text((120, 180), desc_text, fill=(170, 200, 230), font=font)
    else:
        draw.text((120, 120), title_text, fill=(240, 245, 255))
        draw.text((120, 180), desc_text, fill=(170, 200, 230))

    return im


def generate_images(script: dict, out_dir: Path) -> list[Path]:
    cfg = load_config()
    W, H = cfg["images"]["width"], cfg["images"]["height"]
    gen = _gemini if cfg["images"]["provider"] == "gemini" else _openai
    suffix = cfg["images"]["style_suffix"].strip()
    paths, last_ok = [], None
    jobs = [("thumb", script["thumbnail_prompt"])] + [(s["id"], s["image_prompt"]) for s in script["scenes"]]
    for sid, p in jobs:
        out = out_dir / "images" / f"{sid}.png"
        if out.exists():
            paths.append(out); last_ok = out; continue
        prompt = f"{p}. {suffix}"
        success = False
        for attempt in range(3):
            try:
                _fit(gen(prompt, cfg), W, H).save(out, "PNG")
                log.info(f"이미지 {sid} 완료 (API)")
                last_ok = out
                success = True
                break
            except Exception as e:
                log.warning(f"이미지 {sid} 실패({attempt+1}/3): {e}")
                time.sleep(3)

        if not success:
            log.warning(f"이미지 {sid} API 실패/크레딧 부족 → 테스트 단면도 그래픽 생성 적용")
            _draw_fallback_image(prompt, sid, W, H).save(out, "PNG")
            last_ok = out

        paths.append(out)
        time.sleep(1.0)  # rate limit 여유
    return paths
