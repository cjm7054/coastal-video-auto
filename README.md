# 항만·해안 AI 해설 영상 자동 제작 프로그램

'신비한 건축사전' 스타일(AI 단면도 + 움직이는 영상 + AI 나레이션 + 큰 자막)의 정보성 영상을
**주제 한 줄 → 유튜브 업로드**까지 자동으로 만듭니다.

```
topics.txt 주제 → ① Claude 대본(JSON, 장면별 motion 지정) → ② Gemini 이미지(장면당 1장)
  → ②-1 핵심 장면만 Veo 3.1 Lite image-to-video (8초 클립)
  → ③ TTS+자막(SRT)
  → ④ 합성: Veo 클립 + 2.5D 패럴랙스(깊이맵 기반 카메라 이동) + 부유물 파티클 + 자막 + BGM
  → ⑤ 썸네일 → ⑥ YouTube 업로드
```

**움직임 구조 (하이브리드)**
- motion=true 장면(편당 6개): Veo 클립 8초를 0.8배속(10초)으로 재생 → 클립의 마지막 프레임을
  이어받아 패럴랙스로 나머지 시간을 채움 (끊김 없이 연결)
- 나머지 장면: 정지 이미지에서 깊이맵을 추출해 카메라가 단면도 속으로 들어가는 2.5D 효과.
  장면마다 돌리인/돌리아웃/틸트 방향을 바꿔 단조로움 방지
- 모든 장면에 물속 부유물 파티클을 screen 블렌드로 겹침

## 1. 설치 (Windows + PyCharm)

1. **FFmpeg 설치** — https://www.gyan.dev/ffmpeg/builds/ 에서 `ffmpeg-release-essentials.zip` 다운로드
   → `C:\ffmpeg\bin`에 풀고, 시스템 환경변수 `Path`에 `C:\ffmpeg\bin` 추가
   → 터미널에서 `ffmpeg -version` 이 나오면 성공
2. PyCharm에서 이 폴더를 열고 터미널에서 (GPU 없는 노트북 기준):
   ```
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements.txt
   ```
   깊이 추정 모델(약 100MB)은 첫 실행 때 자동 다운로드됩니다.
3. `.env.example`을 복사해 `.env`로 이름 바꾸고 API 키 입력
   - `ANTHROPIC_API_KEY` : https://console.anthropic.com
   - `GEMINI_API_KEY` : https://aistudio.google.com/apikey (이미지 1장 약 55원)
4. `assets/bgm/` 에 저작권 무료 BGM mp3를 몇 개 넣기 (유튜브 오디오 라이브러리 추천). 없으면 BGM 없이 제작됨.

## 2. 첫 실행 (업로드 없이 검토)

```
python run.py --format shorts --topic "해운대 백사장을 붙잡고 있는 물속의 둑" --no-upload   # 쇼츠 (9:16 세로형, 50초, 8개 씬)
python run.py --format longform --topic "해운대 백사장을 붙잡고 있는 물속의 둑" --no-upload # 롱폼 (16:9 가로형, 3.8분, 26개 씬)
```
`output/날짜_주제/` 안에 `final.mp4`, `thumbnail.jpg`, `script.json`이 생깁니다.
**`--format` 옵션을 주지 않으면 `config.yaml`의 기본 설정값(`format: "longform"`)**에 따라 생성됩니다.

비용(8분 영상 1편): 대본 약 100원 + 이미지 19장 약 1,000원 + Veo 6클립(1080p) 약 3,300원 + TTS 무료 ≈ **4,500원**
`video_gen.resolution`을 720p로 낮추면 Veo 비용이 절반. `video_gen.enabled: false`면 패럴랙스만으로 제작(1,100원).

렌더 시간: GPU 없는 노트북에서 8분 영상 기준 약 30~40분 (패럴랙스 CPU 렌더). 자는 동안 돌리는 용도로 적합.

