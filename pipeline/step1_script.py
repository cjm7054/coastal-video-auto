import os, json, re
from pathlib import Path
from .common import load_config, save_json, log

PROMPT = """당신은 대한민국 해안·항만 토목공학의 본질을 밝히는 전문 다큐멘터리 채널 'OCEAN CODE LAB (OCL)'의 총괄 메인 디렉터 겸 수석 대본 작가입니다.
타 채널의 가벼운 유행어나 상투적 클리셰(~환장할 노릇, ~비상한 아이디어 등)를 철저히 배제하고, 압도적인 해양 물리 스케일과 한국 실제 항만의 실증 공학 데이터를 기반으로 시청자를 지적 전율로 사로잡는 고유의 오리지널 다큐멘터리 대본을 작성하세요.

{persona}

주제: {topic}

아래 JSON 형식으로만 답하세요. 설명이나 마크다운 코드블록 없이 순수 JSON만 출력합니다.

{{
  "title": "유튜브 제목 (강렬한 지적 호기심과 실제 공학 수치를 결합한 명품 다큐 제목)",
  "thumbnail_text": "썸네일용 굵고 직관적인 핵심 텍스트 2줄 (줄바꿈 \\n, '수심 30m 해저 비밀\\n1만톤 케이슨의 진실')",
  "thumbnail_prompt": "썸네일용 Unreal Engine 5 단면 투시도 렌더링 프롬프트 (영어, 거대한 해저 지층 단면, 붉은 파압 벡터선과 콘크리트 절단면)",
  "description": "영상 설명란 텍스트 (시청자 지적 호기심 유발 문장 + K-공학 핵심 메커니즘 팩트 요약 + 해시태그 5개)",
  "tags": ["항만", "해안공학", "토목공학", "케이슨방파제", "부산신항", "바다"],
  "scenes": [
    {{
      "id": 1,
      "narration": "장면 나레이션.",
      "image_prompt": "이 장면의 영문 Unreal Engine 5 공학 단면 투시도 렌더링 프롬프트.",
      "motion": true,
      "motion_prompt": "카메라 궤적 및 물리적 시뮬레이션 영문 프롬프트"
    }}
  ]
}}

[★ OCEAN CODE LAB (OCL) 오리지널 4대 스토리텔링 공학 프레임워크]:
- 총 장면 수: 정확히 {n_scenes}개 (씬당 약 6~8초 내외의 숨 막히는 긴장감과 속도감 있는 전개)
- [절대 엄수: 한국 최신 방파제의 90% 이상인 '케이슨 혼성제' 실증 공학 고증]:
  * 허구의 가상 구조물을 배제하고, 실제 한국 주요 항만(부산신항, 포항영일만, 울산신항, 삼척, 울릉도 사동항 등)에 시공된 **'케이슨식 혼성제(Caisson Composite Breakwater)'**의 도면을 정밀 고증하세요.
  * 최신 한국 실증 케이슨 공법을 입체적으로 해부:
    1) **유공 슬릿(Slit) 케이슨**: 전면 유공벽 슬릿 구멍을 통해 파도를 유수실(Chamber) 내부로 유입시켜, 내부 반사파와 후속 입사파의 위상차(Phase-shift) 간섭으로 파동 에너지를 40% 이상 자가 소멸시키는 공법.
    2) **벌집형(Honeycomb) 복합 케이슨**: 내부 격벽을 정육각형 벌집 셀로 설계해 콘크리트 자중은 20% 절감하면서도 비틀림 강성과 파압 저항력을 극대화한 구조.
    3) **소파블록 피복 혼성제**: 케이슨 전면에 사석 마운드와 초대형 테트라포드(TTP 50톤~80톤급), 시락, 아크로포드를 2층 이상 맞물려 거치하여 쇄파 충격을 1차 감쇄하는 복합 방파제.
    4) **인터로킹 키(Interlocking Key) 접합식 케이슨**: 케이슨 블록 사이에 요철형 전단키를 시공해 개별 블록이 수만 톤의 파압에도 밀리지 않고 일체로 거동하게 만드는 활동(Sliding) 방지 메커니즘.
  * 구체적 실증 공학 수치 필수 반영:
    - 수심 20~40m 해저 사석 마운드(Rubble mound) 두께 5~10m 및 기초 지반 개량
    - 아파트 10층 높이, 무게 5,000~10,000톤급 콘크리트 박스의 플로팅 독(Floating dock) 진수 및 해상 예인 거치
    - 케이슨 내부 모래·자갈 속채움(Infill)으로 확보하는 수만 톤 단위의 자중 저항 모멘트
    - Goda 파압 공식과 50년~100년 빈도 극한 설계 파고(H1/3 10m 이상)에 대한 전도·활동 안전율

- 1단계: 거대 스펙의 역설 (Paradox of Scale, 장면 1~3)
  * 오프닝 5초 만에 바다 한가운데 버티고 선 거대 구조물의 압도적 수치와 이를 삼키려는 10m 괴물 파도의 충돌을 대조합니다.
  * OCL 오프닝 시그니처 톤: "수심 30미터, 무게 1만 톤. 아파트 한 동 통째 크기의 콘크리트 덩어리가 바다 위에 떠 있습니다. 하지만 이 거대한 벽은 첫날부터 무너질 운명이었습니다." 등 묵직하고 흡인력 있는 화두를 던집니다.
- 2단계: 해저 파괴 메커니즘 (Hydrodynamic Crisis, 장면 4~6)
  * 단순 직립 콘크리트 벽이 맞닥뜨리는 유체역학적 극한 난관을 과학적으로 분석합니다.
  * 파도가 벽에 부딪히는 순간 발생하는 제곱미터당 수십 톤의 충격 쇄파압, 튕겨 나간 반사파가 해저 사석 바닥을 파내어 결국 제 발밑을 무너뜨리는 세굴(Scour)과 케이슨 전도 파괴의 공포를 극명하게 해부합니다.
- 3단계: K-토목 실증 솔루션 (K-Engineering Breakthrough, 장면 7~13)
  * 대한민국 토목 공학자들이 찾아낸 혁신적 해법을 제시합니다.
  * "벽으로 파도를 막는 대신, 파도가 스스로를 파괴하게 만들었습니다."라는 발상의 전환과 함께 유공 슬릿 유수실의 위상차 간섭, 벌집형 셀 구조의 하중 분산, 인터로킹 전단키와 테트라포드 연동 메커니즘을 3D 단면 투시도로 풀어냅니다.
- 4단계: 공학적 통찰과 해양 주권 (Engineering Insight, 장면 14~16)
  * 거친 동해와 남해의 파도를 물리법칙으로 길들여 낸 한국 해양 토목 기술의 정수를 기리며, 100년 넘게 우리 바다를 지켜내는 진정한 힘의 본질을 짚는 품격 있는 클로징으로 매듭짓습니다.

[★ Unreal Engine 5 기반 고화질 공학 단면 투시도(Cross-section Cutaway) 시각화 규칙]:
- 모든 "image_prompt"는 아래 요소를 필수로 조합하여 장난감 그래픽이 아닌 실제 현장 토목 단면도로 작성하세요:
  * "An isometric 3D architectural engineering cross-section cutaway diagram of a massive modern Korean reinforced concrete caisson composite breakwater in deep ocean"
  * "Photorealistic cross-section showing detailed soil strata, seabed rock bedding, heavy rubble mound foundation with submerged riprap gravel, and interlocking armor blocks"
  * "Detailed perforated slit wave chambers showing water intake and internal phase-shift turbulence, or hexagonal honeycomb cell compartments with stress distribution wireframe"
  * "Glowing red hydrodynamic wave pressure vectors, technical HUD measurement arrows, stress concentration indicators, clean engineering infographic overlay"
  * "Dramatic cinematic lighting, Unreal Engine 5 render, Octane photorealistic, highly detailed physical concrete texture, 8k, professional documentary engineering visual, 16:9"

[나레이션 딕션]:
- 공식 채널명: OCEAN CODE LAB (OCL)
- 신뢰감 넘치고 묵직한 중저음 명품 다큐멘터리 해설 톤.
- 총 {target_minutes}분 분량 ({total_chars}자 내외).
"""


