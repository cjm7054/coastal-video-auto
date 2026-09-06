"""1단계: 주제 → 장면별 대본(JSON). Claude API 사용."""
import os, json, re
from pathlib import Path
import anthropic
from .common import load_config, save_json, log

PROMPT = """당신은 유튜브 정보 채널 "{channel}"의 대본 작가입니다.
{persona}

주제: {topic}

아래 JSON 형식으로만 답하세요. 설명이나 마크다운 코드블록 없이 순수 JSON만 출력합니다.

{{
  "title": "유튜브 제목 (40자 이내, 궁금증 유발, 숫자 포함 권장)",
  "thumbnail_text": "썸네일 큰 글씨 2줄, 줄바꿈은 \\n (각 줄 6자 이내)",
  "thumbnail_prompt": "썸네일용 이미지 프롬프트 (영어, 극적인 단면도 구도)",
  "description": "영상 설명란 텍스트 (3~5문장 + 해시태그 5개)",
  "tags": ["태그1", "태그2", "..."],
  "scenes": [
    {{
      "id": 1,
      "narration": "이 장면의 나레이션. 3~5문장, 약 25~30초 분량(80~110자 정도가 아니라 200~260자). 구어체, 존댓말.",
      "image_prompt": "이 장면 이미지 프롬프트 (영어). 무엇을 어떤 구도로 보여줄지 구체적으로. 사람 얼굴·글자 없이.",
      "motion": false,
      "motion_prompt": "motion이 true인 장면만. 이미지가 어떻게 움직여야 하는지 (영어): 카메라 움직임 + 물·파도·구조물의 동작. 예: 'slow dolly in as a massive wave crashes over the breakwater, spray flying, tetrapods holding firm'"
    }}
  ]
}}

규칙:
- 장면은 정확히 {n_scenes}개.
- 장면 1은 15초 안에 궁금증을 던지는 훅. 마지막 장면은 요약 + 다음 영상 예고 + 구독 요청.
- 나레이션 총 분량은 약 {target_minutes}분 낭독 기준 ({total_chars}자 내외).
- 수치·단위·실제 사례를 구체적으로 넣되, 확실하지 않은 수치는 "약", "정도"로 표현.
- motion=true는 정확히 {n_motion}개. 움직임이 설명에 결정적인 장면(파도가 구조물을 치는 순간, 케이슨 거치, 준설선 작업, 이안류 흐름, 모래 이동 등)에만 배정. 장면 1(훅)은 반드시 motion=true.
- 이미지 프롬프트는 서로 다른 구도·대상이어야 하며, 항만·해안 구조물(방파제, 케이슨, 테트라포드, 안벽, 해빈, 이안류 등)의 단면·수중·항공 시점을 섞어서.
"""


def generate_script(topic: str, out_dir: Path) -> dict:
    cfg = load_config()
    n = cfg["channel"]["scenes"]
    mins = cfg["channel"]["target_minutes"]
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = PROMPT.format(
        channel=cfg["channel"]["name"], persona=cfg["script"]["persona"], topic=topic,
        n_scenes=n, n_motion=cfg['video_gen']['max_scenes'], target_minutes=mins, total_chars=mins * 330,  # 한국어 TTS 약 330자/분
    )
    log.info("대본 생성 중...")
    script = None
    for attempt in range(3):
        with client.messages.stream(
            model=cfg["script"]["model"], max_tokens=24000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            resp = stream.get_final_message()
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        (out_dir / f"script_raw_{attempt}.txt").write_text(text, encoding="utf-8")
        if resp.stop_reason == "max_tokens":
            log.warning(f"대본이 잘림(시도 {attempt+1}/3) → 재시도")
            continue
        text = re.sub(r"^```(json)?\s*|\s*```$", "", text, flags=re.M).strip()
        # 앞뒤에 설명 문장이 섞인 경우 첫 '{'부터 마지막 '}'까지만 사용
        i, j = text.find("{"), text.rfind("}")
        if i >= 0 and j > i:
            text = text[i:j + 1]
        try:
            script = json.loads(text)
            break
        except json.JSONDecodeError as e:
            log.warning(f"JSON 파싱 실패(시도 {attempt+1}/3): {e}")
    if script is None:
        raise RuntimeError("대본 JSON 생성 3회 실패 - output 폴더의 script_raw_*.txt 확인")
    script["topic"] = topic
    assert len(script["scenes"]) >= 3, "장면 수가 너무 적습니다"
    save_json(out_dir / "script.json", script)
    log.info(f"대본 완료: {script['title']} / 장면 {len(script['scenes'])}개")
    return script
