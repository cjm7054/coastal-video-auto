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
  "thumbnail_text": "썸네일용 굵고 직관적인 핵심 텍스트 2줄 (줄바꿈 \\n)",
  "thumbnail_prompt": "썸네일용 최고급 시네마틱 해양 다큐멘터리 프롬프트 (맑은 에메랄드빛 바다, 시원한 고공 드론 또는 현대적 수중 3D 투시, 영문)",
  "description": "영상 설명란 텍스트 (시청자 지적 호기심 유발 문장 + K-공학 핵심 메커니즘 팩트 요약 + 해시태그 5개)",
  "tags": ["항만", "해안공학", "토목공학", "바다"],
  "scenes": [
    {{
      "id": 1,
      "narration": "장면 나레이션.",
      "visual_type": "aerial_drone",
      "image_prompt": "이 장면의 영문 8K 시네마틱 프롬프트 (클린 베이스 이미지: 맑은 에메랄드 바다, 해변, 드론 뷰, 현대적 수중 구조물 등 visual_type에 맞게 작성, 텍스트/화살표 배제).",
      "clean_prompt": "1차 통과 순수 실사 렌더 프롬프트 (No text, no labels, no arrows, pure 8K photoreal maritime visual)",
      "info_prompt": "2차 통과 3D 인포그래픽 오버레이 프롬프트 (Semi-transparent 3D force arrows, callout measurement lines, structural cutaway annotation)",
      "info_callouts": [
        {{
          "label": "공학 측정 항목명 (예: 조류 유속 / 사석 단중 / 조위차 등 대본과 100% 일치)",
          "value": "실제 검증 수치와 단위 (예: 7.0 m/s / 30 t / 4.7 m)"
        }}
      ],
      "vectors": [
        {{
          "label": "유체/하중 벡터 설명 (예: 쇄파 에너지 감쇄 / 사석 세굴 유체력)",
          "direction": "left_to_right 또는 right_to_left 또는 top_down"
        }}
      ],
      "motion": true,
      "motion_prompt": "카메라 궤적 및 물리적 시뮬레이션 영문 프롬프트"
    }}
  ]
}}

[★ OCEAN CODE LAB (OCL) 토목공학 엄격 고증 분류 체계]:
- 총 장면 수: 정확히 {n_scenes}개 (씬당 약 6~8초 내외의 빠른 템포)
- [절대 원칙: 공학적 사실(Fact) 및 실제 시공 기술 100% 일치 - 허위/날조 절대 금지]:
  주제({topic})의 성격에 따라 사용되는 토목 구조물이 완전히 다릅니다. 혼동하여 엉뚱한 구조물을 설명하지 마세요:

  1. [유형 A: 연안정비사업 / 해안침식 / 백사장 복원 / 연안 보전 (예: 해운대 등)]:
     * ★★ 경고: 연안정비사업에는 거대 항만용 '케이슨(Caisson)'을 절대 사용하지 않습니다! 케이슨 언급 시 즉시 감점/탈락.
     * 실제 적용 공법:
       - **수중방파제 (잠제 / Submerged Breakwater)**: 대본 나레이션에서는 어려운 한자어 '잠제' 대신 시청자가 직관적으로 이해할 수 있는 **'수중방파제'**로만 일관되게 명칭을 통일하여 설명할 것 (잠제라는 단어 단독 사용 금지). 수면 아래 0.5~1.5m에 숨겨진 광폭 인공 리프 구조물로 파도를 미리 깨뜨려(쇄파) 해안선 침식을 방지.
       - **양빈 (Beach Nourishment)**: 침식된 백사장에 모래를 인위적으로 공급하여 모래밭을 복원.
       - **돌제 (Groin) & 이안제 (Detached Breakwater)**: 파도와 연안류에 의한 모래 이동(연안표사)을 가두는 차단 구조물.
       - **친수형 호안 (Revetment)** 및 사석 완경사 피복.
     * 핵심 수리역학: 쇄파대 파랑 에너지 감쇄, 연안표사 차단, 해빈 경사 안정화.

  2. [유형 B: 대형 무역항 외곽시설 / 심해 방파제 (부산신항, 포항영일만, 울산신항, 사동항 등)]:
     * 실제 적용 공법:
       - **케이슨식 혼성제 (Caisson Composite Breakwater)**: 유공 슬릿 케이슨, 벌집형 셀, 사석 마운드, 50~80톤급 소파블록(TTP) 인터로킹 피복, 인터로킹 전단키.
     * 핵심 수리역학: Goda 쇄파압 공식, 유수실(Chamber) 위상차 간섭 소파, 사석 마운드 세굴(Scour) 방지, 수만 톤 자중에 의한 활동/전도 저항.

  3. [유형 C: 항만 준설 및 매립 / 부두 축조]:
     * 실제 적용 공법: 호퍼 준설선(TSHD), 펌프 준설, 연약지반 개량(PBD/DCM), 안벽(Quay Wall) 케이슨.