## 3. 유튜브 업로드 연결 (최초 1회)

1. https://console.cloud.google.com → 새 프로젝트 → "YouTube Data API v3" 사용 설정
2. 사용자 인증 정보 → OAuth 클라이언트 ID → **데스크톱 앱** → JSON 다운로드
   → 이 폴더에 `client_secret.json` 이름으로 저장
3. OAuth 동의 화면에서 테스트 사용자에 본인 구글 계정 추가
4. `python run.py --topic "..."` 실행 → 브라우저가 열리면 로그인·허용 → `token.json` 자동 저장
   (이후엔 로그인 없이 자동)

`config.yaml`의 `privacy: "private"`로 두면 비공개 업로드되어 확인 후 공개할 수 있습니다.

## 4. 매일 자동 실행

`topics.txt`에 주제를 쌓아두면 실행할 때마다 위에서 하나씩 꺼내 씁니다.

Windows 작업 스케줄러 → 기본 작업 만들기 → 매일 → 프로그램: `run_daily.bat`

## 4-B. GitHub Actions로 돌리기 (PC 꺼져 있어도 자동 실행)

내 PC 대신 GitHub 서버에서 매일 새벽 3시(KST)에 제작·업로드합니다. 렌더 시간(40~60분)이
GitHub 무료 한도 안에 들어옵니다(비공개 저장소 월 2,000분 ≈ 매일 실행 가능, 공개 저장소는 무제한).

1. 이 폴더를 GitHub 저장소로 올리기 (`.gitignore`가 키 파일은 자동 제외)
2. 로컬에서 유튜브 인증 1회: `python make_token.py` → 브라우저 로그인 → `token.json` 생성
3. 저장소 → Settings → Secrets and variables → Actions → New repository secret 에 5개 등록:

   | Secret 이름 | 값 |
   |---|---|
   | `ANTHROPIC_API_KEY` | Anthropic 키 |
   | `GEMINI_API_KEY` | Gemini 키 |
   | `ELEVENLABS_API_KEY` | (선택) ElevenLabs 키 |
   | `YT_CLIENT_SECRET_JSON` | `client_secret.json` 파일 내용 전체 |
   | `YT_TOKEN_JSON` | `token.json` 파일 내용 전체 |

4. Actions 탭 → `daily-video` → **Run workflow** 로 수동 테스트 (`no_upload` 체크하면 검토용)
5. 완료된 영상은 Actions 실행 페이지 하단 **Artifacts**에서 30일간 내려받을 수 있음

`topics.txt`는 GitHub에서 직접 편집해 주제를 채워 넣으면 됩니다. 사용된 주제는 봇이 자동으로 커밋합니다.

주의: `token.json`의 refresh token은 OAuth 동의 화면이 "테스트" 상태면 7일마다 만료됩니다.
Google Cloud 콘솔에서 앱을 **프로덕션으로 게시**(검증 불필요, 본인 계정만 쓰면 됨)하면 만료되지 않습니다.

## 5. 문제 생겼을 때

- 중간에 실패하면 `python run.py --resume output/폴더명` 으로 이어서 실행 (이미 만든 이미지·음성은 재사용)
- 이미지가 이상하면 해당 `output/.../images/N.png` 삭제 후 `--resume` → 그 장면만 다시 생성
- 자막 글꼴이 깨지면 `config.yaml`의 `subtitle_font` 경로 확인

## 6. 품질 높이는 순서

1. TTS를 ElevenLabs로 교체 (`tts.provider: elevenlabs`, 월 $5 플랜) — 목소리 품질이 조회수에 직결
2. `style_suffix`에 참고 이미지 스타일을 더 구체적으로 (예: "blueprint annotations", "underwater view")
3. 장면 수를 늘리고 각 장면을 짧게 (이미지 전환이 잦을수록 이탈률 감소)
4. 대본 프롬프트에 채널의 잘 된 영상 대본을 예시로 넣기
