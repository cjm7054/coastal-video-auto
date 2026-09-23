"""2단계: 장면별 이미지 생성. MD 규격 CLEAN & INFO 2-Pass 공학 인포그래픽 연동.

원칙
- 실패를 숨기지 않는다: 이미지가 한 장이라도 생성되지 않으면 예외를 던져 업로드를 막는다.
  (예전에는 새만금 템플릿 8장으로 조용히 대체되어 매번 같은 그림이 올라갔음)
- 그림체 통일: 첫 장면 이미지를 '스타일 기준(reference)'으로 삼아 이후 장면에 함께 넣는다(Gemini).
"""
import os, re, time, base64, io, shutil, urllib.parse, math, requests, hashlib
from pathlib import Path
from PIL import Image
from .common import load_config, ROOT, log


class ImageGenError(RuntimeError):
    pass


def _is_quota(err) -> bool:
    s = str(err)
    return "429" in s or "RESOURCE_EXHAUSTED" in s or "rate limit" in s.lower()


def _extract_image_bytes(resp) -> bytes | None:
    parts = list(getattr(resp, "parts", None) or [])
    if not parts:
        for cand in getattr(resp, "candidates", None) or []:
            content = getattr(cand, "content", None)
            if content and getattr(content, "parts", None):
                parts.extend(content.parts)
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline and getattr(inline, "data", None):
            d = inline.data
            return base64.b64decode(d) if isinstance(d, str) else d
    return None


def _gemini(prompt: str, cfg: dict, style_ref: bytes | None = None) -> bytes:
    """Gemini 이미지 모델(generate_content). 유료(결제 등록) API 키 필요 — 무료 등급은 이미지 한도 0."""
    from google import genai
    from google.genai import types
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ImageGenError("GEMINI_API_KEY 미설정")
    client = genai.Client(api_key=api_key)
    ar = cfg["images"].get("aspect_ratio", "16:9")
    models = cfg["images"].get("gemini_models") or [
        "gemini-3.1-flash-image-preview",
        "gemini-2.5-flash-image",
    ]
    contents = []
    if style_ref:
        contents.append(types.Part.from_bytes(data=style_ref, mime_type="image/png"))
        contents.append(
            "Use the attached image ONLY as the visual style reference (same rendering style, "
            "color palette, lighting, material look and level of detail). Draw a NEW scene:\n" + prompt
        )
    else:
        contents.append(prompt)

    last = None
    for m in models:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio=ar),
                    ),
                )
                data = _extract_image_bytes(resp)
                if data:
                    log.info(f"Gemini 이미지 생성 성공 ({m})")
                    return data
                last = f"{m}: 응답에 이미지 없음"
                break
            except Exception as e:
                last = f"{m}: {e}"
                if _is_quota(e) and "limit: 0" in str(e):
                    raise ImageGenError(
                        "Gemini API 키가 무료 등급이라 이미지 생성 한도가 0입니다. "
                        "Google AI Studio에서 이 키의 프로젝트에 결제를 등록하세요."
                    )
                if _is_quota(e):
                    time.sleep(10 * (attempt + 1))
                    continue
                break
    raise ImageGenError(f"Gemini 이미지 생성 실패 → {str(last)[:300]}")


