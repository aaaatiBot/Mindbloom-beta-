"""
sfx.py — MindBloom Sound Effects Engine
========================================
Generates all UI and game sounds procedurally using numpy sine/square waves.
No external audio files required.

Usage
-----
    from sfx import SFX
    sfx = SFX()
    sfx.play("click")       # UI button click
    sfx.play("hover")       # subtle hover tick
    sfx.play("correct")     # ascending chime (correct answer)
    sfx.play("win")         # triumphant chord (game won)
    sfx.play("flip")        # card flip whoosh
    sfx.play("reveal")      # soft reveal shimmer
    sfx.set_volume(0.4)     # master volume (0.0 – 1.0)
"""

import pygame

# numpy is optional — if missing, all sounds are silently skipped
try:
    import numpy as np
    _NP = True
except ImportError:
    _NP = False


# ── Low-level wave builders ────────────────────────────────────────────────

def _silence(sr, dur):
    n = int(sr * dur)
    return np.zeros(n, dtype=np.float32)

def _sine(sr, freq, dur, vol=1.0):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * vol).astype(np.float32)

def _square(sr, freq, dur, vol=1.0, duty=0.5):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wave = np.where((t * freq) % 1.0 < duty, 1.0, -1.0)
    return (wave * vol).astype(np.float32)

def _envelope(wave, attack=0.01, release=0.05, sr=44100):
    n = len(wave)
    env = np.ones(n, dtype=np.float32)
    a = int(attack * sr)
    r = int(release * sr)
    if a: env[:a]  = np.linspace(0, 1, a)
    if r: env[-r:] = np.linspace(1, 0, r)
    return wave * env

def _to_sound(wave, sr=44100, vol=1.0):
    """Convert a float32 mono wave to a pygame.mixer.Sound."""
    pcm    = np.clip(wave * vol, -1.0, 1.0)
    pcm16  = (pcm * 28000).astype(np.int16)
    stereo = np.column_stack([pcm16, pcm16])
    return pygame.sndarray.make_sound(stereo)

def _mix(*waves):
    """Mix multiple waves of possibly different lengths by zero-padding."""
    max_len = max(len(w) for w in waves)
    out = np.zeros(max_len, dtype=np.float32)
    for w in waves:
        out[:len(w)] += w
    # Normalise to avoid clipping
    peak = np.max(np.abs(out))
    if peak > 0:
        out /= peak
    return out


# ── Individual sound recipes ───────────────────────────────────────────────

def _make_click(sr=44100):
    """Short, clean high-pitched tick — UI button press."""
    wave = _sine(sr, 880, 0.06, 0.6)
    wave = _envelope(wave, attack=0.002, release=0.04, sr=sr)
    return _to_sound(wave, sr, vol=0.5)

def _make_hover(sr=44100):
    """Ultra-soft 1200 Hz tick — card/button hover."""
    wave = _sine(sr, 1200, 0.03, 0.3)
    wave = _envelope(wave, attack=0.002, release=0.025, sr=sr)
    return _to_sound(wave, sr, vol=0.25)

def _make_correct(sr=44100):
    """Warm C5-E5-G5 ascending arpeggio — correct answer."""
    notes = [523.25, 659.25, 783.99]   # C5, E5, G5
    total = _silence(sr, 0.75)
    offset = 0
    step   = int(sr * 0.22)
    for freq in notes:
        wave = _sine(sr, freq, 0.35, 0.8)
        wave = _envelope(wave, attack=0.01, release=0.12, sr=sr)
        end = offset + len(wave)
        if end > len(total):
            total = np.append(total, np.zeros(end - len(total)))
        total[offset:end] += wave
        offset += step
    total = np.clip(total / np.max(np.abs(total) + 1e-6), -1, 1)
    return _to_sound(total.astype(np.float32), sr, vol=0.55)

def _make_win(sr=44100):
    """Full C major chord + shimmer — game complete / win screen."""
    freqs = [261.63, 329.63, 392.00, 523.25]   # C4, E4, G4, C5
    waves = [_envelope(_sine(sr, f, 1.2, 0.5), attack=0.02, release=0.3, sr=sr)
             for f in freqs]
    chord = _mix(*waves)
    # Add a bright shimmer overtone
    shimmer = _envelope(_sine(sr, 1046.5, 0.5, 0.25), attack=0.01, release=0.2, sr=sr)
    total_len = max(len(chord), len(shimmer))
    out = np.zeros(total_len, dtype=np.float32)
    out[:len(chord)]   += chord
    out[:len(shimmer)] += shimmer
    out = np.clip(out / (np.max(np.abs(out)) + 1e-6), -1, 1)
    return _to_sound(out.astype(np.float32), sr, vol=0.6)

