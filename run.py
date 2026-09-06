"""전체 파이프라인 실행.
  python run.py                      → topics.txt 첫 주제로 영상 생성+업로드
  python run.py --topic "주제"       → 지정 주제
  python run.py --no-upload          → 업로드 생략 (검토용)
  python run.py --resume output/폴더 → 중단된 작업 이어서
"""
import argparse, sys, traceback
from pathlib import Path
from pipeline.common import load_json, save_json, new_job_dir, pop_next_topic, log, ROOT
from pipeline.step1_script import generate_script
from pipeline.step2_images import generate_images
from pipeline.step2b_video import generate_motion_clips
from pipeline.step3_tts import generate_audio
from pipeline.step4_assemble import assemble
from pipeline.step5_thumbnail import make_thumbnail
from pipeline.step6_upload import upload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic"); ap.add_argument("--resume"); ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args()

    if a.resume:
        job = Path(a.resume); script = load_json(job / "script.json")
    else:
        topic = a.topic or pop_next_topic()
        if not topic:
            log.error("topics.txt에 남은 주제가 없습니다"); sys.exit(1)
        job = new_job_dir(topic)
        script = generate_script(topic, job)

    generate_images(script, job)
    motion_clips = generate_motion_clips(script, job)
    tl_path = job / "timeline.json"
    timeline = load_json(tl_path) if tl_path.exists() else generate_audio(script, job)
    save_json(tl_path, timeline)
    video = job / "final.mp4"
    if not video.exists():
        video = assemble(script, timeline, job, motion_clips)
    thumb = make_thumbnail(script, job)

    if a.no_upload:
        log.info(f"검토용 완료 → {job}"); return
    url = upload(script, video, thumb)
    with open(ROOT / "uploaded.log", "a", encoding="utf-8") as f:
        f.write(f"{job.name}\t{script['title']}\t{url}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc(); sys.exit(1)
