"""공통 유틸: 설정 로드, 작업 폴더, 로그"""
import json, re, datetime, logging, yaml
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cva")


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
