"""4단계: 장면 클립 제작 → 연결 → 자막·파티클·BGM 합성.
- motion 장면: Veo 클립(감속 재생) + 클립 마지막 프레임을 이어받은 패럴랙스로 나머지 시간을 채움
- 일반 장면: 정지 이미지 → 2.5D 패럴랙스 (장면마다 카메라 이동 방향을 바꿔 지루함 방지)"""
import subprocess, random, shutil, json
from pathlib import Path
from .common import load_config, ROOT, log
from .parallax import render_parallax, render_dust


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])


def _dur(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
                         capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def _fit_video(src: Path, out: Path, W, H, fps, slow: float):
    """Veo 클립 → 무음, 감속, 해상도 맞춤"""
    _run(["ffmpeg", "-y", "-i", str(src), "-an",
          "-vf", f"setpts={1/slow:.4f}*PTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},format=yuv420p",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out)])


def _last_frame(video: Path, out: Path):
    _run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(video), "-frames:v", "1", "-update", "1", str(out)])


def _mux_audio(video: Path, mp3: Path, dur: float, out: Path):
    _run(["ffmpeg", "-y", "-i", str(video), "-i", str(mp3), "-t", f"{dur:.3f}", "-af", "apad", "-shortest",
          "-c:v", "copy", "-c:a", "aac", "-ar", "44100", str(out)])


def _concat(parts, out: Path):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])


def build_scene(i: int, sc: dict, out_dir: Path, tmp: Path, motion_clips: dict, cfg) -> Path:
    W, H, fps = cfg["images"]["width"], cfg["images"]["height"], cfg["video"]["fps"]
    strength = cfg["video"]["parallax_strength"]
    sid, dur = sc["id"], sc["duration"]
    img = out_dir / "images" / f"{sid}.png"
    silent = tmp / f"{sid}_v.mp4"
    if sid in motion_clips:
        clip = tmp / f"{sid}_veo.mp4"
        _fit_video(motion_clips[sid], clip, W, H, fps, cfg["video_gen"]["slow_factor"])
        cd = _dur(clip)
        if cd >= dur:
            _run(["ffmpeg", "-y", "-i", str(clip), "-t", f"{dur:.3f}", "-c", "copy", str(silent)])
        else:
            last = tmp / f"{sid}_last.png"; _last_frame(clip, last)
            tail = tmp / f"{sid}_tail.mp4"
            render_parallax(last, dur - cd, tail, fps=fps, mode=i % 6, strength=strength)
            _concat([clip, tail], silent)
        log.info(f"장면 {sid}: Veo {cd:.1f}s + 패럴랙스 {max(dur-cd,0):.1f}s")
    else:
        render_parallax(img, dur, silent, fps=fps, mode=i % 6, strength=strength)
        log.info(f"장면 {sid}: 3D 시네마틱 무빙 {dur:.1f}s (모드 {i % 6})")
    final = tmp / f"{sid}.mp4"
    _mux_audio(silent, Path(sc["mp3"]), dur, final)
    return final