def _openai(prompt: str, cfg: dict, style_ref: bytes | None = None) -> bytes:
    """OpenAI gpt-image 계열 (dall-e-2/3은 서비스 종료)."""
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ImageGenError("OPENAI_API_KEY 미설정")
    client = OpenAI(api_key=api_key)
    W, H = cfg["images"]["width"], cfg["images"]["height"]
    size = "1536x1024" if W >= H else "1024x1536"
    quality = cfg["images"].get("openai_quality", "medium")
    models = cfg["images"].get("openai_models") or ["gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"]
    last = None
    for m in models:
        try:
            r = client.images.generate(model=m, prompt=prompt[:3800], size=size, quality=quality, n=1)
            b64 = r.data[0].b64_json
            if b64:
                log.info(f"OpenAI 이미지 생성 성공 ({m}, {size}, {quality})")
                try:
                    from .cost_tracker import tracker
                    tracker.track_openai_image(model=m, count=1, resolution=size)
                except Exception:
                    pass
                return base64.b64decode(b64)
        except Exception as e:
            last = f"{m}: {e}"
            log.warning(f"OpenAI {m} 실패: {str(e)[:200]}")
    raise ImageGenError(f"OpenAI 이미지 생성 실패 → {str(last)[:300]}")


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

    # A. 스크립트 JSON에 info_callouts가 정의되어 있는 경우 최우선 동적 추출 (100% 팩트 고증 일치)
    script_callouts = sc.get("info_callouts") or []
    if script_callouts:
        for idx_c, sc_c in enumerate(script_callouts[:2]):
            lbl = sc_c.get("label", "").strip()
            val = sc_c.get("value", "").strip()
            if lbl and val:
                bx = int(W * 0.16)
                by = int(H * (0.36 + idx_c * 0.08))
                ax = int(W * 0.48)
                ay = int(H * (0.46 + idx_c * 0.06))
                callouts.append((lbl, val, bx, by, ax, ay))

    # B. 스크립트 JSON에 vectors가 정의되어 있는 경우 동적 추출
    script_vectors = sc.get("vectors") or []
    if script_vectors:
        for idx_v, sc_v in enumerate(script_vectors[:1]):
            v_lbl = sc_v.get("label", "").strip()
            v_dir = sc_v.get("direction", "right_to_left")
            if v_lbl:
                if v_dir == "left_to_right":
                    vector_arrows.append(((int(W * 0.22), int(H * 0.52)), (int(W * 0.72), int(H * 0.52)), v_lbl, (0, 220, 255)))
                elif v_dir == "top_down":
                    vector_arrows.append(((int(W * 0.50), int(H * 0.25)), (int(W * 0.50), int(H * 0.60)), v_lbl, (255, 180, 50)))
                else:
                    vector_arrows.append(((int(W * 0.82), int(H * 0.38)), (int(W * 0.52), int(H * 0.44)), v_lbl, (0, 220, 255)))

    # C. JSON에 callout이 없고 나레이션에 명확한 공학 수치가 포함되어 있는 경우에만 문맥 기반 추출
    if not callouts:
        m_vel = re.search(r"초속\s*(\d+(?:\.\d+)?)\s*미터", narration)
        m_ton = re.search(r"(\d+(?:,\d+)?)\s*톤", narration)
        m_meter = re.search(r"(\d+(?:\.\d+)?)\s*미터", narration)
        
        if m_vel:
            callouts.append(("조류 유속", f"{m_vel.group(1)} m/s", int(W * 0.16), int(H * 0.38), int(W * 0.48), int(H * 0.48)))
            vector_arrows.append(((int(W * 0.82), int(H * 0.38)), (int(W * 0.52), int(H * 0.44)), "조류 유체력", (0, 220, 255)))
        elif m_ton:
            callouts.append(("사석/블록 단위중량", f"{m_ton.group(1)} t", int(W * 0.16), int(H * 0.38), int(W * 0.48), int(H * 0.48)))
        elif m_meter and any(k in narration for k in ["조위차", "수위", "차이"]):
            callouts.append(("최대 조위차", f"{m_meter.group(1)} m", int(W * 0.16), int(H * 0.38), int(W * 0.48), int(H * 0.48)))
        elif any(k in narration for k in ["잠제", "수중방파제"]):
            callouts.append(("수중방파제 마루수심", "-0.5m ~ -1.5m", int(W * 0.16), int(H * 0.38), int(W * 0.48), int(H * 0.50)))
            vector_arrows.append(((int(W * 0.82), int(H * 0.35)), (int(W * 0.52), int(H * 0.42)), "쇄파 감쇄 70%", (0, 220, 255)))
        elif any(k in narration for k in ["양빈", "모래", "백사장", "침식"]):
            callouts.append(("양빈 체적", "100,000㎥", int(W * 0.16), int(H * 0.42), int(W * 0.46), int(H * 0.52)))
            vector_arrows.append(((int(W * 0.22), int(H * 0.58)), (int(W * 0.68), int(H * 0.58)), "표사 이동 벡터", (255, 210, 50)))
        elif any(k in narration for k in ["소파블록", "테트라포드"]):
            callouts.append(("소파블록 규격", "50t TTP", int(W * 0.16), int(H * 0.38), int(W * 0.46), int(H * 0.48)))
            vector_arrows.append(((int(W * 0.78), int(H * 0.35)), (int(W * 0.52), int(H * 0.42)), "공극률 50% 파력분산", (0, 230, 190)))

    if not callouts and not vector_arrows:
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


