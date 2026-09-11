"""3단계: 장면별 나레이션 → mp3 + 단어 타임스탬프 → SRT 자막.
edge-tts(무료)는 WordBoundary 이벤트로 타임스탬프를 제공."""
import asyncio, os, re
from pathlib import Path
from .common import load_config, log

# 영문 단어 및 전문 약어가 TTS에서 알파벳 철자(스펠링)로 읽히지 않고 자연스러운 한국어로 발음되도록 치환
PHONETIC_MAP = {
    "OCEAN CODE LAB": "오션 코드 랩",
    "OCEAN": "오션",
    "CODE": "코드",
    "LAB": "랩",
    "KDS": "케이디에스",
    "TTP": "티티피",
    "TSHD": "호퍼 준설선",
    "PBD": "피비디",
    "DCM": "디씨엠",
    "AI": "에이아이",
    "GPS": "지피에스",
    "HUD": "에이치유디",
    "3D": "쓰리디",
    "2D": "투디",
    "4K": "포케이",
    "8K": "에이트케이",
    "HD": "에이치디",
}


def _normalize_for_tts(text: str) -> str:
    """TTS 엔진에 전달하기 전 영문 고유명사 및 약어를 자연스러운 한글 발음으로 변환"""
    out = text
    for eng, kor in PHONETIC_MAP.items():
        out = re.sub(r"\b" + re.escape(eng) + r"\b", kor, out, flags=re.IGNORECASE)
    # 문장 부호 중 TTS에서 불필요한 멈춤이나 이상 발음을 유발하는 기호 정제
    out = out.replace("—", " ").replace("-", " ")
    return re.sub(r"\s+", " ", out).strip()


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
    import json, subprocess, requests
    api_key = os.environ.get("TYPECAST_API_KEY", "").strip()
    voice_id = os.environ.get("TYPECAST_VOICE_ID", "").strip() or cfg["tts"].get("typecast_voice_id", "tc_6256118ea1103af69f0a87ec")
    model = cfg["tts"].get("typecast_model", "ssfm-v30")
    tempo = cfg["tts"].get("typecast_tempo", 1.05)

    if not api_key:
        raise ValueError("TYPECAST_API_KEY가 설정되지 않았습니다.")

    url = "https://api.typecast.ai/v1/text-to-speech"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
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
    raw_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    # 1. requests 시도
    req_err = None
    try:
        resp = requests.post(url, headers=headers, data=raw_bytes, timeout=60)
        if resp.status_code == 200 and len(resp.content) > 1000:
            mp3.write_bytes(resp.content)
            try:
                from .cost_tracker import tracker
                tracker.track_typecast(len(text), voice_name="모건")
            except Exception:
                pass
            return _calculate_word_timestamps(text, mp3)
        else:
            req_err = f"Status {resp.status_code}: {resp.text}"
    except Exception as e:
        req_err = str(e)

    # 2. Windows 시스템 curl.exe 폴백 (네트워크 환경/SSL 호환성 보장)
    try:
        temp_json = mp3.with_suffix(".json")
        temp_json.write_bytes(raw_bytes)
        cmd = [
            "curl.exe", "-s", "-X", "POST", url,
            "-H", f"X-API-KEY: {api_key}",
            "-H", "Content-Type: application/json; charset=utf-8",
            "--data-binary", f"@{temp_json}",
            "-o", str(mp3)
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=60)
        if temp_json.exists():
            temp_json.unlink()
        if res.returncode == 0 and mp3.exists() and mp3.stat().st_size > 1000:
            try:
                from .cost_tracker import tracker
                tracker.track_typecast(len(text), voice_name="모건")
            except Exception:
                pass
            return _calculate_word_timestamps(text, mp3)
        else:
            raise RuntimeError(f"Typecast curl 실패: {res.stderr.decode('utf-8', errors='ignore')}")
    except Exception as ce:
        raise RuntimeError(f"Typecast 호출 실패 (requests: {req_err}, curl: {ce})")


def _calculate_word_timestamps(text: str, mp3: Path):
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
        display_text = sc["narration"]
        spoken_text = _normalize_for_tts(display_text)
        words = None
        
        if prov == "typecast":
            try:
                log.info(f"타입캐스트 모건 보이스 합성 중: 장면 {sc['id']} (발음 정제: {spoken_text[:40]}...)...")
                words = _typecast_one(spoken_text, mp3, cfg)
            except Exception as te:
                log.warning(f"타입캐스트 합성 실패 ({te}) → Edge-TTS 자동 대체")
                words = asyncio.run(_edge_one(spoken_text, mp3, cfg["tts"]["edge_voice"], cfg["tts"]["rate"]))
        elif prov == "elevenlabs":
            words = _elevenlabs_one(spoken_text, mp3, cfg)
        else:
            words = asyncio.run(_edge_one(spoken_text, mp3, cfg["tts"]["edge_voice"], cfg["tts"]["rate"]))

        dur = _mp3_duration(mp3) + 0.4  # 장면 사이 0.4초 여유
        for s, e, w in _words_to_cues(words):
            srt_lines.append(f"{idx}\n{_fmt(t0 + s)} --> {_fmt(t0 + e)}\n{w}\n"); idx += 1
        timeline.append({"id": sc["id"], "mp3": str(mp3), "start": t0, "duration": dur})
        log.info(f"TTS {sc['id']}: {dur:.1f}s")
        t0 += dur
    (out_dir / "subtitles.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    log.info(f"총 길이 {t0/60:.1f}분")
    return {"scenes": timeline, "total": t0}