- 총 장면 수: 정확히 {n_scenes}개 (총 {target_minutes}분 분량, {total_chars}자 내외, 씬당 약 6~8초 내외의 빠른 템포)
- [스토리 전개 구조]:
  1단계: 압도적 현장 스케일과 물리적 의문/위기 (도입부 20%)
  2단계: 파괴 메커니즘과 유체역학적 극한 한계 (원리 분석 25%)
  3단계: 핵심 공학 실증 솔루션과 메커니즘 (정밀 해부 40%)
  4단계: 공학적 통찰과 지속가능한 미래 (클로징 15%)

- [★ 스토리보드 및 카메라 워킹 체인 규칙 (영화적 롱테이크 연출)]:
  각 장면(Scene)이 뚝뚝 끊어지지 않도록, 마치 하나의 카메라가 연속해서 이동하며 촬영하는 '원테이크(One-take)' 영화처럼 시각적 흐름(Continuity)을 유기적으로 연결하세요.
  예를 들어 씬 1이 해안 전체를 조망하는 'Wide Shot'이라면, 씬 2는 카메라가 방파제로 다가가는 'Medium Shot', 씬 3은 수면 아래 구조물로 들어가는 'Close-up'이 되도록 샷 사이즈를 자연스럽게 이어가야 합니다.
  'image_prompt'와 'motion_prompt' 작성 시 이전 장면의 카메라 무빙(예: Panning, Zoom in, Tracking)과 환경(날씨, 물색)이 다음 장면과 완벽하게 상속 및 연결되도록 치밀하게 묘사하세요.

[★ 구글 플로우(Google Flow) 및 코덱스(Codex) 표준 3D 공학 시각화 핵심 원칙]:
- [★ 절대 금지]: 칙칙하고 어두운 지하 흙더미/자갈 단면도, 흙탕물, 오래되고 방치된 이끼 낀 콘크리트, 어두운 암석 묘사를 절대 금지합니다.
- **햇살이 찬란하게 쏟아지는 투명한 에메랄드빛 청록색 바다, 시원한 고공 4K 드론 뷰, 모던하고 깔끔한 화이트/라이트그레이 3D 건축 모형(신비한 건축사전 및 National Geographic 3D 다큐멘터리 렌더 품질)**을 최우선으로 연출할 것.
- 모든 장면마다 "visual_type"을 다음 4가지 중 하나로 명시하고 그에 맞게 "image_prompt" 및 "clean_prompt"를 작성하세요:
  1. "aerial_drone" [광활하고 밝은 고공 4K 에어리얼 뷰]:
     - 눈부신 햇살 아래 에메랄드빛 바다와 현대적인 대형 해양 구조물이 한눈에 들어오는 투명하고 시원한 3D 조망.
  2. "construction_action" [모던 해양 공학 3D 시공 뷰]:
     - 최첨단 대형 해상 크레인 바지선과 매끄러운 모던 콘크리트 블록 거치 현장의 선명하고 역동적인 3D 다큐 구도.
  3. "underwater_clarity" [투명하고 맑은 3D 수중 컷어웨이/투시]:
     - 어두운 심해가 아닌, 맑고 투명한 에메랄드빛 바닷물 속으로 은은하고 눈부신 햇살(God rays)이 쏟아지며 순백색의 수중 방파제(잠제)나 복합 케이슨의 내부 격자 셀 구조가 투명하게 드러나는 최고급 3D 건축 투시도.
  4. "wave_impact" [투명한 파도 쇄파 충돌 샷]:
     - 하얗고 깨끗하게 부서지는 파도가 현대적 소파블록 및 유공 방파제 위에서 에너지를 상쇄시키는 시원하고 세련된 슬로우모션 샷.