def generate_script(topic: str, out_dir: Path) -> dict:
    cfg = load_config()
    n = cfg["channel"]["scenes"]
    mins = cfg["channel"]["target_minutes"]
    prompt = PROMPT.format(
        channel=cfg["channel"]["name"], persona=cfg["script"]["persona"], topic=topic,
        n_scenes=n, n_motion=cfg['video_gen']['max_scenes'], target_minutes=mins, total_chars=mins * 330,
    )
    log.info("대본 생성 중...")
    script = None

    # 1. Anthropic Claude (우선)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key and not anthropic_key.startswith("sk-ant-..."):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            for attempt in range(3):
                with client.messages.stream(
                    model=cfg["script"]["model"], max_tokens=24000,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    resp = stream.get_final_message()
                text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
                (out_dir / f"script_raw_{attempt}.txt").write_text(text, encoding="utf-8")
                if resp.stop_reason == "max_tokens":
                    continue
                text = re.sub(r"^```(json)?\s*|\s*```$", "", text, flags=re.M).strip()
                i, j = text.find("{"), text.rfind("}")
                if i >= 0 and j > i:
                    text = text[i:j + 1]
                try:
                    script = json.loads(text)
                    break
                except json.JSONDecodeError:
                    pass
        except Exception as ce:
            log.warning(f"Anthropic 대본 생성 예외: {ce}")

    # 2. OpenAI GPT-4o / GPT-4.1 (Anthropic 없을 시 완벽 대체)
    if script is None:
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if openai_key:
            try:
                from openai import OpenAI
                log.info("OpenAI 최신 모델로 고품질 다큐 대본 생성 중...")
                o_client = OpenAI(api_key=openai_key)
                for attempt in range(3):
                    resp = o_client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                    )
                    text = resp.choices[0].message.content.strip()
                    (out_dir / f"script_raw_{attempt}.txt").write_text(text, encoding="utf-8")
                    text = re.sub(r"^```(json)?\s*|\s*```$", "", text, flags=re.M).strip()
                    i, j = text.find("{"), text.rfind("}")
                    if i >= 0 and j > i:
                        text = text[i:j + 1]
                    try:
                        script = json.loads(text)
                        break
                    except json.JSONDecodeError as oe:
                        log.warning(f"OpenAI JSON 파싱 실패({attempt+1}/3): {oe}")
            except Exception as oe2:
                log.warning(f"OpenAI 대본 생성 실패: {oe2}")

    # 3. Google Gemini (무료 티어 텍스트 모델 fallback)
    if script is None:
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key:
            try:
                from google import genai
                log.info("Gemini Flash 모델로 고품질 다큐 대본 생성 중...")
                g_client = genai.Client(api_key=gemini_key)
                resp = g_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                text = resp.text.strip()
                text = re.sub(r"^```(json)?\s*|\s*```$", "", text, flags=re.M).strip()
                i, j = text.find("{"), text.rfind("}")
                if i >= 0 and j > i:
                    text = text[i:j + 1]
                script = json.loads(text)
            except Exception as ge:
                log.warning(f"Gemini 대본 생성 실패: {ge}")

    if script is None:
        raise RuntimeError("대본 JSON 생성 실패 - API 키 및 로그 확인 필요")

    script["topic"] = topic
    assert len(script["scenes"]) >= 3, "장면 수가 너무 적습니다"
    save_json(out_dir / "script.json", script)
    log.info(f"대본 완료: {script['title']} / 장면 {len(script['scenes'])}개")
    return script
