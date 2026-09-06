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

    # FFmpeg subtitles 필터는 경로에 콜론(:)이나 백슬래시(\)가 포함될 경우 에러가 나므로
    # 절대경로(posix)로 변환하고 특수문자를 이스케이프한다.
    subs_file = (tmp / "subs.srt").resolve().as_posix()
    subs_escaped = subs_file.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    fonts_dir = tmp.resolve().as_posix().replace("\\", "/").replace(":", r"\:").replace("'", r"\'")

    font_dir = (ROOT / cfg["video"]["subtitle_font"]).resolve().parent
    shutil.copy(out_dir / "subtitles.srt", tmp / "subs.srt")
    if font_dir.exists() and font_dir != tmp:
        for f in font_dir.glob("*"):
            if f.is_file():
                shutil.copy(f, tmp / f.name)
    style = (f"FontName=Noto Sans CJK KR,FontSize={cfg['video']['subtitle_size']//2},Bold=1,"
             f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Shadow=1,Alignment=2,MarginV=60")
    sub = f"subtitles='{subs_escaped}':fontsdir='{fonts_dir}':force_style='{style}'"

    inputs = ["-i", "joined.mp4"]
    fc, vin = [], "[0:v]"
    dust_op = cfg["video"]["dust_opacity"]
    if dust_op > 0:
        render_dust(min(total, 40), W, H, tmp / "dust.mp4", fps=fps)
        inputs += ["-stream_loop", "-1", "-i", "dust.mp4"]
        fc.append(f"[1:v]scale={W}:{H},lutyuv=y='val*{dust_op:.3f}',format=gbrp[d];"
                  f"{vin}format=gbrp[base];[base][d]blend=all_mode=screen:shortest=1,format=yuv420p[vd]")
        vin = "[vd]"
    fc.append(f"{vin}{sub}[vout]")
    bgms = list((ROOT / cfg["video"]["bgm_dir"]).glob("*.mp3"))
    amap = ["-map", "0:a"]
    if bgms:
        chosen = random.choice(bgms)
        shutil.copy(chosen, tmp / chosen.name)
        idx = 2 if dust_op > 0 else 1
        inputs += ["-stream_loop", "-1", "-i", chosen.name]
        fc.append(f"[{idx}:a]volume={cfg['video']['bgm_volume']}[b];[0:a][b]amix=inputs=2:duration=first:dropout_transition=2[aout]")
        amap = ["-map", "[aout]"]
    r = subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]", *amap,
          "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac",
          "-movflags", "+faststart", "final.mp4"], cwd=str(tmp), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    final = out_dir / "final.mp4"
    shutil.move(str(tmp / "final.mp4"), str(final))
    shutil.rmtree(tmp, ignore_errors=True)
    log.info(f"영상 완료: {final}")
    return final
