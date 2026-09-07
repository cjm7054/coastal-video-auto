"""2단계: 장면별 이미지 생성 (Gemini 또는 OpenAI). 실패 시 재시도 후 직전 이미지로 대체."""
import os, time, base64, io
from pathlib import Path
from PIL import Image
from .common import load_config, ROOT, log


def _pollinations(prompt: str, cfg: dict) -> bytes:
    """무료 Pollinations AI (FLUX 모델) 연동: 실제 항만·해안 토목 구조물 실사 스타일 최우선 반영"""
    import urllib.parse, requests
    w, h = cfg["images"]["width"], cfg["images"]["height"]
    
    # 뜬금없는 건축물/판타지를 배제하고 실제 콘크리트 테트라포드 및 방파제 해안토목 실사 키워드 주입
    core_style = (
        "National Geographic documentary photo, real coastal engineering infrastructure, "
        "authentic concrete tetrapod blocks interlocking on shoreline breakwater, heavy ocean waves crashing, "
        "hyperrealistic 8k, raw industrial concrete, civil engineering photography, no futuristic buildings, "
        "no fictional structures, no CGI cartoon"
    )
    full_prompt = f"{prompt}, {core_style}"
    encoded = urllib.parse.quote(full_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&model=flux&nologo=true&seed={int(time.time()*1000)%100000}"
    resp = requests.get(url, timeout=50)
    if resp.status_code == 200 and resp.content:
        return resp.content
    raise RuntimeError(f"Pollinations 실패 (HTTP {resp.status_code})")


def _gemini(prompt: str, cfg: dict) -> bytes:
    """Google 공식 최신 이미지 생성 API (Imagen 4 / Imagen 3 / Gemini 3.1 Flash Image)"""
    from google import genai
    from google.genai import types
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    
    client = genai.Client(api_key=api_key)
    
    # 1. Imagen 전용 모델 우선 시도 (imagen-3.0-generate-002, imagen-4.0-generate-001)
    models_to_try = [
        cfg["images"].get("gemini_model", "imagen-3.0-generate-002"),
        "imagen-4.0-generate-001",
        "imagen-3.0-generate-002",
    ]
    seen = set()
    for m in models_to_try:
        if not m or m in seen or "imagen" not in m.lower():
            continue
        seen.add(m)
        try:
            resp = client.models.generate_images(
                model=m,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    person_generation="DONT_ALLOW",
                )
            )
            if resp.generated_images and resp.generated_images[0].image.image_bytes:
                return resp.generated_images[0].image.image_bytes
        except Exception as err:
            log.warning(f"Imagen 모델({m}) 시도 실패: {err}")
    
    # 2. Gemini 3.1 Flash Image 멀티모달 생성 시도
    flash_models = ["gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3.1-flash-image-preview"]
    for fm in flash_models:
        try:
            resp = client.models.generate_content(
                model=fm,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9")
                ),
            )
            for part in resp.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
        except Exception as ferr:
            log.warning(f"Gemini 멀티모달 이미지({fm}) 실패: {ferr}")
            
    raise RuntimeError("모든 Google Gemini / Imagen 이미지 모델 생성 호출 실패")


def _openai(prompt: str, cfg: dict) -> bytes:
    from openai import OpenAI
    import requests
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    client = OpenAI(api_key=api_key)
    clean_prompt = prompt[:950]
    
    # 1. DALL-E 3 시도 (1792x1024)
    try:
        r = client.images.generate(
            model="dall-e-3",
            prompt=clean_prompt,
            size="1792x1024",
            quality="standard",
        )
        item = r.data[0]
        if getattr(item, "b64_json", None):
            return base64.b64decode(item.b64_json)
        if getattr(item, "url", None):
            resp = requests.get(item.url, timeout=60)
            if resp.status_code == 200:
                return resp.content
    except Exception as e3:
        log.warning(f"dall-e-3 시도 실패({e3}) → dall-e-2로 재시도")
        # 2. DALL-E 2 시도 (1024x1024)
        r = client.images.generate(
            model="dall-e-2",
            prompt=clean_prompt[:400],
            size="1024x1024",
        )
        item = r.data[0]
        if getattr(item, "b64_json", None):
            return base64.b64decode(item.b64_json)
        if getattr(item, "url", None):
            resp = requests.get(item.url, timeout=60)
            if resp.status_code == 200:
                return resp.content
                
    raise RuntimeError("OpenAI 이미지 데이터 수신 실패")


