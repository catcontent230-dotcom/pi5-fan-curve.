#!/usr/bin/env python3
"""Raspberry Pi 5 Fan Curve Editor — 64-bit edition with free control.

Uses Pi 5 firmware fan-curve settings in the boot config.
64-bit Python only — use the Trixie edition for 64-bit Raspberry Pi OS.
Features free (non-snapping) point placement, hysteresis control, and
a polished dark-themed UI. Uses ONLY pack geometry manager to avoid
TclError: cannot use geometry manager grid inside ... which already
has slaves managed by pack.
"""

import json, subprocess, time, struct, math
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

# 64-bit check
if struct.calcsize("P") * 8 != 64:
    root = tk.Tk()
    root.title("Pi 5 Fan Curve Editor")
    root.geometry("400x150")
    ttk.Label(root, text="This 64-bit edition requires 64-bit Python.\nUse the Trixie 64-bit edition for 64-bit Raspberry Pi OS.").pack(padx=20, pady=20)
    root.mainloop()
    exit(0)

CONFIG = Path.home() / ".config/pi5-fan-curve/curve.json"
APP_DIR = Path("/opt/pi5-fan-curve")
DEFAULT = [{"temp": 40, "level": 0, "hyst": 3}, {"temp": 50, "level": 1, "hyst": 3}, {"temp": 60, "level": 2, "hyst": 3}, {"temp": 67, "level": 3, "hyst": 3}, {"temp": 75, "level": 4, "hyst": 3}]


class Palette:
    """Dark theme palette using CSS-like vars."""
    BG = "#0b1020"
    PANEL = "#121a2d"
    PANEL2 = "#18233a"
    TEXT = "#eef3ff"
    MUTED = "#91a0ba"
    ACCENT = "#8b7cff"
    CYAN = "#4dd8d0"
    WARNING = "#ffb347"
    SUCCESS = "#a7f3d0"
    ERROR = "#ff7878"


def valid_points(points, enforce_spacing=True):
    """Validate curve points.

    Args:
        points: list of dicts with 'temp', 'level', 'hyst' keys.
        enforce_spacing: if True, require ≥2°C between adjacent temps.
    """
    try:
        if not isinstance(points, list) or not 2 <= len(points) <= 12:
            return False
        cleaned = []
        for point in points:
            temp = float(point["temp"])
            level = int(point["level"])
            hyst = float(point.get("hyst", 3))
            if not 30 <= temp <= 90:
                return False
            if not 0 <= level <= 4:
                return False
            if hyst < 1 or hyst > 15:
                return False
            cleaned.append({"temp": temp, "level": level, "hyst": hyst})
        cleaned.sort(key=lambda p: p["temp"])
        if enforce_spacing:
            return all(b["temp"] - a["temp"] >= 2 for a, b in zip(cleaned, cleaned[1:]))
        return True
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def load_curve():
    try:
        pts = json.loads(CONFIG.read_text()).get("points", DEFAULT)
        if valid_points(pts, enforce_spacing=False):
            return sorted(
                [{"temp": float(p["temp"]), "level": int(p["level"]), "hyst": float(p.get("hyst", 3))} for p in pts],
                key=lambda p: p["temp"],
            )
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return [p.copy() for p in DEFAULT]


def save_curve(points):
    if not valid_points(points, enforce_spacing=True):
        raise ValueError(
            "Curve must contain 2–12 points, temperatures 30–90°C, "
            "levels 0–4, and hysteresis 1–15°C. Points must be ≥2°C apart."
        )
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(
            {"points": sorted(points, key=lambda p: p["temp"]), "updated": time.time()},
            indent=2,
        )
    )
    tmp.replace(CONFIG)


def fan_device():
    for d in Path("/sys/class/thermal").glob("cooling_device*"):
        try:
            if "fan" in (d / "type").read_text().strip().lower():
                return d
        except Exception:
            pass
    return None


def cpu_temp():
    try:
        return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
    except Exception:
        return None


