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
    targets = [s for s in script["scenes"] if s.get("motion")][: vcfg["max_scenes"]]
    result = {}
    for sc in targets:
        out = out_dir / "videos" / f"{sc['id']}.mp4"
        if out.exists():
            result[sc["id"]] = out; continue
        img = types.Image.from_file(location=str(out_dir / "images" / f"{sc['id']}.png"))
        prompt = f"{sc.get('motion_prompt') or sc['image_prompt']}. {vcfg['style_suffix'].strip()}"
        try:
            op = client.models.generate_videos(
                model=vcfg["model"], prompt=prompt, image=img,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9", resolution=vcfg["resolution"],
                    duration_seconds=str(vcfg["seconds"]), person_generation="allow_adult"),
            )
            waited = 0
            while not op.done:
                time.sleep(10); waited += 10
                op = client.operations.get(op)
                if waited > 600:
                    raise TimeoutError("Veo 생성 10분 초과")
            vid = op.response.generated_videos[0]
            client.files.download(file=vid.video)
            vid.video.save(str(out))
            result[sc["id"]] = out
            log.info(f"Veo 클립 {sc['id']} 완료")
        except Exception as e:
            log.error(f"Veo 클립 {sc['id']} 실패 → 패럴랙스로 대체: {e}")
    return result
