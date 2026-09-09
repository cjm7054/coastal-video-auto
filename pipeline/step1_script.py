import os, json, re
from pathlib import Path
from .common import load_config, save_json, log

PROMPT = """당신은 유튜브 100만 조회수를 기록하는 공학 전문 채널 '신비한 건축사전'의 메인 총괄 디렉터 겸 수석 대본 작가입니다.
시청자를 단 1초 만에 사로잡는 '신비한 건축사전'(@신비한_건축사전_1) 고유의 치밀한 연출 공식과 3D 건축 디오라마 시각 스타일을 해안·항만·바다 토목공학 다큐멘터리에 완벽하게 이식하여 대본을 작성하세요.

{persona}

주제: {topic}

아래 JSON 형식으로만 답하세요. 설명이나 마크다운 코드블록 없이 순수 JSON만 출력합니다.

{{
  "title": "유튜브 제목 (강렬한 호기심 유발, '왜 OO는 XX할까?', 구체적 숫자 포함)",
  "thumbnail_text": "썸네일용 굵고 짧은 핵심 텍스트 2줄 (줄바꿈 \\n, '수심 50m 비밀\\n테트라포드의 진실')",
  "thumbnail_prompt": "썸네일용 3D 디오라마 단면 투시도 렌더링 프롬프트 (영어, 극적인 단면 컷어웨이와 붉은 치수선)",
  "description": "영상 설명란 텍스트 (호기심 유발 문장 + 공학적 팩트 요약 + 해시태그 5개)",
  "tags": ["항만", "해안공학", "토목공학", "테트라포드", "방파제", "바다"],
  "scenes": [
    {{
      "id": 1,
      "narration": "장면 나레이션.",
      "image_prompt": "이 장면의 영문 3D 건축/토목 디오라마 렌더링 프롬프트.",
      "motion": true,
      "motion_prompt": "카메라 궤적 및 물리적 시뮬레이션 영문 프롬프트"
    }}
  ]
}}

[★ 신비한 건축사전 완벽 복제: 4단계 스토리텔링 & 한국형 실증 공학 팩트 규칙]:
- 총 장면 수: 정확히 {n_scenes}개
- [절대 엄수: 한국 최신 방파제의 90% 이상인 '케이슨 혼성제' 실증 공학 고증]:
  * 허구의 판타지 구조물이나 외국식 단순 직립제를 배제하고, 실제 한국 주요 항만(부산신항, 포항영일만, 울산신항, 삼척, 울릉도 사동항 등)에 시공된 **'케이슨식 혼성제(Caisson Composite Breakwater)'**를 완벽 고증하세요.
  * 최신 한국 실증 케이슨 종류를 주제에 맞게 적극 반영:
    1) **유공 슬릿(Slit) 케이슨**: 파도가 들이치는 전면벽에 세로/가로 슬릿 구멍을 뚫어 챔버(유수실) 내부로 물을 끌어들여 위상차 간섭으로 파력을 40% 이상 상쇄시키는 공법.
    2) **벌집형(Honeycomb) 복합 케이슨**: 내부 격벽을 정육각형 벌집 모양으로 설계해 콘크리트 자중은 20% 줄이면서 비틀림 강성과 파압 저항력을 극대화한 신공법.
    3) **소파블록 피복 케이슨 혼성제**: 케이슨 전면에 사석 마운드와 테트라포드(TTP)/시락/아크로포드를 2층 이상 피복하여 쇄파 충격을 1차 흡수하는 복합 구조.
    4) **인터로킹 키(Interlocking Key) 케이슨**: 케이슨 블록 간 요철 맞물림 전단키를 두어 블록끼리 서로를 지지하는 활동(Sliding) 방지 메커니즘.
  * 구체적 실증 수치 필수 제시:
    - 수심 20~40m 해저 사석 마운드(Rubble mound) 두께 5~10m
    - 아파트 10층 높이, 무게 5,000~10,000톤급 대형 케이슨의 진수(Floating dock) 및 예인 거치
    - 케이슨 내부 속채움(모래/자갈)으로 얻는 수만 톤 단위의 자중 저항력
    - Goda 파압 공식 계산 및 50년~100년 빈도 설계 파고(H1/3 10m 이상)에 대한 안정성 검토

- 1단계: 도입 (Hook, 장면 1~3)
  * 반드시 시그니처 멘트 "여기 [구조물 이름]가 있습니다."로 포문을 엽니다.
  * 일상에서 흔히 보지만 아무도 몰랐던 기괴한 형태나 크기에 날카로운 질문을 던집니다. (예: "아파트 10층 크기의 거대한 콘크리트 박스가 어떻게 바다 한가운데 떠서 벽이 될 수 있었을까?", "방파제 벽면에 왜 무수한 구멍이 뚫려 있을까?")
- 2단계: 난관 (Conflict & Crisis, 장면 4~6)
  * 자연의 가혹함과 단순 직립 콘크리트 벽의 치명적 한계를 유체역학적 팩트로 극적으로 부각합니다. (충격 쇄파압 집중, 반사파에 의한 기초 세굴 및 침하, 케이슨 전도 및 활동 파괴 등)
  * 난관의 정점에서 반드시 시그니처 멘트: "아주 환장할 노릇이죠." 또는 "순식간에 산산조각 나기 십상입니다."를 사용합니다.
- 3단계: 해결 (Resolution & Engineering, 장면 7~13)
  * 공학자들의 기발한 역발상과 최신 케이슨 실증 공법(유공 슬릿 유수실 간섭, 벌집형 셀 격벽 구조, 하부 사석 마운드 압밀 치환 및 피복 블록 맞물림)을 논리적으로 제시.
  * 반드시 시그니처 멘트: "비상한 [공학/아이디어]가 등장합니다.", "발상을 완전히 뒤집은 겁니다."를 투입합니다.
  * 3D 시각화와 실제 공학 메커니즘을 결합하여 왜 한국 바다에 이 케이슨이 놓였는지 쾌도난마처럼 풀어냅니다.
- 4단계: 요약 및 클로징 (Summary & Outro, 장면 14~16)
  * "결국 [구조물/기술]은 이렇게 탄생한 겁니다."라는 확정 클로징으로 매듭을 짓고, 한국 해양토목 기술의 위대함을 기리는 3줄 핵심 요약과 감탄을 남깁니다.

- [시각 연출 및 3D 시네마틱 카메라 모션 엔진 (비용 0원, 100% 역동적 무빙)]:
  * 모든 장면은 신비한 건축사전식 '3D 엔지니어링 일러스트'를 기반으로, 6대 첨단 카메라 워킹 엔진에 의해 한순간도 정지하지 않고 살아 움직입니다:
    1) **360도 오비탈 회전 드론 뷰(360° Orbital Drone View)**: 구조물 둘레를 회전 선회하며 파고드는 입체 궤적
    2) **초고고도 수직 상승 크레인 샷(Giant Crane Tilt-Up)**: 수중 사석 마운드 기초에서 아파트 10층 상판까지 수직 비상
    3) **FPV 드론 다이브 급강하(FPV Drone Dive)**: 상공에서 케이슨 유공벽/소파블록 전면으로 속도감 있게 돌진
    4) **광활한 해안선 수평 트래킹 헬리캠(Horizon Coastal Tracking)**: 수평선을 질주하며 방파제 라인 전경을 훑는 트래킹
    5) **크레인 수직 하강 & 투시도 포커스(Crane Tilt-Down)**: 상공에서 수중 기초 암반층으로 수직 침하
    6) **360도 반경 롤링 아크 샷(Arc Pan & Roll)**: 곡선 선회와 뱅크 롤링으로 구조물의 스케일을 극대화
  * "motion": false로 설정하고, 각 장면의 시각적 요소(전면 유공벽, 벌집 셀 격벽, 사석 마운드 등)가 선명하게 드러나는 "image_prompt"를 작성하세요.

[★ Google Flow 스타일 시각 스토리보드 & 한국형 케이슨 시각화 규칙]:
- Google Flow에서 검증된 4대 핵심 비주얼 기법을 프롬프트에 직접 반영합니다:
  1) [물리적 충격 시각화 (FORCE SIMULATION)]: 파도의 거대한 타격력을 붉은색 에너지 와이어프레임과 충격파 메트릭스로 표현 (예: "Red translucent giant wave pressure vector HUD showing 100 TONS strike force against caisson wall, dynamic pressure metrics, holographic engineering HUD")
  2) [케이슨 유공벽/벌집 셀 3D 내부 투시 (INTERNAL CELL MECHANICS)]: 슬릿 유공벽을 통과해 챔버에서 부딪히는 수류, 또는 정육각형 벌집형 내부 셀 격벽(Hexagonal honeycomb cell compartments)의 하중 분산 와이어프레임.
  3) [사석 마운드와 소파블록 하부 단면 (RUBBLE MOUND & ARMOR LAYER)]: 해저 지반 위의 사석 기초 마운드(Rubble mound bedding), 피복석(Riprap), 테트라포드 연동 맞물림 및 수중 세굴 방지공(Scour protection).
  4) [구조 비교 인포그래픽 (SOLID VS SLIT CAISSON)]: 일반 직립 케이슨(파도를 그대로 튕겨냄)과 유공 슬릿 케이슨(챔버 내 수면 진동으로 파도를 흡수 소파)의 파동 위상차(Phase-shift wave dissipation) 대조.

- 모든 "image_prompt"는 아래 요소를 필수로 조합하여 작성하세요:
  * "Clean stylish 3D isometric architectural engineering illustration of modern Korean caisson composite breakwater, showing detailed perforated slit wave chambers or hexagonal honeycomb cell compartments on heavy rubble mound"
  * "Visible submerged foundation showing riprap gravel bedding, seabed contours, and interlocking armor blocks with clear vibrant ocean water"
  * "Prominent red dimension measurement lines, bold engineering line-art accents, glowing scientific callout arrows, technical HUD infographic overlay"
  * "Cinema 4D, Octane Render isometric view, hyper-clean textures, sharp focus, professional technical explainer illustration style like Mysterious Architecture Dictionary, 16:9"

- "motion_prompt" (Veo 3.1 비디오 지시어):
  * "Continuous smooth dynamic 3D orbital camera flight around massive Korean caisson engineering structure, active fluid dynamic ocean waves rushing into slit chambers, slow-motion water spray, clean cinematic technical animation"

[나레이션 딕션]:
- 공식 채널명: OCEAN CODE LAB (OCL)
- 어설픈 감탄사나 상투적인 기계적 나레이션을 배제하고, 실제 다큐멘터리 성우처럼 지적이고 단단하며 신뢰감 넘치는 어조.
- 인트로: "안녕하세요, 해양 공학의 모든 비밀을 푸는 OCEAN CODE LAB, OCL입니다." 또는 "여기 OO가 있습니다."
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

