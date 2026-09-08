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
                    strength=0.08):
    """신비한 건축사전식 고화질 시네마틱 3D 카메라 워킹 엔진 (GPU 불필요, 비용 0원).
    - Mode 0: [360도 오비탈 회전 드론 뷰 (360° Orbital Drone View)] - 구조물 주위를 궤도 회전하며 회전 각도와 줌을 동시에 전개
    - Mode 1: [초고고도 수직 상승 크레인 샷 (Giant Crane Vertical Tilt-Up)] - 기초 사석 마운드에서 아파트 10층 상판까지 수직 비상
    - Mode 2: [FPV 드론 다이브 급강하 (FPV Drone Dive & Flare)] - 고공에서 케이슨 유공벽/소파블록 전면으로 속도감 있게 급강하
    - Mode 3: [광활한 해안선 수평 트래킹 헬리캠 (Horizon Coastal Tracking)] - 수평선을 가로지르며 방파제 전체 전경을 유려하게 훑음
    - Mode 4: [크레인 수직 하강 & 투시도 포커스 (Crane Tilt-Down & Focus)] - 수면 상부에서 수중 기초 암반층으로 수직 하강
    - Mode 5: [다이내믹 360도 반경 롤링 패닝 (360° Arc Pan & Roll)] - 완만한 회전 궤적과 광각 돌리 줌 결합
    """
    import cv2
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    
    # 회전 및 고배율 무빙 시 여백이 보이지 않도록 캔버스를 1.55배 확장
    pad = 1.55
    big_w, big_h = int(W * pad), int(H * pad)
    big = img.resize((big_w, big_h), Image.LANCZOS)
    src = np.array(big)[:, :, ::-1]  # BGR for OpenCV
    
    n = int(duration * fps)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    # 캔버스 중심 및 최대 패닝 허용 폭
    max_dx = (big_w - W) * 0.46
    max_dy = (big_h - H) * 0.46
    cx_base = big_w / 2.0
    cy_base = big_h / 2.0
    
    camera_mode = mode % 6
    
    for f in range(n):
        t = f / max(n - 1, 1)
        # 단 1밀리초도 멈추지 않는 선형 등속도 65% + 부드러운 가속도 35% 지속 속도 함수
        v = 0.65 * t + 0.35 * (0.5 - 0.5 * math.cos(math.pi * t))
        
        angle = 0.0  # 카메라 롤 회전 각도 (Degrees)
        
        if camera_mode == 0:
            # 1. [360도 오비탈 회전 드론 뷰어]: 타원형 360 궤도 회전 + 서서히 구조물로 파고드는 줌인
            theta = 2.0 * math.pi * v
            scale = 1.05 + 0.28 * v
            cur_dx = max_dx * 0.85 * math.cos(theta)
            cur_dy = max_dy * 0.70 * math.sin(theta)
            angle = -3.5 * math.sin(theta)  # 드론 선회 비행 시 자연스러운 뱅크 각도
            
        elif camera_mode == 1:
            # 2. [초고고도 수직 상승 크레인 샷 (Tilt-Up)]: 수중 기초 바닥에서 케이슨 상판까지 거대 크레인 비상
            scale = 1.04 + 0.25 * v
            cur_dx = max_dx * 0.25 * (1.0 - 2.0 * t)
            cur_dy = max_dy * (1.0 - 2.0 * v)  # 하단에서 상단으로 강력한 수직 상승
            angle = 0.8 * (1.0 - 2.0 * t)
            
        elif camera_mode == 2:
            # 3. [FPV 드론 다이브 급강하]: 상공에서 케이슨 유공벽/소파블록을 향해 쏜살같이 파고듦
            scale = 1.02 + 0.38 * (v ** 1.3)  # 점점 더 빨라지는 돌진 다이브
            cur_dx = -max_dx * 0.6 * (1.0 - 2.0 * t)
            cur_dy = -max_dy * 0.7 * (1.0 - 2.0 * t)
            angle = 2.5 * math.sin(math.pi * t)
            
        elif camera_mode == 3:
            # 4. [수평선 광각 트래킹 헬리캠]: 수평선을 가로지르며 방파제 전체 라인을 시네마틱하게 질주
            scale = 1.32 - 0.26 * v
            cur_dx = max_dx * (1.0 - 2.0 * t)   # 우측에서 좌측으로 고속 수평 트래킹
            cur_dy = max_dy * 0.30 * math.sin(math.pi * t)
            angle = -1.5 * (1.0 - 2.0 * t)
            
        elif camera_mode == 4:
            # 5. [크레인 수직 하강 & 투시도 포커스 (Tilt-Down)]: 상공 조감도에서 수중 사석 마운드 단면으로 하강
            scale = 1.30 - 0.22 * v
            cur_dx = -max_dx * 0.3 * (1.0 - 2.0 * t)
            cur_dy = -max_dy * (1.0 - 2.0 * v)  # 상단에서 하단으로 수직 하강
            angle = -0.8 * (1.0 - 2.0 * t)
            
        else:
            # 6. [360도 반경 롤링 아크 샷 (Arc Pan)]: 반원형 곡선 궤도로 구조물을 훑으며 드라마틱 롤링
            theta = math.pi * v
            scale = 1.08 + 0.26 * math.sin(theta)
            cur_dx = -max_dx * math.cos(theta)
            cur_dy = max_dy * 0.5 * math.sin(theta)
            angle = 3.0 * math.cos(theta)
            
        # 목표 크롭 크기
        crop_w = int(W / scale)
        crop_h = int(H / scale)
        
        # 크롭 중심점
        cx = cx_base + cur_dx
        cy = cy_base + cur_dy
        
        x1 = max(0, min(big_w - crop_w, int(cx - crop_w / 2)))
        y1 = max(0, min(big_h - crop_h, int(cy - crop_h / 2)))
        
        cropped = src[y1:y1 + crop_h, x1:x1 + crop_w]
        
        # 360도 회전 / 뱅크 롤링 앵글 적용
        if abs(angle) > 0.01:
            h_c, w_c = cropped.shape[:2]
            M = cv2.getRotationMatrix2D((w_c / 2, h_c / 2), angle, 1.0)
            cropped = cv2.warpAffine(cropped, M, (w_c, h_c), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            
        frame = cv2.resize(cropped, (W, H), interpolation=cv2.INTER_LINEAR)
        proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        
    proc.stdin.close(); proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("시네마틱 카메라 무빙 인코딩 실패")
