"""2단계: 장면별 이미지 생성 (Gemini 또는 OpenAI). 실패 시 신뢰도 높은 해양 토목 실사 아카이브 연동."""
import os, time, base64, io, shutil, urllib.parse, requests
from pathlib import Path
from PIL import Image
from .common import load_config, ROOT, log


def _gemini(prompt: str, cfg: dict) -> bytes:
    """Google Gemini & Imagen 공식 이미지 생성 API (generate_images / generate_content / Interactions API)"""
    from google import genai
    from google.genai import types
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    
    clean_prompt = prompt[:900]
    client = genai.Client(api_key=api_key)

    # 1. Imagen 3.0 / 4.0 models.generate_images (Google 공식 Text-to-Image 표준 엔드포인트)
    imagen_models = [
        "imagen-3.0-generate-002",
        "imagen-4.0-generate-001",
    ]
    ar = cfg.get("images", {}).get("aspect_ratio") or ("9:16" if cfg.get("current_format") == "shorts" else "16:9")
    for m in imagen_models:
        try:
            log.info(f"Google Imagen({m}, {ar}) 시도...")
            resp = client.models.generate_images(
                model=m,
                prompt=clean_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=ar,
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

    # 2. Gemini 멀티모달 generate_content (IMAGE 모달리티 백업)
    multimodal_models = ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]
    for fm in multimodal_models:
        try:
            log.info(f"Gemini({fm}) 이미지 생성 호출: {clean_prompt[:60]}...")
            resp = client.models.generate_content(
                model=fm,
                contents=clean_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=ar)
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
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    client = OpenAI(api_key=api_key)
    
    clean_prompt = prompt[:950]
    dalle_size = cfg.get("images", {}).get("dalle_size") or ("1024x1792" if cfg.get("current_format") == "shorts" else "1792x1024")
    
    # 1. DALL-E 3 네이티브 비율 + HD
    try:
        log.info(f"OpenAI(dall-e-3 {dalle_size} HD natural) 호출: {clean_prompt[:70]}...")
        r = client.images.generate(
            model="dall-e-3",
            prompt=clean_prompt,
            size=dalle_size,
            quality="hd",
            style="natural",
        )
        if r and r.data:
            item = r.data[0]
            try:
                from .cost_tracker import tracker
                tracker.track_openai_image(model="dall-e-3", count=1)
            except Exception:
                pass
            b64 = getattr(item, "b64_json", None)
            if b64:
                return base64.b64decode(b64)
            url = getattr(item, "url", None)
            if url:
                resp = requests.get(url, timeout=60)
                if resp.status_code == 200:
                    return resp.content
    except Exception as me:
        log.warning(f"DALL-E 3 {dalle_size} HD 생성 실패: {me} → 표준 모드로 재시도")

    # 2. DALL-E 3 표준 백업
    try:
        fallback_size = dalle_size if dalle_size in ["1024x1792", "1792x1024"] else "1024x1024"
        r = client.images.generate(
            model="dall-e-3",
            prompt=clean_prompt,
            size=fallback_size,
            quality="standard",
            style="natural",
        )
        if r and r.data:
            item = r.data[0]
            url = getattr(item, "url", None)
            if url:
                resp = requests.get(url, timeout=60)
                if resp.status_code == 200:
                    return resp.content
    except Exception as de:
        log.warning(f"DALL-E 3 표준 모드 실패: {de}")

    raise RuntimeError("OpenAI 이미지 데이터 수신 실패")


