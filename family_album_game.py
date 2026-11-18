"""
family_album_game.py
====================
MindBloom – Family Album Game
Themed to match the MindBloom suite (dark navy + grid background, purple
buttons, white text, rounded cards with white outlines).

Key fix vs. v1
--------------
  • During PLAY mode, photo cards show NO labels — the whole point is to
    recognise the face, not read the name.  Labels only appear on the card
    after a CORRECT match, as warm confirmation.
  • Visual theme now exactly matches picture_matching.py / mindbloom_gui.py:
    dark navy BG, subtle grid, purple buttons, blue home button, white text.

Design principles
-----------------
  NO timers  •  NO scores  •  NO error sounds  •  NO negative feedback
  Large visuals  •  High-contrast text  •  Short, warm phrases only

Entry point: call run() from mindbloom_gui.py or run this file directly.
"""

import os
import sys
import json
import random
import math
import threading
import pygame

# Tkinter is used only for file/text dialogs (not for any GUI widgets)
import tkinter as tk
from tkinter import filedialog, simpledialog

# Shared MindBloom sound effects (gracefully absent if sfx.py not found)
try:
    from sfx import sfx as _sfx
except ImportError:
    _sfx = None

# ═══════════════════════════════════════════════════════════════════════════
#  MINDBLOOM THEME  (copied exactly from picture_matching.py)
# ═══════════════════════════════════════════════════════════════════════════

BG          = (8,   27,  70)    # deep navy background
GRID        = (18,  43,  91)    # subtle grid lines
WHITE       = (250, 252, 255)   # primary text / outlines
PURPLE      = (116, 70,  224)   # button fill
PURPLE_DARK = (81,  46,  164)   # button shadow
PURPLE_LT   = (190, 153, 255)   # button outline / hover accent
CARD_BLUE   = (22,  55,  112)   # card background
CARD_BLUE_H = (33,  80,  160)   # card background on hover
GREEN       = (47,  190, 112)   # correct / positive accent
YELLOW      = (255, 207, 66)    # star / celebratory accent
SHADOW      = (3,   12,  35)    # drop-shadow colour
HOME_BLUE   = (43,  139, 242)   # home-button circle fill
HOME_BLU_LT = (113, 193, 255)   # home-button circle outline
TEXT_MID    = (175, 194, 225)   # secondary / hint text

# ═══════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SCREEN_W, SCREEN_H = 1280, 720
CARD_W, CARD_H     = 220, 220   # photo area inside each card
CARD_PAD           = 14         # padding around photo
CARD_RADIUS        = 18         # rounded corner radius
ROUNDS_TO_WIN      = 4          # correct answers to trigger completion
IMAGE_EXTS         = [("Images", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
                      ("All files", "*.*")]
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "family_data.json")

# ═══════════════════════════════════════════════════════════════════════════
#  FONT HELPER  (matches MindBloom style exactly)
# ═══════════════════════════════════════════════════════════════════════════

_font_cache: dict = {}