class App:
    """Polished 64-bit Pi 5 Fan Curve Editor with free control.

    Uses ONLY pack geometry manager to avoid TclError about grid/pack mixing.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Pi 5 Fan Curve Editor — 64-bit Free Control")
        self.root.geometry("950x680")
        self.root.minsize(800, 560)
        self.root.configure(bg=Palette.BG)

        # Custom font setup for crisp rendering
        try:
            self.nunifont = tkfont.Font(family="Noto Sans", size=10)
            self.titlefont = tkfont.Font(family="Noto Sans", size=14, weight="bold")
            self.bigfont = tkfont.Font(family="Noto Sans", size=20, weight="bold")
        except Exception:
            self.nunifont = tkfont.Font(default="TkDefaultFont")
            self.titlefont = tkfont.Font(default="TkDefaultFont")
            self.bigfont = tkfont.Font(default="TkDefaultFont")

        self.points = load_curve()
        self.selected = None
        self.drag = False
        self._dragoff = (0, 0)

        self.status = tk.StringVar(value="Ready")
        self.stats = tk.StringVar(value="Reading hardware…")

        # ---- Main layout using ONLY pack ----
        # Top: control buttons bar
        top_bar = tk.Frame(root, bg=Palette.BG, padx=16, pady=4)
        top_bar.pack(fill="x")

        # Canvas area - takes most space, packed left/top
        self.canvas = tk.Canvas(root, bg=Palette.PANEL2, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Right panel - hysteresis info + status
        right_panel = tk.Frame(root, bg=Palette.PANEL2, width=320)
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)

        # ---- Top bar buttons ----
        bstyle = {"bg": Palette.PANEL2, "fg": Palette.TEXT, "activebackground": Palette.ACCENT,
                  "activeforeground": "white", "bd": 0, "font": self.nunifont}

        tk.Button(top_bar, text="⊕ Add Point", command=self._add_point_dialog, **bstyle).pack(side="left", padx=2)
        tk.Button(top_bar, text="⊝ Remove Selected", command=self._remove_selected, **bstyle).pack(side="left", padx=2)
        tk.Button(top_bar, text="⟳ Restore Defaults", command=self._restore_defaults, **bstyle).pack(side="left", padx=2)
        tk.Button(top_bar, text="✅ Apply", command=self.apply, bg=Palette.ACCENT, fg="white",
                  activebackground="#a69cff", font=self.nunifont).pack(side="right", padx=2)

        # Hysteresis info label
        tk.Label(right_panel, text="Hysteresis (°C): Prevents rapid switching near boundaries.",
                 bg=Palette.PANEL2, fg=Palette.MUTED, font=self.nunifont).pack(anchor="w", padx=8, pady=8)

        # Status at bottom of right panel
        self.status_lbl = tk.Label(right_panel, textvariable=self.stats, bg=Palette.PANEL2, fg=Palette.MUTED,
                                   font=self.nunifont)
        self.status_lbl.pack(anchor="w", padx=8, pady=(0, 8))

        # Bind canvas events
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.move)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        self.canvas.bind("<Button-3>", self.delete_at)
        self.canvas.bind("<Motion>", self._mouse_move)

        # Initial draw
        self.draw()
        self._refresh_stats()

    # ---- Graph drawing ----

    def _bounds(self):
        w = max(self.canvas.winfo_width(), 600)
        h = max(self.canvas.winfo_height(), 420)
        l, r, t, b = 60, w - 40, 40, h - 60
        return l, r, t, b

    def _temp_to_x(self, temp):
        l, r, _, _ = self._bounds()
        return l + (temp - 30) / 60 * (r - l)

    def _level_to_y(self, level):
        _, _, t, b = self._bounds()
        # level 0 at top, level 4 at bottom
        return t + level / 4 * (b - t)

    def draw(self):
        self.canvas.delete("all")
        l, r, t, b = self._bounds()

        # --- Background / grid ---
        for yy in range(t, b + 20, 20):
            self.canvas.create_line(l, yy, r, yy, fill=Palette.PANEL, dash=(2, 4))
        for xx in range(l, r + 30, 30):
            self.canvas.create_line(xx, t, xx, b, fill=Palette.PANEL, dash=(2, 2))

        # Temperature axis labels (bottom)
        for temp in range(30, 91, 10):
            x = self._temp_to_x(temp)
            self.canvas.create_line(x, t, x, b, fill=Palette.MUTED, dash=(2, 2))
            self.canvas.create_text(x, b + 16, text=str(temp), fill=Palette.MUTED,
                                    font=self.nunifont)

        # Level axis labels (left)
        for lev in range(5):
            y = self._level_to_y(lev)
            self.canvas.create_line(l, y, r, y, fill=Palette.PANEL, dash=(2, 2))
            label = "Full" if lev == 4 else f"{lev*25}%" if lev > 0 else "Off"
            self.canvas.create_text(l - 8, y, text=label, fill=Palette.MUTED,
                                    font=self.nunifont, anchor="e")

        # --- Draw curve line from points ---
        pts = sorted(self.points, key=lambda p: p["temp"])
        if len(pts) >= 2:
            coords = [(self._temp_to_x(p["temp"]), self._level_to_y(p["level"])) for p in pts]
            # Draw polyline through points
            flat = []
            for i, (x, y) in enumerate(coords):
                flat.extend([x, y])
            if len(flat) >= 4:
                self.canvas.create_line(*flat, fill=Palette.ACCENT, width=3, smooth=True)

        # --- Draw points (draggable circles) ---
        for p in pts:
            x = self._temp_to_x(p["temp"])
            y = self._level_to_y(p["level"])
            rad = max(6, min(14, int(self.canvas.winfo_width()) / 60))
            is_sel = (p is self.selected)
            fill_color = Palette.ACCENT if is_sel else Palette.CYAN
            outline_color = "white" if is_sel else Palette.MUTED
            width = 2 if is_sel else 1

            obj = self.canvas.create_oval(x - rad, y - rad, x + rad, y + rad,
                                          fill=fill_color, outline=outline_color, width=width)
            # Store point reference on the canvas item for binding
            self.canvas.tag_bind(obj, "<Button-1>", lambda e, pt=p: self._start_drag(e, pt))
            self.canvas.tag_bind(obj, "<B1-Motion>", lambda e, pt=p: self._drag(e, pt))

            # Temperature label above point
            self.canvas.create_text(x, y - 20, text=f"{p['temp']:.0f}°C",
                                    fill=Palette.TEXT, font=self.nunifont)

            # Level label below point
            self.canvas.create_text(x, y + 20, text=f"Level {p['level']}",
                                    fill=Palette.MUTED, font=self.nunifont)

            # Hysteresis small text
            self.canvas.create_text(x, y + 40, text=f"hys {p.get('hyst', 3)}°C",
                                    fill=Palette.MUTED, font=self.nunifont)

        # --- Instructions ---
        self.canvas.create_text(60, self.canvas.winfo_height() - 10,
                                text="LMB drag points · RMB delete · Add: button or click empty space",
                                fill=Palette.MUTED, font=self.nunifont)

    # ---- Point management ----

    def _start_drag(self, event, point):
        self.selected = point
        self.drag = True
        l, _, _, _ = self._bounds()
        ix = self._temp_to_x(point["temp"])
        yi = self._level_to_y(point["level"])
        self._dragoff = (event.x - ix, event.y - yi)
        self.draw()

    def _drag(self, event):
        if not self.drag or not self.selected:
            return
        # Free movement - no snapping/grid locking
        x = self.canvas.canvasx(event.x) + self._dragoff[0]
        y = self.canvas.canvasy(event.y) + self._dragoff[1]
        # Clamp to bounds
        l, r, t, b = self._bounds()
        x = max(l + 10, min(r - 10, x))
        y = max(t + 10, min(b - 10, y))
        # Convert to temp/level with free (non-snapped) mapping
        temp = 30 + (x - l) / (r - l) * 60
        # level: map y pixel to 0-4, level 0 at top, 4 at bottom
        level = round(4 - (y - t) / (b - t) * 4)
        level = max(0, min(4, level))
        temp = max(30, min(90, temp))
        self.selected["temp"] = round(temp, 1)
        self.selected["level"] = int(level)
        self.draw()

    def _mouse_move(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        l, r, t, b = self._bounds()
        if l < x < r and t < y < b:
            nearest = None
            best_dist = 999
            for p in self.points:
                ix = self._temp_to_x(p["temp"])
                iy = self._level_to_y(p["level"])
                d = (x - ix) ** 2 + (y - iy) ** 2
                if d < best_dist:
                    best_dist = d
                    nearest = p
            if nearest and best_dist < 400:
                self.status.set(f"Near point: T={nearest['temp']:.0f}°C L={nearest['level']} H={nearest.get('hyst', 3)}°C")
            else:
                self.status.set("Click & drag to move a point, Right-click to delete, Add button to add with free placement")
        else:
            self.status.set("Ready")

    def _add_point_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Add Point")
        dlg.geometry="320x220"
        dlg.configure(bg=Palette.PANEL)
        dlg.transient(self.root)
        dlg.grab_set()

        f = tk.Frame(dlg, bg=Palette.PANEL, padx=20, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Temperature (°C):", bg=Palette.PANEL, fg=Palette.TEXT, font=self.nunifont).pack(anchor="w")
        temp_var = tk.StringVar(value="65")
        tk.Entry(f, textvariable=temp_var, bg=Palette.PANEL2, fg=Palette.TEXT,
                 insertbackground=Palette.TEXT, font=self.nunifont).pack(fill="x", pady=2)

        tk.Label(f, text="Fan Level (0–4):", bg=Palette.PANEL, fg=Palette.TEXT, font=self.nunifont).pack(anchor="w", pady=(8, 0))
        level_var = tk.StringVar(value="2")
        tk.Entry(f, textvariable=level_var, bg=Palette.PANEL2, fg=Palette.TEXT,
                 insertbackground=Palette.TEXT, font=self.nunifont).pack(fill="x", pady=2)

        tk.Label(f, text="Hysteresis (°C, 1–15):", bg=Palette.PANEL, fg=Palette.TEXT, font=self.nunifont).pack(anchor="w", pady=(8, 0))
        hyst_var = tk.StringVar(value="3")
        tk.Entry(f, textvariable=hyst_var, bg=Palette.PANEL2, fg=Palette.TEXT,
                 insertbackground=Palette.TEXT, font=self.nunifont).pack(fill="x", pady=2)

        def ok():
            try:
                t = float(temp_var.get())
                lvl = int(level_var.get())
                h = float(hyst_var.get())
                if not (30 <= t <= 90):
                    raise ValueError("Temperature must be 30–90°C")
                if not (0 <= lvl <= 4):
                    raise ValueError("Level must be 0–4")
                if not (1 <= h <= 15):
                    raise ValueError("Hysteresis must be 1–15°C")
                new_pts = self.points + [{"temp": t, "level": lvl, "hyst": h}]
                if not valid_points(new_pts, enforce_spacing=True):
                    messagebox.showerror("Invalid", "Points must be ≥2°C apart. Please adjust.")
                    return
                self.points.append({"temp": t, "level": lvl, "hyst": h})
                self.points.sort(key=lambda p: p["temp"])
                self.draw()
                self._refresh_stats()
                dlg.destroy()
            except ValueError as ve:
                messagebox.showerror("Invalid", str(ve))
                return

        btn_frame = tk.Frame(f, bg=Palette.PANEL)
        btn_frame.pack(fill="x", pady=12)
        tk.Button(btn_frame, text="Cancel", command=dlg.destroy,
                  bg=Palette.PANEL2, fg=Palette.TEXT, font=self.nunifont).pack(side="right", padx=6)
        tk.Button(btn_frame, text="Add", command=ok,
                  bg=Palette.ACCENT, fg="white", font=self.nunifont).pack(side="right")

        dlg.update()
        dlg.geometry(f"+{self.root.winfo_x() + 50}+{self.root.winfo_y() + 50}")

    def _remove_selected(self):
        if self.selected is None or len(self.points) < 2:
            messagebox.showinfo("Info", "Select a point first (click on a point in the graph).")
            return
        self.points.remove(self.selected)
        self.selected = None if len(self.points) < 2 else self.points[-1]
        self.draw()
        self._refresh_stats()

    def _restore_defaults(self):
        if messagebox.askyesno("Restore Defaults",
                               "Restore the default 5-point fan curve?"):
            self.points = [p.copy() for p in DEFAULT]
            self.selected = None
            self.draw()
            self._refresh_stats()

    # ---- Actions ----

    def apply(self):
        try:
            save_curve(self.points)
        except ValueError as e:
            messagebox.showerror("Save Error", str(e))
            return
        self.status.set("Curve saved to ~/.config/pi5-fan-curve/curve.json")
        self._refresh_stats()
        messagebox.showinfo("Saved", "Fan curve saved successfully.\n\n"
                          "The daemon checks this file every ~1 second.\n"
                          "Restart the service for changes to take effect.")

    def _refresh_stats(self):
        temp = cpu_temp()
        d = fan_device()
        state = "Fan interface not detected"
        if d:
            try:
                state = f"State: {(d/'cur_state').read_text().strip()}/{(d/'max_state').read_text().strip()}"
            except Exception:
                state = f"Device: {d}"
        self.stats.set(
            f"CPU: {temp:.1f}°C · " if temp is not None else "CPU unavailable · "
        )
        self.root.after(1500, self._refresh_stats)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()