"""비용 및 크레딧 사용량 정밀 추적기 (Cost & Credit Tracker)
- OpenAI (대본 GPT-4.1-mini, 이미지 gpt-image-1-mini)
- Typecast (음성 합성 글자수 및 비용)
- Gemini / Anthropic (사용 시)
- 영상 생성 완료 후 터미널 출력 및 GitHub Actions Summary 마크다운 파일 자동 기록
"""
import os, json, datetime
from pathlib import Path
from .common import ROOT, log

class CostTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topic": "",
            "items": [],
            "total_usd": 0.0,
            "total_krw": 0.0,
            "typecast_chars": 0
        }

    def set_topic(self, topic: str):
        self.data["topic"] = topic

    def track_openai_chat(self, model: str, prompt_tokens: int, completion_tokens: int, purpose: str = "대본/에이전트 감수"):
        # gpt-4.1-mini 기준: input $0.15 / 1M, output $0.60 / 1M
        in_cost = (prompt_tokens / 1_000_000) * 0.15
        out_cost = (completion_tokens / 1_000_000) * 0.60
        cost = in_cost + out_cost
        krw = cost * 1400
        self.data["items"].append({
            "service": "OpenAI LLM",
            "model": model,
            "usage": f"입력 {prompt_tokens}토큰, 출력 {completion_tokens}토큰 ({purpose})",
            "cost_usd": round(cost, 5),
            "cost_krw": round(krw, 1)
        })
        self.data["total_usd"] += cost
        self.data["total_krw"] += krw

    def track_openai_image(self, model: str, count: int = 1, resolution: str = "1024x1024"):
        # gpt-image-1-mini: 약 $0.006 (장당 약 8.4원)
        # dall-e-3: $0.040 (장당 약 56원)
        unit_cost = 0.006 if "mini" in model else 0.040
        cost = count * unit_cost
        krw = cost * 1400
        self.data["items"].append({
            "service": "OpenAI Image",
            "model": model,
            "usage": f"{count}장 생성 ({resolution})",
            "cost_usd": round(cost, 5),
            "cost_krw": round(krw, 1)
        })
        self.data["total_usd"] += cost
        self.data["total_krw"] += krw

    def track_typecast(self, char_count: int, voice_name: str = "모건"):
        # 타입캐스트: 월 구독 크레딧 차감 (글자수 추적)
        self.data["typecast_chars"] += char_count
        self.data["items"].append({
            "service": "Typecast AI",
            "model": f"{voice_name} ({voice_name} 보이스)",
            "usage": f"{char_count:,} 글자 음성 합성",
            "cost_usd": 0.0,
            "cost_krw": 0.0,
            "note": "타입캐스트 유료 구독 크레딧 차감"
        })

    def save_and_brief(self, out_dir: Path):
        summary_file = out_dir / "credit_report.json"
        summary_file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

        md = self.generate_markdown()
        (out_dir / "credit_report.md").write_text(md, encoding="utf-8")

        # GitHub Actions STEP_SUMMARY 환경변수가 있으면 자동 등록
        step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary and os.path.exists(os.path.dirname(step_summary)):
            try:
                with open(step_summary, "a", encoding="utf-8") as f:
                    f.write("\n\n" + md + "\n")
            except Exception as e:
                log.warning(f"GitHub Summary 쓰기 실패: {e}")

        log.info("=" * 60)
        log.info("📊 [크레딧 & 비용 결산 브리핑]")
        log.info(f"주제: {self.data['topic']}")
        for it in self.data["items"]:
            log.info(f"- [{it['service']}] {it['model']}: {it['usage']} ➔ ${it['cost_usd']:.4f} ({it['cost_krw']:.1f}원)")
        log.info(f"★ 총 사용 비용: ${self.data['total_usd']:.4f} (약 {self.data['total_krw']:.1f}원)")
        if self.data["typecast_chars"] > 0:
            log.info(f"★ 타입캐스트 차감 글자수: {self.data['typecast_chars']:,} 자")
        log.info("=" * 60)

    def generate_markdown(self) -> str:
        md = f"### 📊 이번 영상 제작 크레딧 & 비용 상세 결산\n\n"
        md += f"- **주제**: {self.data['topic']}\n"
        md += f"- **제작 완료 시각**: {self.data['timestamp']}\n"
        md += f"- **총 발생 비용**: **${self.data['total_usd']:.4f} (약 {self.data['total_krw']:.1f}원)**\n\n"
        md += "| 서비스 | 모델/엔진 | 사용량 | 발생 비용 (USD) | 원화 환산 |\n"
        md += "|---|---|---|---|---|\n"
        for it in self.data["items"]:
            note = it.get("note", "")
            cost_str = f"${it['cost_usd']:.4f}" if it['cost_usd'] > 0 else "-"
            krw_str = f"약 {it['cost_krw']:.1f}원" if it['cost_krw'] > 0 else (note or "-")
            md += f"| {it['service']} | {it['model']} | {it['usage']} | {cost_str} | {krw_str} |\n"
        
        if self.data["typecast_chars"] > 0:
            md += f"\n> 🎙️ **타입캐스트 유료 플랜**: 총 **{self.data['typecast_chars']:,}글자** 차감\n"
        return md

tracker = CostTracker()