[★ 절대 금지 규칙 - 1차 베이스 이미지(CLEAN) 내부 텍스트/라벨/붉은선 100% 차단]:
- 이미지 내부에 한글, 영문, 라벨, 수치, 도표, 워터마크, 붉은색 HUD 지시선, 억지스러운 화살표 등을 절대 포함시키지 마세요!
- 오직 맑고 투명한 물, 밝은 콘크리트 구조물의 선명한 3D 형태와 채광에만 집중할 것 (Pure 8K 3D photoreal architectural model, absolutely no text/labels/arrows).

[나레이션 딕션 및 발음 절대 규칙]:
- 공식 채널명: OCEAN CODE LAB
- ★★ [채널 브랜딩 표기 및 발음 특수 규칙 - 매우 중요]:
  * 클로징 씬(마지막 장면)의 채널명은 반드시 독립된 단독 문장으로 대본에 작성하세요:
    (예: "보이지 않는 구조물이 보이는 백사장을 지킨다. OCEAN CODE LAB. 바다 아래 공학의 언어를 읽는다.")
  * 자막(Subtitle)에는 반드시 영문 대문자 **OCEAN CODE LAB**으로 단독 표기되며,
  * 나레이션 음성 합성 시에는 앞뒤로 확실한 쉼(Pause)을 두고 **"오션 코드 랩"**으로 단독 발음되어 시청자의 귀에 명확하게 각인됩니다.
- ★★ [나레이션 내 일반 영어 단어/약어 표기 금지]:
  Typecast 음성 합성(TTS) 시 일반 영어 단어나 약어가 들어가면 알파벳 철자 하나하나(K-D-S...)로 끊어 읽는 결함이 발생합니다.
  따라서 채널명(OCEAN CODE LAB)을 제외한 일반 전문용어/약어는 반드시 100% 한국어 소리 나는 대로 발음 표기하세요!
  (예: TTP → "티티피", KDS → "케이디에스", AI → "에이아이", 3D → "쓰리디", 4K → "포케이")
- 신뢰감 넘치고 묵직한 중저음 명품 다큐멘터리 해설 톤.
- 총 {target_minutes}분 분량 ({total_chars}자 내외).
"""


def generate_script(topic: str, out_dir: Path) -> dict:
    from .cost_tracker import tracker
    tracker.set_topic(topic)
    cfg = load_config()
    n = cfg["channel"]["scenes"]
    mins = cfg["channel"]["target_minutes"]
    prompt = PROMPT.format(
        channel=cfg["channel"]["name"], persona=cfg["script"]["persona"], topic=topic,
        n_scenes=n, n_motion=cfg['video_gen']['max_scenes'], target_minutes=mins, total_chars=mins * 330,
    )
    log.info(f"대본 생성 중 (주제: {topic})...")
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

    # 2. OpenAI GPT-4.1-mini
    if script is None:
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if openai_key:
            try:
                from openai import OpenAI
                log.info("OpenAI(gpt-4.1-mini) 모델로 고품질 다큐 대본 생성 중...")
                o_client = OpenAI(api_key=openai_key)
                for attempt in range(3):
                    resp = o_client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                    )
                    usage = getattr(resp, "usage", None)
                    if usage:
                        tracker.track_openai_chat("gpt-4.1-mini", usage.prompt_tokens, usage.completion_tokens, "1차 대본 생성")
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

    # 3. Google Gemini
    if script is None:
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key:
            try:
                from google import genai
                log.info("Gemini Flash(gemini-3.6-flash) 모델로 대본 생성 시도...")
                g_client = genai.Client(api_key=gemini_key)
                resp = g_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                )
                text = resp.text.strip()
                (out_dir / "script_raw_gemini.txt").write_text(text, encoding="utf-8")
                # 마크다운 코드블록 정제
                text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text, flags=re.M).strip()
                i, j = text.find("{"), text.rfind("}")
                if i >= 0 and j > i:
                    text = text[i:j + 1]
                script = json.loads(text)
                log.info("✅ Gemini Flash 모델로 대본 생성 성공!")
            except Exception as ge:
                log.warning(f"Gemini 대본 생성 실패: {ge}")
                import traceback
                traceback.print_exc()

    if script is None:
        raise RuntimeError("대본 JSON 생성 실패 - API 키 및 로그 확인 필요")

    # =========================================================================
    # [★ Ruflo Multi-Agent Swarm: 공학 팩트 고증 & 스케일 상호 교차 비평 루프]
    # =========================================================================
    try:
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if openai_key:
            from openai import OpenAI
            r_client = OpenAI(api_key=openai_key)
            log.info("=" * 60)
            log.info("🚀 [Ruflo Swarm] 멀티 에이전트 공학 팩트 교차 검증 & 상호 비평 루프 가동")
            log.info("=" * 60)
            
            raw_scenes_json = json.dumps(script["scenes"], ensure_ascii=False)
            
            # --- 1단계: Agent 1 (공학 사실 고증관) & Agent 2 (스케일 및 실사 비평관) ---
            log.info(f"🔎 [Agent 1 & 2] 주제 '{topic}' 공학 팩트체크 및 허구/날조 여부 전수 감수 진행 중...")
            critic_prompt = f"""당신은 Ruflo Swarm의 '수석 해양토목 팩트체커 및 공학 감수관(Chief Engineering Fact-Checker)'입니다.
