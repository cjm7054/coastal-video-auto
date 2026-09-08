"""2단계: 장면별 이미지 생성 (Gemini 또는 OpenAI). 실패 시 재시도 후 직전 이미지로 대체."""
import os, time, base64, io, shutil
from pathlib import Path
from PIL import Image
from .common import load_config, ROOT, log


def _gemini(prompt: str, cfg: dict) -> bytes:
    """Google Gemini & Imagen 공식 이미지 생성 API (generate_content / generate_images / Interactions API)"""
    from google import genai
    from google.genai import types
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    
    clean_prompt = prompt[:900]
    client = genai.Client(api_key=api_key)

    # 1. Gemini 멀티모달 generate_content (IMAGE 모달리티) - Google AI Studio 키에서 100% 정상 작동 검증
    multimodal_models = ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]
    for fm in multimodal_models:
        try:
            log.info(f"Gemini({fm}) 이미지 생성 호출: {clean_prompt[:60]}...")
            resp = client.models.generate_content(
                model=fm,
                contents=clean_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9")
                ),
            )
            for part in getattr(resp, "parts", []):
                if hasattr(part, "as_image"):
                    try:
                        pil_img = part.as_image()
                        buf = io.BytesIO()
                        pil_img.save(buf, format="PNG")
                        return buf.getvalue()
                    except Exception:
                        pass
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    d = part.inline_data.data
                    return base64.b64decode(d) if isinstance(d, str) else d
        except Exception as ferr:
            log.warning(f"Gemini generate_content({fm}) 실패: {ferr}")

    # 2. Imagen 3.0 / 4.0 models.generate_images (Vertex 연계 또는 Developer 모드)
    imagen_models = [
        "imagen-3.0-generate-002",
        "imagen-4.0-generate-001",
    ]
    for m in imagen_models:
        try:
            log.info(f"Google Imagen({m}) 시도...")
            resp = client.models.generate_images(
                model=m,
                prompt=clean_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                ),
            )
            if resp and resp.generated_images:
                img_wrapper = resp.generated_images[0]
                img_obj = getattr(img_wrapper, "image", img_wrapper)
                raw = getattr(img_obj, "image_bytes", None) or getattr(img_obj, "_image_bytes", None)
                if raw:
                    return base64.b64decode(raw) if isinstance(raw, str) else raw
                if hasattr(img_obj, "save"):
                    buf = io.BytesIO()
                    img_obj.save(buf, format="JPEG")
                    return buf.getvalue()
        except Exception as err:
            log.warning(f"Google Imagen({m}) 시도 실패: {err}")

    # 3. Interactions API (gemini-3.1-flash-image)
    interactions_models = ["gemini-3.1-flash-image", "gemini-3-pro-image-preview"]
    for im in interactions_models:
        try:
            log.info(f"Interactions API({im}) 시도...")
            interaction = client.interactions.create(
                model=im,
                input=clean_prompt,
                response_modalities=["IMAGE"],
            )
            for out in getattr(interaction, "outputs", []):
                if getattr(out, "type", "") == "image":
                    d = getattr(out, "data", None)
                    if d:
                        return base64.b64decode(d) if isinstance(d, str) else d
        except Exception as ierr:
            log.warning(f"Interactions API({im}) 시도 실패: {ierr}")

    # 4. Google Gemini OpenAI 호환 엔드포인트
    try:
        from openai import OpenAI
        log.info("Google Gemini OpenAI-compatible 엔드포인트 시도...")
        oai_client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        r = oai_client.images.generate(
            model="gemini-2.5-flash-image",
            prompt=clean_prompt,
            size="1024x1024",
            response_format="b64_json",
        )
        item = r.data[0]
        if getattr(item, "b64_json", None):
            return base64.b64decode(item.b64_json)
    except Exception as oe:
        log.warning(f"Google Gemini OpenAI 호환 호출 실패: {oe}")

    raise RuntimeError("Google Gemini / Imagen 이미지 생성 전체 실패")


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
        log.warning(f"dall-e-3 시도 실패({e3})")
        # 2. DALL-E 2 시도 (1024x1024)
        try:
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
        except Exception as e2:
            log.warning(f"dall-e-2 시도 실패({e2})")
                
    raise RuntimeError("OpenAI 이미지 데이터 수신 실패")