def _make_flip(sr=44100):
    """Soft whoosh — card flip."""
    dur  = 0.12
    t    = np.linspace(0, dur, int(sr * dur), endpoint=False)
    # Frequency sweep 400→200 Hz
    freq = np.linspace(400, 200, len(t))
    wave = np.sin(2 * np.pi * np.cumsum(freq) / sr).astype(np.float32)
    wave = _envelope(wave, attack=0.005, release=0.06, sr=sr)
    return _to_sound(wave * 0.4, sr, vol=0.4)

def _make_reveal(sr=44100):
    """Bright shimmer — image reveal."""
    wave = _sine(sr, 1568.0, 0.18, 0.5)   # G6
    wave = _envelope(wave, attack=0.005, release=0.12, sr=sr)
    return _to_sound(wave, sr, vol=0.4)

def _make_back(sr=44100):
    """Descending two-note — back/home navigation."""
    n1 = _envelope(_sine(sr, 659.25, 0.12, 0.6), attack=0.005, release=0.08, sr=sr)
    n2 = _envelope(_sine(sr, 523.25, 0.14, 0.6), attack=0.005, release=0.10, sr=sr)
    total = np.zeros(int(sr * 0.3), dtype=np.float32)
    total[:len(n1)] += n1
    total[int(sr*0.14):int(sr*0.14)+len(n2)] += n2
    total = np.clip(total / (np.max(np.abs(total)) + 1e-6), -1, 1)
    return _to_sound(total.astype(np.float32), sr, vol=0.45)

def _make_start(sr=44100):
    """Upward sweep + chime — game start."""
    t    = np.linspace(0, 0.3, int(sr * 0.3), endpoint=False)
    freq = np.linspace(300, 700, len(t))
    sweep = np.sin(2 * np.pi * np.cumsum(freq) / sr).astype(np.float32)
    sweep = _envelope(sweep, attack=0.01, release=0.1, sr=sr)
    chime = _envelope(_sine(sr, 880, 0.3, 0.6), attack=0.005, release=0.15, sr=sr)
    total = _mix(sweep * 0.5, chime)
    return _to_sound(total.astype(np.float32), sr, vol=0.5)


# ── Public SFX manager ─────────────────────────────────────────────────────

class SFX:
    """
    Lazy-loads all sounds on first use.  Silently skips if numpy or
    pygame.mixer are unavailable.

    Sounds
    ------
    click    – button pressed
    hover    – button/card hovered
    correct  – correct answer (C-E-G arpeggio)
    win      – game won (full chord)
    flip     – card flipped
    reveal   – image revealed
    back     – home / back navigation
    start    – game starting
    """

    _RECIPES = {
        "click"  : _make_click,
        "hover"  : _make_hover,
        "correct": _make_correct,
        "win"    : _make_win,
        "flip"   : _make_flip,
        "reveal" : _make_reveal,
        "back"   : _make_back,
        "start"  : _make_start,
    }

    def __init__(self, master_volume: float = 0.5):
        self._cache: dict = {}
        self._vol = master_volume
        self._ok  = False
        self._init_mixer()

    def _init_mixer(self):
        if not _NP:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._ok = True
        except Exception:
            pass

    def _load(self, name: str):
        if name in self._cache:
            return self._cache[name]
        if not self._ok or name not in self._RECIPES:
            return None
        try:
            sound = self._RECIPES[name]()
            if sound:
                sound.set_volume(self._vol)
            self._cache[name] = sound
            return sound
        except Exception:
            self._cache[name] = None
            return None

    def play(self, name: str):
        """Play a named sound (non-blocking).  Silently ignores failures."""
        s = self._load(name)
        if s:
            try: s.play()
            except Exception: pass

    def set_volume(self, vol: float):
        """Set master volume (0.0–1.0) and update all cached sounds."""
        self._vol = max(0.0, min(1.0, vol))
        for s in self._cache.values():
            if s:
                try: s.set_volume(self._vol)
                except Exception: pass


# Singleton — import and share across modules
sfx = SFX(master_volume=0.45)
