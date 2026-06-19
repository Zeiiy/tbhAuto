"""TBH AFK Bot - application de bureau native (customtkinter).

Reutilise tout le moteur du bot (bot/*). Lancer : python gui.py
ou via l'exe construit par build_exe.ps1.
"""
import os
import sys
import time
import queue
import threading
import tkinter as tk
import tkinter.messagebox as messagebox

import cv2
import customtkinter as ctk
from PIL import Image, ImageTk

from bot.config import Config
from bot.engine import BotEngine
from bot.log_watch import LogWatcher, classify_chest_key
from bot import calib_store
from bot import updater

APP_VERSION = "1.1.4"


def resource_dir():
    """Ressources read-only bundlees (templates). _MEIPASS si exe, sinon script."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def persist_dir():
    """Dossier persistant et modifiable (logs, calibration.json)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

GREEN, RED, AMBER, BLUE, MUTED = "#3fb950", "#f0506e", "#d9a441", "#4aa3df", "#8b97a5"
ACCENT = "#2dd4bf"

# (cle feature, titre, description, cle d'intervalle next_due ou None, texte cadence fixe)
FEATURES = [
    ("auto_synthesis", "Auto Synthèse", "Fusionne les grades cochés ci-dessous",
     "auto_synthesis", None, "#2dd4bf"),
    ("auto_chest", "Auto Coffre", "Ouvre les coffres dès leur apparition",
     None, "en continu", "#d9a441"),
    ("auto_ranger", "Auto Ranger", "Range le stash (nombre de pages réglable)",
     "tout_ranger", None, "#4aa3df"),
]
# Ordre du jeu : gris < vert < bleu < orange < rouge < violet. (cle, label, couleur)
GRADES_UI = [
    ("common", "Gris", "#c9d1d9"), ("uncommon", "Vert", "#3fb950"),
    ("rare", "Bleu", "#4aa3df"), ("legendary", "Orange", "#e3852b"),
    ("immortal", "Rouge", "#f0506e"), ("arcana", "Violet", "#a371f7"),
]
GOLD = "#e3b341"
# Cartes de l'Assistant (timers de coffres). (cle type, titre, couleur, sous-titre)
CHESTS_UI = [
    ("elite", "Coffre Élite", GOLD, "boss de fin de run · 7 min"),
    ("normal", "Coffre Normal", BLUE, "monstres normaux · 5 min"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"TBH AFK Bot  v{APP_VERSION}")
        self.geometry("880x920")
        self.minsize(840, 800)

        os.chdir(persist_dir())
        self.cfg = Config()
        self.cfg.templates_dir = os.path.join(resource_dir(), "templates")
        calib_store.load_into(self.cfg)
        self.log_q = queue.Queue()
        self.engine = BotEngine(self.cfg, log=self.log_q.put)

        self.feat_vars = {}
        self.count_labels = {}
        self.interval_entries = {}   # nd_key -> (emin, emax)
        self.countdowns = {}         # feature key -> (label, nd_key)
        self.calib_entries = {}
        self.assistant_win = None
        self.update_q = queue.Queue()
        self.update_info = None
        self._imgtk = None
        self._pscale = 0.0
        self._fsize = (0, 0)

        self._build()
        self._load_entries()
        self._load_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self._drain_logs)
        self.after(400, self._refresh_state)
        self.after(1500, self._start_update_check)

    # ------------------------------ UI ------------------------------
    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 2))
        ctk.CTkLabel(head, text="TBH AFK Bot",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(head, text="Assistant personnel", width=168, height=30,
                      fg_color="#6366f1", hover_color="#818cf8", text_color="white",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._open_assistant).pack(side="left", padx=14)
        # Bouton de mise a jour : cree masque, packe seulement si une maj est dispo.
        self.update_btn = ctk.CTkButton(head, text="", width=176, height=30,
                                        fg_color=AMBER, hover_color="#c8922f",
                                        text_color="#241a05",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        command=self._do_update)
        self.status_dot = ctk.CTkLabel(head, text="●  Arrêté", text_color=MUTED,
                                       font=ctk.CTkFont(size=13, weight="bold"),
                                       corner_radius=999, fg_color="#1c232d",
                                       width=110, height=30)
        self.status_dot.pack(side="right")
        self.cal_warn = ctk.CTkLabel(head, text="", text_color=AMBER, font=ctk.CTkFont(size=12))
        self.cal_warn.pack(side="right", padx=10)

        self.tabs = ctk.CTkTabview(self, corner_radius=12)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=10)
        self._build_control(self.tabs.add("Contrôle"))
        self._build_calib(self.tabs.add("Calibrage"))

    def _build_control(self, parent):
        for key, title, desc, nd_key, cadence, accent in FEATURES:
            card = self._feature_card(parent, key, title, desc, nd_key, cadence, accent)
            if key == "auto_synthesis":
                self._grade_selector(card)
            elif key == "auto_ranger":
                self._ranger_pages(card)

        # Reglages communs
        srow = ctk.CTkFrame(parent, corner_radius=12)
        srow.pack(fill="x", padx=6, pady=(8, 6))
        inner = ctk.CTkFrame(srow, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(inner, text="Durée max").pack(side="left")
        self.maxrun = ctk.CTkEntry(inner, width=70)
        self.maxrun.pack(side="left", padx=(8, 4))
        self.maxrun.bind("<FocusOut>", lambda e: self._apply_settings())
        ctk.CTkLabel(inner, text="min  (0 = illimité)", text_color=MUTED).pack(side="left")
        self.debug_var = ctk.BooleanVar(value=self.cfg.debug)
        ctk.CTkCheckBox(inner, text="Debug", variable=self.debug_var,
                        command=lambda: setattr(self.cfg, "debug", self.debug_var.get())
                        ).pack(side="right")

        # Demarrer / Arreter
        crow = ctk.CTkFrame(parent, fg_color="transparent")
        crow.pack(fill="x", padx=6, pady=6)
        self.run_btn = ctk.CTkButton(crow, text="▶   Démarrer", height=46,
                                     font=ctk.CTkFont(size=16, weight="bold"),
                                     fg_color=GREEN, hover_color="#2ea043",
                                     text_color="#06281f", command=self._toggle_run)
        self.run_btn.pack(side="left", fill="x", expand=True)
        self.runtime_lbl = ctk.CTkLabel(crow, text="", text_color=MUTED, width=80)
        self.runtime_lbl.pack(side="left", padx=10)

        # Journal
        ctk.CTkLabel(parent, text="Journal", anchor="w",
                     text_color=MUTED).pack(fill="x", padx=14, pady=(6, 0))
        self.console = ctk.CTkTextbox(parent, font=ctk.CTkFont(family="Consolas", size=12),
                                      corner_radius=10)
        self.console.pack(fill="both", expand=True, padx=6, pady=(2, 4))
        self.console.configure(state="disabled")
        ctk.CTkLabel(parent, text="Arrêt d'urgence : souris coin haut-gauche  ·  Ctrl+Alt+K",
                     text_color=MUTED, font=ctk.CTkFont(size=11)).pack(pady=(0, 6))

    def _feature_card(self, parent, key, title, desc, nd_key, cadence, accent="#2dd4bf"):
        card = ctk.CTkFrame(parent, corner_radius=14)
        card.pack(fill="x", padx=4, pady=7)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(13, 2))
        ctk.CTkLabel(top, text="●", text_color=accent,
                     font=ctk.CTkFont(size=15)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(top, text=title,
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        var = ctk.BooleanVar(value=self.engine.features.get(key, False))
        self.feat_vars[key] = var
        ctk.CTkSwitch(top, text="", variable=var, width=48,
                      progress_color=ACCENT,
                      command=lambda k=key, v=var: self.engine.set_feature(k, v.get())
                      ).pack(side="right")
        cnt = ctk.CTkLabel(top, text="0", width=42, height=26, corner_radius=8,
                           fg_color="#0b3b37", text_color=ACCENT,
                           font=ctk.CTkFont(size=14, weight="bold"))
        cnt.pack(side="right", padx=12)
        self.count_labels[key] = cnt

        ctk.CTkLabel(card, text=desc, text_color=MUTED,
                     anchor="w").pack(fill="x", padx=16, pady=(0, 2))

        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 12))
        if nd_key:
            ctk.CTkLabel(bottom, text="toutes les").pack(side="left")
            emin = ctk.CTkEntry(bottom, width=46)
            emin.pack(side="left", padx=4)
            ctk.CTkLabel(bottom, text="à").pack(side="left")
            emax = ctk.CTkEntry(bottom, width=46)
            emax.pack(side="left", padx=4)
            ctk.CTkLabel(bottom, text="min").pack(side="left")
            emin.bind("<FocusOut>", lambda e: self._apply_settings())
            emax.bind("<FocusOut>", lambda e: self._apply_settings())
            self.interval_entries[nd_key] = (emin, emax)
            cd = ctk.CTkLabel(bottom, text="", text_color=ACCENT,
                              font=ctk.CTkFont(size=13, weight="bold"))
            cd.pack(side="right")
            self.countdowns[key] = (cd, nd_key)
        else:
            ctk.CTkLabel(bottom, text=cadence, text_color=ACCENT).pack(side="left")
        return card

    def _grade_selector(self, card):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(row, text="Fusionner :", text_color=MUTED).pack(side="left", padx=(0, 8))
        self.grade_vars = {}
        for gkey, glabel, gcol in GRADES_UI:
            v = ctk.BooleanVar(value=gkey in self.cfg.synthesis_allowed_grades)
            self.grade_vars[gkey] = v
            ctk.CTkCheckBox(row, text=glabel, variable=v,
                            checkbox_width=18, checkbox_height=18,
                            text_color=gcol, fg_color=gcol,
                            hover_color=gcol, border_color=gcol,
                            command=self._apply_grades).pack(side="left", padx=5)

    def _apply_grades(self):
        self.cfg.synthesis_allowed_grades = [g for g, v in self.grade_vars.items() if v.get()]
        try:
            calib_store.save(self.cfg)
        except Exception:
            pass

    def _ranger_pages(self, card):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(row, text="Pages de stash à ranger :").pack(side="left", padx=(0, 8))
        n = max(1, len(self.cfg.stash_page_tabs) or 4)
        self.ranger_pages_var = ctk.StringVar(value=str(min(self.cfg.ranger_pages, n)))
        ctk.CTkOptionMenu(row, values=[str(i) for i in range(1, n + 1)],
                          variable=self.ranger_pages_var, width=72,
                          command=lambda _v: self._apply_ranger_pages()).pack(side="left")

    def _apply_ranger_pages(self):
        try:
            self.cfg.ranger_pages = int(self.ranger_pages_var.get())
        except ValueError:
            pass
        try:
            calib_store.save(self.cfg)
        except Exception:
            pass

    # --------------------------- reglages ---------------------------
    def _range_of(self, nd_key):
        return (self.cfg.tout_ranger_interval_range if nd_key == "tout_ranger"
                else self.cfg.action_interval_ranges[nd_key])

    def _set_range(self, nd_key, r):
        if nd_key == "tout_ranger":
            self.cfg.tout_ranger_interval_range = r
        else:
            self.cfg.action_interval_ranges[nd_key] = r

    def _apply_settings(self):
        for nd_key, (emin, emax) in self.interval_entries.items():
            cur = self._range_of(nd_key)
            try:
                lo, hi = float(emin.get()) * 60.0, float(emax.get()) * 60.0
                self._set_range(nd_key, (lo, hi) if hi >= lo else (hi, lo))
            except ValueError:
                pass  # garde l'ancienne valeur
        try:
            self.cfg.max_runtime_minutes = int(self.maxrun.get())
        except ValueError:
            pass
        try:
            calib_store.save(self.cfg)
        except Exception:
            pass

    def _load_settings(self):
        for nd_key, (emin, emax) in self.interval_entries.items():
            lo, hi = self._range_of(nd_key)
            emin.delete(0, "end"); emin.insert(0, f"{lo / 60:g}")
            emax.delete(0, "end"); emax.insert(0, f"{hi / 60:g}")
        self.maxrun.delete(0, "end")
        self.maxrun.insert(0, str(self.cfg.max_runtime_minutes))

    # --------------------------- assistant --------------------------
    def _open_assistant(self):
        """Ouvre (ou ramene au premier plan) la fenetre detachable de l'Assistant."""
        if self.assistant_win is not None and self.assistant_win.winfo_exists():
            self.assistant_win.deiconify()
            self.assistant_win.lift()
            self.assistant_win.focus()
            return
        self.assistant_win = AssistantWindow(self, self.cfg)

    # ----------------------- mise a jour auto -----------------------
    def _start_update_check(self):
        """Verifie en tache de fond si une version plus recente est dispo (exe seulement).

        Se reprogramme toutes les 30 min tant qu'aucune maj n'a ete trouvee, pour qu'un
        run AFK de plusieurs heures voie le bouton apparaitre sans relancer l'app.
        """
        if not updater.is_frozen() or self.update_info:
            return
        def work():
            self.update_q.put(updater.check_for_update(APP_VERSION))
        threading.Thread(target=work, daemon=True).start()
        self.after(30 * 60 * 1000, self._start_update_check)

    def _show_update(self, info):
        self.update_info = info
        self.update_btn.configure(text=f"↑Mise à jour {info['version']}", state="normal")
        if not self.update_btn.winfo_ismapped():
            self.update_btn.pack(side="left", padx=6)

    def _do_update(self):
        info = self.update_info
        if not info or not updater.is_frozen():
            return
        if not messagebox.askyesno(
                "Mise à jour",
                f"Installer la version {info['version']} ?\n\n"
                "L'app va se fermer pour l'installer ; tu la rouvriras "
                "(double-clic) pour terminer."):
            return
        self.update_btn.configure(state="disabled", text="Téléchargement… 0%")

        def work():
            dest = updater.current_exe() + ".new"
            try:
                def prog(got, total):
                    pct = int(got * 100 / total) if total else 0
                    self.after(0, lambda: self.update_btn.configure(text=f"Téléchargement… {pct}%"))
                updater.download(info["url"], dest, prog)
            except Exception as e:
                self.after(0, lambda: (self.update_btn.configure(
                    state="normal", text=f"↑Réessayer {info['version']}"),
                    self.log_q.put(f"[maj] echec telechargement: {e}")))
                return
            self.after(0, lambda: self._finish_update(dest))
        threading.Thread(target=work, daemon=True).start()

    def _finish_update(self, dest):
        ver = (self.update_info or {}).get("version", "")
        try:
            updater.stage_replace(dest)
        except Exception as e:
            self.log_q.put(f"[maj] echec installation: {e}")
            self.update_btn.configure(state="normal", text="↑Réessayer")
            return
        self.log_q.put("[maj] telechargee, installation a la fermeture")
        messagebox.showinfo(
            "Mise à jour prête",
            f"La version {ver} a été téléchargée.\n\n"
            "L'app va se fermer pour l'installer, puis rouvre TBHBot.exe "
            "(double-clic) pour lancer la nouvelle version.")
        self._on_close()   # quitte pour liberer l'exe ; le relais remet le nouvel exe en place

    # --------------------------- controle ---------------------------
    def _toggle_run(self):
        if self.engine.running:
            self.engine.stop()
        else:
            self._apply_settings()   # applique les champs avant de lancer
            self.engine.start()

    @staticmethod
    def _fmt(sec):
        sec = max(0, int(sec))
        return f"{sec // 60}m{sec % 60:02d}s" if sec >= 60 else f"{sec}s"

    def _drain_logs(self):
        try:
            while True:
                line = self.log_q.get_nowait()
                self.console.configure(state="normal")
                self.console.insert("end", line + "\n")
                self.console.see("end")
                self.console.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(150, self._drain_logs)

    def _refresh_state(self):
        run = self.engine.running
        self.run_btn.configure(text="■   Arrêter" if run else "▶   Démarrer",
                               fg_color=RED if run else GREEN,
                               hover_color="#c9304c" if run else "#2ea043",
                               text_color="#2a050d" if run else "#06281f")
        self.status_dot.configure(text=("●  En cours" if run else "●  Arrêté"),
                                  text_color=GREEN if run else MUTED,
                                  fg_color="#0e2a1e" if run else "#1c232d")
        if run and self.engine._started_at:
            el = int(time.time() - self.engine._started_at)
            self.runtime_lbl.configure(text=f"{el // 60:02d}:{el % 60:02d}")
        else:
            self.runtime_lbl.configure(text="")
        for k, lbl in self.count_labels.items():
            lbl.configure(text=str(self.engine.counters.get(k, 0)))
        now = time.time()
        for key, (lbl, nd_key) in self.countdowns.items():
            if run and self.engine.features.get(key) and nd_key in self.engine._next_due:
                rem = self.engine._next_due[nd_key] - now
                lbl.configure(text=("prochaine : " + self._fmt(rem)) if rem > 0 else "en cours…")
            elif self.engine.features.get(key):
                lbl.configure(text="prête")
            else:
                lbl.configure(text="")
        cal = bool(self.cfg.synthesis_grid_rect and self.cfg.stash_grid_rect)
        self.cal_warn.configure(text="" if cal else "⚠ non calibré")
        try:
            info = self.update_q.get_nowait()
            if info:
                self._show_update(info)
        except queue.Empty:
            pass
        self.after(500, self._refresh_state)

    # --------------------------- calibrage --------------------------
    def _build_calib(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(top, text="Rafraîchir l'aperçu", command=self.refresh_preview,
                      width=170).pack(side="left", padx=4)
        self.win_lbl = ctk.CTkLabel(top, text="Clique « Rafraîchir » pour capturer.")
        self.win_lbl.pack(side="left", padx=12)
        self.hsv_lbl = ctk.CTkLabel(top, text="HSV : —  (clic sur l'image)")
        self.hsv_lbl.pack(side="right", padx=8)

        self.img_label = tk.Label(parent, bg="#0d1117", cursor="crosshair",
                                  text="(aperçu)", fg=MUTED)
        self.img_label.pack(padx=8, pady=4)
        self.img_label.bind("<Button-1>", self._on_preview_click)

        ed = ctk.CTkFrame(parent)
        ed.pack(fill="x", padx=8, pady=6)
        self._rect_row(ed, "Synthèse — rect (x,y,w,h)", "synthesis_grid_rect")
        self._rc_row(ed, "Synthèse — lignes / cols", "synthesis_grid_rows", "synthesis_grid_cols")
        self._rect_row(ed, "Stash — rect (x,y,w,h)", "stash_grid_rect")
        self._rc_row(ed, "Stash — lignes / cols", "stash_grid_rows", "stash_grid_cols")
        self._rect_row(ed, "Inventaire — rect (x,y,w,h)", "inventory_grid_rect")
        self._rc_row(ed, "Inventaire — lignes / cols", "inventory_grid_rows", "inventory_grid_cols")
        self._tabs_row(ed)

        btns = ctk.CTkFrame(parent, fg_color="transparent")
        btns.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(btns, text="Enregistrer", command=self.save_calib).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Adapter à la taille actuelle", fg_color="gray30",
                      command=self.rescale_calib).pack(side="left", padx=4)
        self.calib_msg = ctk.CTkLabel(btns, text="")
        self.calib_msg.pack(side="left", padx=10)

    def _row(self, parent, label):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", pady=3)
        ctk.CTkLabel(r, text=label, width=200, anchor="w").pack(side="left", padx=6)
        return r

    def _rect_row(self, parent, label, key):
        r = self._row(parent, label)
        self.calib_entries[key] = [self._mini(r) for _ in range(4)]

    def _rc_row(self, parent, label, kr, kc):
        r = self._row(parent, label)
        self.calib_entries[kr] = self._mini(r)
        self.calib_entries[kc] = self._mini(r)

    def _tabs_row(self, parent):
        r = self._row(parent, "Onglets pages (x,y ; …)")
        e = ctk.CTkEntry(r, width=340)
        e.pack(side="left", padx=3)
        self.calib_entries["stash_page_tabs"] = e

    def _mini(self, parent):
        e = ctk.CTkEntry(parent, width=66)
        e.pack(side="left", padx=3)
        return e

    def refresh_preview(self):
        try:
            frame, _, _ = self.engine.cap.grab()
        except Exception as e:
            self.win_lbl.configure(text=f"capture impossible : {e}", text_color=RED)
            return
        overlay = calib_store.render_overlay(self.cfg, frame)
        h, w = overlay.shape[:2]
        self._fsize = (w, h)
        scale = min(820 / w, 430 / h)
        self._pscale = scale
        disp = cv2.resize(overlay, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        img = Image.fromarray(cv2.cvtColor(disp, cv2.COLOR_BGR2RGB))
        self._imgtk = ImageTk.PhotoImage(img)
        self.img_label.configure(image=self._imgtk, text="")
        win = self.engine.cap.get_window()
        cw = self.cfg.calib_window_size
        if win and cw:
            ok = abs(win.width - cw[0]) <= 3 and abs(win.height - cw[1]) <= 3
            if ok:
                self.win_lbl.configure(
                    text=f"Fenêtre {win.width}×{win.height} · taille de référence ✓",
                    text_color=GREEN)
            else:
                s = ((win.width / cw[0]) + (win.height / cw[1])) / 2
                self.win_lbl.configure(
                    text=f"Fenêtre {win.width}×{win.height} · auto-calibrage échelle ×{s:.2f}",
                    text_color=AMBER)
        elif win:
            self.win_lbl.configure(text=f"Fenêtre {win.width}×{win.height}", text_color=MUTED)
        else:
            self.win_lbl.configure(text="fenêtre du jeu introuvable", text_color=RED)

    def _on_preview_click(self, ev):
        if not self._pscale:
            return
        fx, fy = int(ev.x / self._pscale), int(ev.y / self._pscale)
        try:
            frame, _, _ = self.engine.cap.grab()
        except Exception:
            return
        hsv = calib_store.sample_hsv(frame, fx, fy)
        self.hsv_lbl.configure(text=(f"({fx},{fy})  H={hsv['h']} S={hsv['s']} V={hsv['v']}"
                                     if hsv else f"({fx},{fy}) hors cadre"))

    def _load_entries(self):
        c = self.cfg

        def fill(entry, val):
            entry.delete(0, "end")
            entry.insert(0, "" if val is None else str(val))

        for key in ("synthesis_grid_rect", "stash_grid_rect", "inventory_grid_rect"):
            for e, v in zip(self.calib_entries[key], getattr(c, key) or (0, 0, 0, 0)):
                fill(e, v)
        for key in ("synthesis_grid_rows", "synthesis_grid_cols",
                    "stash_grid_rows", "stash_grid_cols",
                    "inventory_grid_rows", "inventory_grid_cols"):
            fill(self.calib_entries[key], getattr(c, key))
        fill(self.calib_entries["stash_page_tabs"],
             " ; ".join(f"{x},{y}" for x, y in (c.stash_page_tabs or [])))

    def _read_entries(self):
        d = {}
        for key in ("synthesis_grid_rect", "stash_grid_rect", "inventory_grid_rect"):
            d[key] = [int(e.get()) for e in self.calib_entries[key]]
        for key in ("synthesis_grid_rows", "synthesis_grid_cols",
                    "stash_grid_rows", "stash_grid_cols",
                    "inventory_grid_rows", "inventory_grid_cols"):
            d[key] = int(self.calib_entries[key].get())
        tabs = []
        for part in self.calib_entries["stash_page_tabs"].get().split(";"):
            part = part.strip()
            if part:
                x, y = part.split(",")
                tabs.append([int(x), int(y)])
        d["stash_page_tabs"] = tabs
        return d

    def save_calib(self):
        if self.engine.running:
            self.calib_msg.configure(text="Arrête le bot avant de calibrer.", text_color=RED)
            return
        try:
            calib_store.apply_dict(self.cfg, self._read_entries())
            calib_store.save(self.cfg)
        except Exception as e:
            self.calib_msg.configure(text=f"Erreur : {e}", text_color=RED)
            return
        self.calib_msg.configure(text="Enregistré ✓", text_color=GREEN)
        self.refresh_preview()

    def rescale_calib(self):
        win = self.engine.cap.get_window()
        cw = self.cfg.calib_window_size
        if not (win and cw):
            self.calib_msg.configure(text="fenêtre ou taille de calib inconnue", text_color=RED)
            return
        sx, sy = win.width / cw[0], win.height / cw[1]

        def sr(r):
            return (int(r[0] * sx), int(r[1] * sy), int(r[2] * sx), int(r[3] * sy)) if r else r
        self.cfg.synthesis_grid_rect = sr(self.cfg.synthesis_grid_rect)
        self.cfg.stash_grid_rect = sr(self.cfg.stash_grid_rect)
        self.cfg.stash_page_tabs = [(int(x * sx), int(y * sy)) for x, y in self.cfg.stash_page_tabs]
        self.cfg.calib_window_size = (win.width, win.height)
        self._load_entries()
        self.calib_msg.configure(text="Géométrie adaptée — templates à recapturer.",
                                 text_color=AMBER)
        self.refresh_preview()

    def _on_close(self):
        try:
            if self.assistant_win is not None and self.assistant_win.winfo_exists():
                self.assistant_win._on_close()
        except Exception:
            pass
        try:
            self.engine.stop()
        except Exception:
            pass
        self.destroy()


class AssistantWindow(ctk.CTkToplevel):
    """Fenetre detachable : timers de coffres bases sur le LOG du jeu (player.log).

    Lit en direct les acquisitions "GetBoxCount ... ItemKey : KEY", relance le
    compte a rebours du type correspondant (normal 5 min / elite 7 min) et affiche
    "Obtenable" quand il est ecoule. Ne clique jamais : c'est le bot qui ouvre les
    coffres. Les types sont reconnus via cfg.chest_key_map (910501 normal, 920501 elite).
    """

    def __init__(self, master, cfg):
        super().__init__(master)
        self.cfg = cfg
        self.title("Assistant personnel")
        self.geometry("360x300")
        self.minsize(300, 260)
        self.configure(fg_color="#0d1117")

        self.events = queue.Queue()
        self.cooldown_end = {"normal": 0.0, "elite": 0.0}  # 0 = jamais vu
        self.last_seen = {"normal": 0.0, "elite": 0.0}
        self.last_box = None        # (item_key, ts) du dernier coffre vu (tout type)
        self.cards = {}

        self._build()
        self.watcher = LogWatcher(cfg, on_box=self._on_box)
        self.watcher.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self._tick)

    # le callback tourne dans le thread du watcher -> on passe par une queue
    def _on_box(self, key, count, ts):
        self.events.put((key, ts))

    # ------------------------------ UI ------------------------------
    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(12, 2))
        ctk.CTkLabel(head, text="Assistant personnel",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text="timers de coffres", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=8)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=4)
        for ctype, label, color, sub in CHESTS_UI:
            self.cards[ctype] = self._chest_card(body, ctype, label, color, sub)

        self.status_lbl = ctk.CTkLabel(self, text="", text_color=MUTED,
                                       font=ctk.CTkFont(size=11), anchor="w")
        self.status_lbl.pack(fill="x", padx=14, pady=(0, 8))

    def _chest_card(self, parent, ctype, label, color, sub):
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color="#161b22")
        card.pack(fill="both", expand=True, pady=6)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(top, text="●", text_color=color,
                     font=ctk.CTkFont(size=15)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(top, text=label, text_color=color,
                     font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        state = ctk.CTkLabel(top, text="—", text_color=MUTED,
                             font=ctk.CTkFont(size=12, weight="bold"))
        state.pack(side="right")
        timer = ctk.CTkLabel(card, text="--:--", text_color=MUTED,
                             font=ctk.CTkFont(family="Consolas", size=32, weight="bold"))
        timer.pack(anchor="w", padx=18, pady=(2, 2))
        bar = ctk.CTkProgressBar(card, height=8, corner_radius=6, progress_color=color)
        bar.pack(fill="x", padx=18, pady=(0, 4))
        bar.set(0)
        subl = ctk.CTkLabel(card, text=sub, text_color=MUTED, font=ctk.CTkFont(size=11))
        subl.pack(anchor="w", padx=18, pady=(0, 12))
        return {"timer": timer, "bar": bar, "sub": subl, "state": state, "color": color}

    # ----------------------------- logique --------------------------
    def _ingest(self, key, ts):
        self.last_box = (key, ts)
        ctype = classify_chest_key(self.cfg, key)
        if ctype in self.cooldown_end:
            cd = float(self.cfg.chest_cooldowns_s.get(ctype, 300.0))
            self.cooldown_end[ctype] = ts + cd
            self.last_seen[ctype] = ts

    def _tick(self):
        try:
            while True:
                key, ts = self.events.get_nowait()
                self._ingest(key, ts)
        except queue.Empty:
            pass

        now = time.time()
        mapped_types = set(self.cfg.chest_key_prefixes.values()) | set(self.cfg.chest_key_map.values())
        for ctype, c in self.cards.items():
            total = float(self.cfg.chest_cooldowns_s.get(ctype, 300.0))
            end = self.cooldown_end[ctype]
            if ctype not in mapped_types:
                c["timer"].configure(text="non réglé", text_color=MUTED)
                c["state"].configure(text="—", text_color=MUTED)
                c["bar"].configure(progress_color="#30363d"); c["bar"].set(0)
                c["sub"].configure(text="type non configuré (chest_key_prefixes)")
            elif end <= 0:
                c["timer"].configure(text="--:--", text_color=MUTED)
                c["state"].configure(text="en veille", text_color=MUTED)
                c["bar"].configure(progress_color="#30363d"); c["bar"].set(0)
                c["sub"].configure(text="aucun loot détecté pour l'instant")
            else:
                rem = end - now
                if rem > 0:
                    c["timer"].configure(text=self._mmss(rem), text_color=c["color"])
                    c["state"].configure(text="cooldown", text_color=c["color"])
                    c["bar"].configure(progress_color=c["color"])
                    c["bar"].set(max(0.0, min(1.0, 1 - rem / total)))
                    c["sub"].configure(text="dernier loot il y a " + self._ago(now - self.last_seen[ctype]))
                else:
                    c["timer"].configure(text="Obtenable", text_color=GREEN)
                    c["state"].configure(text="✓ prêt", text_color=GREEN)
                    c["bar"].configure(progress_color=GREEN); c["bar"].set(1.0)
                    c["sub"].configure(text="lootable maintenant")

        st = self.watcher.status if self.watcher else "—"
        extra = ""
        if self.last_box:
            key, ts = self.last_box
            lbl = {"normal": "normal", "elite": "élite"}.get(
                classify_chest_key(self.cfg, key), f"clé {key}")
            extra = f" · dernier : {lbl} il y a {self._ago(now - ts)}"
        self.status_lbl.configure(text=f"surveillance : {st}{extra}")
        self.after(250, self._tick)

    @staticmethod
    def _mmss(sec):
        sec = max(0, int(round(sec)))
        return f"{sec // 60}:{sec % 60:02d}"

    @staticmethod
    def _ago(sec):
        sec = max(0, int(sec))
        if sec < 60:
            return f"{sec}s"
        if sec < 3600:
            return f"{sec // 60}m{sec % 60:02d}s"
        return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"

    def _on_close(self):
        try:
            if self.watcher:
                self.watcher.stop()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