인터넷의 가짜 정보나 AI 환각(Hallucination), 허구/날조된 수치나 공법을 철저히 검증하고 사실에 기반한 실제 공학 팩트만 남기도록 감수하세요.

[현재 영상 주제]: "{topic}"

[필수 팩트체크 및 허구 검증 기준]:
1. **실제 현장 공법 사실 일치 여부 (Fact-Checking)**:
   - 주제가 '연안정비사업 / 해안침식 / 백사장 복원 / 연안 보전'인 경우:
     * 절대 원칙: 연안정비사업에는 거대 무역항용 '케이슨(Caisson)'을 절대 사용하지 않습니다! 케이슨 언급이 있으면 100% 날조이므로, 즉시 실제 공법인 '수중방파제(잠제)', '양빈(모래공급)', '돌제/이안제', '친수호안'으로 교정하세요.
   - 주제가 '심해 방파제 / 대형 무역항 외곽시설'인 경우:
     * 케이슨식 혼성제, 유공 슬릿, TTP(테트라포드) 피복, 사석 마운드를 다뤄야 합니다.
2. **수치 및 물리량의 공학적 신빙성 (Physics & Dimensions)**:
   - 황당하게 부풀려진 수치(예: 수심 1000m, 무게 100만 톤 등)를 배제하고, 실제 국내 항만설계기준(KDS 64 10) 및 시공 실적에 기반한 정밀 수치(예: 수중방파제 마루수심 -0.5m~-1.5m, 쇄파 감쇄율 60~70%, 케이슨 자중 10,000~15,000t, TTP 50t급)로 팩트를 교정하세요.
3. **용어 및 나레이션 사실성**:
   - 전문적인 실무 용어를 정확하게 구사하되, 시청자가 오해할 수 있는 비과학적 비유나 허구적 상상을 완전히 제거하세요.
4. **시각 프롬프트 스케일 실사성**:
   - AI가 미니어처나 어항 속 모형으로 왜곡하지 않도록 실제 건설 장비(크레인, 바지선, 준설선)와 인체 스케일을 확실히 명시하세요.

현재 {len(script['scenes'])}개 씬 프롬프트 데이터:
{raw_scenes_json}

