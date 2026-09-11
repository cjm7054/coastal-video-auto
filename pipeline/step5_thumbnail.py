"""5단계: 썸네일 (이미지 + 흰 글씨/검은 외곽선 큰 텍스트)"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .common import load_config, ROOT, log


def make_thumbnail(script: dict, out_dir: Path) -> Path:
    cfg = load_config()
    t_w, t_h = cfg["thumbnail"].get("size", [1280, 720])
    im = Image.open(out_dir / "images" / "thumb.png").convert("RGB").resize((t_w, t_h), Image.LANCZOS)
    
    # 하단 살짝 어둡게 → 글씨 가독성
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    start_y = int(t_h * 0.55)
    for y in range(start_y, t_h):
        alpha = int((y - start_y) / (t_h - start_y) * 160)
        d.line([(0, y), (t_w, y)], fill=(0, 0, 0, alpha))
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    
    font_size = cfg["thumbnail"].get("font_size", 105)
    font = ImageFont.truetype(str(ROOT / cfg["thumbnail"]["font"]), font_size)
    d = ImageDraw.Draw(im)
    lines = script["thumbnail_text"].replace("\\n", "\n").split("\n")[:2]
    
    # 신비한 건축사전 시그니처: 가독성 높은 그라데이션 및 선명한 텍스트
    y_pos = int(t_h * 0.72) if len(lines) == 1 else int(t_h * 0.65)
    x_pos = int(t_w * 0.06)
    for i, ln in enumerate(lines):
        color = "#FF2A2A" if i == 0 else "white"
        d.text((x_pos, y_pos), ln.strip(), font=font, fill=color, stroke_width=8, stroke_fill="black")
        y_pos += font_size + 20
    out = out_dir / "thumbnail.jpg"
    im.save(out, "JPEG", quality=95)
    log.info(f"썸네일 완료 ({t_w}x{t_h})")
    return out
