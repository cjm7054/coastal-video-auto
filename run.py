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
            # [Ruflo Autonomous Topic Generator] topics.txt가 비어있어도 절대 중단되지 않고 대한민국 항만 토목 공학 주제를 자동 발굴
            log.info("topics.txt가 비어있어, AI 총괄 기획 에이전트가 최신 해양 토목 공학 주제를 자동 발굴합니다...")
            try:
                import os
                from openai import OpenAI
                openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
                if openai_key:
                    o_client = OpenAI(api_key=openai_key)
                    t_resp = o_client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[{
                            "role": "user",
                            "content": "대한민국 해양·항만 토목공학 다큐멘터리 'OCEAN CODE LAB'에 어울리는 압도적 스케일의 케이슨, 방파제, 조석간만, 수리역학, 소파블록 공법 주제를 단 한 줄의 매력적인 한글 제목으로 추천해줘 (따옴표나 부가설명 없이 제목만)."
                        }],
                        temperature=0.7,
                    )
                    topic = t_resp.choices[0].message.content.strip().replace('"', '')
            except Exception as te:
                log.warning(f"자동 주제 발굴 실패: {te}")
            
            if not topic:
                topic = "울릉도 사동항 50m 초심해 케이슨과 극한의 너울성 파도 극복 기술"
            log.info(f"선정된 자동 발굴 주제: {topic}")
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

    # [★ 비용 및 크레딧 결산 브리핑 - 깃허브 Actions Step Summary 및 로그 자동 기록]
    try:
        from pipeline.cost_tracker import tracker
        tracker.save_and_brief(job)
    except Exception as te:
        log.warning(f"크레딧 결산 기록 실패: {te}")

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
