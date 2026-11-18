import pygame
import sys
import math

# ---- Family Album launcher (runs inline, returns to menu when done) ----
def _run_family_album():
    from family_album_game import run as _fa
    _fa(screen=screen, clock=clock, return_callback=None)

# ============================================================
# MINDBLOOM - Main Menu
# A responsive GUI inspired by the provided reference image.
# ============================================================

pygame.init()

# -------------------- DISPLAY --------------------
pygame.display.set_caption("MindBloom")

info = pygame.display.Info()
START_W = max(1000, info.current_w)
START_H = max(650, info.current_h)

screen = pygame.display.set_mode((START_W, START_H), pygame.RESIZABLE)
clock = pygame.time.Clock()

# -------------------- COLORS --------------------
BG = (25, 35, 70)
GRID = (34, 46, 84)
WHITE = (248, 249, 252)
TITLE_BLUE = (99, 145, 255)
SUBTITLE = (240, 242, 248)
SCORE_BLUE = (95, 145, 255)

CARD_COLORS = [
    (190, 132, 50),   # Picture Making
    (108, 106, 225),  # Color Garden
    (202, 48, 111),   # What Is This?
    (48, 157, 82),    # Garden Sorting
    (166, 57, 45),    # Which One Belongs?
    (119, 82, 181),   # Memory Peek
    (60, 140, 200),   # Family Album
]

GAME_NAMES = [
    "PICTURE MAKING",
    "COLOR GARDEN",
    "WHAT IS THIS?",
    "GARDEN SORTING",
    "WHICH ONE BELONGS?",
    "MEMORY PEEK",
    "FAMILY ALBUM",
]

# -------------------- FONT HELPER --------------------
def get_font(size, bold=False):
    candidates = [
        "arial",
        "segoeui",
        "dejavusans",
        "liberationsans",
    ]

    for name in candidates:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)

    return pygame.font.Font(None, size)


# -------------------- DRAW HELPERS --------------------
def draw_background(surface):
    surface.fill(BG)

    # Subtle square grid like the reference image
    w, h = surface.get_size()
    spacing = max(22, int(min(w, h) * 0.028))

    for x in range(0, w, spacing):
        pygame.draw.line(surface, GRID, (x, 0), (x, h), 1)

    for y in range(0, h, spacing):
        pygame.draw.line(surface, GRID, (0, y), (w, y), 1)


def draw_centered_text(surface, text, font, color, center):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


def rounded_card(surface, rect, color, hover=False):
    # Small lift effect on hover
    if hover:
        shadow = rect.copy()
        shadow.y += 6
        pygame.draw.rect(
            surface,
            (12, 19, 43),
            shadow,
            border_radius=18
        )

        # Slightly brighter card on hover
        color = tuple(min(255, c + 12) for c in color)

    pygame.draw.rect(
        surface,
        color,
        rect,
        border_radius=18
    )

    # White outline from the reference design
    pygame.draw.rect(
        surface,
        WHITE,
        rect,
        width=3,
        border_radius=18
    )


# -------------------- LAYOUT --------------------
def calculate_layout(width, height):
    # The whole content is kept centered and resized with the window.
    content_width = min(width * 0.76, 1200)
    content_width = max(content_width, 700)

    gap_x = max(24, int(content_width * 0.035))
    gap_y = max(24, int(height * 0.035))

    card_width = (content_width - gap_x * 2) / 3
    card_height = min(max(height * 0.16, 115), 175)

    total_grid_width = card_width * 3 + gap_x * 2
    total_grid_height = card_height * 2 + gap_y

    grid_x = (width - total_grid_width) / 2

    # Header area
    title_y = height * 0.115
    subtitle_y = height * 0.205
    score_y = height * 0.255

    # Keep cards comfortably below the score
    grid_y = max(height * 0.30, score_y + 55)

    # If the window becomes short, reduce card height and move grid upward.
    if grid_y + total_grid_height > height * 0.92:
        available = height * 0.92 - grid_y
        card_height = max(90, (available - gap_y) / 2)

    cards = []

    for row in range(3):                             # 3 rows for 7 cards
        cols_in_row = 3 if row < 2 else 1            # last row: 1 centred card
        row_w = cols_in_row * card_width + (cols_in_row - 1) * gap_x
        row_x = (width - row_w) / 2
        for col in range(cols_in_row):
            idx = row * 3 + col
            if idx >= len(GAME_NAMES):
                break
            x = row_x + col * (card_width + gap_x)
            y = grid_y + row * (card_height + gap_y)
            cards.append(pygame.Rect(round(x), round(y),
                                     round(card_width), round(card_height)))

    return cards, title_y, subtitle_y, score_y


# -------------------- MAIN LOOP --------------------
high_score = 0
selected_game = None

running = True

while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            # Quick testing: 1-6 selects a game
            elif pygame.K_1 <= event.key <= pygame.K_6:
                index = event.key - pygame.K_1
                selected_game = GAME_NAMES[index]

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse = pygame.mouse.get_pos()

            for i, rect in enumerate(cards):
                if rect.collidepoint(mouse):
                    selected_game = GAME_NAMES[i]
                    print(f"Selected: {selected_game}")
                    if i == 6:          # Family Album
                        _run_family_album()

    width, height = screen.get_size()

    cards, title_y, subtitle_y, score_y = calculate_layout(width, height)

    # -------------------- DRAW --------------------
    draw_background(screen)

    # Fonts scale with screen size
    title_size = max(42, min(76, int(width * 0.040)))
    subtitle_size = max(22, min(36, int(width * 0.019)))
    score_size = max(20, min(32, int(width * 0.017)))
    card_size = max(20, min(34, int(min(width, height) * 0.023)))

    title_font = get_font(title_size, bold=True)
    subtitle_font = get_font(subtitle_size, bold=True)
    score_font = get_font(score_size, bold=True)
    card_font = get_font(card_size, bold=True)

    # Header
    draw_centered_text(
        screen,
        "MINDBLOOM",
        title_font,
        TITLE_BLUE,
        (width / 2, title_y)
    )

    draw_centered_text(
        screen,
        "SELECT YOUR GAME",
        subtitle_font,
        SUBTITLE,
        (width / 2, subtitle_y)
    )

    draw_centered_text(
        screen,
        f"HIGH SCORE: {high_score}",
        score_font,
        SCORE_BLUE,
        (width / 2, score_y)
    )

    mouse = pygame.mouse.get_pos()

    # Six perfectly aligned cards
    for i, rect in enumerate(cards):
        hovered = rect.collidepoint(mouse)

        rounded_card(
            screen,
            rect,
            CARD_COLORS[i],
            hovered
        )

        # Keep long text inside the card
        text = GAME_NAMES[i]

        # Slightly smaller font for the longest labels
        current_font = card_font

        if len(text) >= 19:
            smaller_size = max(17, int(card_size * 0.82))
            current_font = get_font(smaller_size, bold=True)

        draw_centered_text(
            screen,
            text,
            current_font,
            WHITE,
            rect.center
        )

    # Small feedback when a game is selected
    if selected_game:
        feedback_font = get_font(max(16, int(width * 0.012)), bold=False)
        feedback = feedback_font.render(
            f"Selected: {selected_game}",
            True,
            (190, 200, 225)
        )
        feedback_rect = feedback.get_rect(
            center=(width / 2, height - 28)
        )
        screen.blit(feedback, feedback_rect)

    pygame.display.flip()

pygame.quit()
sys.exit()
