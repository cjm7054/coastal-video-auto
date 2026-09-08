"""1단계: 주제 → 장면별 대본(JSON). Claude API 사용."""
import os, json, re
from pathlib import Path
import anthropic
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

[★ 신비한 건축사전 완벽 복제: 4단계 스토리텔링 & 시그니처 대사 규칙]:
- 총 장면 수: 정확히 {n_scenes}개
- 1단계: 도입 (Hook, 장면 1~2)
  * 반드시 시그니처 멘트 "여기 [구조물 이름]가 있습니다."로 포문을 엽니다.
  * 일상에서 흔히 보지만 아무도 몰랐던 기괴한 형태나 크기에 날카로운 질문을 던집니다.
- 2단계: 난관 (Conflict & Crisis, 장면 3~4)
  * 자연의 가혹함과 기존 방식의 한계를 극적으로 부각합니다. (수십 톤의 파도 충격력, 태풍, 연약 지반 침하 등)
  * 난관의 정점에서 반드시 시그니처 멘트: "아주 환장할 노릇이죠." 또는 "순식간에 산산조각 나기 십상입니다."를 사용합니다.
- 3단계: 해결 (Resolution & Engineering, 장면 5~8)
  * 공학자들의 기발한 역발상과 해결책 제시. 반드시 시그니처 멘트: "비상한 [공학/아이디어]가 등장합니다.", "발상을 완전히 뒤집은 겁니다."를 투입합니다.
  * 3D 단면 컷어웨이와 수치(높이, 무게, 각도, 압력 분산 등)를 통해 공학적 메커니즘을 시각적·논리적으로 쾌도난마처럼 풀어냅니다.
- 4단계: 요약 및 클로징 (Summary & Outro, 장면 9~10)
  * "결국 [구조물/기술]은 이렇게 탄생한 겁니다."라는 확정 클로징으로 매듭을 짓고, 3줄 핵심 요약과 감탄을 남깁니다.

- [비디오 모션(Veo) 할당 규칙]:
  * 가장 시각적 충격이 필요한 핵심 승부처 4개 장면(예: 장면 1 인트로 파도, 장면 3 난관 파도 충격, 장면 6 내부 메커니즘, 장면 8 완성된 방파제)에 "motion": true를 부여하고, 각 장면의 "motion_prompt"를 작성하세요.
  * 나머지 장면은 "motion": false로 설정하세요 (3D 고화질 디오라마 렌더링에 카메라 줌/팬 모션 엔진이 자동 적용됩니다).

[★ Google Flow 스타일 시각 스토리보드 & 시각화 규칙 (신비한 건축사전 x OCEAN CODE LAB)]:
- Google Flow에서 검증된 4대 핵심 비주얼 기법을 프롬프트에 직접 반영합니다:
  1) [물리적 충격 시각화 (FORCE SIMULATION)]: 파도의 거대한 타격력을 붉은색 에너지 와이어프레임과 충격파 메트릭스로 표현 (예: "Red translucent giant hammer wireframe visual impact symbol showing 100 TONS strike force against seawall, dynamic pressure metrics, holographic engineering HUD")
  2) [인터로킹 맞물림 3D 시연 (SELF-LOCKING MECHANICS)]: 테트라포드 4개의 다리가 서로 맞물려 자물쇠처럼 고정되는 기하학적 결합 시연 (예: "Glowing blue geometric CAD wireframe highlighting four interlocking legs of concrete tetrapods, self-locking structural mechanism, load distribution vectors")
  3) [에너지 감쇄 물리 시뮬레이션 (ENERGY DISSIPATION)]: 파도가 블록 틈새를 통과하며 유체 소용돌이와 열/마찰 에너지로 분산되는 전산유체역학(CFD) 단면 (예: "CFD fluid dynamic simulation cross-section of ocean wave passing through armor layer, turbulence dissipation, foam energy reduction, technical cross-section")
  4) [구조 비교 인포그래픽 (REFLECTION VS ABSORPTION)]: 수직 직립벽(파도를 튕겨냄)과 경사 사석 방파제(파도를 흡수함)의 물리적 차이를 3D 컷어웨이로 대조.

- 모든 "image_prompt"는 아래 요소를 필수로 조합하여 작성하세요:
  * "Photorealistic 3D cinematic aerial ocean perspective, detailed coastal maritime engineering in expansive natural shoreline landscape"
  * "Submerged underwater foundation view showing gravel bedding, natural seabed contours, and reinforced concrete structure seamlessly integrated with ocean environment"
  * "Subtle red dimension measurement lines, glowing scientific callout arrows, technical HUD overlay"
  * "Octane Render, Cinema 4D, hyper-detailed 8k, natural daylight and atmospheric ocean spray, ray-traced water transparency"

- "motion_prompt" (Veo 3.1 비디오 지시어):
  * "Continuous smooth dynamic cinematic 3D orbital camera flight around massive coastal engineering structure, realistic fluid dynamic waves crashing, slow-motion water spray, active coastal atmosphere"

[나레이션 딕션]:
- 공식 채널명: OCEAN CODE LAB (OCL)
- 군더더기 없는 단문 위주의 빠른 템포, 귀에 쏙쏙 박히는 아나운서 해설 톤.
- 인트로: "안녕하세요, 해양 공학의 모든 비밀을 푸는 OCEAN CODE LAB, OCL입니다." 또는 "여기 OO가 있습니다."
- 총 {target_minutes}분 분량 ({total_chars}자 내외).
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
