"""2단계: 장면별 이미지 생성 (Gemini 또는 OpenAI). MD 규격 CLEAN & INFO 2-Pass 공학 인포그래픽 연동."""
import os, time, base64, io, shutil, urllib.parse, math, requests
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

    ar = cfg.get("images", {}).get("aspect_ratio") or ("9:16" if cfg.get("current_format") == "shorts" else "16:9")
    # 1. Gemini 멀티모달 generate_content (gemini-2.5-flash-image / gemini-3.1-flash-image-preview)
    multimodal_models = [
        "gemini-2.5-flash-image",
        "gemini-3.1-flash-image-preview",
        "gemini-3.1-flash-image",
    ]
    for fm in multimodal_models:
        for attempt in range(2):
            try:
                log.info(f"Gemini({fm}, {ar}, 시도 {attempt+1}) 이미지 생성 호출: {clean_prompt[:60]}...")
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
                log.warning(f"Gemini generate_content({fm}) 시도 {attempt+1} 실패: {ferr}")
                if "429" in str(ferr) or "RESOURCE_EXHAUSTED" in str(ferr):
                    time.sleep(3 * (attempt + 1))
                else:
                    break

    # 2. Imagen 3.0 / 4.0 models.generate_images
    imagen_models = [
        "imagen-3.0-generate-002",
        "imagen-4.0-generate-001",
    ]
    for m in imagen_models:
        for attempt in range(2):
            try:
                log.info(f"Google Imagen({m}, {ar}, 시도 {attempt+1}) 호출...")
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
                log.warning(f"Google Imagen({m}) 실패 ({err})")
                if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                    time.sleep(3 * (attempt + 1))
                else:
                    break

    # 3. Interactions API
    interactions_models = ["gemini-3.1-flash-image-preview", "gemini-3.1-flash-image", "gemini-3-pro-image-preview"]
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
        log.info(f"OpenAI(dall-e-3 {dalle_size} HD) 호출: {clean_prompt[:70]}...")
        r = client.images.generate(
            model="dall-e-3",
            prompt=clean_prompt,
            size=dalle_size,
            quality="hd",
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

    # 3. DALL-E 2 백업 (1024x1024)
    try:
        log.info(f"OpenAI(dall-e-2 1024x1024) 폴백 시도...")
        r = client.images.generate(
            model="dall-e-2",
            prompt=clean_prompt[:900],
            size="1024x1024",
        )
        if r and r.data:
            item = r.data[0]
            url = getattr(item, "url", None)
            if url:
                resp = requests.get(url, timeout=60)
                if resp.status_code == 200:
                    return resp.content
    except Exception as d2e:
        log.warning(f"DALL-E 2 폴백 실패: {d2e}")

    raise RuntimeError("OpenAI 이미지 데이터 수신 실패")


def _fit(data: bytes, w: int, h: int) -> Image.Image:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    ratio = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))