def _fetch_real_coastal_photo(context_text: str, used_urls: set = None) -> bytes | None:
    """위키미디어 공용(Wikimedia Commons)에서 나레이션/주제에 정확히 일치하는 최신 컬러 실사 사진만 검색 및 다운로드.
    도면, 스케치, 판화, 흑백 고문서, 블루프린트, 2D 다이어그램은 철저히 배제."""
    import urllib.parse, requests
    if used_urls is None:
        used_urls = set()

    low = context_text.lower()
    terms = []

    # 나레이션 및 프롬프트 내용에 따른 정밀 검색어 도출 (현대 컬러 사진 유도 키워드 추가)
    if any(k in low or k in context_text for k in ["준설", "dredg", "파내", "밑바닥", "수심", "바닥"]):
        terms += [
            "Trailing suction hopper dredger ship color photo",
            "Dredging vessel harbor construction",
            "Cutter suction dredger marine",
            "Modern dredging in port",
        ]
    if any(k in low or k in context_text for k in ["케이슨", "caisson", "교각", "기초", "바다 위 도로", "해상교량"]):
        terms += [
            "Concrete caisson maritime construction photo",
            "Floating caisson installation harbor",
            "Caisson breakwater installation",
            "Concrete caisson harbor dock",
        ]
    if any(k in low or k in context_text for k in ["테트라포드", "tetrapod", "4개 다리", "인터로킹", "소파블록"]):
        terms += [
            "Tetrapod concrete breakwater ocean photo",
            "Tetrapods coastal protection colored",
            "Concrete dolos sea breakwater",
        ]
    if any(k in low or k in context_text for k in ["방파제", "breakwater", "해일", "방파", "파도막이"]):
        terms += [
            "Ocean harbor breakwater aerial photograph",
            "Concrete coastal breakwater modern",
            "Seawall storm ocean waves photograph",
        ]
    if any(k in low or k in context_text for k in ["컨테이너", "container", "크레인", "부두", "선석", "터미널"]):
        terms += [
            "Modern container terminal port cranes photograph",
            "Container ship harbor quay color",
            "Commercial harbor container terminal aerial",
        ]
    if any(k in low or k in context_text for k in ["침식", "모래", "erosion", "백사장", "연안"]):
        terms += [
            "Beach nourishment coastal engineering photo",
            "Coastal erosion shoreline protection aerial",
        ]

    # 기본 해안/항만 토목 공학 최신 사진 키워드
    terms += [
        "Harbor civil engineering modern photograph",
        "Maritime civil engineering dock container",
        "Breakwater concrete ocean waves photography",
    ]

    headers = {
        "User-Agent": "CoastalVideoBot/1.0 (https://github.com/cjm7054/coastal-video-auto; contact@example.com)"
    }

    # 절대로 허용하지 않는 문서, 보고서, 흑백, 도면, 설계도, 판화, PDF 키워드
    BANNED_KEYWORDS = [
        "blueprint", "drawing", "engraving", "sketch", "plan", "diagram", "historic",
        "18", "190", "191", "192", "193", "194", "195", "196", "197", "198", "199",
        "lithograph", "illustration", "schematic", "patent", "report", "cover", "title",
        "archive", "vintage", "antique", "black and white", "b&w", "monochrome", "woodcut",
        "document", "paper", "text", "book", "bulletin", "publication", "page", "letter",
        "board", "cerc", "usace", "manual", "technical", "thesis"
    ]

    for term in terms:
        try:
            search_url = (
                f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(term)}&gsrnamespace=6&gsrlimit=15&prop=imageinfo"
                f"&iiprop=url|thumburl|mime|size&iiurlwidth=1920&format=json"
            )
            r = requests.get(search_url, headers=headers, timeout=8)
            if r.status_code != 200:
                continue
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                title = page.get("title", "").lower()
                # 고문서, 도면, 흑백 판화, 다이어그램, PDF 배제
                if any(bk in title for bk in BANNED_KEYWORDS):
                    continue
                if ".pdf" in title or ".djvu" in title:
                    continue

                info_list = page.get("imageinfo", [])
                if not info_list:
                    continue
                info = info_list[0]
                mime = info.get("mime", "").lower()
                download_url = info.get("thumburl") or info.get("url")
                
                # PDF, SVG, 문서류 절대 배제
                if not download_url or download_url in used_urls or "pdf" in mime or "djvu" in mime or download_url.endswith(".svg"):
                    continue
                if any(bk in download_url.lower() for bk in BANNED_KEYWORDS):
                    continue

                if "image/jpeg" in mime or "image/png" in mime or download_url.endswith((".jpg", ".jpeg", ".png")):
                    img_resp = requests.get(download_url, headers=headers, timeout=12)
                    if img_resp.status_code == 200 and len(img_resp.content) > 40000:
                        # 흑백 이미지 여부 간이 검사 (RGB 채널 분산 확인)
                        try:
                            sample = Image.open(io.BytesIO(img_resp.content)).convert("RGB").resize((64, 64))
                            pixels = list(sample.getdata())
                            # R, G, B 차이의 평균이 너무 작으면 흑백 사진/청사진
                            color_diff = sum(abs(p[0]-p[1]) + abs(p[1]-p[2]) + abs(p[2]-p[0]) for p in pixels) / len(pixels)
                            if color_diff < 15.0:  # 흑백 혹은 모노크롬 도면 판정
                                continue
                        except Exception:
                            continue

                        used_urls.add(download_url)
                        log.info(f"실사 컬러 사진 아카이브 매칭 성공: {term} -> {title} ({download_url[:60]}...)")
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


