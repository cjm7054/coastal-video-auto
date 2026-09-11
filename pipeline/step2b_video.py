"""2-1단계: 대본에서 motion=true인 장면만 Veo 3.1 Lite image-to-video로 8초 클립 생성.
정지 이미지를 첫 프레임으로 넣어 장면 일관성을 유지한다. 실패하면 그 장면은 패럴랙스로 대체."""
import os, time
from pathlib import Path
from .common import load_config, log


def generate_motion_clips(script: dict, out_dir: Path) -> dict:
    """{scene_id: mp4 path} 반환"""
    cfg = load_config()
    vcfg = cfg["video_gen"]
    if not vcfg.get("enabled", True):
        return {}
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    (out_dir / "videos").mkdir(exist_ok=True)
    # motion이 명시된 장면 우선, 없으면 시각적 설명이 풍부한 전반부/중반부 장면 선택
    targets = [s for s in script["scenes"] if s.get("motion")]
    if len(targets) < vcfg["max_scenes"]:
        remaining = [s for s in script["scenes"] if s not in targets]
        targets += remaining[: vcfg["max_scenes"] - len(targets)]
    targets = targets[: vcfg["max_scenes"]]
    ar = "9:16" if cfg.get("current_format") == "shorts" else "16:9"
    for sc in targets:
        out = out_dir / "videos" / f"{sc['id']}.mp4"
        if out.exists():
            result[sc["id"]] = out; continue
        clean_img_path = out_dir / "clean" / f"{sc['id']}.png"
        img_path = clean_img_path if clean_img_path.exists() else out_dir / "images" / f"{sc['id']}.png"
        if not img_path.exists():
            continue
        img = types.Image.from_file(location=str(img_path))
        
        # MD Stage 6 규격: CLEAN 시작 프레임에서 자연스러운 카메라 무빙 및 유체 역학 시뮬레이션
        m_prompt = sc.get('motion_prompt') or sc.get('clean_prompt') or sc.get('image_prompt', '')
        prompt = f"Cinematic photorealistic 3D engineering documentary shot, subtle 5-15 degree camera movement, fluid dynamics and wave motion, {m_prompt}. {vcfg.get('style_suffix', '').strip()}"
        try:
            log.info(f"Veo 영상 생성 호출 시도 ({sc['id']}, {ar}, {vcfg['model']}): {prompt[:80]}...")
            # 1. source 객체 전달 방식 시도
            try:
                op = client.models.generate_videos(
                    model=vcfg["model"],
                    source=types.GenerateVideosSource(
                        prompt=prompt,
                        image=img,
                    ),
                    config=types.GenerateVideosConfig(
                        number_of_videos=1,
                        aspect_ratio=ar,
                        duration_seconds=vcfg.get("seconds", 5),
                        enhance_prompt=True,
                    ),
                )
            except Exception as src_err:
                log.info(f"GenerateVideosSource 방식 예외({src_err}) → 직접 인자 전달 시도...")
                op = client.models.generate_videos(
                    model=vcfg["model"],
                    prompt=prompt,
                    image=img,
                    config=types.GenerateVideosConfig(
                        aspect_ratio=ar,
                        duration_seconds=vcfg.get("seconds", 5),
                    ),
                )
            waited = 0
            while not op.done:
                time.sleep(10); waited += 10
                op = client.operations.get(op)
                if waited > 600:
                    raise TimeoutError("Veo 생성 10분 초과")
            vid = op.response.generated_videos[0]
            try:
                client.files.download(file=vid.video, destination=str(out))
            except Exception:
                if getattr(vid.video, "video_bytes", None):
                    out.write_bytes(vid.video.video_bytes)
                elif hasattr(vid.video, "save"):
                    vid.video.save(str(out))
                else:
                    raise
            result[sc["id"]] = out
            log.info(f"Veo 클립 {sc['id']} 생성 및 저장 완료")
        except Exception as e:
            log.error(f"Veo 클립 {sc['id']} 실패 → 패럴랙스로 대체: {e}")
    return result