def _fetch_real_coastal_photo(context_text: str, used_urls: set = None) -> bytes | None:
    """위키미디어 공용 및 고화질 해양 토목/바다 실사 사진 아카이브에서 문맥에 맞는 실사 사진을 다운로드."""
    if used_urls is None:
        used_urls = set()

    low = context_text.lower()
    terms = []

    # 나레이션 및 프롬프트 내용에 따른 정밀 검색어 도출
    if any(k in low or k in context_text for k in ["준설", "dredg", "파내", "밑바닥", "수심", "바닥"]):
        terms += [
            "Trailing suction hopper dredger",
            "Dredging vessel harbor",
            "Cutter suction dredger",
            "Dredging port ship",
        ]
    if any(k in low or k in context_text for k in ["케이슨", "caisson", "교각", "기초", "바다 위 도로", "해상교량"]):
        terms += [
            "Concrete caisson harbor",
            "Caisson breakwater installation",
            "Caisson maritime construction",
            "Concrete caisson dock",
        ]
    if any(k in low or k in context_text for k in ["테트라포드", "tetrapod", "4개 다리", "인터로킹", "소파블록"]):
        terms += [
            "Tetrapod concrete breakwater",
            "Tetrapods coastal protection",
            "Concrete dolos sea breakwater",
        ]
    if any(k in low or k in context_text for k in ["방파제", "breakwater", "해일", "방파", "파도막이", "잠제", "수중방파제"]):
        terms += [
            "Ocean harbor breakwater aerial",
            "Breakwater coastal defense aerial",
            "Seawall ocean waves concrete",
            "Submerged breakwater ocean",
        ]
    if any(k in low or k in context_text for k in ["컨테이너", "container", "크레인", "부두", "선석", "터미널"]):
        terms += [
            "Container terminal port cranes aerial",
            "Container ship harbor quay",
            "Commercial harbor cranes aerial",
        ]
    if any(k in low or k in context_text for k in ["침식", "모래", "erosion", "백사장", "연안", "양빈"]):
        terms += [
            "Beach nourishment coastal protection",
            "Coastal erosion shoreline protection aerial",
            "Sandy beach coastal breakwater",
        ]

    # 기본 해안/항만 토목 공학 최신 사진 키워드
    terms += [
        "Harbor civil engineering modern",
        "Ocean breakwater aerial view",
        "Maritime port container terminal",
        "Coastal engineering seawall breakwater",
        "Tetrapod breakwater coastline",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 CoastalVideo/2.0"
    }

    # 절대로 허용하지 않는 문서, 보고서, 도면, 설계도 키워드
    BANNED_KEYWORDS = [
        "blueprint", "drawing", "engraving", "sketch", "plan", "diagram",
        "lithograph", "illustration", "schematic", "patent", "report", "cover", "title",
        "archive", "vintage", "antique", "black and white", "b&w", "monochrome", "woodcut",
        "document", "paper", "text", "book", "bulletin", "publication", "page", "letter",
        "board", "cerc", "usace", "manual", "technical", "thesis"
    ]

    # 1. 위키미디어 공용 검색
    for term in terms:
        try:
            search_url = (
                f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(term)}&gsrnamespace=6&gsrlimit=12&prop=imageinfo"
                f"&iiprop=url|thumburl|mime|size&iiurlwidth=1920&format=json"
            )
            r = requests.get(search_url, headers=headers, timeout=8)
            if r.status_code != 200:
                continue
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                title = page.get("title", "").lower()
                if any(bk in title for bk in BANNED_KEYWORDS) or ".pdf" in title or ".djvu" in title:
                    continue

                info_list = page.get("imageinfo", [])
                if not info_list:
                    continue
                info = info_list[0]
                mime = info.get("mime", "").lower()
                download_url = info.get("thumburl") or info.get("url")
                
                if not download_url or download_url in used_urls or "pdf" in mime or "djvu" in mime or download_url.endswith(".svg"):
                    continue
                if any(bk in download_url.lower() for bk in BANNED_KEYWORDS):
                    continue

                if "image/jpeg" in mime or "image/png" in mime or download_url.endswith((".jpg", ".jpeg", ".png")):
                    img_resp = requests.get(download_url, headers=headers, timeout=12)
                    if img_resp.status_code == 200 and len(img_resp.content) > 30000:
                        used_urls.add(download_url)
                        log.info(f"실사 사진 아카이브 매칭 성공: {term} -> {title} ({download_url[:60]}...)")
                        return img_resp.content
        except Exception as e:
            log.warning(f"실사 아카이브 검색({term}) 예외: {e}")
            continue

    # 2. 고화질 오픈 소스 해양/토목 사진 URL 백업 풀 (신뢰할 수 있는 직접 다운로드)
    CURATED_COASTAL_PHOTOS = [
        # 방파제 / 테트라포드 / 에어리얼
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Tetrapods_in_Hel%2C_Poland.jpg/1920px-Tetrapods_in_Hel%2C_Poland.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Tetrapods_at_the_harbour_of_Heraklion%2C_Crete%2C_Greece.jpg/1920px-Tetrapods_at_the_harbour_of_Heraklion%2C_Crete%2C_Greece.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Port_of_Marseille_aerial_view.jpg/1920px-Port_of_Marseille_aerial_view.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Breakwater_and_lighthouse_in_the_harbor_of_San_Juan%2C_Puerto_Rico.jpg/1920px-Breakwater_and_lighthouse_in_the_harbor_of_San_Juan%2C_Puerto_Rico.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Dredging_vessel_Willem_van_Oranje_in_Rotterdam.jpg/1920px-Dredging_vessel_Willem_van_Oranje_in_Rotterdam.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Port_Taranaki_Breakwater.jpg/1920px-Port_Taranaki_Breakwater.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Aerial_view_of_the_Port_of_Valencia%2C_Spain.jpg/1920px-Aerial_view_of_the_Port_of_Valencia%2C_Spain.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Breakwater_at_Rostock_harbor.jpg/1920px-Breakwater_at_Rostock_harbor.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Container_terminal_at_Port_of_Hamburg.jpg/1920px-Container_terminal_at_Port_of_Hamburg.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Concrete_breakwater_blocks_sea_storm.jpg/1920px-Concrete_breakwater_blocks_sea_storm.jpg",
    ]

    for curl in CURATED_COASTAL_PHOTOS:
        if curl not in used_urls:
            try:
                c_resp = requests.get(curl, headers=headers, timeout=12)
                if c_resp.status_code == 200 and len(c_resp.content) > 30000:
                    used_urls.add(curl)
                    log.info(f"큐레이션 실사 해양 사진 매칭 성공: {curl[:60]}...")
                    return c_resp.content
            except Exception:
                continue

    return None