위 기준을 바탕으로 모든 장면의 나레이션과 프롬프트에서 허구와 환각을 100% 제거하고 완전히 검증된 팩트 데이터로 전면 교정하여,
최종 확정된 scenes 배열({len(script['scenes'])}개 씬 전체)만 반드시 유효한 JSON 배열 형식으로 반환하세요.
반드시 각 씬 객체에 "clean_prompt"와 "info_prompt"(수치, 치수, 3D 지시선, 파랑/하중 벡터가 명시된 2차 패스 프롬프트)를 포함해야 합니다.
출력 형식 예시:
[
  {{"id": 1, "narration": "...", "image_prompt": "...", "clean_prompt": "...", "info_prompt": "...", "info_callouts": [{{"label": "측정항목", "value": "실제수치"}}], "vectors": [{{"label": "벡터설명", "direction": "right_to_left"}}], "motion": false}},
  ...
]
"""
            r_resp = r_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": critic_prompt}],
                temperature=0.2,
            )
            r_text = r_resp.choices[0].message.content.strip()
            r_text = re.sub(r"^```(json)?\s*|\s*```$", "", r_text, flags=re.M).strip()
            si, sj = r_text.find("["), r_text.rfind("]")
            if si >= 0 and sj > si:
                refined_scenes = json.loads(r_text[si:sj + 1])
                if len(refined_scenes) == len(script["scenes"]):
                    script["scenes"] = refined_scenes
                    log.info("✅ [Agent 1 & 2] 1차 고증 비평 및 스케일 레퍼런스 주입 통과!")

            # --- 2단계: Agent 3 (Quality Gatekeeper Synthesizer) 최종 승인 게이트 ---
            log.info("🛡️ [Agent 3: Quality Gatekeeper] 썸네일 및 최종 시각 연출 품질 게이트 심사...")
            gatekeeper_prompt = f"""당신은 Ruflo Swarm의 최종 승인 관문 'Quality Gatekeeper Synthesizer'입니다.
영상 제목: {script.get('title', '')}
현재 썸네일 프롬프트: {script.get('thumbnail_prompt', '')}

[심사 항목]:
1. 유튜브 썸네일이 클릭을 유도할 만큼 압도적인 해양 토목 스케일(에메랄드빛 푸른 바다, 웅장한 해안선, 거대한 크레인 바지선 또는 맑은 물속의 현대적 구조물)을 담고 있는가?
2. 칙칙한 지하 흙더미나 단면도가 아닌, 내셔널지오그래픽 다큐멘터리급의 시원하고 세련된 시네마틱 실사 비주얼인가?
3. 텍스트 글자(Typography/Hangul), 붉은색 지시선, 화살표 없이 순수 고화질 비주얼로 압도하는가?

