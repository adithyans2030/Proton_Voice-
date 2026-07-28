"""
Proton Desktop Overlay — Cute Space-Mouse Robot Mascot
Transparent background, no title bar, always on top.
Chibi-style character with round space helmet, white suit, expressive face.
"""
import tkinter as tk
import math
import queue

STATE_IDLE      = "idle"
STATE_LISTENING = "listening"
STATE_THINKING  = "thinking"
STATE_SPEAKING  = "speaking"
STATE_SLEEPING  = "sleeping"

# Transparent key colour (will be invisible on screen)
TRANSPARENT = "#ff00fe"

# Palette
C_HELMET_OUTER = "#c8d8f0"   # light silver-blue helmet
C_HELMET_INNER = "#9ab8d8"   # helmet mid ring
C_VISOR        = "#101820"   # dark visor face
C_VISOR_GLOSS  = "#1e3048"   # gloss on visor
C_EAR          = "#b0c8e0"   # mouse ears
C_EAR_INNER    = "#e8d0e0"   # inner ear pink
C_SUIT         = "#e8eef8"   # white suit
C_SUIT_SHADE   = "#c8d4e8"   # suit shading
C_SUIT_DETAIL  = "#a0b8d0"   # suit detail lines
C_BOOT         = "#90a8c0"   # boots/joints
C_TAIL         = "#a0b8c8"   # tail
C_EYE_CLOSED   = "#f0f0f0"   # eye slits when happy/idle
C_GLOW_BLUE    = "#40c8ff"   # active glow
C_GLOW_GREEN   = "#00ffb3"   # speaking glow
C_GLOW_PURPLE  = "#c060ff"   # thinking glow
C_GLOW_WHITE   = "#ffffff"   # antenna light


