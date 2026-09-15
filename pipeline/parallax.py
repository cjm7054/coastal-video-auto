"""2.5D 패럴랙스 렌더러 (GPU 불필요).
이미지 → 깊이맵(Depth-Anything V2 Small, CPU) → 깊이별 레이어 분리
→ 가상 카메라 이동(돌리/팬)으로 레이어를 서로 다른 속도로 움직여 입체감
→ FFmpeg로 인코딩. 파티클은 render_dust로 1회 생성해 최종 단계에서 겹침."""
import subprocess, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from .common import log

_pipe = None


def depth_map(img: Image.Image) -> np.ndarray:
    """0(멀다)~1(가깝다) float 배열. 모델 로드 실패 시 상하 그라데이션으로 대체."""
    global _pipe
    try:
        if _pipe is None:
            from transformers import pipeline
            _pipe = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")
        small = img.resize((640, 360))
        d = np.array(_pipe(small)["depth"].resize(img.size, Image.BILINEAR), dtype=np.float32)
        d = (d - d.min()) / (d.max() - d.min() + 1e-6)
        return d
    except Exception as e:
        log.warning(f"깊이 모델 사용 불가({e}) → 그라데이션 대체")
        h, w = img.height, img.width
        return np.tile(np.linspace(0.2, 1.0, h, dtype=np.float32)[:, None], (1, w))


def render_dust(duration: float, W: int, H: int, out: Path, fps=24, n=110, seed=0):
    """물속 부유물/먼지 파티클 영상을 검정 배경으로 1회 렌더 → 최종 합성 시 screen 블렌드로 겹침."""
    import cv2
    rnd = random.Random(seed)
    P = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1.5, 4.0),
          rnd.uniform(-8, 8), rnd.uniform(-18, -4), rnd.uniform(0, 6.28)] for _ in range(n)]
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for f in range(int(duration * fps)):
        t = f / fps
        fr = np.zeros((H, W), np.uint8)
        for x0, y0, r, vx, vy, ph in P:
            x = int((x0 + vx * t + 10 * math.sin(t * 0.7 + ph)) % W)
            y = int((y0 + vy * t) % H)
            a = int(90 + 70 * math.sin(t * 1.3 + ph))
            cv2.circle(fr, (x, y), int(r), max(0, a), -1, cv2.LINE_AA)
        fr = cv2.GaussianBlur(fr, (0, 0), 1.2)
        proc.stdin.write(fr.tobytes())
    proc.stdin.close(); proc.wait()


