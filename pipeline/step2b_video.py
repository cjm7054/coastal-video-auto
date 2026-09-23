"""2-1단계: 대본에서 motion=true인 장면만 Seedance 2.5 (30s) 비디오 생성.
정지 이미지를 레퍼런스로 넣어 장면 일관성을 유지하며 30초 롱테이크를 생성합니다.
(Antigravity CLI `agy`를 통해 시스템 내장 도구를 호출합니다)"""
import os, time, subprocess
from pathlib import Path
from .common import load_config, log


def generate_motion_clips(script: dict, out_dir: Path) -> dict:
    """{scene_id: mp4 path} 반환"""
    cfg = load_config()
    vcfg = cfg["video_gen"]
    if not vcfg.get("enabled", True):
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
    
    for sc in targets:
        out = out_dir / "videos" / f"{sc['id']}.mp4"
        if out.exists():
             result[sc["id"]] = out
             continue
             
        clean_img_path = out_dir / "clean" / f"{sc['id']}.png"
        img_path = clean_img_path if clean_img_path.exists() else out_dir / "images" / f"{sc['id']}.png"
        
        if not img_path.exists():
            log.warning(f"장면 {sc['id']}: 레퍼런스 이미지가 없어 비디오 생성을 건너뜁니다.")
            continue
            
        m_prompt = sc.get('motion_prompt') or sc.get('clean_prompt') or sc.get('image_prompt', '')
        prompt = (
            f"Ultra-bright modern 3D engineering documentary shot, crystal clear sparkling water, "
            f"subtle 5-15 degree camera movement, fluid dynamics and wave motion, {m_prompt}. "
            f"{vcfg.get('style_suffix', '').strip()}"
        )
        
        log.info(f"Seedance 2.5 30s 영상 생성 요청 ({sc['id']}): {prompt[:80]}...")
        
        # Antigravity CLI를 통해 seedane-2.5-30s 스킬 호출
        # -f 로 이미지 레퍼런스를 첨부하고, 프롬프트에 저장 위치를 명시하여 에이전트가 해당 경로로 파일을 옮기도록 지시합니다.
        # 비율(ar)과 30초 시간(30s)을 명시합니다.
        cmd = [
            "agy", "do",
            f"seedance 30s. Ratio: {ar}. Motion prompt: {prompt}. IMPORTANT: You MUST save the generated video exactly to this absolute path: {out.resolve()}",
            "-f", str(img_path.resolve())
        ]
        
        try:
            # agy 프로세스를 실행하고 끝날 때까지 대기합니다. 
            # 비디오 생성이 30초 분량이므로 수 분이 소요될 수 있습니다.
            subprocess.run(cmd, check=True)
            
            if out.exists():
                result[sc["id"]] = out
                log.info(f"비디오 클립 {sc['id']} 생성 성공 (Seedance 2.5 30s)")
            else:
                log.warning(f"명령어는 성공했으나 {out.name} 파일이 생성되지 않았습니다.")
        except subprocess.CalledProcessError as e:
            log.warning(f"Seedance 2.5 클립 {sc['id']} 생성 실패 ({e}) → 고화질 3D 패럴랙스 렌더로 대체")
                
    return result
