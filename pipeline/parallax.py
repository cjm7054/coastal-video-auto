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
    """왜곡 없는 고화질 시네마틱 켄 번스(Ken Burns) 카메라 무빙.
    2D 평면을 무리하게 비틀어 생기는 젤리 현상/찢어짐을 완전히 방지하고,
    다큐멘터리 방송 스타일의 우아하고 부드러운 고화질 줌인/줌아웃/패닝을 수행.
    mode: 0 돌리인+우측팬, 1 돌리아웃+좌측팬, 2 상승 틸트+줌인, 3 하강 틸트+줌아웃"""
    import cv2
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    
    # 역동적인 고배율 캔버스 확장 (광각 패닝 및 강력한 줌인/줌아웃 무빙용)
    pad = 1.38
    big_w, big_h = int(W * pad), int(H * pad)
    big = img.resize((big_w, big_h), Image.LANCZOS)
    src = np.array(big)[:, :, ::-1]  # BGR for cv2
    
    n = int(duration * fps)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    # 캔버스 패닝 이동 최대폭
    max_dx = (big_w - W) * 0.48
    max_dy = (big_h - H) * 0.48
    
    for f in range(n):
        t = f / max(n - 1, 1)
        # 단 한 순간도 정지하지 않는 지속 이동 커브 (선형 등속도 60% + 부드러운 가속도 40% 결합)
        # 코사인 커브만 쓰면 시작과 끝점(t=0, t=1) 미분값이 0이 되어 순간 멈춤 느낌이 나므로, 선형 t를 결합해 항상 초당 일정 픽셀 이상 지속 이동 보장!
        v = 0.6 * t + 0.4 * (0.5 - 0.5 * math.cos(math.pi * t))
        
        if mode == 0:
            # 1. 광각 돌리 줌인 (1.0 -> 1.34) + 좌하단에서 우상단으로 속도감 있는 전진 패닝
            scale = 1.0 + 0.34 * v
            cur_dx = -max_dx * (1.0 - 2.0 * t)
            cur_dy = -max_dy * 0.6 * (1.0 - 2.0 * t)
        elif mode == 1:
            # 2. 광각 돌리 줌아웃 (1.35 -> 1.02) + 우측에서 좌측으로 역동적 수평 트래킹
            scale = 1.35 - 0.33 * v
            cur_dx = max_dx * (1.0 - 2.0 * t)
            cur_dy = max_dy * 0.35 * (1.0 - 2.0 * t)
        elif mode == 2:
            # 3. 웅장한 크레인 수직 상승 (Tilt-Up) + 집중 줌인 (1.04 -> 1.30)
            scale = 1.04 + 0.26 * v
            cur_dx = max_dx * 0.4 * (1.0 - 2.0 * t)
            cur_dy = max_dy * (1.0 - 2.0 * t)
        else:
            # 4. 하강 헬리캠 샷 (Tilt-Down) + 대각선 오비탈 패닝 (1.32 -> 1.05)
            scale = 1.32 - 0.27 * v
            cur_dx = -max_dx * 0.45 * (1.0 - 2.0 * t)
            cur_dy = -max_dy * (1.0 - 2.0 * t)
        
        # 현재 크기
        crop_w = int(W / scale)
        crop_h = int(H / scale)
        
        # 크롭 중심점
        cx = (big_w / 2) + cur_dx
        cy = (big_h / 2) + cur_dy
        
        x1 = max(0, min(big_w - crop_w, int(cx - crop_w / 2)))
        y1 = max(0, min(big_h - crop_h, int(cy - crop_h / 2)))
        
        cropped = src[y1:y1 + crop_h, x1:x1 + crop_w]
        frame = cv2.resize(cropped, (W, H), interpolation=cv2.INTER_LINEAR)
        proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        
    proc.stdin.close(); proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("카메라 무빙 인코딩 실패")
