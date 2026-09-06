"""2단계: 장면별 이미지 생성 (Gemini 또는 OpenAI). 실패 시 재시도 후 직전 이미지로 대체."""
import os, time, base64, io
from pathlib import Path
from PIL import Image
from .common import load_config, log


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
        for attempt in range(3):
            try:
                _fit(gen(prompt, cfg), W, H).save(out, "PNG")
                log.info(f"이미지 {sid} 완료")
                last_ok = out
                break
            except Exception as e:
                log.warning(f"이미지 {sid} 실패({attempt+1}/3): {e}")
                time.sleep(5)
        else:
            if last_ok is None:
                raise RuntimeError("첫 이미지부터 실패 - API 키/모델 확인")
            log.error(f"이미지 {sid} 포기 → 직전 이미지 재사용")
            Image.open(last_ok).save(out)
        paths.append(out)
        time.sleep(1.5)  # rate limit 여유
    return paths
