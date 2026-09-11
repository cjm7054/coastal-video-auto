"""전체 파이프라인 실행.
  python run.py                      → topics.txt 첫 주제로 영상 생성+업로드
  python run.py --topic "주제"       → 지정 주제
  python run.py --no-upload          → 업로드 생략 (검토용)
  python run.py --resume output/폴더 → 중단된 작업 이어서
"""
import argparse, sys, traceback
from pathlib import Path
from pipeline.common import load_json, save_json, new_job_dir, pop_next_topic, log, ROOT, set_active_format, load_config
from pipeline.step1_script import generate_script
from pipeline.step2_images import generate_images
from pipeline.step2b_video import generate_motion_clips
from pipeline.step3_tts import generate_audio
from pipeline.step4_assemble import assemble
from pipeline.step5_thumbnail import make_thumbnail
from pipeline.step6_upload import upload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["longform", "shorts"], help="영상 포맷 선택: longform(16:9 롱폼) 또는 shorts(9:16 쇼츠)")
    ap.add_argument("--topic")
    ap.add_argument("--resume")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--step", choices=["all", "script", "visual", "audio", "assemble", "thumbnail", "upload"], default="all")
    ap.add_argument("--job-dir")
    a = ap.parse_args()

    # 포맷 선택: CLI 인자가 없으면 터미널에서 대화형으로 롱폼/쇼츠 선택
    if a.format:
        set_active_format(a.format)
    elif not a.job_dir and not a.resume:
        print("\n" + "=" * 60)
        print("🎬 [OCEAN CODE LAB] 영상 제작 포맷을 선택하세요:")
        print("  1) 쇼츠   (9:16 세로형 쇼츠, 약 50초, 8장면) [기본값]")
        print("  2) 롱폼   (16:9 가로형 다큐, 약 3.8분, 26장면)")
        print("=" * 60)
        try:
            choice = input("선택 번호를 입력하세요 (1 또는 2, 엔터시 1): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"
        chosen_fmt = "longform" if choice == "2" else "shorts"
        set_active_format(chosen_fmt)
        log.info(f"선택된 영상 포맷: {'롱폼 (16:9 다큐)' if chosen_fmt == 'longform' else '쇼츠 (9:16 세로)'}")

    if a.job_dir:
        job = Path(a.job_dir)
        script = load_json(job / "script.json") if (job / "script.json").exists() else None
        if script and "format" in script and not a.format:
            set_active_format(script["format"])
    elif a.resume:
        job = Path(a.resume)
        script = load_json(job / "script.json")
        if script and "format" in script and not a.format:
            set_active_format(script["format"])
    else:
        topic = a.topic or pop_next_topic()
        if not topic:
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
        script = None

    # Step 1: Script (기획 & 대본 에이전트)
    if a.step in ["all", "script"]:
        if script is None:
            script = generate_script(topic if 'topic' in locals() and topic else "해양 토목 공학", job)
        if a.step == "script":
            print(f"JOB_DIR={job.resolve()}")
            return

    # Step 2: Visual Studio Agent (이미지 및 비디오 생성)
    if a.step in ["all", "visual"]:
        generate_images(script, job)
        motion_clips = generate_motion_clips(script, job)
        if a.step == "visual":
            return

    # Step 3: Audio Master Agent (타입캐스트 모건 보이스 합성)
    if a.step in ["all", "audio"]:
        tl_path = job / "timeline.json"
        timeline = load_json(tl_path) if tl_path.exists() else generate_audio(script, job)
        save_json(tl_path, timeline)
        if a.step == "audio":
            return

    # Step 4: Video Editor Agent (최종 렌더링 & 믹싱)
    if a.step in ["all", "assemble"]:
        tl_path = job / "timeline.json"
        timeline = load_json(tl_path) if tl_path.exists() else generate_audio(script, job)
        motion_clips = generate_motion_clips(script, job)
        video = job / "final.mp4"
        if not video.exists():
            video = assemble(script, timeline, job, motion_clips)
        thumb = make_thumbnail(script, job)
        if a.step == "assemble":
            return

    # Step 5: Thumbnail Agent
    if a.step in ["all", "thumbnail"]:
        thumb = make_thumbnail(script, job)
        if a.step == "thumbnail":
            return

    # Step 6: Publisher Agent (유튜브 업로드)
    video = job / "final.mp4"
    thumb = job / "thumbnail.jpg"

    try:
        from pipeline.cost_tracker import tracker
        tracker.save_and_brief(job)
    except Exception as te:
        log.warning(f"크레딧 결산 기록 실패: {te}")

    if a.no_upload or a.step != "all":
        log.info(f"작업 완료 → {job}")
        return
    url = upload(script, video, thumb)
    with open(ROOT / "uploaded.log", "a", encoding="utf-8") as f:
        f.write(f"{job.name}\t{script['title']}\t{url}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc(); sys.exit(1)