def fnt(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    f = None
    for name in ["arial", "segoeui", "dejavusans", "liberationsans"]:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            f = pygame.font.Font(path, size)
            break
    if f is None:
        f = pygame.font.Font(None, size)
    _font_cache[key] = f
    return f

# ═══════════════════════════════════════════════════════════════════════════
#  DATA PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════
#
#  family_data.json  — list of objects, one per person:
#  [
#    { "name": "Saloni", "relationship": "Daughter",
#      "photo_path": "C:/Users/.../saloni.jpg" },
#    ...
#  ]

def load_family_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [d for d in data
                    if isinstance(d, dict)
                    and d.get("name") and d.get("relationship")
                    and d.get("photo_path")]
        except (json.JSONDecodeError, OSError):
            return []
    return []

def save_family_data(members):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(members, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"[FamilyAlbum] Could not save: {e}")

# ═══════════════════════════════════════════════════════════════════════════
#  IMAGE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def load_photo(path, size):
    try:
        raw = pygame.image.load(path).convert_alpha()
        return scale_cover(raw, size)
    except Exception:
        return make_placeholder(size)

def scale_cover(surf, size):
    tw, th = size
    sw, sh = surf.get_size()
    ratio  = max(tw / sw, th / sh)
    nw, nh = int(sw * ratio), int(sh * ratio)
    scaled  = pygame.transform.smoothscale(surf, (nw, nh))
    ox, oy  = (nw - tw) // 2, (nh - th) // 2
    out     = pygame.Surface(size, pygame.SRCALPHA)
    out.blit(scaled, (0, 0), (ox, oy, tw, th))
    return out

def make_placeholder(size):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((30, 60, 110))
    cx, cy = size[0] // 2, size[1] // 2
    r = size[0] // 6
    pygame.draw.circle(surf, (80, 130, 200), (cx, cy - r), r)
    pygame.draw.ellipse(surf, (80, 130, 200),
                        pygame.Rect(cx - r, cy, r * 2, int(r * 1.4)))
    return surf

# ═══════════════════════════════════════════════════════════════════════════
#  DRAW HELPERS  (MindBloom style)
# ═══════════════════════════════════════════════════════════════════════════

def draw_grid_background(surface):
    """Navy background with subtle grid — matches all MindBloom games."""
    surface.fill(BG)
    w, h = surface.get_size()
    spacing = max(24, int(min(w, h) * 0.032))
    for x in range(0, w, spacing):
        pygame.draw.line(surface, GRID, (x, 0), (x, h), 1)
    for y in range(0, h, spacing):
        pygame.draw.line(surface, GRID, (0, y), (w, y), 1)

def rounded_rect(surface, color, rect, radius=18):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_text_center(surface, text, font_obj, color, center, max_w=None):
    if max_w:
        lines = _wrap(text, font_obj, max_w)
    else:
        lines = [text]
    lh = font_obj.get_linesize()
    y  = center[1] - lh * len(lines) // 2
    for line in lines:
        s = font_obj.render(line, True, color)
        surface.blit(s, (center[0] - s.get_width() // 2, y))
        y += lh

def _wrap(text, font_obj, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font_obj.size(test)[0] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines or [""]

def draw_star(surface, center, radius, color):
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        r   = radius if i % 2 == 0 else radius * 0.42
        pts.append((center[0] + math.cos(ang) * r,
                    center[1] + math.sin(ang) * r))
    pygame.draw.polygon(surface, color, pts)

def draw_home_button(surface, rect):
    """Circular blue home-button — identical to picture_matching.py."""
    sh = rect.copy(); sh.y += 5
    pygame.draw.ellipse(surface, SHADOW, sh)
    pygame.draw.ellipse(surface, HOME_BLUE, rect)
    pygame.draw.ellipse(surface, HOME_BLU_LT, rect, width=3)
    cx, cy = rect.center
    sz = rect.width * 0.34
    roof = [
        (cx,          cy - sz * 0.55),
        (cx - sz * 0.72, cy),
        (cx - sz * 0.48, cy),
        (cx - sz * 0.48, cy + sz * 0.58),
        (cx + sz * 0.48, cy + sz * 0.58),
        (cx + sz * 0.48, cy),
        (cx + sz * 0.72, cy),
    ]
    pygame.draw.polygon(surface, WHITE, roof)
    door = pygame.Rect(cx - sz * 0.14, cy + sz * 0.08,
                       sz * 0.28, sz * 0.50)
    pygame.draw.rect(surface, HOME_BLUE, door)

def draw_title_banner(surface, rect):
    """Purple banner with 'Family Album' — style matches MindBloom banners."""
    sh = rect.copy(); sh.y += 7
    rounded_rect(surface, PURPLE_DARK, sh, 35)
    rounded_rect(surface, PURPLE, rect, 35)
    pygame.draw.rect(surface, PURPLE_LT, rect, width=3, border_radius=35)
    title_f = fnt(max(26, min(44, int(rect.height * 0.52))), bold=True)
    draw_text_center(surface, "📸  Family Album", title_f, WHITE, rect.center)

def draw_purple_button(surface, rect, label, font_obj, hovered=False):
    """Standard MindBloom purple button with shadow + outline."""
    col = (139, 91, 245) if hovered else PURPLE
    sh  = rect.copy(); sh.y += 5
    rounded_rect(surface, SHADOW, sh, 20)
    rounded_rect(surface, col,    rect, 20)
    pygame.draw.rect(surface, PURPLE_LT, rect, width=3, border_radius=20)
    draw_text_center(surface, label, font_obj, WHITE, rect.center)

# ═══════════════════════════════════════════════════════════════════════════
#  TKINTER FILE / TEXT DIALOGS  (run in background threads)
# ═══════════════════════════════════════════════════════════════════════════

def _pick_file_threaded(holder):
    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
    path = filedialog.askopenfilename(title="Choose a family photo",
                                      filetypes=IMAGE_EXTS)
    root.destroy(); holder[0] = path

def _ask_string_threaded(prompt, title, holder):
    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
    value = simpledialog.askstring(title, prompt, parent=root)
    root.destroy(); holder[0] = value or ""

def _run_in_thread(fn, *args):
    done = threading.Event()
    def wrapper(): fn(*args); done.set()
    threading.Thread(target=wrapper, daemon=True).start()
    while not done.is_set():
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: done.set()
        pygame.time.wait(40)

def pick_photo_path():
    h = [None]; _run_in_thread(_pick_file_threaded, h); return h[0] or ""

def ask_string(prompt, title="Family Album"):
    h = [None]; _run_in_thread(_ask_string_threaded, prompt, title, h)
    return h[0] or ""

# ═══════════════════════════════════════════════════════════════════════════
#  OPTIONAL GENTLE CHIME
# ═══════════════════════════════════════════════════════════════════════════

def _generate_chime():
    try:
        import numpy as np
        sr  = 44100; dur = 0.6; freq = 523.25
        t   = np.linspace(0, dur, int(sr * dur), endpoint=False)
        wav = np.sin(2 * np.pi * freq * t)
        fade = int(sr * 0.05)
        wav[:fade]  *= np.linspace(0, 1, fade)
        wav[-fade:] *= np.linspace(1, 0, fade)
        pcm    = (wav * 24000).astype(np.int16)
        stereo = np.column_stack([pcm, pcm])
        return pygame.sndarray.make_sound(stereo)
    except Exception:
        return None

# ═══════════════════════════════════════════════════════════════════════════
#  PHOTO CARD
# ═══════════════════════════════════════════════════════════════════════════

class PhotoCard:
    """
    A clickable photo card shown during Play Mode.

    CRITICAL DESIGN RULE — labels are hidden during play:
      • idle / hover  → photo only, NO name or relationship shown.
                        This forces recognition of the face, not reading text.
      • correct       → gentle green glow + name shown as warm confirmation.

    Wrong clicks do NOTHING (no border change, no sound, no message).
    """

    def __init__(self, member, photo_surf, full_rect):
        self.member    = member
        self.photo     = photo_surf          # CARD_W × CARD_H surface
        self.rect      = pygame.Rect(full_rect)   # full card rect incl. padding
        self.state     = "idle"              # "idle" | "hover" | "correct"

    # photo area (inset from the card border by CARD_PAD)
    @property
    def photo_rect(self):
        return pygame.Rect(self.rect.x + CARD_PAD,
                           self.rect.y + CARD_PAD,
                           CARD_W, CARD_H)

    def draw(self, surface):
        pr = self.photo_rect

        # ── shadow ────────────────────────────────────────────────────────
        sh = self.rect.copy(); sh.y += 6
        rounded_rect(surface, SHADOW, sh, CARD_RADIUS)

        # ── card background ───────────────────────────────────────────────
        bg_col = CARD_BLUE_H if self.state == "hover" else CARD_BLUE
        if self.state == "correct":
            bg_col = (15, 60, 40)   # dark green tint for confirmed card
        rounded_rect(surface, bg_col, self.rect, CARD_RADIUS)

        # ── border ────────────────────────────────────────────────────────
        if self.state == "correct":
            border_col = GREEN;  bw = 4
        elif self.state == "hover":
            border_col = (113, 193, 255); bw = 3   # light blue on hover
        else:
            border_col = WHITE;  bw = 2
        pygame.draw.rect(surface, border_col, self.rect,
                         width=bw, border_radius=CARD_RADIUS)

        # ── photo ─────────────────────────────────────────────────────────
        surface.blit(self.photo, pr.topleft)

        # ── label — ONLY shown after a correct match ──────────────────────
        if self.state == "correct":
            name_f = fnt(max(22, int(self.rect.width * 0.13)), bold=True)
            rel_f  = fnt(max(17, int(self.rect.width * 0.10)))

            name_surf = name_f.render(self.member["name"], True, GREEN)
            rel_surf  = rel_f.render(self.member["relationship"],
                                     True, (140, 220, 160))

            label_y = pr.bottom + 6
            surface.blit(name_surf,
                         (self.rect.centerx - name_surf.get_width() // 2,
                          label_y))
            surface.blit(rel_surf,
                         (self.rect.centerx - rel_surf.get_width() // 2,
                          label_y + name_f.get_linesize() + 2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            if self.state != "correct":
                self.state = ("hover"
                              if self.rect.collidepoint(event.pos)
                              else "idle")
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def mark_correct(self):
        self.state = "correct"

    def reset(self):
        self.state = "idle"

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN GAME CLASS
# ═══════════════════════════════════════════════════════════════════════════

class FamilyAlbumGame:
    """
    States:  menu → setup → play → correct → complete
    """

    def __init__(self, screen, clock, return_callback=None):
        self.screen          = screen
        self.clock           = clock
        self.return_callback = return_callback
        self.running         = True
        self.state           = "menu"

        self.members         = load_family_data()
        self.cards           = []
        self.correct_member  = None
        self.question_text   = ""
        self.score           = 0
        self.flash_msg       = ""
        self.round_locked    = False

        self._init_audio()

    # ── audio ──────────────────────────────────────────────────────────────
    def _init_audio(self):
        # Audio handled by shared sfx module; keep _generate_chime as fallback
        self.chime = None
        if _sfx is None:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16,
                                      channels=2, buffer=512)
                self.chime = _generate_chime()
                if self.chime:
                    self.chime.set_volume(0.35)
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════════════
    #  PLAY MODE
    # ══════════════════════════════════════════════════════════════════════

    def _start_play(self):
        self.state = "play"
        self.score = 0
        self._new_round()

    def _new_round(self):
        self.round_locked = False
        self.flash_msg    = ""

        if len(self.members) < 2:
            self.state = "menu"; return

        sw, sh = self.screen.get_size()

        # Pick correct answer + up-to-3 distractors
        self.correct_member = random.choice(self.members)
        others      = [m for m in self.members if m != self.correct_member]
        num_dist    = min(3, len(others))
        all_choices = [self.correct_member] + random.sample(others, num_dist)
        random.shuffle(all_choices)
        n = len(all_choices)

        # Question text
        if random.random() < 0.5:
            self.question_text = (
                f"Who is your {self.correct_member['relationship'].lower()}?"
            )
        else:
            self.question_text = f"Can you find {self.correct_member['name']}?"

        # Card layout
        # Each card = CARD_W + 2*CARD_PAD wide, plus label area height below
        label_h    = fnt(26, True).get_linesize() + fnt(20).get_linesize() + 10
        card_full_w = CARD_W + CARD_PAD * 2
        card_full_h = CARD_H + CARD_PAD * 2 + label_h
        gap         = max(20, int(sw * 0.03))
        total_w     = n * card_full_w + (n - 1) * gap
        # Push cards down — leave ~30% of screen height for question
        top_margin  = int(sh * 0.30)
        avail_h     = sh - top_margin - 20
        start_x     = (sw - total_w) // 2
        start_y     = top_margin + (avail_h - card_full_h) // 2

        self.cards = []
        for i, member in enumerate(all_choices):
            photo = load_photo(member["photo_path"], (CARD_W, CARD_H))
            rect  = pygame.Rect(start_x + i * (card_full_w + gap),
                                start_y,
                                card_full_w,
                                card_full_h)
            self.cards.append(PhotoCard(member, photo, rect))

    # ══════════════════════════════════════════════════════════════════════
    #  SETUP MODE
    # ══════════════════════════════════════════════════════════════════════

    def _add_family_member(self):
        """3-step caregiver dialog: pick photo → name → relationship."""
        path = pick_photo_path()
        if not path: return

        name = ask_string("Enter their first name  (e.g. Saloni):",
                          "Add Family Member")
        if not name.strip(): return

        rel = ask_string(
            f"What is {name.strip()}'s relationship?\n"
            "(e.g.  Daughter, Son, Sister, Friend …)",
            "Add Family Member")
        if not rel.strip(): return

        self.members.append({
            "name":         name.strip().title(),
            "relationship": rel.strip().title(),
            "photo_path":   os.path.abspath(path),
        })
        save_family_data(self.members)

    def _remove_member(self, index):
        if 0 <= index < len(self.members):
            self.members.pop(index)
            save_family_data(self.members)

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN LOOP
    # ══════════════════════════════════════════════════════════════════════

    def run(self):
        while self.running:
            dt = self.clock.tick(60)
            self._handle_events()
            self._draw()
            pygame.display.flip()

    # ══════════════════════════════════════════════════════════════════════
    #  EVENTS
    # ══════════════════════════════════════════════════════════════════════

    def _handle_events(self):
        sw, sh = self.screen.get_size()
        mouse  = pygame.mouse.get_pos()
        home_rect = pygame.Rect(18, 14, 56, 56)   # circular home button

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # Home button — always active
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and home_rect.collidepoint(event.pos)):
                self._go_home(); return

            if self.state == "menu":
                self._ev_menu(event, sw, sh)
            elif self.state == "setup":
                self._ev_setup(event, sw, sh)
            elif self.state == "play":
                self._ev_play(event)
            elif self.state == "correct":
                self._ev_correct(event, sw, sh)
            elif self.state == "complete":
                self._ev_complete(event, sw, sh)

    def _ev_menu(self, event, sw, sh):
        play_rect  = self._btn_rect_centered(sw, sh, 0.56, 240, 54)   # must match _draw_menu
        setup_rect = self._btn_rect_centered(sw, sh, 0.68, 220, 50)   # must match _draw_menu

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if play_rect.collidepoint(event.pos) and len(self.members) >= 2:
                self._start_play()
            elif setup_rect.collidepoint(event.pos):
                self.state = "setup"
            elif play_rect.collidepoint(event.pos) and len(self.members) < 2:
                self.state = "setup"   # nudge to add photos first

    def _ev_setup(self, event, sw, sh):
        add_rect  = pygame.Rect(sw // 2 - 240, sh - 72, 210, 50)
        done_rect = pygame.Rect(sw // 2 + 50,  sh - 72, 170, 50)

        # Per-member remove buttons (y positions match _draw_setup)
        thumb_s, row_h = 60, 76
        list_top = 130

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if add_rect.collidepoint(event.pos):
                if _sfx: _sfx.play("click")
                self._add_family_member()
            elif done_rect.collidepoint(event.pos):
                if _sfx: _sfx.play("click")
                self.state = "menu"
            else:
                for i in range(len(self.members)):
                    rb = pygame.Rect(sw - 190,
                                     list_top + i * row_h + 8, 140, 40)
                    if rb.collidepoint(event.pos):
                        self._remove_member(i); break

    def _ev_play(self, event):
        if self.round_locked: return
        for card in self.cards:
            if card.handle_event(event):
                self._on_card_clicked(card)
                break
        # hover updates for cards not clicked
        for card in self.cards:
            card.handle_event(event)

    def _ev_correct(self, event, sw, sh):
        next_rect = self._btn_rect_centered(sw, sh, 0.87, 220, 52)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if next_rect.collidepoint(event.pos):
                self._advance()

    def _ev_complete(self, event, sw, sh):
        again_rect  = pygame.Rect(sw // 2 - 250, int(sh * 0.65), 230, 56)
        return_rect = pygame.Rect(sw // 2 + 20,  int(sh * 0.65), 230, 56)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if again_rect.collidepoint(event.pos):
                self._start_play()
            elif return_rect.collidepoint(event.pos):
                self._go_home()

    # ══════════════════════════════════════════════════════════════════════
    #  GAME LOGIC
    # ══════════════════════════════════════════════════════════════════════

    def _on_card_clicked(self, card):
        """
        DEMENTIA-FRIENDLY FEEDBACK RULE:
          Correct → warm flash, green glow on card, chime.
          Wrong   → NOTHING at all.  The card does not change.
                    The player can click other cards freely.
        """
        if card.member == self.correct_member:
            card.mark_correct()
            self.score       += 1
            self.flash_msg    = f"Yes!  That's {self.correct_member['name']}! 💛"
            self.round_locked = True
            self.state        = "correct"
            # Play gentle chime via shared sfx, or fall back to local chime
            if _sfx:
                try: _sfx.play("correct")
                except Exception: pass
            elif self.chime:
                try: self.chime.play()
                except Exception: pass
        # Wrong answer: intentionally do nothing.

    def _advance(self):
        if self.score >= ROUNDS_TO_WIN:
            self.state = "complete"
        else:
            self._new_round()
            self.state = "play"

    def _go_home(self):
        if _sfx:
            try: _sfx.play("back")
            except Exception: pass
        self.running = False
        if self.return_callback:
            self.return_callback()

    # ══════════════════════════════════════════════════════════════════════
    #  DRAWING
    # ══════════════════════════════════════════════════════════════════════

    def _draw(self):
        draw_grid_background(self.screen)
        sw, sh = self.screen.get_size()

        # Home button (always visible except on menu where there's nothing to go back to)
        if self.state != "menu":
            draw_home_button(self.screen, pygame.Rect(18, 14, 56, 56))

        if self.state == "menu":
            self._draw_menu(sw, sh)
        elif self.state == "setup":
            self._draw_setup(sw, sh)
        elif self.state in ("play", "correct"):
            self._draw_play(sw, sh)
        elif self.state == "complete":
            self._draw_complete(sw, sh)

    # ── Menu ───────────────────────────────────────────────────────────────
    def _draw_menu(self, sw, sh):
        # Title banner
        banner = pygame.Rect(int(sw * 0.22), int(sh * 0.08),
                             int(sw * 0.56), int(sh * 0.14))
        draw_title_banner(self.screen, banner)

        # Welcome message
        wf = fnt(max(24, min(38, int(sw * 0.026))), bold=True)
        draw_text_center(self.screen,
                         "Hello!  Let's look at your family. 🌼",
                         wf, WHITE, (sw // 2, int(sh * 0.38)),
                         max_w=int(sw * 0.75))

        # Hint
        cnt  = len(self.members)
        hint = ("No photos added yet. Please add some below."
                if cnt == 0 else
                "Add at least one more photo to begin."
                if cnt == 1 else
                f"{cnt} family members are ready. Let's begin!")
        hf = fnt(max(18, int(sw * 0.016)))
        draw_text_center(self.screen, hint, hf, TEXT_MID,
                         (sw // 2, int(sh * 0.46)))

        # Buttons
        play_rect  = self._btn_rect_centered(sw, sh, 0.56, 240, 54)
        setup_rect = self._btn_rect_centered(sw, sh, 0.68, 220, 50)
        bf = fnt(max(20, int(sw * 0.019)), bold=True)
        sf = fnt(max(18, int(sw * 0.016)), bold=True)

        m = pygame.mouse.get_pos()
        if cnt >= 2:
            draw_purple_button(self.screen, play_rect,
                               "▶  Let's Begin", bf,
                               hovered=play_rect.collidepoint(m))
        draw_purple_button(self.screen, setup_rect,
                           "📷  Add Photos", sf,
                           hovered=setup_rect.collidepoint(m))

    # ── Setup ──────────────────────────────────────────────────────────────
    def _draw_setup(self, sw, sh):
        # Title banner
        banner = pygame.Rect(int(sw * 0.22), int(sh * 0.04),
                             int(sw * 0.56), int(sh * 0.12))
        draw_title_banner(self.screen, banner)

        # Section heading
        hf = fnt(max(18, int(sw * 0.016)), bold=True)
        draw_text_center(self.screen,
                         "Caregiver Setup — Add Family Members",
                         hf, TEXT_MID, (sw // 2, int(sh * 0.22)))

        # Member list
        thumb_s, row_h, list_top = 60, 76, 130
        if not self.members:
            sf = fnt(max(18, int(sw * 0.016)))
            draw_text_center(self.screen, "No family members added yet.",
                             sf, TEXT_MID, (sw // 2, list_top + 30))
        else:
            for i, m in enumerate(self.members):
                y = list_top + i * row_h
                # Row background
                row_bg = pygame.Rect(140, y - 4, sw - 300, thumb_s + 8)
                rounded_rect(self.screen, CARD_BLUE, row_bg, 10)
                pygame.draw.rect(self.screen, WHITE, row_bg,
                                 width=1, border_radius=10)
                # Thumbnail
                thumb = load_photo(m["photo_path"], (thumb_s, thumb_s))
                self.screen.blit(thumb, (160, y))
                # Label
                nf  = fnt(max(20, int(sw * 0.017)), bold=True)
                rf  = fnt(max(16, int(sw * 0.013)))
                ns  = nf.render(m["name"], True, WHITE)
                rs  = rf.render(m["relationship"], True, TEXT_MID)
                self.screen.blit(ns, (230, y + 4))
                self.screen.blit(rs, (230, y + 4 + nf.get_linesize()))
                # Remove button
                rb  = pygame.Rect(sw - 190, y + 8, 140, 40)
                hov = rb.collidepoint(pygame.mouse.get_pos())
                col = (180, 55, 55) if hov else (140, 40, 40)
                sh_rb = rb.copy(); sh_rb.y += 3
                rounded_rect(self.screen, SHADOW, sh_rb, 10)
                rounded_rect(self.screen, col, rb, 10)
                pygame.draw.rect(self.screen, (255, 130, 130), rb,
                                 width=2, border_radius=10)
                rbf = fnt(max(16, int(sw * 0.013)), bold=True)
                draw_text_center(self.screen, "✖  Remove", rbf, WHITE,
                                 rb.center)

        # Bottom buttons
        add_rect  = pygame.Rect(sw // 2 - 240, sh - 72, 210, 50)
        done_rect = pygame.Rect(sw // 2 + 50,  sh - 72, 170, 50)
        bf = fnt(max(18, int(sw * 0.016)), bold=True)
        m  = pygame.mouse.get_pos()
        draw_purple_button(self.screen, add_rect,  "➕  Add Person",
                           bf, hovered=add_rect.collidepoint(m))

        # Green "Done" button
        done_col = (60, 160, 90) if done_rect.collidepoint(m) else (40, 130, 70)
        sh_d = done_rect.copy(); sh_d.y += 4
        rounded_rect(self.screen, SHADOW, sh_d, 18)
        rounded_rect(self.screen, done_col, done_rect, 18)
        pygame.draw.rect(self.screen, (120, 230, 150), done_rect,
                         width=3, border_radius=18)
        df = fnt(max(18, int(sw * 0.016)), bold=True)
        draw_text_center(self.screen, "✔  Done", df, WHITE, done_rect.center)

        # Tip
        tf = fnt(max(14, int(sw * 0.012)))
        draw_text_center(self.screen,
                         "Tip: Add 4 or more people for the best activity.",
                         tf, TEXT_MID, (sw // 2, sh - 90))

    # ── Play / Correct ─────────────────────────────────────────────────────
    def _draw_play(self, sw, sh):
        # Question text — large, bold, white, centred in top ~25% of screen
        qf = fnt(max(32, min(56, int(sw * 0.042))), bold=True)
        draw_text_center(self.screen, self.question_text, qf, WHITE,
                         (sw // 2, int(sh * 0.19)), max_w=int(sw * 0.85))

        # Photo cards (labels hidden inside PhotoCard.draw() unless correct)
        for card in self.cards:
            card.draw(self.screen)

        # Success banner (state == "correct")
        if self.state == "correct":
            # Semi-transparent overlay strip at the bottom
            ov  = pygame.Surface((sw, 80), pygame.SRCALPHA)
            ov.fill((10, 60, 30, 200))
            self.screen.blit(ov, (0, sh - 110))
            ff = fnt(max(22, min(36, int(sw * 0.026))), bold=True)
            draw_text_center(self.screen, self.flash_msg, ff, GREEN,
                             (sw // 2, sh - 70))
            # Next button
            next_rect = self._btn_rect_centered(sw, sh, 0.87, 220, 52)
            nf = fnt(max(20, int(sw * 0.018)), bold=True)
            m  = pygame.mouse.get_pos()
            draw_purple_button(self.screen, next_rect, "Next  ➜",
                               nf, hovered=next_rect.collidepoint(m))

        # Progress dots
        self._draw_progress_dots(sw, sh)

    def _draw_progress_dots(self, sw, sh):
        dot_r = 9; gap = 26
        total = ROUNDS_TO_WIN * (dot_r * 2 + gap) - gap
        x0    = sw // 2 - total // 2 + dot_r
        y0    = sh - 22
        for i in range(ROUNDS_TO_WIN):
            cx = x0 + i * (dot_r * 2 + gap)
            if i < self.score:
                pygame.draw.circle(self.screen, GREEN,  (cx, y0), dot_r)
            else:
                pygame.draw.circle(self.screen, WHITE,  (cx, y0), dot_r, 2)

    # ── Complete ───────────────────────────────────────────────────────────
    def _draw_complete(self, sw, sh):
        # Dark overlay panel
        panel = pygame.Rect(int(sw * 0.18), int(sh * 0.15),
                            int(sw * 0.64), int(sh * 0.58))
        sh_p  = panel.copy(); sh_p.y += 8
        rounded_rect(self.screen, SHADOW,       sh_p,  30)
        rounded_rect(self.screen, (22, 55, 112), panel, 30)
        pygame.draw.rect(self.screen, (100, 174, 255), panel,
                         width=4, border_radius=30)

        # Star burst
        draw_star(self.screen, (sw // 2, int(sh * 0.33)), 36, YELLOW)

        wf = fnt(max(30, min(50, int(sw * 0.038))), bold=True)
        draw_text_center(self.screen, "You did beautifully! 🌸",
                         wf, YELLOW, (sw // 2, int(sh * 0.40)))

        df = fnt(max(20, min(30, int(sw * 0.022))), bold=True)
        draw_text_center(self.screen, "What wonderful memories.",
                         df, WHITE, (sw // 2, int(sh * 0.50)))

        sf = fnt(max(17, int(sw * 0.015)))
        draw_text_center(self.screen,
                         "Would you like to see your family again?",
                         sf, TEXT_MID, (sw // 2, int(sh * 0.59)))

        # Buttons
        again_rect  = pygame.Rect(sw // 2 - 250, int(sh * 0.68), 230, 56)
        return_rect = pygame.Rect(sw // 2 + 20,  int(sh * 0.68), 230, 56)
        bf = fnt(max(18, int(sw * 0.017)), bold=True)
        m  = pygame.mouse.get_pos()
        draw_purple_button(self.screen, again_rect, "🔄  Play Again",
                           bf, hovered=again_rect.collidepoint(m))

        # Return button (blue home style)
        rc = (60, 100, 180) if return_rect.collidepoint(m) else (43, 80, 150)
        sh_r = return_rect.copy(); sh_r.y += 4
        rounded_rect(self.screen, SHADOW, sh_r, 18)
        rounded_rect(self.screen, rc, return_rect, 18)
        pygame.draw.rect(self.screen, HOME_BLU_LT, return_rect,
                         width=3, border_radius=18)
        draw_text_center(self.screen, "🏠  Main Menu", bf, WHITE,
                         return_rect.center)

    # ── Utilities ──────────────────────────────────────────────────────────
    def _btn_rect_centered(self, sw, sh, y_frac, w, h):
        return pygame.Rect(sw // 2 - w // 2, int(sh * y_frac), w, h)

# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def run(screen=None, clock=None, return_callback=None):
    """
    Called by mindbloom_gui.py:
        from family_album_game import run as run_family_album
        run_family_album(screen=screen, clock=clock,
                         return_callback=show_main_menu)

    Also works standalone:  python family_album_game.py
    """
    standalone = screen is None
    if standalone:
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
        pygame.display.set_caption("MindBloom – Family Album")
        clock  = pygame.time.Clock()

    FamilyAlbumGame(screen, clock, return_callback).run()

    if standalone:
        pygame.quit()

if __name__ == "__main__":
    run()
