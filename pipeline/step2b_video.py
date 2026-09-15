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
    try:
        from google import genai
        from google.genai import types
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            log.warning("GEMINI_API_KEY 미설정 → 고화질 3D 패럴랙스 렌더로 자동 대체")
            return {}
        client = genai.Client(api_key=api_key)
    except Exception as ge:
        log.warning(f"Google GenAI SDK 로드 불가({ge}) → 고화질 3D 패럴랙스 렌더로 자동 대체")
        return {}
    (out_dir / "videos").mkdir(exist_ok=True)
    # motion이 명시된 장면 우선, 없으면 시각적 설명이 풍부한 전반부/중반부 장면 선택
    targets = [s for s in script["scenes"] if s.get("motion")]
    if len(targets) < vcfg["max_scenes"]:
        remaining = [s for s in script["scenes"] if s not in targets]
        targets += remaining[: vcfg["max_scenes"] - len(targets)]
    targets = targets[: vcfg["max_scenes"]]
    ar = "9:16" if cfg.get("current_format") == "shorts" else "16:9"
    result = {}
    video_models = [vcfg.get("model", "gemini-omni-1.1-flash"), "veo-3.1-generate-preview", "veo-2.0-generate-001"]
    
    for sc in targets:
        out = out_dir / "videos" / f"{sc['id']}.mp4"
        if out.exists():
            result[sc["id"]] = out
            continue
        clean_img_path = out_dir / "clean" / f"{sc['id']}.png"
        img_path = clean_img_path if clean_img_path.exists() else out_dir / "images" / f"{sc['id']}.png"
        if not img_path.exists():
            continue
        img = types.Image.from_file(location=str(img_path))
        
        # 코덱스 & 구글 플로우 규격: 밝은 3D 공학 시뮬레이션 및 부드러운 카메라 워킹
        m_prompt = sc.get('motion_prompt') or sc.get('clean_prompt') or sc.get('image_prompt', '')
        prompt = (
            f"Ultra-bright modern 3D engineering documentary shot, crystal clear sparkling water, "
            f"subtle 5-15 degree camera movement, fluid dynamics and wave motion, {m_prompt}. "
            f"{vcfg.get('style_suffix', '').strip()}"
        )
        
        clip_created = False
        for vm in video_models:
            try:
                log.info(f"Google Video/Flow 생성 호출 시도 ({sc['id']}, {ar}, {vm}): {prompt[:80]}...")
                try:
                    op = client.models.generate_videos(
                        model=vm,
                        source=types.GenerateVideosSource(
                            prompt=prompt,
                            image=img,
                        ),
                        config=types.GenerateVideosConfig(
                            number_of_videos=1,
                            aspect_ratio=ar,
                            duration_seconds=vcfg.get("seconds", 4),
                            enhance_prompt=True,
                        ),
                    )
                except Exception as src_err:
                    op = client.models.generate_videos(
                        model=vm,
                        prompt=prompt,
                        image=img,
                        config=types.GenerateVideosConfig(
                            aspect_ratio=ar,
                            duration_seconds=vcfg.get("seconds", 4),
                        ),
                    )
                waited = 0
                while not op.done:
                    time.sleep(8); waited += 8
                    op = client.operations.get(op)
                    if waited > 300:
                        raise TimeoutError("영상 생성 시간 초과")
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
                log.info(f"비디오 클립 {sc['id']} 생성 성공 ({vm})")
                clip_created = True
                break
            except Exception as e:
                log.warning(f"모델 {vm} 클립 {sc['id']} 생성 실패 ({e}) → 다음 모델 시도")
                
        if not clip_created:
            log.info(f"장면 {sc['id']}: AI 비디오 생성 패스 → 고화질 3D 패럴랙스 렌더로 대체")
    return result