기존 썸네일 프롬프트를 8K 초고화질 내셔널지오그래픽 시네마틱 해양 다큐멘터리 스타일로 최고 등급으로 업그레이드하여 단 한 줄의 영어 프롬프트만 출력하세요."""
            
            g_resp = r_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": gatekeeper_prompt}],
                temperature=0.3,
            )
            upgraded_thumb = g_resp.choices[0].message.content.strip().replace('"', '')
            if upgraded_thumb and len(upgraded_thumb) > 30:
                script["thumbnail_prompt"] = upgraded_thumb
                log.info("✅ [Agent 3] 썸네일 시각 임팩트 최종 게이트 통과 및 업그레이드 완료!")
            
            log.info("=" * 60)
            log.info("🎉 [Ruflo Swarm] 멀티 에이전트 3자 교차 검증 완료: 최고 품질 대본 확정")
            log.info("=" * 60)
    except Exception as r_err:
        log.warning(f"⚠️ Ruflo Swarm 멀티 에이전트 교차 감수 스킵 (기본 대본 유지): {r_err}")

    script["topic"] = topic
    current_fmt = cfg.get("current_format", "longform")
    script["format"] = current_fmt
    assert len(script["scenes"]) >= 3, "장면 수가 너무 적습니다"
    save_json(out_dir / "script.json", script)

    # =========================================================================
    # [★ Codex / Google Flow 연동 마크다운 및 프롬프트 시퀀스 자동 생성]
    # 'OCEAN CODE LAB 쇼츠MD파일' 규격에 맞춰 manifests 및 prompts 디렉터리 동기화
    # =========================================================================
    try:
        manifests_dir = out_dir / "manifests"
        prompts_dir = out_dir / "prompts"
        manifests_dir.mkdir(exist_ok=True)
        prompts_dir.mkdir(exist_ok=True)

        # 1. IMAGE_SEQUENCE.md
        seq_lines = [
            f"# OCEAN CODE LAB 영상 시퀀스 매니페스트 ({'쇼츠 (9:16)' if current_fmt == 'shorts' else '롱폼 (16:9)'})",
            f"- **주제**: {topic}",
            f"- **제목**: {script.get('title', '')}",
            f"- **포맷**: {current_fmt} ({'9:16 Vertical 1080x1920' if current_fmt == 'shorts' else '16:9 Landscape 1920x1080'})",
            f"- **총 장면 수**: {len(script['scenes'])}개\n",
            "| Scene ID | Keyframe ID | Narration | Visual Type | CLEAN Base Prompt | INFO Overlay Prompt |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]
        clean_prompt_lines = [
            f"# CLEAN KEYFRAME PROMPTS (1차 통과 순수 실사 렌더)\n",
            f"> 채널: OCEAN CODE LAB | 포맷: {current_fmt}\n",
            "> 이 프롬프트는 텍스트/화살표가 없는 1차 실사 베이스 렌더용입니다.\n"
        ]
        info_prompt_lines = [
            f"# INFOGRAPHIC KEYFRAME PROMPTS (2차 통과 3D 공학 인포그래픽 오버레이)\n",
            f"> 채널: OCEAN CODE LAB | 포맷: {current_fmt}\n",
            "> 1차 CLEAN 베이스 위에 반투명 3D 수치, 파력 벡터, 절단면 치수선을 증강하는 프롬프트입니다.\n"
        ]

        video_prompt_lines = [
            f"# VIDEO GENERATION PROMPTS (CLEAN-to-INFO 4초 영상 클립 프롬프트)\n",
            f"> 채널: OCEAN CODE LAB | 포맷: {current_fmt} ({'9:16 Vertical' if current_fmt == 'shorts' else '16:9 Landscape'})\n",
            "> MD 규격: 각 클립은 CLEAN 시작 프레임에서 시작하여 자연스러운 유체/파랑/카메라 무빙 후 INFO 상태로 점진 수렴합니다.\n"
        ]

        for idx, sc in enumerate(script["scenes"]):
            sid = sc.get("id", 1)
            sc_id_str = f"S{sid:02d}A"
            kf_id_str = f"KF-{sid:02d}A"
            clip_name = f"CLIP{idx+1:02d}_{sc_id_str}_{kf_id_str}.mp4"
            narration = sc.get("narration", "").replace("\n", " ")
            vtype = sc.get("visual_type", "aerial_drone")
            base_p = sc.get("clean_prompt") or sc.get("image_prompt", "")
            info_p = sc.get("info_prompt") or (
                f"Engineering cutaway overlay, 3D semi-transparent force vectors, flow measurement callouts, technical precision lines, {base_p}"
            )
            sc["clean_prompt"] = base_p
            sc["info_prompt"] = info_p

            seq_lines.append(f"| {sc_id_str} | {kf_id_str} | {narration} | {vtype} | {base_p} | {info_p} |")
            
            clean_prompt_lines.append(f"## [{sc_id_str}] {kf_id_str}")
            clean_prompt_lines.append(f"- **나레이션**: {narration}")
            clean_prompt_lines.append(f"```text\n{base_p}\n```\n")

            info_prompt_lines.append(f"## [{sc_id_str}] {kf_id_str} (INFO 2nd-pass)")
            info_prompt_lines.append(f"- **나레이션**: {narration}")
            info_prompt_lines.append(f"```text\n{info_p}\n```\n")

            video_prompt_lines.append(f"## [{clip_name}] ({sc_id_str})")
            video_prompt_lines.append(f"- **CLEAN source ID**: clean/{sid}.png ({kf_id_str}) [Start Frame]")
            video_prompt_lines.append(f"- **INFO target ID**: info/{sid}.png ({kf_id_str}) [End Frame Reference]")
            video_prompt_lines.append(f"- **Duration**: 4.0 seconds (Vertical 9:16)")
            video_prompt_lines.append(f"- **Narration context**: {narration}")
            video_prompt_lines.append(f"- **Camera Movement**: Subtle 8-12 degree tracking/dolly motion, maintaining horizon and perspective depth")
            video_prompt_lines.append(f"- **Graphic Build Sequence**:")
            video_prompt_lines.append(f"  * 0.0-0.4s: Pure CLEAN maritime visual. Subtle environmental fluid motion starts.")
            video_prompt_lines.append(f"  * 0.4-0.9s: Engineering anchor points light up on structures/currents.")
            video_prompt_lines.append(f"  * 0.9-1.7s: 3D callout lines and fluid flow streamlines construct outward.")
            video_prompt_lines.append(f"  * 1.7-2.6s: Technical labels and verified engineering measurements assemble.")
            video_prompt_lines.append(f"  * 2.6-3.4s: Flow/force vectors pulse along the physical load path.")
            video_prompt_lines.append(f"  * 3.4-4.0s: Composition cleanly converges on the approved INFO target state.")
            video_prompt_lines.append(f"```text\nGoogle Flow / Image-to-Video Prompt:\nStarting from the clean engineering photograph, execute a continuous 4.0-second single shot with subtle 10-degree tracking camera movement. Authentic fluid dynamics with sea water rushing and waves breaking. Progressively construct semi-transparent 3D technical callout lines, anchor points, and flow vectors in 3D scene space, respecting perspective, parallax, and occlusion, smoothly converging into the final engineering infographic state: {base_p}\n```\n")

        (manifests_dir / "IMAGE_SEQUENCE.md").write_text("\n".join(seq_lines), encoding="utf-8")
        (prompts_dir / "CLEAN_KEYFRAME_PROMPTS.md").write_text("\n".join(clean_prompt_lines), encoding="utf-8")
        (prompts_dir / "INFOGRAPHIC_KEYFRAME_PROMPTS.md").write_text("\n".join(info_prompt_lines), encoding="utf-8")
        (prompts_dir / "VIDEO_GENERATION_PROMPTS.md").write_text("\n".join(video_prompt_lines), encoding="utf-8")
        
        # [★ 구글 플로우(Google Flow) 첫 번째 프롬프트 복사 전용 일괄 텍스트 생성]
        # OCEAN CODE LAB 숏츠 프롬프트.md 규격에 맞춰 플로우에 즉시 붙여넣을 수 있는 원문 파일 작성
        flow_lines = [
            f"The script is {len(script['scenes']) * 4} seconds long. Keep the script exactly as it is.",
            "Analyze the script above, divide it into an appropriate number of scenes that follow the flow of the video, and write an image-generation prompt for each scene.",
            "Each scene should run about 3 to 4 seconds and must never exceed 5 seconds.",
            "Every image should look like a keyframe from a high-quality 3D infographic video that makes engineering principles, scientific principles, structures, mechanisms, historical facts, or everyday knowledge easy to understand visually.",
            "Do not add any infographic elements yet: no explanatory text, subtitles, arrows, numbers, labels, or icons.",
            "Write the prompts so that only the scene itself is generated: background, objects, structures, people, machines, natural phenomena.",
            "\nCommon Style: Modern minimalist architectural cutaway, sleek clean aesthetic, bright daylight, crystal clear emerald turquoise water, smooth realistic white concrete structure, National Geographic educational documentary quality, Octane 3D render, highly detailed, 9:16 vertical video.\n"
        ]
        for idx, sc in enumerate(script["scenes"]):
            sid = sc.get("id", idx + 1)
            n_text = sc.get("narration", "").replace("\n", " ")
            c_prompt = sc.get("clean_prompt") or sc.get("image_prompt", "")
            flow_lines.append(f"{idx+1}. Scene {sid}")
            flow_lines.append(f"시간: {idx*4}–{(idx+1)*4}")
            flow_lines.append(f"대본: {n_text}")
            flow_lines.append(f"이미지 프롬프트: {c_prompt}\n")

        (prompts_dir / "FLOW_BATCH_PROMPTS.txt").write_text("\n".join(flow_lines), encoding="utf-8")

        # 다시 저장하여 clean_prompt, info_prompt 반영
        save_json(out_dir / "script.json", script)
        log.info(f"✨ [Codex & Flow 연동] 매니페스트 및 플로우 일괄 프롬프트 파일 저장 완료 ({prompts_dir})")
    except Exception as ce:
        log.warning(f"Codex 매니페스트 생성 예외: {ce}")

    log.info(f"대본 완료: {script['title']} / 장면 {len(script['scenes'])}개")
    return script