def _fit(data: bytes, w: int, h: int) -> Image.Image:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    ratio = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def _draw_emergency_coastal_visual(prompt: str, sid: str | int, w: int, h: int) -> Image.Image:
    """비상 상황에서도 어두운 빈 화면이 아닌, 맑은 에메랄드 해안선과 방파제 윤곽의 현대적 다큐멘터리 아트워크 생성"""
    from PIL import ImageDraw
    im = Image.new("RGB", (w, h), color=(15, 45, 75))
    draw = ImageDraw.Draw(im)

    # 1. 하늘 그라데이션 (밝은 청명한 아침 바다 하늘)
    sky_h = int(h * 0.42)
    for y in range(sky_h):
        r = int(140 - (y / sky_h) * 50)
        g = int(195 - (y / sky_h) * 45)
        b = int(240 - (y / sky_h) * 30)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 2. 에메랄드빛 푸른 바다 수면 그라데이션
    for y in range(sky_h, h):
        factor = (y - sky_h) / (h - sky_h)
        r = int(10 + factor * 10)
        g = int(115 - factor * 45)
        b = int(160 - factor * 40)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 3. 수평선 파도 및 방파제 원경 실루엣
    horizon_y = sky_h
    draw.line([(0, horizon_y), (w, horizon_y)], fill=(230, 245, 255), width=2)
    
    # 방파제 콘크리트 및 테트라포드 실루엣
    bw_y = int(h * 0.65)
    draw.polygon([(0, h), (int(w * 0.6), h), (int(w * 0.45), bw_y), (0, int(bw_y * 1.1))], fill=(75, 85, 95))
    draw.polygon([(0, int(bw_y * 1.1)), (int(w * 0.45), bw_y), (int(w * 0.42), int(bw_y * 0.96)), (0, int(bw_y * 1.05))], fill=(110, 120, 130))

    return im


def generate_images(script: dict, out_dir: Path) -> list[Path]:
    cfg = load_config()
    W, H = cfg["images"]["width"], cfg["images"]["height"]
    provider = cfg.get("images", {}).get("provider", "gemini")
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    
    # 1. API 키 가용성에 따른 최적 엔진 매핑 (Gemini Imagen 우선)
    generators = []
    if provider == "gemini":
        generators = [("Google Imagen/Gemini", _gemini), ("OpenAI DALL-E", _openai)]
    elif provider == "openai":
        generators = [("OpenAI DALL-E", _openai), ("Google Imagen/Gemini", _gemini)]
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

        clean_p = p.strip().rstrip(".")
        for ban in ["cross-section cutaway diagram", "cross-section", "cutaway diagram", "glowing red hydrodynamic wave pressure vectors", "glowing red pressure vectors", "technical HUD overlays"]:
            clean_p = clean_p.replace(ban, "cinematic clear ocean perspective")
        prompt = f"{clean_p}. {suffix}"
        success = False

        # 1차: AI 이미지 생성기 (Google Imagen 또는 DALL-E 3)
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

        # 4차: 앞선 장면 이미지가 있다면 직전 장면 재사용
        if not success:
            prev_imgs = [p for p in paths if p.name != "thumb.png" and p.exists()]
            if prev_imgs:
                log.warning(f"이미지 {sid}: 직전 장면({prev_imgs[-1].name}) 재사용 연결")
                shutil.copy(prev_imgs[-1], out)
                success = True

        # 5차: 최종 비상 시각화 그래픽 (맑은 에메랄드 해안 풍경)
        if not success:
            log.warning(f"이미지 {sid}: 비상 에메랄드 해안 아트워크 생성")
            try:
                _draw_emergency_coastal_visual(prompt, sid, W, H).save(out, "PNG")
                success = True
            except Exception as ee:
                log.error(f"이미지 {sid} 비상 그래픽 생성 실패: {ee}")

        paths.append(out)
        time.sleep(0.5)
    return paths