def _draw_emergency_coastal_visual(prompt: str, sid: str | int, w: int, h: int) -> Image.Image:
    """극단적 비상 상황에서도 글자 노출 없이 다큐멘터리 방송 분위기의 시네마틱 해양 그라데이션 그래픽 생성"""
    from PIL import ImageDraw
    im = Image.new("RGB", (w, h), color=(10, 20, 32))
    draw = ImageDraw.Draw(im)

    # 웅장한 심해 시네마틱 그라데이션
    for y in range(h):
        r = int(6 + (y / h) * 18)
        g = int(14 + (y / h) * 38)
        b = int(28 + (y / h) * 55)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 수평선 및 수면 연출
    sea_y = int(h * 0.58)
    for y in range(sea_y, h):
        factor = (y - sea_y) / (h - sea_y)
        r = int(12 + factor * 20)
        g = int(35 + factor * 45)
        b = int(55 + factor * 60)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    return im


def generate_images(script: dict, out_dir: Path) -> list[Path]:
    cfg = load_config()
    W, H = cfg["images"]["width"], cfg["images"]["height"]
    provider = cfg["images"].get("provider", "openai")
    
    # 1. API 키 가용성에 따른 최적 엔진 매핑
    generators = []
    if provider == "openai":
        generators = [("OpenAI DALL-E", _openai), ("Google Imagen/Gemini", _gemini)]
    elif provider == "gemini":
        generators = [("Google Imagen/Gemini", _gemini), ("OpenAI DALL-E", _openai)]
    else:
        generators = [("Google Imagen/Gemini", _gemini), ("OpenAI DALL-E", _openai)]

    suffix = cfg["images"]["style_suffix"].strip()
    paths = []
    used_archive_urls = set()
    topic = script.get("topic", "")

    # 작업 리스트: (장면ID, 영문 이미지 프롬프트, 한국어 나레이션/문맥)
    jobs = [("thumb", script["thumbnail_prompt"], script.get("title", ""))] + [
        (s["id"], s["image_prompt"], f"{topic} {s.get('narration', '')}") for s in script["scenes"]
    ]
    
    for sid, p, context_text in jobs:
        out = out_dir / "images" / f"{sid}.png"
        if out.exists():
            paths.append(out)
            continue
        prompt = f"{p}. {suffix}"
        success = False

        # 1차: AI 이미지 생성기 (DALL-E 3 또는 Google Imagen)
        for gen_name, gen_func in generators:
            try:
                log.info(f"이미지 {sid}: {gen_name} 시도 중...")
                img_data = gen_func(prompt, cfg)
                if img_data:
                    _fit(img_data, W, H).save(out, "PNG")
                    log.info(f"이미지 {sid} 생성 성공 ({gen_name})")
                    success = True
                    break
            except Exception as ge:
                log.warning(f"이미지 {sid} {gen_name} 실패: {ge}")

        # 2차: AI 모델 1차 실패 시 단순화된 안전 프롬프트로 재시도
        if not success:
            log.info(f"이미지 {sid}: 핵심 해양 토목 키워드로 단순화 재시도...")
            simple_prompt = f"Authentic documentary 4k photograph of maritime civil engineering harbor construction, {p[:200]}. {suffix}"
            for gen_name, gen_func in generators:
                try:
                    img_data = gen_func(simple_prompt, cfg)
                    if img_data:
                        _fit(img_data, W, H).save(out, "PNG")
                        log.info(f"이미지 {sid} 단순화 재시도 성공 ({gen_name})")
                        success = True
                        break
                except Exception as ge2:
                    log.warning(f"이미지 {sid} {gen_name} 재시도 실패: {ge2}")

        # 3차: AI 생성 실패 시 고화질 해양 토목 실사 사진 아카이브에서 문맥에 맞는 사진 검색
        if not success:
            log.info(f"이미지 {sid}: 고화질 컬러 실사 사진 아카이브 매칭 시도...")
            real_photo = _fetch_real_coastal_photo(context_text, used_archive_urls)
            if real_photo:
                try:
                    _fit(real_photo, W, H).save(out, "PNG")
                    log.info(f"이미지 {sid} 실사 사진 매칭 저장 완료")
                    success = True
                except Exception as rpe:
                    log.warning(f"실사 사진 가공 실패: {rpe}")

        # 4차: 앞선 장면 이미지가 있다면 시각적 일관성을 위해 직전 장면 재사용
        if not success:
            prev_imgs = [p for p in paths if p.name != "thumb.png" and p.exists()]
            if prev_imgs:
                log.warning(f"이미지 {sid}: AI 모델 일시 제한으로 직전 고화질 장면({prev_imgs[-1].name}) 연속 연결")
                shutil.copy(prev_imgs[-1], out)
                success = True

        # 5차: 썸네일이거나 첫 장면인 경우에도 절대 다운되지 않도록 긴급 시네마틱 비주얼 생성
        if not success:
            log.warning(f"이미지 {sid}: 최후의 비상 시네마틱 해양 배경 생성")
            _draw_emergency_coastal_visual(prompt, sid, W, H).save(out, "PNG")
            success = True

        paths.append(out)
        time.sleep(1.0)
    return paths
