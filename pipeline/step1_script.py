"""1단계: 주제 → 장면별 대본(JSON). Claude API 사용."""
import os, json, re
from pathlib import Path
import anthropic
from .common import load_config, save_json, log

PROMPT = """당신은 유튜브 인기 공학 정보 채널 "{channel}"의 전문 기획자 겸 대본 작가입니다.
유튜브 채널 '신비한 건축사전' 특유의 흡입력 넘치는 시그니처 연출 기법을 '해안·항만·바다 토목 공학'에 완벽히 접목하여 대본을 작성하세요.

{persona}

주제: {topic}

아래 JSON 형식으로만 답하세요. 설명이나 마크다운 코드블록 없이 순수 JSON만 출력합니다.

{{
  "title": "유튜브 제목 (강렬한 호기심 유발, '왜 OO는 XX할까?', 구체적 숫자 포함)",
  "thumbnail_text": "썸네일용 굵고 짧은 핵심 텍스트 2줄 (줄바꿈 \\n, '수심 50m 비밀\\n테트라포드의 진실')",
  "thumbnail_prompt": "썸네일용 초고화질 실사 이미지 프롬프트 (영어, 극적인 앵글)",
  "description": "영상 설명란 텍스트 (호기심 유발 문장 + 공학적 팩트 요약 + 해시태그 5개)",
  "tags": ["항만", "해안공학", "토목공학", "테트라포드", "방파제", "바다"],
  "scenes": [
    {{
      "id": 1,
      "narration": "장면 나레이션. 구어체 존댓말, 명확한 단문 위주, 귀에 쏙쏙 박히는 아나운서 브리핑 톤.",
      "image_prompt": "이 장면의 영문 이미지 프롬프트 (실제 항만/해안 공학 현장 실사 묘사)",
      "motion": false,
      "motion_prompt": ""
    }}
  ]
}}

[신비한 건축사전식 필수 4단계 스토리텔링 구조]:
- 총 장면 수: 정확히 {n_scenes}개
- 1단계 [도입·훅 (장면 1)]: "바닷가에서 무심코 지나치는 테트라포드, 그런데 이 거대한 덩어리가 왜 4개의 다리를 가졌는지 알고 계셨나요?" 같은 일상적 시선에서의 강렬한 호기심 유발.
- 2단계 [위기·난관 (장면 2~3)]: 바다의 가혹한 물리적 한계 제시. "만약 일반 사각 콘크리트 벽을 세운다면 20미터 폭풍 파도의 충격력(수십 톤)을 정면으로 맞아 순식간에 박살 납니다."
- 3단계 [공학적 해결 (장면 4~5)]: 해안 토목공학의 놀라운 지혜와 수치. "파도를 막는 게 아니라, 틈새로 파도를 통과시켜 스스로 에너지를 상쇄시키는 4차원 인터로킹(맞물림) 메커니즘"을 비유와 핵심 수치로 명쾌하게 해설.
- 4단계 [요약·여운 (마지막 장면)]: 감탄을 자아내는 공학적 가치 정리 + 다음 편 예고 + 구독/좋아요 클로징.

[나레이션 톤앤매너]:
- 총 낭독 시간: 약 {target_minutes}분 ({total_chars}자 내외).
- 군더더기 없는 명확한 단문, 지적이면서도 귀에 쏙쏙 박히는 몰입감 높은 딕션.
- 전문 용어는 반드시 직관적인 일상 비유와 함께 설명.
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