def _draw_engineering_info_overlay(clean_img: Image.Image, sc: dict) -> Image.Image:
    """MD 규격 Stage 4 (INFO) & 신비한 건축사전 레퍼런스 스타일:
    - 절대 금지(Forbidden): 화면을 뒤덮는 거대한 사각 박스, 전체 화면 플랫 HUD
    - 준수(Standard): 얇은 1~2px 시안/골드 헤어라인 지시선, 미세 앵커 닷(r=3~4px),
      작고 정제된 기술 라벨(18~22px) 및 핵심 수치 배지만 배치
    - 안전 영역: 상단 20%~하단 65% 내부로 제한하여 쇼츠 자막 및 상단 상태바 침범 완전 차단
    """
    from PIL import ImageDraw, ImageFont
    
    info_img = clean_img.copy()
    W, H = info_img.size
    
    # 반투명 오버레이 레이어 생성 (RGBA)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # 정밀 폰트 로드 (모바일 쇼츠 가독성을 고려한 절제된 폰트 크기)
    font_val = None
    font_label = None
    font_candidates = [
        "c:/Windows/Fonts/malgunbd.ttf",
        "c:/Windows/Fonts/malgun.ttf",
        "assets/fonts/NotoSansCJK-Bold.ttc",
        "NotoSansCJK-Bold.ttc"
    ]
    for fc in font_candidates:
        if os.path.exists(fc):
            try:
                font_val = ImageFont.truetype(fc, int(W * 0.024))      # 약 26px (단정하고 날렵한 수치)
                font_label = ImageFont.truetype(fc, int(W * 0.018))    # 약 19px (극도로 정제된 라벨)
                break
            except Exception:
                continue
    if font_val is None:
        font_val = ImageFont.load_default()
        font_label = font_val

    narration = sc.get("narration", "")
    sid = sc.get("id", 1)
    
    # 1. 기술 데이터베이스 및 치수 도출 (MD 규격: 씬당 1~2개의 미세 지시선만 허용)
    callouts = []
    vector_arrows = []
    
    # 쇼츠 세로 안전 영역 (X: 12%~88%, Y: 25%~60% - 좌우 및 상하 여백 확보)
    if any(k in narration for k in ["잠제", "수중방파제", "수중", "물속"]):
        callouts.append(("수중방파제 마루수심", "-0.5m ~ -1.5m", int(W * 0.16), int(H * 0.38), int(W * 0.48), int(H * 0.50)))
        vector_arrows.append(((int(W * 0.82), int(H * 0.35)), (int(W * 0.52), int(H * 0.42)), "쇄파 감쇄 70%", (0, 220, 255)))
    elif any(k in narration for k in ["양빈", "모래", "백사장", "침식"]):
        callouts.append(("양빈 체적", "100,000㎥", int(W * 0.16), int(H * 0.42), int(W * 0.46), int(H * 0.52)))
        vector_arrows.append(((int(W * 0.22), int(H * 0.58)), (int(W * 0.68), int(H * 0.58)), "표사 이동 벡터", (255, 210, 50)))
    elif any(k in narration for k in ["케이슨", "자중", "혼성제"]):
        callouts.append(("설계 자중", "15,000 t", int(W * 0.16), int(H * 0.36), int(W * 0.48), int(H * 0.46)))
        vector_arrows.append(((int(W * 0.82), int(H * 0.38)), (int(W * 0.54), int(H * 0.44)), "Goda 쇄파압", (255, 90, 60)))
    elif any(k in narration for k in ["테트라포드", "소파블록", "4개"]):
        callouts.append(("소파블록 규격", "50t TTP", int(W * 0.16), int(H * 0.38), int(W * 0.46), int(H * 0.48)))
        vector_arrows.append(((int(W * 0.78), int(H * 0.35)), (int(W * 0.52), int(H * 0.42)), "공극률 50% 파력분산", (0, 230, 190)))
    elif any(k in narration for k in ["준설", "수심"]):
        callouts.append(("항로 계획수심", "-16.0 m", int(W * 0.16), int(H * 0.40), int(W * 0.48), int(H * 0.52)))
    else:
        # 일반 풍경이나 인트로 등에서는 강제 허위 라벨을 그리지 않고 클린 상태 유지
        return clean_img

    # 2. 물리/유체 벡터 화살표 렌더링 (신비한 건축사전: 슬림한 2px 선 + 세련된 미니멀 화살촉)
    for start_pt, end_pt, vec_label, color_rgb in vector_arrows:
        x1, y1 = start_pt
        x2, y2 = end_pt
        
        # 얇고 섬세한 발광 라인
        draw.line([(x1, y1), (x2, y2)], fill=(color_rgb[0], color_rgb[1], color_rgb[2], 120), width=5)
        draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 230), width=2)
        
        # 슬림한 화살표 촉
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length > 8:
            ux, uy = dx / length, dy / length
            asize = int(W * 0.022)
            wx1 = x2 - asize * ux + asize * 0.4 * uy
            wy1 = y2 - asize * uy - asize * 0.4 * ux
            wx2 = x2 - asize * ux - asize * 0.4 * uy
            wy2 = y2 - asize * uy + asize * 0.4 * ux
            draw.polygon([(x2, y2), (wx1, wy1), (wx2, wy2)], fill=(color_rgb[0], color_rgb[1], color_rgb[2], 240))
            
        # 벡터 설명 미니 뱃지 (화면 중심 방해 없이 선 중간에 살짝 부착)
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2 - int(H * 0.018)
        lw = int(draw.textlength(vec_label, font=font_label))
        draw.rectangle([(mx - lw // 2 - 6, my - 3), (mx + lw // 2 + 6, my + int(H * 0.020))],
                       fill=(10, 20, 35, 180), outline=(color_rgb[0], color_rgb[1], color_rgb[2], 160), width=1)
        draw.text((mx - lw // 2, my), vec_label, fill=(235, 245, 255, 240), font=font_label)

    # 3. 3D 공학 지시선 & 미니멀 치수 뱃지 (신비한 건축사전 및 MD 규격)
    for label, val_text, badge_x, badge_y, anchor_x, anchor_y in callouts:
        # 미세 앵커 닷 (Point Anchor)
        draw.ellipse([(anchor_x - 3, anchor_y - 3), (anchor_x + 3, anchor_y + 3)], fill=(0, 255, 255, 255))
        draw.ellipse([(anchor_x - 6, anchor_y - 6), (anchor_x + 6, anchor_y + 6)], outline=(0, 255, 255, 120), width=1)
        
        # 1~2px 헤어라인 꺾임 지시선
        elbow_x = badge_x + int(W * 0.08)
        draw.line([(anchor_x, anchor_y), (elbow_x, badge_y + int(H * 0.015)), (badge_x + int(W * 0.02), badge_y + int(H * 0.015))],
                  fill=(0, 230, 255, 180), width=1)
        
        # 초경량 미니멀 글래스 뱃지 (더 이상 거대한 박스가 아님!)
        w_lbl = int(draw.textlength(label, font=font_label))
        w_val = int(draw.textlength(val_text, font=font_val))
        bw = max(w_lbl, w_val) + int(W * 0.03)
        bh = int(H * 0.038)
        
        # 딥 다크 네이비 투명 블렌딩 + 1px 시안 보더
        draw.rectangle([(badge_x, badge_y), (badge_x + bw, badge_y + bh)],
                       fill=(8, 18, 32, 175), outline=(0, 210, 255, 160), width=1)
        # 좌측 2px 액센트 바
        draw.line([(badge_x, badge_y), (badge_x, badge_y + bh)], fill=(0, 255, 255, 255), width=2)
        
        draw.text((badge_x + int(W * 0.015), badge_y + 2), label, fill=(160, 215, 255, 220), font=font_label)
        draw.text((badge_x + int(W * 0.015), badge_y + int(H * 0.016)), val_text, fill=(255, 255, 255, 255), font=font_val)

    # 오버레이 블렌딩
    info_img = Image.alpha_composite(info_img.convert("RGBA"), overlay).convert("RGB")
    return info_img


def generate_images(script: dict, out_dir: Path) -> list[Path]:
    """MD 규격 완벽 준수:
    1. 각 장면마다 순수 3D 실사 렌더링 'clean/{id}.png' (Stage 2) 생성
    2. 지시선, 치수, 수치, 파랑/하중 벡터가 결합된 'info/{id}.png' (Stage 4) 정밀 제작
    3. 대표 이미지 'images/{id}.png'에 동기화 보존
    """
    cfg = load_config()
    W, H = cfg["images"]["width"], cfg["images"]["height"]
    provider = cfg.get("images", {}).get("provider", "gemini")
    
    img_dir = out_dir / "images"
    clean_dir = out_dir / "clean"
    info_dir = out_dir / "info"
    img_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)
    
    generators = []
    if provider == "gemini":
        generators = [("Google Imagen/Gemini", _gemini), ("OpenAI DALL-E", _openai)]
    elif provider == "openai":
        generators = [("OpenAI DALL-E", _openai), ("Google Imagen/Gemini", _gemini)]
    else:
        generators = [("Google Imagen/Gemini", _gemini), ("OpenAI DALL-E", _openai)]

    suffix = cfg["images"]["style_suffix"].strip()
    paths = []
    topic = script.get("topic", "")

    # 작업 리스트: (장면ID, clean 프롬프트, info 프롬프트, 장면 데이터)
    jobs = [
        ("thumb", script["thumbnail_prompt"], "", {"id": "thumb", "narration": script.get("title", "")})
    ]
    for sc in script["scenes"]:
        cp = sc.get("clean_prompt") or sc.get("image_prompt", "")
        ip = sc.get("info_prompt") or ""
        jobs.append((sc["id"], cp, ip, sc))
    
    for sid, clean_p_raw, info_p_raw, sc_data in jobs:
        out_main = img_dir / f"{sid}.png"
        out_clean = clean_dir / f"{sid}.png"
        out_info = info_dir / f"{sid}.png"
        
        if out_main.exists() and out_clean.exists() and out_info.exists():
            paths.append(out_main)
            continue

        clean_p = clean_p_raw.strip().rstrip(".")
        for ban in ["cross-section cutaway diagram", "cross-section", "cutaway diagram", "glowing red hydrodynamic wave pressure vectors", "glowing red pressure vectors", "technical HUD overlays"]:
            clean_p = clean_p.replace(ban, "cinematic clear ocean perspective")
        prompt = f"{clean_p}. {suffix}"
        success = False
        clean_pil = None

        # 1차: AI 이미지 생성기 (Google Imagen 또는 DALL-E 3)
        for gen_name, gen_func in generators:
            try:
                log.info(f"CLEAN 이미지 {sid}: {gen_name} 시도 중...")
                img_data = gen_func(prompt, cfg)
                if img_data:
                    clean_pil = _fit(img_data, W, H)
                    log.info(f"CLEAN 이미지 {sid} AI 생성 성공 ({gen_name})")
                    success = True
                    break
            except Exception as ge:
                log.warning(f"CLEAN 이미지 {sid} {gen_name} 실패: {ge}")

        # 2차: 단순화 프롬프트로 재시도
        if not success:
            log.info(f"CLEAN 이미지 {sid}: 핵심 해양 토목 키워드로 단순화 재시도...")
            simple_prompt = f"Authentic 4k documentary photography of {topic}, {clean_p_raw[:180]}. {suffix}"
            for gen_name, gen_func in generators:
                try:
                    img_data = gen_func(simple_prompt, cfg)
                    if img_data:
                        clean_pil = _fit(img_data, W, H)
                        log.info(f"CLEAN 이미지 {sid} 단순화 재시도 성공 ({gen_name})")
                        success = True
                        break
                except Exception as ge2:
                    log.warning(f"CLEAN 이미지 {sid} {gen_name} 재시도 실패: {ge2}")

        # 3차: 이전 유효 장면 재사용 (무관한 해외 사진 크롤러는 완전 배제)
        if not success:
            prev_imgs = [p for p in clean_dir.glob("*.png") if p.name != "thumb.png" and p.exists()]
            if prev_imgs:
                log.warning(f"CLEAN 이미지 {sid}: 직전 고화질 3D 장면({prev_imgs[-1].name}) 재사용")
                clean_pil = Image.open(prev_imgs[-1]).convert("RGB")
                success = True

        if not success:
            raise RuntimeError(f"장면 {sid} 이미지 생성 실패: AI(Google Imagen / Gemini / DALL-E) 호출이 실패하였습니다. 유치한 2D 그림은 생성하지 않고 중단합니다.")

        # CLEAN 이미지 저장
        clean_pil.save(out_clean, "PNG")

        # INFO 이미지 제작: MD Stage 4 규격에 맞춰 3D 치수선, 수치, 라벨, 하중 화살표 정밀 증강
        if sid == "thumb":
            # 썸네일은 텍스트 없이 고화질 유지
            info_pil = clean_pil.copy()
        else:
            log.info(f"INFO 인포그래픽 {sid}: 치수선, 수치, 하중/파력 벡터 결합 중...")
            info_pil = _draw_engineering_info_overlay(clean_pil, sc_data)
        
        info_pil.save(out_info, "PNG")
        
        # 메인 이미지 디렉토리에는 INFO 상태를 기본 저장하여 하위 호환성 유지
        info_pil.save(out_main, "PNG")
        paths.append(out_main)
        time.sleep(0.5)

    return paths


