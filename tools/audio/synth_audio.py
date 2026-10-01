#!/usr/bin/env python3
"""Procedurally synthesise the game's placeholder audio (no licensed samples needed).
Writes 16-bit 48 kHz WAVs to ~/gta-india/assets/audio/."""
import os
import wave

import numpy as np

SR = 48000
OUT = os.path.expanduser("~/gta-india/assets/audio")
rng = np.random.default_rng(7)


def write(name, x, stereo=False):
    os.makedirs(OUT, exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    peak = np.max(np.abs(x)) or 1.0
    x = x / peak * 0.89
    data = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.T.flatten().tobytes() if stereo else data.tobytes())
    print("wrote", name, round(len(x if not stereo else x[0]) / SR, 2), "s")


def t(sec):
    return np.arange(int(sec * SR)) / SR


def onepole_lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def fast_lp(x, cutoff):
    """FFT brick-ish low-pass (fast for long signals)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def fast_bp(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (1 / (1 + (f / hi) ** 4)) * (1 - 1 / (1 + (f / lo) ** 4))
    return np.fft.irfft(X, len(x))


def loopable(x, fade=1.0):
    """Crossfade the tail into the head so the clip loops seamlessly."""
    n = int(fade * SR)
    head, body, tail = x[:n], x[n:-n] if len(x) > 2 * n else x[n:], x[-n:]
    w = np.linspace(0, 1, n)
    mixed = tail * (1 - w) + head * w
    return np.concatenate([mixed, x[n:-n]])


def slow_env(sec, rate, depth, seed=0):
    r = np.random.default_rng(seed)
    pts = r.random(int(sec * rate) + 3)
    xs = np.linspace(0, sec, len(pts))
    return 1 - depth + depth * np.interp(t(sec), xs, pts)


def river(sec=40):
    n = rng.standard_normal(int(sec * SR))
    brown = np.cumsum(n)
    brown -= fast_lp(brown, 0.5)  # remove drift
    base = fast_lp(brown, 500) * slow_env(sec, 0.3, 0.4, 1)
    lap = fast_bp(rng.standard_normal(int(sec * SR)), 300, 2500)
    # water lapping: short swells
    env = np.zeros(int(sec * SR))
    for _ in range(int(sec * 1.4)):
        c = rng.integers(0, len(env))
        L = int(rng.uniform(0.25, 0.9) * SR)
        seg = np.sin(np.linspace(0, np.pi, L)) ** 2 * rng.uniform(0.3, 1.0)
        env[c:c + L] += seg[: max(0, min(L, len(env) - c))]
    x = base / np.std(base) * 0.6 + lap / np.std(lap) * env * 0.35
    return loopable(x, 1.5)


def city(sec=45):
    n = int(sec * SR)
    hum = fast_bp(rng.standard_normal(n), 60, 400) * slow_env(sec, 0.2, 0.3, 2)
    murmur = fast_bp(rng.standard_normal(n), 250, 1800) * slow_env(sec, 1.5, 0.6, 3)
    x = hum / np.std(hum) * 0.5 + murmur / np.std(murmur) * 0.25
    tt = t(sec)
    for _ in range(int(sec / 3.5)):  # distant horns
        c = rng.uniform(0, sec - 1.5)
        f = rng.choice([392, 440, 466, 523, 587])
        dur = rng.uniform(0.15, 0.6)
        m = (tt >= c) & (tt < c + dur)
        tone = np.sign(np.sin(2 * np.pi * f * tt[m])) * 0.5 + np.sin(2 * np.pi * f * 1.5 * tt[m]) * 0.3
        env = np.minimum(1, np.minimum((tt[m] - c) / 0.02, (c + dur - tt[m]) / 0.03))
        x[m] += tone * env * rng.uniform(0.08, 0.2)
    for _ in range(int(sec / 6)):  # bicycle bells / rickshaw bells
        c = rng.uniform(0, sec - 1)
        for k in range(2):
            s = c + k * 0.18
            m = (tt >= s) & (tt < s + 0.5)
            x[m] += np.sin(2 * np.pi * 2600 * tt[m]) * np.exp(-(tt[m] - s) * 12) * 0.12
    return loopable(fast_lp(x, 6000), 1.5)


def bell_strike(dur=4.0, f0=620):
    tt = t(dur)
    partials = [(1.0, 1.0, 1.2), (2.01, 0.6, 2.0), (2.76, 0.45, 2.6), (4.07, 0.3, 3.5), (5.43, 0.2, 5.0), (0.5, 0.35, 0.8)]
    x = sum(a * np.sin(2 * np.pi * f0 * r * tt + rng.uniform(0, 6)) * np.exp(-tt * d) for r, a, d in partials)
    x *= 1 + 0.15 * np.sin(2 * np.pi * 3.2 * tt)
    return x


def temple_bells(sec=30):
    x = np.zeros(int(sec * SR))
    c = 1.0
    while c < sec - 5:
        strikes = rng.integers(2, 6)
        for k in range(strikes):
            s = int((c + k * rng.uniform(0.35, 0.6)) * SR)
            b = bell_strike(4.0, rng.choice([580, 620, 700, 820]))
            x[s:s + len(b)] += b[: len(x) - s] * rng.uniform(0.6, 1.0)
        c += rng.uniform(6, 11)
    return x


def train_horn():
    tt = t(2.4)
    f = [311.1, 370.0, 466.2]
    saw = lambda fr: 2 * ((tt * fr) % 1) - 1
    x = sum(saw(fr) for fr in f)
    x = fast_lp(x, 2500)
    env = np.minimum(1, tt / 0.08) * np.clip((2.4 - tt) / 0.25, 0, 1)
    env *= 1 + 0.05 * np.sin(2 * np.pi * 5 * tt)
    return x * env


def train_loop(sec=8.0):
    n = int(sec * SR)
    tt = t(sec)
    rumble = fast_bp(rng.standard_normal(n), 30, 250)
    rumble /= np.std(rumble)
    x = rumble * 0.6
    period = 1.1  # clack-clack per rail joint
    c = 0.1
    while c < sec - 0.3:
        for off in (0.0, 0.12):
            s = int((c + off) * SR)
            L = int(0.09 * SR)
            click = fast_bp(rng.standard_normal(L), 400, 3000) * np.exp(-np.linspace(0, 8, L))
            x[s:s + L] += click / (np.std(click) + 1e-9) * 0.5
        c += period
    return loopable(x, 0.4)


def bike_engine(sec=2.0, rpm=1800):
    """Single-cylinder four-stroke thump; the game shifts pitch with speed."""
    tt = t(sec)
    fire = rpm / 60 / 2  # firing frequency (Hz)
    x = np.zeros_like(tt)
    for h, a in ((1, 1.0), (2, 0.6), (3, 0.45), (4, 0.25), (6, 0.15), (8, 0.08)):
        x += a * np.sin(2 * np.pi * fire * h * tt + h)
    pulses = (np.sin(2 * np.pi * fire * tt) > 0.7).astype(float)
    x += fast_lp(pulses, 900) * 0.8
    x += fast_bp(rng.standard_normal(len(tt)), 800, 4000) * 0.08
    # make the length an integer number of cycles
    cycles = int(sec * fire)
    L = int(cycles / fire * SR)
    return fast_lp(x[:L], 3000)


def bike_horn():
    tt = t(0.9)
    x = np.zeros_like(tt)
    for s in (0.0, 0.42):
        m = (tt >= s) & (tt < s + 0.3)
        x[m] = (np.sign(np.sin(2 * np.pi * 420 * tt[m])) * 0.6 + np.sign(np.sin(2 * np.pi * 525 * tt[m])) * 0.4) * np.minimum(1, (tt[m] - s) / 0.01)
    return fast_lp(x, 3500)


def splash():
    tt = t(1.2)
    x = fast_bp(rng.standard_normal(len(tt)), 200, 5000) * np.exp(-tt * 4)
    x += fast_bp(rng.standard_normal(len(tt)), 80, 500) * np.exp(-tt * 7) * 2
    return x


def swim_stroke():
    tt = t(0.6)
    return fast_bp(rng.standard_normal(len(tt)), 300, 3500) * np.sin(np.pi * tt / 0.6) ** 2


def ui_click():
    tt = t(0.08)
    return np.sin(2 * np.pi * 1400 * tt) * np.exp(-tt * 60)


def cash():
    tt = t(0.9)
    x = bell_strike(0.9, 1800) * 0.4
    for s in (0.0, 0.08):
        m = tt >= s
        x[m] += np.sin(2 * np.pi * 2600 * (tt[m] - s)) * np.exp(-(tt[m] - s) * 10) * 0.6
    return x


if __name__ == "__main__":
    write("A_AmbRiver", river())
    write("A_AmbCity", city())
    write("A_TempleBells", temple_bells())
    write("S_TrainHorn", train_horn())
    write("A_TrainLoop", train_loop())
    write("A_BikeEngine", bike_engine())
    write("S_BikeHorn", bike_horn())
    write("S_Splash", splash())
    write("S_SwimStroke", swim_stroke())
    write("S_UIClick", ui_click())
    write("S_Cash", cash())
