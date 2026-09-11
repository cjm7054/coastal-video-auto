"""공통 유틸: 설정 로드, 작업 폴더, 로그"""
import json, re, datetime, logging, yaml
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cva")


_CURRENT_FORMAT = None


def set_active_format(fmt: str):
    global _CURRENT_FORMAT
    _CURRENT_FORMAT = fmt


def load_config(format_override: str | None = None) -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 포맷 결정: 파라미터 전달값 > 전역 지정값 > config.yaml 기본값
    fmt = format_override or _CURRENT_FORMAT or cfg.get("format", "longform")
    formats = cfg.get("formats", {})
    if fmt not in formats:
        fmt = "longform"
    
    cfg["current_format"] = fmt
    f_data = formats.get(fmt, {})

    # 하위 호환성 및 전역 편의를 위해 channel, images, video 등에 병합
    if "channel" not in cfg:
        cfg["channel"] = {}
    cfg["channel"]["target_minutes"] = f_data.get("target_minutes", 3.8)
    cfg["channel"]["scenes"] = f_data.get("scenes", 26)

    if "images" not in cfg:
        cfg["images"] = {}
    cfg["images"]["width"] = f_data.get("width", 1920)
    cfg["images"]["height"] = f_data.get("height", 1080)
    cfg["images"]["aspect_ratio"] = f_data.get("aspect_ratio", "16:9")
    cfg["images"]["dalle_size"] = f_data.get("dalle_size", "1792x1024")

    if "video" not in cfg:
        cfg["video"] = {}
    cfg["video"]["subtitle_font_size"] = f_data.get("subtitle_font_size", 54)
    cfg["video"]["subtitle_margin_v"] = f_data.get("subtitle_margin_v", 110)

    if "thumbnail" not in cfg:
        cfg["thumbnail"] = {}
    cfg["thumbnail"]["size"] = f_data.get("thumbnail_size", [1280, 720])
    cfg["thumbnail"]["font_size"] = f_data.get("thumbnail_font_size", 105)

    return cfg


def slugify(text: str, n: int = 30) -> str:
    """폴더 이름용. FFmpeg 필터 경로 문제를 피하기 위해 영문·숫자·밑줄만 남긴다."""
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text[:n] or "job"


def new_job_dir(topic: str) -> Path:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    d = ROOT / "output" / f"{stamp}_{slugify(topic)}"
    (d / "images").mkdir(parents=True, exist_ok=True)
    (d / "audio").mkdir(exist_ok=True)
    return d


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pop_next_topic():
    """topics.txt 첫 줄을 꺼내 topics_done.txt로 옮긴다."""
    src = ROOT / "topics.txt"
    lines = src.read_text(encoding="utf-8").splitlines()
    remaining, topic = [], None
    for ln in lines:
        s = ln.strip()
        if topic is None and s and not s.startswith("#"):
            topic = s
        else:
            remaining.append(ln)
    if topic is None:
        return None
    src.write_text("\n".join(remaining) + "\n", encoding="utf-8")
    with open(ROOT / "topics_done.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.date.today()}\t{topic}\n")
    return topic