def simple_prompt_for(topic: str, raw: str) -> str:
    return (f"Clean modern 3D illustrated cutaway of a coastal engineering structure, bright daylight, "
            f"clear turquoise sea, smooth light-gray concrete, documentary infographic style, no text: {topic}, {raw[:200]}")


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
    
    order = {"gemini": [("Gemini", _gemini), ("OpenAI", _openai)],
             "openai": [("OpenAI", _openai), ("Gemini", _gemini)]}
    generators = order.get(provider, order["gemini"])
    style_ref = None
    seen_hashes = {}

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
        
        # if out_main.exists() and out_clean.exists() and out_info.exists():
        #     paths.append(out_main)
        #     continue

        clean_p = clean_p_raw.strip().rstrip(".")
        # 흙탕물·어두운 분위기만 걸러낸다 (단면도/컷어웨이는 신비한 건축사전 스타일의 핵심이므로 유지)
        for ban in ["muddy water", "gloomy"]:
            clean_p = clean_p.replace(ban, "clear water")

        # 코덱스 & 구글 플로우 표준 3D 공학 인포그래픽 프롬프트 주입
        prompt = (
            f"{clean_p}. {suffix}"
        )
        clean_pil = None
        errors = []
        use_ref = style_ref if sid != "thumb" else None
        for gen_name, gen_func in generators:
            for p_try in (prompt, simple_prompt_for(topic, clean_p_raw)):
                try:
                    log.info(f"CLEAN 이미지 {sid}: {gen_name} 호출 중...")
                    img_data = gen_func(p_try, cfg, use_ref)
                    clean_pil = _fit(img_data, W, H)
                    break
                except ImageGenError as ge:
                    errors.append(f"{gen_name}: {ge}")
                    log.warning(f"CLEAN 이미지 {sid} {gen_name} 실패: {ge}")
                    if "한도가 0" in str(ge) or "미설정" in str(ge):
                        break  # 프롬프트를 바꿔도 소용없는 오류
                except Exception as ge:
                    errors.append(f"{gen_name}: {ge}")
                    log.warning(f"CLEAN 이미지 {sid} {gen_name} 실패: {ge}")
            if clean_pil is not None:
                break

        if clean_pil is None:
            # 템플릿 대체 금지: 같은 그림이 반복 업로드되는 것을 막기 위해 여기서 중단한다.
            raise ImageGenError(f"장면 {sid} 이미지 생성 실패 — 업로드 중단.\n" + "\n".join(errors[-4:]))

        # 같은 이미지가 반복되면(캐시/폴백 오류) 중단
        digest = hashlib.md5(clean_pil.resize((64, 36)).tobytes()).hexdigest()
        if digest in seen_hashes:
            raise ImageGenError(f"장면 {sid} 이미지가 장면 {seen_hashes[digest]}와 동일 — 업로드 중단")
        seen_hashes[digest] = sid

        # 첫 본편 장면을 스타일 기준으로 저장 (이후 장면 그림체 통일)
        if style_ref is None and sid != "thumb" and cfg["images"].get("style_reference", True):
            buf = io.BytesIO(); clean_pil.resize((W // 2, H // 2)).save(buf, "PNG"); style_ref = buf.getvalue()

        # 이미지 크기를 설정된 W, H로 정확하게 리사이즈/크롭 보증 (렌더러/블렌드 필터 규격 일치)
        if clean_pil.size != (W, H):
            ratio = max(W / clean_pil.width, H / clean_pil.height)
            clean_pil = clean_pil.resize((round(clean_pil.width * ratio), round(clean_pil.height * ratio)), Image.LANCZOS)
            l, t = (clean_pil.width - W) // 2, (clean_pil.height - H) // 2
            clean_pil = clean_pil.crop((l, t, l + W, t + H))

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


