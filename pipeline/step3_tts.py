"""3단계: 장면별 나레이션 → mp3 + 단어 타임스탬프 → SRT 자막.
edge-tts(무료)는 WordBoundary 이벤트로 타임스탬프를 제공."""
import asyncio, os, re
from pathlib import Path
from .common import load_config, log


def _fmt(t: float) -> str:
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s - int(s)) * 1000):03}"


async def _edge_one(text: str, mp3: Path, voice: str, rate: str):
    import edge_tts
    tts = edge_tts.Communicate(text, voice, rate=rate)
    words = []
    with open(mp3, "wb") as f:
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append((chunk["offset"] / 1e7, (chunk["offset"] + chunk["duration"]) / 1e7, chunk["text"]))
    return words


def _elevenlabs_one(text: str, mp3: Path, cfg: dict):
    import base64
    from elevenlabs.client import ElevenLabs
    c = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    r = c.text_to_speech.convert_with_timestamps(
        voice_id=cfg["tts"]["elevenlabs_voice_id"], text=text, model_id=cfg["tts"]["elevenlabs_model"])
    mp3.write_bytes(base64.b64decode(r.audio_base_64))
    al = r.alignment
    # 문자 단위 → 공백 기준 단어로 묶기
    words, cur, st = [], "", None
    for ch, s, e in zip(al.characters, al.character_start_times_seconds, al.character_end_times_seconds):
        if ch == " ":
            if cur: words.append((st, e, cur)); cur, st = "", None
        else:
            if st is None: st = s
            cur += ch
    if cur: words.append((st, al.character_end_times_seconds[-1], cur))
    return words


def _mp3_duration(mp3: Path) -> float:
    import subprocess, json
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(mp3)],
                         capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def _words_to_cues(words, max_chars=22):
    """단어 타임스탬프를 자막 줄(약 22자)로 묶는다."""
    cues, buf, st = [], [], None
    for s, e, w in words:
        if st is None: st = s
        if buf and len(" ".join(buf + [w])) > max_chars:
            cues.append((st, s, " ".join(buf))); buf, st = [], s
        buf.append(w)
        last_e = e
    if buf: cues.append((st, last_e, " ".join(buf)))
    return cues


def _typecast_one(text: str, mp3: Path, cfg: dict):
    """Typecast AI 공식 REST API를 통한 유료 '모건' 보이스 합성"""
    import requests
    api_key = os.environ.get("TYPECAST_API_KEY", "").strip()
    voice_id = os.environ.get("TYPECAST_VOICE_ID", "").strip() or cfg["tts"].get("typecast_voice_id", "tc_6256118ea1103af69f0a87ec")
    model = cfg["tts"].get("typecast_model", "ssfm-v30")
    tempo = cfg["tts"].get("typecast_tempo", 1.05)

    if not api_key:
        raise ValueError("TYPECAST_API_KEY가 설정되지 않았습니다.")

    url = "https://api.typecast.ai/v1/text-to-speech"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    payload = {
        "voice_id": voice_id,
        "text": text,
        "model": model,
        "language": "kor",
        "output": {
            "volume": 100,
            "audio_pitch": 0,
            "audio_tempo": tempo,
            "audio_format": "mp3"
        }
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Typecast API 호출 실패 ({resp.status_code}): {resp.text}")

    mp3.write_bytes(resp.content)
    
    # 균등 타임스탬프 계산 (단어 단위 자막 생성용)
    total_dur = _mp3_duration(mp3)
    raw_words = text.split()
    words = []
    if raw_words:
        per_word = total_dur / len(raw_words)
        for i, w in enumerate(raw_words):
            words.append((i * per_word, (i + 1) * per_word, w))
    return words


def generate_audio(script: dict, out_dir: Path) -> dict:
    cfg = load_config()
    prov = cfg["tts"].get("provider", "typecast")
    timeline, t0, srt_lines, idx = [], 0.0, [], 1
    for sc in script["scenes"]:
        mp3 = out_dir / "audio" / f"{sc['id']}.mp3"
        text = sc["narration"]
        words = None
        
        if prov == "typecast":
            try:
                log.info(f"타입캐스트 모건 보이스 합성 중: 장면 {sc['id']}...")
                words = _typecast_one(text, mp3, cfg)
            except Exception as te:
                log.warning(f"타입캐스트 합성 실패 ({te}) → Edge-TTS 자동 대체")
                words = asyncio.run(_edge_one(text, mp3, cfg["tts"]["edge_voice"], cfg["tts"]["rate"]))
        elif prov == "elevenlabs":
            words = _elevenlabs_one(text, mp3, cfg)
        else:
            words = asyncio.run(_edge_one(text, mp3, cfg["tts"]["edge_voice"], cfg["tts"]["rate"]))

        dur = _mp3_duration(mp3) + 0.4  # 장면 사이 0.4초 여유
        for s, e, w in _words_to_cues(words):
            srt_lines.append(f"{idx}\n{_fmt(t0 + s)} --> {_fmt(t0 + e)}\n{w}\n"); idx += 1
        timeline.append({"id": sc["id"], "mp3": str(mp3), "start": t0, "duration": dur})
        log.info(f"TTS {sc['id']}: {dur:.1f}s")
        t0 += dur
    (out_dir / "subtitles.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    log.info(f"총 길이 {t0/60:.1f}분")
    return {"scenes": timeline, "total": t0}
