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
  "thumbnail_prompt": "썸네일용 Unreal Engine 5 단면 투시도 렌더링 프롬프트 (영어, 단면)",
  "description": "영상 설명란 텍스트 (시청자 지적 호기심 유발 문장 + K-공학 핵심 메커니즘 팩트 요약 + 해시태그 5개)",
  "tags": ["항만", "해안공학", "토목공학", "바다"],
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

[★ OCEAN CODE LAB (OCL) 토목공학 엄격 고증 분류 체계]:
- 총 장면 수: 정확히 {n_scenes}개 (씬당 약 6~8초 내외의 빠른 템포)
- [절대 원칙: 공학적 사실(Fact) 및 실제 시공 기술 100% 일치 - 허위/날조 절대 금지]:
  주제({topic})의 성격에 따라 사용되는 토목 구조물이 완전히 다릅니다. 혼동하여 엉뚱한 구조물을 설명하지 마세요:

  1. [유형 A: 연안정비사업 / 해안침식 / 백사장 복원 / 연안 보전]:
     * ★★ 경고: 연안정비사업에는 거대 항만용 '케이슨(Caisson)'을 절대 사용하지 않습니다! 케이슨 언급 시 즉시 감점/탈락.
     * 실제 적용 공법:
       - **잠제 (Submerged Breakwater)**: 수면 아래 0.5~1.5m에 숨겨진 광폭 인공 리프 구조물로 파도를 미리 깨뜨려(쇄파) 해안선 침식을 방지.
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

- 1단계: 압도적 현장 스케일과 물리적 위기 (장면 1~5) - 거대한 자연 파력과 구조물의 스케일 충돌
- 2단계: 파괴 메커니즘과 유체역학적 극한 한계 (장면 6~11) - 세굴, 전도, 쇄파압의 과학적 위기
- 3단계: K-토목 실증 혁신 솔루션 (장면 12~21) - 해당 공법의 실제 도면, 단면 투시, 시공 메커니즘 10개 씬 정밀 해부
- 4단계: 공학적 통찰과 지속가능한 해양 (장면 22~26) - 100년 내구성과 자연과의 공존을 담은 클로징

[★ 신비한 건축사전식 시각화 규칙: Unreal Engine 5 공학 단면 투시도 & 다각도 컷]:
- "image_prompt"는 장난감 모형 느낌을 철저히 배제하고, 장면마다 카메라 앵글을 다채롭게 교차할 것:
  * [항공 조감도 (Aerial Drone 8k)]: 넓은 해역 전체와 구조물의 배치를 조망하는 광각 뷰
  * [단면 투시도 (Cross-section Cutaway)]: 해저 지층, 사석 기초, 내부 챔버/셀 구조와 붉은 수리역학 파압 벡터 HUD 오버레이
  * [스케일 클로즈업 (Human/Vessel Scale)]: 500톤 크레인선, 안전모를 쓴 인부, 50톤 TTP가 한눈에 보이는 실물 스케일 대비
  * [수중 수리역학 (Underwater Hydrodynamics)]: 파도가 구조물과 충돌하며 포말과 와류를 형성하는 시뮬레이션

[나레이션 딕션]:
- 공식 채널명: OCEAN CODE LAB (OCL)
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
            log.info(f"🔎 [Agent 1 & 2] 주제 '{topic}' 공학 고증 및 장난감 모형 여부 전수 비평 진행 중...")
            critic_prompt = f"""당신은 Ruflo Swarm의 2개 수석 에이전트 팀입니다:
- 에이전트 1 (한국 토목공학 엄격 팩트체커):
  * 현재 영상 주제: "{topic}"
  * 절대 원칙: "연안정비사업 / 해안침식 / 백사장 복원" 주제인 경우, 절대로 케이슨(Caisson) 구조물이 나와선 안 됩니다!
    연안정비사업은 잠제(Submerged breakwater), 인공리프, 양빈(모래공급), 돌제(Groin), 이안제를 다뤄야 하며, 케이슨 언급이 있으면 전부 수중 잠제/사석호안/양빈으로 즉시 교정할 것.
  * 반대로 "심해 방파제 / 대형 무역항" 주제인 경우에만 케이슨 혼성제, TTP, 사석 마운드를 적용할 것.
- 에이전트 2 (스케일 & 실사 비평관):
  * AI가 어항 속 장난감 블록이나 미니어처처럼 그리지 않도록 크기 증명 객체(인간 작업자, 작업선, 크레인 등) 강제 주입.

현재 {len(script['scenes'])}개 씬 프롬프트 데이터:
{raw_scenes_json}

위 기준을 바탕으로 나레이션과 image_prompt에 엉뚱한 공법이나 허위 사실이 들어가지 않도록 완벽히 교정하여,
최종 확정된 scenes 배열({len(script['scenes'])}개 씬 전체)만 반드시 유효한 JSON 배열 형식으로 반환하세요.
출력 형식 예시:
[
  {{"id": 1, "narration": "...", "image_prompt": "...", "motion": false}},
  ...
]
"""
            r_resp = r_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": critic_prompt}],
                temperature=0.25,
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
1. 유튜브 썸네일이 클릭을 유도할 만큼 파괴적인 해양 토목 스케일(괴물 파도, 500톤 크레인선, 거대 케이슨 투시 단면)을 담고 있는가?
2. 텍스트 글자(Typography/Hangul) 없이 순수 3D 시네마틱 비주얼로 압도하는가?

기존 썸네일 프롬프트를 8K 초고화질 다큐멘터리 언리얼 엔진 5 단면도 스타일로 최고 등급으로 업그레이드하여 단 한 줄의 영어 프롬프트만 출력하세요."""
            
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
    assert len(script["scenes"]) >= 3, "장면 수가 너무 적습니다"
    save_json(out_dir / "script.json", script)
    log.info(f"대본 완료: {script['title']} / 장면 {len(script['scenes'])}개")
    return script
