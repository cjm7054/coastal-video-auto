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
            render_parallax(last, dur - cd, tail, fps=fps, mode=i % 4, strength=strength)
            _concat([clip, tail], silent)
        log.info(f"장면 {sid}: Veo {cd:.1f}s + 패럴랙스 {max(dur-cd,0):.1f}s")
    else:
        render_parallax(img, dur, silent, fps=fps, mode=i % 4, strength=strength)
        log.info(f"장면 {sid}: 패럴랙스 {dur:.1f}s")
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

    # 자막 파일 준비: SRT → ASS 변환 (스타일 및 폰트 호환성 극대화)
    # 신비한 건축사전식: 굵은 노란색 본문 + 굵은 검은색 외곽선(Outline=4) + 명확한 여백
    subs_srt = out_dir / "subtitles.srt"
    subs_ass = tmp / "subs.ass"
    
    # ffmpeg를 통해 srt를 ass로 변환
    subprocess.run(["ffmpeg", "-y", "-i", str(subs_srt), str(subs_ass)], cwd=str(tmp), capture_output=True)
    
    # ASS 파일에 신비한 건축사전 전용 스타일 강제 주입
    if subs_ass.exists():
        ass_content = subs_ass.read_text(encoding="utf-8")
        # Style 정의 교체
        custom_style = (
            "Style: Default,Noto Sans CJK KR,28,&H0000FFFF,&H000000FF,&H00000000,&H80000000,"
            "-1,0,0,0,100,100,0,0,1,4,2,2,30,30,60,1"
        )
        if "Style: Default" in ass_content:
            lines = []
            for line in ass_content.splitlines():
                if line.startswith("Style: Default"):
                    lines.append(custom_style)
                else:
                    lines.append(line)
            subs_ass.write_text("\n".join(lines), encoding="utf-8")
        sub_filter = "ass=subs.ass"
    else:
        # Fallback srt
        shutil.copy(subs_srt, tmp / "subs.srt")
        style = (f"FontName=Noto Sans CJK KR,FontSize={cfg['video']['subtitle_size']//2},Bold=1,"
                 f"PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,Outline=4,Shadow=2,Alignment=2,MarginV=65")
        sub_filter = f"subtitles=subs.srt:force_style='{style}'"

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

    # 1차 시도: ASS 또는 SRT 자막 포함 렌더링
    fc_with_sub = fc + [f"{vin}{sub_filter}[vout]"]
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc_with_sub), "-map", "[vout]", *amap,
           "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-movflags", "+faststart", "final.mp4"]
    r = subprocess.run(cmd, cwd=str(tmp), capture_output=True, text=True)

    # 2차 시도: 혹시 필터 이름이나 폰트 매핑 실패 시 subtitles 기본 필터로 재시도
    if r.returncode != 0:
        log.warning(f"1차 자막 필터 에러 ({r.stderr[-250:].strip()}) → srt 기본 필터로 재시도")
        shutil.copy(subs_srt, tmp / "subs.srt")
        fc_sub2 = fc + [f"{vin}subtitles=subs.srt[vout]"]
        cmd_sub2 = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc_sub2), "-map", "[vout]", *amap,
                    "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-movflags", "+faststart", "final.mp4"]
        r = subprocess.run(cmd_sub2, cwd=str(tmp), capture_output=True, text=True)

    # 3차 비상: 자막 실패 시에도 영상은 유지
    if r.returncode != 0:
        log.warning(f"자막 필터 전체 실패 ({r.stderr[-200:].strip()}) → 기본 영상으로 폴백")
        fc_no_sub = fc + [f"{vin}copy[vout]"] if vin != "[0:v]" else fc
        vout_map = "[vout]" if vin != "[0:v]" else "0:v"
        cmd2 = ["ffmpeg", "-y", *inputs]
        if fc_no_sub:
            cmd2 += ["-filter_complex", ";".join(fc_no_sub)]
        cmd2 += ["-map", vout_map, *amap, "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium",
                 "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", "final.mp4"]
        r2 = subprocess.run(cmd2, cwd=str(tmp), capture_output=True, text=True)
        if r2.returncode != 0:
            raise RuntimeError(r2.stderr[-3000:])

    final = out_dir / "final.mp4"
    shutil.move(str(tmp / "final.mp4"), str(final))
    shutil.rmtree(tmp, ignore_errors=True)
    log.info(f"영상 완료: {final}")
    return final