def _fetch_real_coastal_photo(query_prompt: str) -> bytes | None:
    """위키미디어 공용(Wikimedia Commons) 등 글로벌 고화질 아카이브에서 실제 해안·방파제·테트라포드 실사 사진 검색 및 다운로드"""
    import urllib.parse, requests
    
    # 핵심 검색 키워드 추출 (테트라포드, 방파제, 케이슨, 해안침식 등)
    low = query_prompt.lower()
    if "tetrapod" in low or "테트라포드" in query_prompt:
        terms = ["Tetrapod concrete breakwater", "Tetrapod coastal defense", "Tetrapods breakwater waves", "Concrete tetrapod block"]
    elif "caisson" in low or "케이슨" in query_prompt:
        terms = ["Caisson breakwater", "Concrete caisson breakwater harbor", "Harbor caisson engineering"]
    elif "erosion" in low or "침식" in query_prompt or "beach" in low or "모래" in query_prompt:
        terms = ["Coastal erosion beach", "Sea cliff erosion coastal defense", "Groyne coastal protection", "Beach nourishment dredging"]
    elif "breakwater" in low or "방파제" in query_prompt:
        terms = ["Breakwater heavy sea waves", "Harbor breakwater concrete", "Riprap breakwater ocean"]
    elif "wave" in low or "파도" in query_prompt or "storm" in low:
        terms = ["Ocean storm waves crashing", "Rough sea harbor waves", "Large storm wave seawall"]
    else:
        terms = ["Harbor breakwater engineering", "Coastal defense concrete", "Port engineering sea"]

    headers = {"User-Agent": "CoastalVideoAutoBot/1.0 (contact: admin@coastalengineering.org)"}
    
    for term in terms:
        try:
            search_url = (
                f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(term)}&gsrlimit=8&prop=imageinfo"
                f"&iiprop=url|mime|size&format=json"
            )
            r = requests.get(search_url, headers=headers, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                info_list = page.get("imageinfo", [])
                if not info_list:
                    continue
                info = info_list[0]
                mime = info.get("mime", "")
                url = info.get("url", "")
                # 고화질 실사 사진 (JPG/PNG 및 최소 1200px 이상)
                if ("jpeg" in mime or "png" in mime) and url and not url.endswith(".svg") and not url.endswith(".tif"):
                    w_img = info.get("width", 0)
                    if w_img >= 1200 or w_img == 0:
                        img_resp = requests.get(url, headers=headers, timeout=25)
                        if img_resp.status_code == 200 and len(img_resp.content) > 100000:
                            return img_resp.content
        except Exception as e:
            log.warning(f"실사 아카이브 검색({term}) 예외: {e}")
            continue
            
    return None


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
    provider = cfg["images"].get("provider", "pollinations")
    if provider == "gemini":
        gen = _gemini
    elif provider == "openai":
        gen = _openai
    else:
        gen = _pollinations
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
                log.info(f"이미지 {sid} 완료 ({provider})")
                last_ok = out
                success = True
                break
            except Exception as e:
                log.warning(f"이미지 {sid} 실패({attempt+1}/3): {e}")
                time.sleep(3)

        if not success:
            log.info(f"이미지 {sid}: 글로벌 해안·항만 토목 실사 아카이브(Wikimedia Commons HD)에서 실제 현장 사진 다운로드 시도...")
            real_data = _fetch_real_coastal_photo(prompt)
            if real_data:
                _fit(real_data, W, H).save(out, "PNG")
                log.info(f"이미지 {sid} 실제 현장 다큐멘터리 실사 사진 반영 완료 (Wikimedia HD)")
                last_ok = out
                success = True
            else:
                # 마지막 비상 시에도 저퀄리티 파란 화면 대신 이전 성공 실사 사진 복제
                if last_ok and last_ok.exists():
                    import shutil
                    shutil.copyfile(str(last_ok), str(out))
                    log.info(f"이미지 {sid}: 이전 고화질 실사 이미지 재활용")
                else:
                    _draw_fallback_image(prompt, sid, W, H).save(out, "PNG")
                last_ok = out

        paths.append(out)
        time.sleep(1.0)  # rate limit 여유
    return paths
