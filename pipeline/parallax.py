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
                    strength=0.045):
    """깊이 기반 픽셀 변위(cv2.remap)로 프레임을 생성. 1080p 30fps 기준 초당 약 1초 렌더.
    mode: 0 돌리인+우측팬, 1 돌리아웃+좌측팬, 2 상승 틸트, 3 하강 틸트"""
    import cv2
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    pad = 1.10
    big = img.resize((int(W * pad), int(H * pad)), Image.LANCZOS)
    BW, BH = big.size
    depth = depth_map(big)
    depth = cv2.GaussianBlur(depth, (0, 0), 6)  # 경계 찢어짐 완화
    src = np.array(big)[:, :, ::-1].copy()  # BGR for cv2
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    cxb, cyb = BW / 2, BH / 2
    n = int(duration * fps)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    cx0, cy0 = (BW - W) // 2, (BH - H) // 2
    for f in range(n):
        t = f / max(n - 1, 1)
        e = 0.5 - 0.5 * math.cos(math.pi * t)
        if mode == 0:   zoom, dx, dy = 1.0 + 0.08 * e, -0.5 + e, 0.0
        elif mode == 1: zoom, dx, dy = 1.08 - 0.08 * e, 0.5 - e, 0.0
        elif mode == 2: zoom, dx, dy = 1.0 + 0.05 * e, 0.0, 0.5 - e
        else:           zoom, dx, dy = 1.05 - 0.05 * e, 0.0, -0.5 + e
        # 깊이에 따른 변위: 가까운 픽셀은 카메라 이동 반대방향으로 더 크게
        par = (depth - 0.5) * 2
        zdepth = 1.0 / (1.0 + (zoom - 1) * (0.6 + 0.8 * depth))  # 근경일수록 더 확대
        map_x = cxb + (xx - cxb) * zdepth - dx * strength * W * par
        map_y = cyb + (yy - cyb) * zdepth - dy * strength * H * par
        warped = cv2.remap(src, map_x.astype(np.float32), map_y.astype(np.float32),
                           cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        frame = warped[cy0:cy0 + H, cx0:cx0 + W, ::-1]
        proc.stdin.write(np.ascontiguousarray(frame).tobytes())
    proc.stdin.close(); proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("패럴랙스 인코딩 실패")