def assemble(script: dict, timeline: dict, out_dir: Path, motion_clips: dict | None = None) -> Path:
    cfg = load_config()
    motion_clips = motion_clips or {}
    W, H, fps = cfg["images"]["width"], cfg["images"]["height"], cfg["video"]["fps"]
    tmp = out_dir / "clips"; tmp.mkdir(exist_ok=True)
    parts = []
    for i, sc in enumerate(timeline["scenes"]):
        clip = tmp / f"{sc['id']}.mp4"
        if not clip.exists():
            build_scene(i, sc, out_dir, tmp, motion_clips, cfg)
        parts.append(clip)
    joined = tmp / "joined.mp4"
    _concat(parts, joined)
    total = _dur(joined)

    # 자막 파일 준비: ASS 자막 직접 생성 (신비한 건축사전 스타일: 굵은 노란색 본문 + 굵은 검은색 외곽선 5px + 하단 중앙 배치)
    subs_srt = out_dir / "subtitles.srt"
    subs_ass = tmp / "subs.ass"
    sub_filter = None

    if subs_srt.exists():
        import re
        content = subs_srt.read_text(encoding="utf-8")
        blocks = re.split(r"\n\s*\n", content.strip())
        
        # Windows와 Linux 모두에서 한글 자막이 절대 깨지지 않도록 시스템 기본 고딕 및 로컬 폰트 지정
        sub_fsize = cfg["video"].get("subtitle_font_size", 54)
        sub_margin_v = cfg["video"].get("subtitle_margin_v", 110)
        
        ass_header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {W}\n"
            f"PlayResY: {H}\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,맑은 고딕,{sub_fsize},&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,{sub_margin_v},1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        events = []
        for block in blocks:
            lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
            if len(lines) >= 3 and "-->" in lines[1]:
                m = re.match(r"(\d+:\d+:\d+),(\d+)\s*-->\s*(\d+:\d+:\d+),(\d+)", lines[1])
                if m:
                    s_hms, s_ms, e_hms, e_ms = m.groups()
                    s_ass = f"{int(s_hms.split(':')[0])}:{s_hms.split(':')[1]}:{s_hms.split(':')[2]}.{int(s_ms)//10:02d}"
                    e_ass = f"{int(e_hms.split(':')[0])}:{e_hms.split(':')[1]}:{e_hms.split(':')[2]}.{int(e_ms)//10:02d}"
                    text = "\\N".join(lines[2:])
                    events.append(f"Dialogue: 0,{s_ass},{e_ass},Default,,0,0,0,,{text}")
        
        subs_ass.write_text(ass_header + "\n".join(events) + "\n", encoding="utf-8-sig")
        
        local_font = ROOT / cfg["video"].get("subtitle_font", "assets/fonts/NotoSansCJK-Bold.ttc")
        if local_font.exists():
            shutil.copy(local_font, tmp / "font.ttc")
        
        # ass 필터 및 폰트 디렉토리 안전 참조
        sub_filter = "ass=subs.ass:fontsdir=."

    inputs = ["-i", "joined.mp4"]
    fc, vin = [], "[0:v]"
    dust_op = cfg["video"]["dust_opacity"]
    if dust_op > 0:
        render_dust(min(total, 40), W, H, tmp / "dust.mp4", fps=fps)
        inputs += ["-stream_loop", "-1", "-i", "dust.mp4"]
        fc.append(f"[1:v]scale={W}:{H},lutyuv=y='val*{dust_op:.3f}',format=gbrp[d];"
                  f"{vin}format=gbrp[base];[base][d]blend=all_mode=screen:shortest=1,format=yuv420p[vd]")
        vin = "[vd]"
    bgms = list((ROOT / cfg["video"]["bgm_dir"]).glob("*.mp3"))
    amap = ["-map", "0:a"]
    if bgms:
        chosen = random.choice(bgms)
        shutil.copy(chosen, tmp / chosen.name)
        idx = 2 if dust_op > 0 else 1
        inputs += ["-stream_loop", "-1", "-i", chosen.name]
        fc.append(f"[{idx}:a]volume={cfg['video']['bgm_volume']}[b];[0:a][b]amix=inputs=2:duration=first:dropout_transition=2[aout]")
        amap = ["-map", "[aout]"]

    # 1차 시도: ASS 자막 합성 렌더링
    fc_with_sub = fc + [f"{vin}{sub_filter}[vout]"] if sub_filter else fc
    vout_map = "[vout]" if sub_filter else (vin if vin != "[0:v]" else "0:v")
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc_with_sub), "-map", vout_map, *amap,
           "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-movflags", "+faststart", "final.mp4"]
    r = subprocess.run(cmd, cwd=str(tmp), capture_output=True, text=True)

    # 2차 시도: 혹시 ASS 필터 문제 발생 시 SRT 기본 필터로 재시도 (맑은 고딕 / NotoSans fallback)
    if r.returncode != 0 and subs_srt.exists():
        log.warning(f"1차 ASS 렌더링 실패 ({r.stderr[-200:].strip()}) → SRT 자막으로 재시도")
        shutil.copy(subs_srt, tmp / "subs.srt")
        fc_srt = fc + [f"{vin}subtitles=subs.srt:force_style='FontName=맑은 고딕,FontSize=28,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3'[vout]"]
        cmd_retry = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc_srt), "-map", "[vout]", *amap,
                     "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-movflags", "+faststart", "final.mp4"]
        r = subprocess.run(cmd_retry, cwd=str(tmp), capture_output=True, text=True)

    # 3차 비상: 자막 실패 시에도 무결한 영상은 보존
    if r.returncode != 0:
        log.warning(f"자막 필터 실패 ({r.stderr[-200:].strip()}) → 자막 제외 영상 생성")
        fc_nosub = fc + [f"{vin}copy[vout]"] if vin != "[0:v]" else fc
        vmap = "[vout]" if vin != "[0:v]" else "0:v"
        cmd_nosub = ["ffmpeg", "-y", *inputs]
        if fc_nosub:
            cmd_nosub += ["-filter_complex", ";".join(fc_nosub)]
        cmd_nosub += ["-map", vmap, *amap, "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium",
                      "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", "final.mp4"]
        r_nosub = subprocess.run(cmd_nosub, cwd=str(tmp), capture_output=True, text=True)
        if r_nosub.returncode != 0:
            raise RuntimeError(f"최종 렌더링 실패: {r_nosub.stderr[-2000:]}")

    final = out_dir / "final.mp4"
    shutil.move(str(tmp / "final.mp4"), str(final))
    shutil.rmtree(tmp, ignore_errors=True)
    log.info(f"영상 완료: {final}")
    return final
