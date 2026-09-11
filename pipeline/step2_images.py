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


def _draw_engineering_info_overlay(clean_img: Image.Image, sc: dict) -> Image.Image:
    """MD 규격 Stage 4 (INFO): CLEAN 이미지 위에 3D 원근 투시 지시선, 한국어 공학 치수/수치 박스, 파랑 및 하중 벡터 화살표를 정밀 합성"""
    from PIL import ImageDraw, ImageFont
    
    info_img = clean_img.copy()
    W, H = info_img.size
    
    # 반투명 오버레이 레이어 생성 (RGBA)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # 폰트 로드 (기본 맑은 고딕 또는 대체 폰트)
    font_large, font_small, font_title = None, None, None
    font_candidates = [
        "c:/Windows/Fonts/malgunbd.ttf",
        "c:/Windows/Fonts/malgun.ttf",
        "assets/fonts/NotoSansCJK-Bold.ttc",
        "NotoSansCJK-Bold.ttc"
    ]
    for fc in font_candidates:
        if os.path.exists(fc):
            try:
                font_large = ImageFont.truetype(fc, int(W * 0.038))
                font_small = ImageFont.truetype(fc, int(W * 0.026))
                font_title = ImageFont.truetype(fc, int(W * 0.044))
                break
            except Exception:
                continue
    if font_large is None:
        font_large = ImageFont.load_default()
        font_small = font_large
        font_title = font_large

    narration = sc.get("narration", "")
    sid = sc.get("id", 1)
    
    # 1. 기술 데이터베이스 및 치수 도출
    tech_tags = []
    vectors = []
    
    if any(k in narration for k in ["잠제", "수중", "보이지 않", "물속"]):
        tech_tags.append(("수중방파제 (잠제)", "마루수심 -0.5m ~ -1.5m", int(W * 0.12), int(H * 0.46)))
        tech_tags.append(("파랑 에너지 소파", "쇄파 감쇄율 70% 이상", int(W * 0.52), int(H * 0.35)))
        vectors.append(((int(W * 0.85), int(H * 0.38)), (int(W * 0.55), int(H * 0.45)), "파랑 내습 에너지", (0, 210, 255)))
    elif any(k in narration for k in ["양빈", "모래", "백사장", "침식"]):
        tech_tags.append(("인공 양빈 공법", "모래 보충 체적 100,000㎥", int(W * 0.10), int(H * 0.50)))
        tech_tags.append(("연안표사 차단", "해빈 경사 1:50 안정화", int(W * 0.50), int(H * 0.38)))
        vectors.append(((int(W * 0.20), int(H * 0.65)), (int(W * 0.60), int(H * 0.60)), "연안표사 이동 벡터", (255, 215, 0)))
    elif any(k in narration for k in ["케이슨", "자중", "혼성제"]):
        tech_tags.append(("케이슨 본체", "설계 자중 15,000t 급", int(W * 0.12), int(H * 0.42)))
        tech_tags.append(("사석 마운드", "두께 5.0m 지지층", int(W * 0.52), int(H * 0.68)))
        vectors.append(((int(W * 0.88), int(H * 0.42)), (int(W * 0.58), int(H * 0.45)), "Goda 쇄파압 파력", (255, 75, 45)))
    elif any(k in narration for k in ["테트라포드", "소파블록", "4개"]):
        tech_tags.append(("소파블록 피복", "단위중량 50t TTP", int(W * 0.15), int(H * 0.48)))
        tech_tags.append(("인터로킹 맞물림", "파력 분산 공극률 50%", int(W * 0.50), int(H * 0.36)))
        vectors.append(((int(W * 0.82), int(H * 0.35)), (int(W * 0.55), int(H * 0.45)), "수리 충격 분산", (0, 230, 180)))
    elif any(k in narration for k in ["준설", "수심"]):
        tech_tags.append(("대형 호퍼 준설", "목표 계획수심 -16.0m", int(W * 0.12), int(H * 0.45)))
        tech_tags.append(("항로 정비", "준설 속도 1.8 knot", int(W * 0.52), int(H * 0.35)))
        vectors.append(((int(W * 0.30), int(H * 0.50)), (int(W * 0.30), int(H * 0.70)), "해저 토사 흡입력", (255, 180, 0)))
    else:
        tech_tags.append(("해안 수리역학 해석", "수치 시뮬레이션 KDS 64", int(W * 0.12), int(H * 0.42)))
        tech_tags.append(("파랑 에너지 제어", "에너지 투과율 감쇄", int(W * 0.52), int(H * 0.35)))
        vectors.append(((int(W * 0.85), int(H * 0.40)), (int(W * 0.55), int(H * 0.45)), "유체 압력 벡터", (0, 220, 255)))

    # 2. 파랑 / 하중 벡터 화살표 렌더링 (Stage 4 Force/Pressure Vectors)
    for start_pt, end_pt, vec_label, color_rgb in vectors:
        x1, y1 = start_pt
        x2, y2 = end_pt
        
        # 반투명 발광 효과
        draw.line([(x1, y1), (x2, y2)], fill=(color_rgb[0], color_rgb[1], color_rgb[2], 140), width=9)
        draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 240), width=4)
        
        # 화살표 촉 (Arrowhead) 계산
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length > 10:
            ux = dx / length
            uy = dy / length
            arrow_size = int(W * 0.035)
            # 좌우 날개
            wx1 = x2 - arrow_size * ux + arrow_size * 0.5 * uy
            wy1 = y2 - arrow_size * uy - arrow_size * 0.5 * ux
            wx2 = x2 - arrow_size * ux - arrow_size * 0.5 * uy
            wy2 = y2 - arrow_size * uy + arrow_size * 0.5 * ux
            draw.polygon([(x2, y2), (wx1, wy1), (wx2, wy2)], fill=(color_rgb[0], color_rgb[1], color_rgb[2], 230))
            
        # 벡터 라벨
        mid_x = (x1 + x2) // 2
        mid_y = (y1 + y2) // 2 - int(H * 0.025)
        tw = int(draw.textlength(vec_label, font=font_small))
        draw.rectangle([(mid_x - tw // 2 - 8, mid_y - 4), (mid_x + tw // 2 + 8, mid_y + int(H * 0.025) + 4)],
                       fill=(10, 20, 35, 200), outline=(color_rgb[0], color_rgb[1], color_rgb[2], 220), width=1)
        draw.text((mid_x - tw // 2, mid_y), vec_label, fill=(240, 245, 255, 255), font=font_small)

    # 3. 3D 공학 지시선 및 치수 라벨 박스 렌더링 (Stage 4 Callouts & Dimensions)
    for title, val, bx, by in tech_tags:
        # 앵커 포인트 및 지시선 (선명한 꺾임 지시선)
        anchor_x = bx + int(W * 0.12)
        anchor_y = by + int(H * 0.09)
        draw.ellipse([(anchor_x - 4, anchor_y - 4), (anchor_x + 4, anchor_y + 4)], fill=(0, 255, 255, 255))
        draw.ellipse([(anchor_x - 8, anchor_y - 8), (anchor_x + 8, anchor_y + 8)], outline=(0, 255, 255, 160), width=2)
        
        elbow_x = bx + int(W * 0.06)
        elbow_y = by + int(H * 0.04)
        draw.line([(anchor_x, anchor_y), (elbow_x, elbow_y), (bx + int(W * 0.02), elbow_y)], fill=(0, 220, 255, 220), width=2)
        
        # 반투명 테크니컬 HUD 글래스 박스
        t_w1 = int(draw.textlength(title, font=font_small))
        t_w2 = int(draw.textlength(val, font=font_large))
        box_w = max(t_w1, t_w2) + int(W * 0.04)
        box_h = int(H * 0.065)
        
        # 박스 배경 및 외곽 테두리 (모던 블루 테크)
        draw.rectangle([(bx, by - int(H * 0.02)), (bx + box_w, by + box_h)], fill=(12, 28, 48, 205), outline=(0, 210, 255, 220), width=2)
        # 상단 테두리 포인트 바
        draw.rectangle([(bx, by - int(H * 0.02)), (bx + int(box_w * 0.35), by - int(H * 0.02) + 3)], fill=(0, 255, 255, 255))
        
        draw.text((bx + int(W * 0.02), by - int(H * 0.012)), title, fill=(160, 215, 255, 255), font=font_small)
        draw.text((bx + int(W * 0.02), by + int(H * 0.015)), val, fill=(255, 255, 255, 255), font=font_large)

    # 4. 상단 우측 공학 다큐멘터리 엠블럼 워터마크
    sub_title_text = f"OCEAN CODE LAB ENG-SPEC // SCENE {sid:02d}"
    sw = int(draw.textlength(sub_title_text, font=font_small))
    top_x = W - sw - int(W * 0.05)
    top_y = int(H * 0.04)
    draw.rectangle([(top_x - 10, top_y - 4), (W - int(W * 0.03), top_y + int(H * 0.028))], fill=(5, 15, 30, 180), outline=(0, 180, 240, 140), width=1)
    draw.text((top_x, top_y), sub_title_text, fill=(140, 210, 255, 230), font=font_small)

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
                log.warning(f"CLEAN 이미지 {sid}: 직전 장면({prev_imgs[-1].name}) 재사용")
                clean_pil = Image.open(prev_imgs[-1]).convert("RGB")
                success = True

        # 4차: 최종 비상 시각화 그래픽 (맑은 에메랄드 해안 풍경)
        if not success:
            log.warning(f"CLEAN 이미지 {sid}: 고화질 에메랄드 해안 아트워크 생성")
            clean_pil = _draw_emergency_coastal_visual(prompt, sid, W, H)
            success = True

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