class ProtonOverlay:
    """
    Transparent floating robot window.
    Chibi space-mouse character, no background panel.
    """

    WIN_W  = 180
    WIN_H  = 280
    MARGIN = 24   # from screen edge

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Proton")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=TRANSPARENT)
        self.root.attributes("-transparentcolor", TRANSPARENT)
        self.root.resizable(False, False)

        self._state    = STATE_IDLE
        self._tick     = 0
        self._text     = ""
        self._ui_queue = queue.Queue()
        self._hide_timer = None

        self.canvas = tk.Canvas(
            self.root,
            width=self.WIN_W, height=self.WIN_H,
            bg=TRANSPARENT, highlightthickness=0
        )
        self.canvas.pack()

        # Position bottom-right
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = sw - self.WIN_W - self.MARGIN
        y  = sh - self.WIN_H - self.MARGIN - 48
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+{x}+{y}")

        # Right-click menu
        self._menu = tk.Menu(
            self.root, tearoff=0,
            bg="#0d1117", fg="#d0e8ff",
            activebackground="#1e3a5f", activeforeground="white",
            font=("Segoe UI", 10)
        )
        self._menu.add_command(label="⏸  Pause",  command=self._on_pause)
        self._menu.add_command(label="▶  Resume", command=self._on_resume)
        self._menu.add_separator()
        self._menu.add_command(label="✕  Exit",   command=self._on_exit)
        self.canvas.bind("<Button-3>", self._show_menu)

        # Drag support
        self.canvas.bind("<ButtonPress-1>",  self._drag_start)
        self.canvas.bind("<B1-Motion>",      self._drag_move)
        self._drag_x = self._drag_y = 0

        # Public callbacks
        self.pause_callback  = None
        self.resume_callback = None
        self.exit_callback   = None

        self._animate()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str):
        self._ui_queue.put(("state", state))

    def show_text(self, text: str, auto_hide_sec: float = 8.0):
        self._ui_queue.put(("text", text, auto_hide_sec))

    def hide(self):
        self._ui_queue.put(("idle",))

    def show(self):
        pass

    def run(self):
        self.root.mainloop()

    def stop(self):
        try:
            self.root.quit()
        except Exception:
            pass

    # ── Queue ─────────────────────────────────────────────────────────────────

    def _process_queue(self):
        try:
            while True:
                msg = self._ui_queue.get_nowait()
                cmd = msg[0]
                if cmd == "state":
                    self._state = msg[1]
                    if self._state in (STATE_IDLE, STATE_SLEEPING):
                        self._text = ""
                elif cmd == "text":
                    self._text = msg[1]
                    if self._hide_timer:
                        self.root.after_cancel(self._hide_timer)
                    delay = int(msg[2] * 1000) if len(msg) > 2 else 8000
                    self._hide_timer = self.root.after(delay, self._expire_text)
                elif cmd == "idle":
                    self._text  = ""
                    self._state = STATE_IDLE
        except queue.Empty:
            pass

    def _expire_text(self):
        self._text  = ""
        self._state = STATE_IDLE

    # ── Animation ─────────────────────────────────────────────────────────────

    def _animate(self):
        self._process_queue()
        self._tick += 1
        self._draw(self._tick)
        self.root.after(40, self._animate)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def _draw(self, t):
        c = self.canvas
        c.delete("all")

        s = self._state
        cx = self.WIN_W // 2   # horizontal centre = 90

        # ── Vertical bob ──────────────────────────────────────────────────────
        bob_amp = {
            STATE_IDLE:      2.5,
            STATE_SLEEPING:  1.0,
            STATE_LISTENING: 4.0,
            STATE_THINKING:  2.0,
            STATE_SPEAKING:  5.0,
        }.get(s, 2)
        bob_speed = {
            STATE_IDLE:      0.04,
            STATE_SLEEPING:  0.015,
            STATE_LISTENING: 0.10,
            STATE_THINKING:  0.07,
            STATE_SPEAKING:  0.18,
        }.get(s, 0.04)
        dy = math.sin(t * bob_speed) * bob_amp

        # ── Glow colour ───────────────────────────────────────────────────────
        glow = {
            STATE_IDLE:      C_GLOW_BLUE,
            STATE_SLEEPING:  "#204060",
            STATE_LISTENING: C_GLOW_BLUE,
            STATE_THINKING:  C_GLOW_PURPLE,
            STATE_SPEAKING:  C_GLOW_GREEN,
        }.get(s, C_GLOW_BLUE)

        # ── State ring under character ─────────────────────────────────────
        if s in (STATE_LISTENING, STATE_SPEAKING, STATE_THINKING):
            pulse = abs(math.sin(t * 0.12))
            rr = 38 + pulse * 12
            ry = 230 + dy
            for i in range(4, 0, -1):
                alpha_col = self._dim(glow, 0.12 * i)
                c.create_oval(cx - rr - i*4, ry - (rr+i*4)//4,
                              cx + rr + i*4, ry + (rr+i*4)//4,
                              fill="", outline=alpha_col, width=1)

        # ── Tail ──────────────────────────────────────────────────────────────
        tail_swing = math.sin(t * 0.08) * 15
        c.create_line(cx + 28, 210 + dy,
                      cx + 55, 230 + dy + tail_swing,
                      cx + 48, 248 + dy + tail_swing,
                      fill=C_TAIL, width=4, smooth=True)

        # ── Legs / boots ──────────────────────────────────────────────────────
        walk = math.sin(t * 0.14) * 5 if s == STATE_SPEAKING else 0
        self._draw_leg(c, cx - 18, 215 + dy + walk, -walk * 0.3)
        self._draw_leg(c, cx + 18, 215 + dy - walk,  walk * 0.3)

        # ── Body (suit) ───────────────────────────────────────────────────────
        self._draw_body(c, cx, 175 + dy, s, t)

        # ── Arms ──────────────────────────────────────────────────────────────
        arm_swing = math.sin(t * 0.15) * 8 if s == STATE_SPEAKING else 0
        self._draw_arm(c, cx - 38, 180 + dy, "left",  arm_swing)
        self._draw_arm(c, cx + 38, 180 + dy, "right", -arm_swing)

        # ── Helmet ────────────────────────────────────────────────────────────
        self._draw_helmet(c, cx, 110 + dy, s, t, glow)

        # ── Antenna ───────────────────────────────────────────────────────────
        self._draw_antenna(c, cx, 65 + dy, s, t, glow)

        # ── Mouse ears ────────────────────────────────────────────────────────
        self._draw_ear(c, cx - 44, 75 + dy, "left")
        self._draw_ear(c, cx + 44, 75 + dy, "right")

        # ── Speech bubble (above head) ────────────────────────────────────────
        if self._text:
            self._draw_bubble(c, cx, 30 + dy)

    # ── Sub-drawers ───────────────────────────────────────────────────────────

    def _draw_antenna(self, c, cx, top_y, s, t, glow):
        # Stick
        c.create_line(cx, top_y + 12, cx, top_y - 10, fill=C_SUIT_DETAIL, width=3)
        # Ball
        pulse = 0.5 + 0.5 * math.sin(t * 0.18)
        br = 7 + int(pulse * 4)
        # Glow rings
        if s not in (STATE_SLEEPING,):
            for i in range(3, 0, -1):
                c.create_oval(cx - br - i*3, top_y - 10 - br - i*3,
                              cx + br + i*3, top_y - 10 + br + i*3,
                              fill="", outline=glow, width=1)
        bc = glow if s != STATE_SLEEPING else "#1a2a3a"
        c.create_oval(cx - br, top_y - 10 - br, cx + br, top_y - 10 + br,
                      fill=bc, outline=C_GLOW_WHITE, width=1)

    def _draw_ear(self, c, ex, ey, side):
        # Outer ear
        c.create_oval(ex - 16, ey - 16, ex + 16, ey + 16,
                      fill=C_EAR, outline=C_HELMET_INNER, width=2)
        # Inner ear
        c.create_oval(ex - 9, ey - 9, ex + 9, ey + 9,
                      fill=C_EAR_INNER, outline="")

    def _draw_helmet(self, c, cx, cy, s, t, glow):
        HR = 52   # helmet radius

        # Outer glow aura when active
        if s in (STATE_LISTENING, STATE_SPEAKING, STATE_THINKING):
            pulse = 0.3 + 0.25 * abs(math.sin(t * 0.14))
            for i in range(5, 0, -1):
                c.create_oval(cx - HR - i*4, cy - HR - i*4,
                              cx + HR + i*4, cy + HR + i*4,
                              fill="", outline=glow, width=1)

        # Outer helmet shell
        c.create_oval(cx - HR, cy - HR, cx + HR, cy + HR,
                      fill=C_HELMET_OUTER, outline=C_HELMET_INNER, width=3)

        # Mid ring
        MR = HR - 8
        c.create_oval(cx - MR, cy - MR, cx + MR, cy + MR,
                      fill=C_HELMET_INNER, outline=C_SUIT_DETAIL, width=2)

        # Visor (dark face)
        VR = HR - 16
        c.create_oval(cx - VR, cy - VR, cx + VR, cy + VR,
                      fill=C_VISOR, outline=C_VISOR_GLOSS, width=2)

        # Visor gloss reflection
        c.create_arc(cx - VR + 6, cy - VR + 4,
                     cx - 4, cy - 2,
                     start=30, extent=120,
                     fill="", outline=C_VISOR_GLOSS, width=2)

        # Face
        self._draw_face(c, cx, cy, s, t)

        # Helmet highlight
        c.create_arc(cx - HR + 6, cy - HR + 5,
                     cx + 4, cy - 10,
                     start=20, extent=130,
                     fill="", outline="#e0eeff", width=2)

    def _draw_face(self, c, cx, cy, s, t):
        """Draw the face inside the visor."""
        if s == STATE_SLEEPING:
            # Closed squinting eyes (curved lines)
            for dx in [-14, 14]:
                c.create_arc(cx + dx - 10, cy - 8,
                             cx + dx + 10, cy + 8,
                             start=0, extent=180,
                             fill="", outline=C_EYE_CLOSED, width=2)
            # Zzz
            c.create_text(cx + 28, cy - 20, text="z z",
                          fill=C_GLOW_BLUE, font=("Segoe UI", 7, "bold"))
        elif s == STATE_THINKING:
            # One raised eyebrow, thinking look
            c.create_arc(cx - 24, cy - 12, cx - 4, cy + 2,
                         start=0, extent=180, fill=C_EYE_CLOSED, outline="")
            c.create_arc(cx + 4, cy - 16, cx + 24, cy - 2,
                         start=0, extent=180, fill=C_EYE_CLOSED, outline="")
            # Mouth: straight line
            c.create_line(cx - 10, cy + 12, cx + 10, cy + 12,
                          fill=C_EYE_CLOSED, width=2)
        elif s == STATE_SPEAKING:
            # Wide open eyes (circles) + open mouth
            for dx in [-14, 14]:
                c.create_oval(cx + dx - 9, cy - 12,
                              cx + dx + 9, cy + 6,
                              fill=C_EYE_CLOSED, outline="")
                c.create_oval(cx + dx - 4, cy - 8, cx + dx + 4, cy,
                              fill=C_VISOR, outline="")
            # Mouth open
            mo = abs(math.sin(t * 0.25)) * 10 + 4
            c.create_oval(cx - 12, cy + 6, cx + 12, cy + 6 + mo,
                          fill=C_EYE_CLOSED, outline="")
        elif s == STATE_LISTENING:
            # Alert wide eyes
            for dx in [-14, 14]:
                c.create_oval(cx + dx - 10, cy - 13,
                              cx + dx + 10, cy + 7,
                              fill=C_EYE_CLOSED, outline="")
                c.create_oval(cx + dx - 4, cy - 7, cx + dx + 4, cy + 1,
                              fill=C_VISOR, outline="")
            # Small smile
            c.create_arc(cx - 12, cy + 6, cx + 12, cy + 16,
                         start=200, extent=140, fill="", outline=C_EYE_CLOSED, width=2)
        else:  # IDLE — happy squint
            # Classic happy half-moon eyes
            for dx in [-14, 14]:
                c.create_arc(cx + dx - 11, cy - 10,
                             cx + dx + 11, cy + 10,
                             start=0, extent=180,
                             fill=C_EYE_CLOSED, outline="")
            # Small smile
            c.create_arc(cx - 12, cy + 6, cx + 12, cy + 16,
                         start=200, extent=140,
                         fill="", outline=C_EYE_CLOSED, width=2)

    def _draw_body(self, c, cx, cy, s, t):
        # Main torso (rounded rect via oval + rect)
        BW, BH = 58, 52
        c.create_rectangle(cx - BW//2, cy - BH//2,
                            cx + BW//2, cy + BH//2,
                            fill=C_SUIT, outline=C_SUIT_DETAIL, width=2)
        # Suit collar detail
        c.create_rectangle(cx - 18, cy - BH//2 - 2, cx + 18, cy - BH//2 + 10,
                            fill=C_HELMET_INNER, outline=C_SUIT_DETAIL, width=1)

        # Chest button / badge area
        c.create_oval(cx - 10, cy - 8, cx + 10, cy + 8,
                      fill=C_SUIT_SHADE, outline=C_SUIT_DETAIL, width=1)

        # Suit crease lines
        c.create_line(cx - 20, cy - 10, cx - 20, cy + 20,
                      fill=C_SUIT_DETAIL, width=1)
        c.create_line(cx + 20, cy - 10, cx + 20, cy + 20,
                      fill=C_SUIT_DETAIL, width=1)

        # Crossed arms effect (overlay shape)
        arm_y = cy + 8
        # Left arm over body
        c.create_arc(cx - BW//2 - 5, arm_y - 14, cx + 10, arm_y + 14,
                     start=350, extent=180, fill=C_SUIT_SHADE, outline=C_SUIT_DETAIL, width=1)
        # Right arm over body
        c.create_arc(cx - 10, arm_y - 14, cx + BW//2 + 5, arm_y + 14,
                     start=350, extent=180, fill=C_SUIT, outline=C_SUIT_DETAIL, width=1)

    def _draw_arm(self, c, ax, ay, side, swing):
        # Upper arm
        if side == "left":
            x1, x2 = ax - 8, ax + 8
        else:
            x1, x2 = ax - 8, ax + 8
        c.create_oval(x1, ay - 16 + swing, x2, ay + 16 + swing,
                      fill=C_SUIT_SHADE, outline=C_SUIT_DETAIL, width=1)
        # Glove/hand
        hr = 10
        c.create_oval(ax - hr, ay + 14 + swing, ax + hr, ay + 28 + swing,
                      fill=C_BOOT, outline=C_SUIT_DETAIL, width=1)

    def _draw_leg(self, c, lx, ly, angle):
        # Upper leg
        c.create_oval(lx - 10, ly, lx + 10, ly + 22,
                      fill=C_SUIT_SHADE, outline=C_SUIT_DETAIL, width=1)
        # Lower leg / boot
        c.create_oval(lx - 12, ly + 18, lx + 12, ly + 38,
                      fill=C_BOOT, outline=C_SUIT_DETAIL, width=2)
        # Boot thruster detail
        c.create_oval(lx - 8, ly + 34, lx + 8, ly + 42,
                      fill=C_GLOW_BLUE, outline="")

    def _draw_bubble(self, c, cx, top_y):
        """Small speech bubble floating above the head."""
        text  = self._text[:80] + ("…" if len(self._text) > 80 else "")
        # Measure approximate height
        lines = len(text) // 22 + 1
        bw    = min(160, len(text) * 7 + 20)
        bh    = lines * 18 + 14
        bx    = max(4, min(cx - bw // 2, self.WIN_W - bw - 4))
        by    = max(4, top_y - bh - 14)

        # Shadow
        c.create_rectangle(bx + 3, by + 3, bx + bw + 3, by + bh + 3,
                            fill="#050810", outline="")
        # Bubble
        pts = [bx+8, by, bx+bw-8, by,
               bx+bw, by, bx+bw, by+8,
               bx+bw, by+bh-8, bx+bw, by+bh,
               bx+bw-8, by+bh, bx+8, by+bh,
               bx, by+bh, bx, by+bh-8,
               bx, by+8, bx, by]
        c.create_polygon(pts, smooth=True,
                         fill="#0a1628", outline="#1e4a8a", width=1)
        # Tail triangle pointing down toward head
        mid = bx + bw // 2
        c.create_polygon(mid - 6, by + bh,
                         mid + 6, by + bh,
                         mid, by + bh + 10,
                         fill="#0a1628", outline="#1e4a8a")
        # Text
        c.create_text(bx + bw // 2, by + bh // 2,
                      text=text, fill="#d0e8ff",
                      font=("Segoe UI", 9), width=bw - 12, anchor="center")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _dim(hex_col, factor):
        """Return a dimmed version of a hex colour."""
        factor = max(0.0, min(1.0, factor))
        r = int(int(hex_col[1:3], 16) * factor)
        g = int(int(hex_col[3:5], 16) * factor)
        b = int(int(hex_col[5:7], 16) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _show_menu(self, e):
        self._menu.tk_popup(e.x_root, e.y_root)

    def _on_pause(self):
        if self.pause_callback:
            self.pause_callback()
        self._text  = "Paused. Right-click → Resume."
        self._state = STATE_SLEEPING

    def _on_resume(self):
        if self.resume_callback:
            self.resume_callback()
        self._text  = ""
        self._state = STATE_IDLE

    def _on_exit(self):
        if self.exit_callback:
            self.exit_callback()
        self.stop()
