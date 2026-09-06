"""5단계: 썸네일 (이미지 + 흰 글씨/검은 외곽선 큰 텍스트)"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .common import load_config, ROOT, log


def make_thumbnail(script: dict, out_dir: Path) -> Path:
    cfg = load_config()
    im = Image.open(out_dir / "images" / "thumb.png").convert("RGB").resize((1280, 720), Image.LANCZOS)
    # 하단 살짝 어둡게 → 글씨 가독성
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(360, 720):
        d.line([(0, y), (1280, y)], fill=(0, 0, 0, int((y - 360) / 360 * 140)))
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    font = ImageFont.truetype(str(ROOT / cfg["thumbnail"]["font"]), cfg["thumbnail"]["font_size"])
    d = ImageDraw.Draw(im)
    lines = script["thumbnail_text"].replace("\\n", "\n").split("\n")[:2]
    y = 720 - 40 - len(lines) * (cfg["thumbnail"]["font_size"] + 10)
    for ln in lines:
        d.text((50, y), ln, font=font, fill="white", stroke_width=10, stroke_fill="black")
        y += cfg["thumbnail"]["font_size"] + 10
    out = out_dir / "thumbnail.jpg"
    im.save(out, "JPEG", quality=92)
    log.info("썸네일 완료")
    return out