def render_parallax(img_path: Path, duration: float, out: Path, fps=30, mode=0,
                    strength=0.08, info_img_path: Path | None = None,
                    target_w: int | None = None, target_h: int | None = None):
    """신비한 건축사전식 고화질 시네마틱 3D 카메라 워킹 엔진 (GPU 불필요, 비용 0원).
    - MD Stage 6 규격 지원: CLEAN 실사 이미지에서 시작하여 0.4초 이후 3D 지시선, 치수, 하중 화살표(INFO)가 유려하게 떠오르는 트랜지션 연출
    - Mode 0: [360도 오비탈 회전 드론 뷰 (360° Orbital Drone View)]
    - Mode 1: [초고고도 수직 상승 크레인 샷 (Giant Crane Vertical Tilt-Up)]
    - Mode 2: [FPV 드론 다이브 급강하 (FPV Drone Dive & Flare)]
    - Mode 3: [광활한 해안선 수평 트래킹 헬리캠 (Horizon Coastal Tracking)]
    - Mode 4: [크레인 수직 하강 & 투시도 포커스 (Crane Tilt-Down & Focus)]
    - Mode 5: [다이내믹 360도 반경 롤링 패닝 (360° Arc Pan & Roll)]
    """
    import cv2
    clean_img = Image.open(img_path).convert("RGB")
    W = target_w or clean_img.width
    H = target_h or clean_img.height

    if clean_img.size != (W, H):
        ratio = max(W / clean_img.width, H / clean_img.height)
        clean_img = clean_img.resize((round(clean_img.width * ratio), round(clean_img.height * ratio)), Image.LANCZOS)
        l, t = (clean_img.width - W) // 2, (clean_img.height - H) // 2
        clean_img = clean_img.crop((l, t, l + W, t + H))
    
    # 회전 및 고배율 무빙 시 여백이 보이지 않도록 캔버스를 1.75배로 충분히 확장
    pad = 1.75
    big_w, big_h = int(W * pad), int(H * pad)
    big_clean = clean_img.resize((big_w, big_h), Image.LANCZOS)
    src_clean = np.array(big_clean)[:, :, ::-1]  # BGR for OpenCV

    
    # INFO 타겟 이미지가 있을 경우 동일 캔버스로 준비
    src_info = None
    if info_img_path and Path(info_img_path).exists():
        try:
            info_img = Image.open(info_img_path).convert("RGB")
            big_info = info_img.resize((big_w, big_h), Image.LANCZOS)
            src_info = np.array(big_info)[:, :, ::-1]
        except Exception as ie:
            log.warning(f"INFO 이미지 로드 실패 ({ie}) → CLEAN 단독 모션")
    
    src = src_clean
    
    n = int(duration * fps)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    # 캔버스 중심 및 패닝 이동 최대 허용 폭 (강력한 기동)
    max_dx = (big_w - W) * 0.48
    max_dy = (big_h - H) * 0.48
    cx_base = big_w / 2.0
    cy_base = big_h / 2.0
    
    camera_mode = mode % 6
    
    for f in range(n):
        t = f / max(n - 1, 1)
        # 멈춤이나 감속 체감 없이 지속적으로 속도감이 느껴지는 80% 등속 + 20% 가속 커브
        v = 0.80 * t + 0.20 * (0.5 - 0.5 * math.cos(math.pi * t))
        
        angle = 0.0  # 카메라 롤 회전 각도 (Degrees)
        
        if camera_mode == 0:
            # 1. [FPV 오비탈 선회 궤적]: 정제된 3D 궤적 기동
            theta = 1.6 * math.pi * v
            scale = 1.04 + 0.16 * (v ** 0.85)
            cur_dx = max_dx * 0.40 * math.cos(theta)
            cur_dy = max_dy * 0.35 * math.sin(theta)
            angle = -2.5 * math.sin(theta)
            
        elif camera_mode == 1:
            # 2. [수직 상승 크레인 틸트업]: 하단에서 상부로 안정적 상승
            scale = 1.03 + 0.15 * v
            cur_dx = max_dx * 0.20 * (1.0 - 2.0 * t)
            cur_dy = max_dy * 0.50 * (1.0 - 2.0 * v)
            angle = 1.0 * (1.0 - 2.0 * t)
            
        elif camera_mode == 2:
            # 3. [FPV 다이브 포커스]: 상공에서 구조물 코앞으로 슬라이딩
            scale = 1.02 + 0.18 * (v ** 1.1)
            cur_dx = -max_dx * 0.35 * (1.0 - 2.0 * t)
            cur_dy = -max_dy * 0.40 * (1.0 - 2.0 * t)
            angle = 2.0 * math.sin(math.pi * t)
            
        elif camera_mode == 3:
            # 4. [해안선 수평 트래킹]: 수평선을 부드럽게 가로지르는 트래킹
            scale = 1.18 - 0.14 * v
            cur_dx = max_dx * 0.45 * (1.0 - 2.0 * t)
            cur_dy = max_dy * 0.20 * math.sin(math.pi * t)
            angle = -1.2 * (1.0 - 2.0 * t)
            
        elif camera_mode == 4:
            # 5. [수직 하강 투시도 포커스]: 상단에서 하단으로 안정적인 틸트다운
            scale = 1.16 - 0.12 * (v ** 0.9)
            cur_dx = -max_dx * 0.25 * (1.0 - 2.0 * t)
            cur_dy = -max_dy * 0.45 * (1.0 - 2.0 * v)
            angle = -1.0 * (1.0 - 2.0 * t)
            
        else:
            # 6. [아크 스위프]: 회전하며 다이내믹하게 빨려 들어가는 무빙
            theta = 1.2 * math.pi * v
            scale = 1.05 + 0.14 * math.sin(math.pi * v)
            cur_dx = -max_dx * 0.35 * math.cos(theta)
            cur_dy = max_dy * 0.35 * math.sin(theta)
            angle = 2.5 * math.cos(theta)
            
        # 미세 시네마틱 텐션
        micro_zoom = 1.0 + 0.015 * math.sin(4 * math.pi * t)
        scale *= micro_zoom

        # 목표 크롭 크기
        crop_w = int(W / scale)
        crop_h = int(H / scale)
        
        # 크롭 중심점 및 좌표 계산
        cx = cx_base + cur_dx
        cy = cy_base + cur_dy
        x1 = max(0, min(big_w - crop_w, int(cx - crop_w / 2)))
        y1 = max(0, min(big_h - crop_h, int(cy - crop_h / 2)))
        
        # MD Stage 6 규격: 0.0~0.5초 순수 CLEAN 유지 후, 0.5~2.2초에 걸쳐 INFO 레이어(치수, 지시선, 화살표)가 부드럽게 페이드인 안착
        current_time = t * duration
        if src_info is not None:
            if current_time < 0.5:
                blend_src = src_clean
            elif current_time < 2.2:
                alpha = (current_time - 0.5) / 1.7
                # 부드러운 S-커브 가중치
                alpha_smooth = 0.5 - 0.5 * math.cos(math.pi * alpha)
                blend_src = cv2.addWeighted(src_clean, 1.0 - alpha_smooth, src_info, alpha_smooth, 0)
            else:
                blend_src = src_info
        else:
            blend_src = src_clean

        cropped = blend_src[y1:y1 + crop_h, x1:x1 + crop_w]
        
        # 360도 회전 / 뱅크 롤링 앵글 적용
        if abs(angle) > 0.01:
            h_c, w_c = cropped.shape[:2]
            M = cv2.getRotationMatrix2D((w_c / 2, h_c / 2), angle, 1.0)
            cropped = cv2.warpAffine(cropped, M, (w_c, h_c), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            
        frame = cv2.resize(cropped, (W, H), interpolation=cv2.INTER_LINEAR)
        # 밝고 선명한 3D 다큐멘터리 톤 보정 (감마 1.05 및 미세 대비 강화로 칙칙함 완전 차단)
        frame = cv2.convertScaleAbs(frame, alpha=1.04, beta=5)
        proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        
    proc.stdin.close(); proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("시네마틱 카메라 무빙 인코딩 실패")
