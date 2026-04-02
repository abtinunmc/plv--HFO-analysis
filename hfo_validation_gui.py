"""
HFO Validation GUI - Step 3: Inputs Wired
All input widgets hold real state via tkinter variables.
Browse dialogs, run checkboxes, options, and log/clear all functional.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog


# Default run labels shown in the Runs section
DEFAULT_RUNS = ["run-01", "run-02", "run-03", "run-04", "run-05"]


class HFOValidationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HFO Validation - qHFO Clean-Signal Validator")
        self.root.minsize(720, 620)

        # ── Main container with padding ──
        main = ttk.Frame(root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # ══════════════════════════════════════════════
        # Section 1: Directories
        # ══════════════════════════════════════════════
        sec_dirs = ttk.LabelFrame(main, text="Directories", padding=8)
        sec_dirs.pack(fill=tk.X, pady=(0, 6))

        self.raw_dir_var = tk.StringVar()
        self.h5_dir_var = tk.StringVar()
        self.out_dir_var = tk.StringVar()

        dir_items = [
            ("Raw Data Dir:", self.raw_dir_var),
            ("H5 Dir:",       self.h5_dir_var),
            ("Output Dir:",   self.out_dir_var),
        ]
        for i, (label, var) in enumerate(dir_items):
            ttk.Label(sec_dirs, text=label).grid(row=i, column=0, sticky=tk.W, padx=(0, 4), pady=2)
            entry = ttk.Entry(sec_dirs, width=55, textvariable=var)
            entry.grid(row=i, column=1, sticky=tk.EW, pady=2)
            ttk.Button(
                sec_dirs, text="Browse…",
                command=lambda v=var, l=label: self._browse_dir(v, l),
            ).grid(row=i, column=2, padx=(4, 0), pady=2)
        sec_dirs.columnconfigure(1, weight=1)

        # ══════════════════════════════════════════════
        # Section 2: Runs
        # ══════════════════════════════════════════════
        sec_runs = ttk.LabelFrame(main, text="Runs", padding=8)
        sec_runs.pack(fill=tk.X, pady=(0, 6))

        runs_frame = ttk.Frame(sec_runs)
        runs_frame.pack(anchor=tk.W)

        self.run_vars = {}  # name -> BooleanVar
        for r in DEFAULT_RUNS:
            var = tk.BooleanVar(value=True)
            self.run_vars[r] = var
            ttk.Checkbutton(runs_frame, text=r, variable=var).pack(side=tk.LEFT, padx=(0, 10))

        btn_frame = ttk.Frame(sec_runs)
        btn_frame.pack(anchor=tk.W, pady=(4, 0))
        ttk.Button(btn_frame, text="Select All", command=self._select_all_runs).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Clear All", command=self._clear_all_runs).pack(side=tk.LEFT)

        # ══════════════════════════════════════════════
        # Section 3: Options
        # ══════════════════════════════════════════════
        sec_opts = ttk.LabelFrame(main, text="Options", padding=8)
        sec_opts.pack(fill=tk.X, pady=(0, 6))

        opts_row = ttk.Frame(sec_opts)
        opts_row.pack(anchor=tk.W)

        self.debug_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_row, text="Debug Intersection", variable=self.debug_var
                         ).pack(side=tk.LEFT, padx=(0, 20))

        self.limit_hfo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_row, text="Limit Random Valid HFOs", variable=self.limit_hfo_var,
                         command=self._toggle_spinbox
                         ).pack(side=tk.LEFT, padx=(0, 4))

        self.max_hfo_var = tk.IntVar(value=500)
        self.max_hfo_spin = ttk.Spinbox(opts_row, from_=1, to=99999, width=8,
                                         textvariable=self.max_hfo_var)
        self.max_hfo_spin.pack(side=tk.LEFT)

        # ══════════════════════════════════════════════
        # Section 4: Control buttons
        # ══════════════════════════════════════════════
        ctrl = ttk.Frame(main)
        ctrl.pack(fill=tk.X, pady=(0, 6))

        self.start_btn = ttk.Button(ctrl, text="▶  Start Processing")
        self.start_btn.pack(side=tk.LEFT)
        self.cancel_btn = ttk.Button(ctrl, text="Cancel", state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=(8, 0))

        # ══════════════════════════════════════════════
        # Section 5: Progress
        # ══════════════════════════════════════════════
        prog_frame = ttk.Frame(main)
        prog_frame.pack(fill=tk.X, pady=(0, 6))

        self.progress = ttk.Progressbar(prog_frame, mode='determinate')
        self.progress.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(prog_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=(8, 0))

        # ══════════════════════════════════════════════
        # Section 6: Log output
        # ══════════════════════════════════════════════
        log_frame = ttk.LabelFrame(main, text="Log", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED,
                                bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ══════════════════════════════════════════════
        # Section 7: Bottom bar
        # ══════════════════════════════════════════════
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X, pady=(6, 0))

        ttk.Button(bottom, text="Open Output Folder", command=self._open_output_folder).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Clear Log", command=self._clear_log).pack(side=tk.RIGHT)

    # ──────────────────────────────────────────────
    # Callbacks
    # ──────────────────────────────────────────────

    def _browse_dir(self, var, title):
        """Open a folder picker and set the StringVar to the chosen path."""
        path = filedialog.askdirectory(title=f"Select {title.replace(':', '')}")
        if path:
            var.set(path)

    def _select_all_runs(self):
        for var in self.run_vars.values():
            var.set(True)

    def _clear_all_runs(self):
        for var in self.run_vars.values():
            var.set(False)

    def _toggle_spinbox(self):
        """Enable/disable the max-HFO spinbox based on the limit checkbox."""
        if self.limit_hfo_var.get():
            self.max_hfo_spin.configure(state=tk.NORMAL)
        else:
            self.max_hfo_spin.configure(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _open_output_folder(self):
        """Open the selected output directory in the system file explorer."""
        folder = self.out_dir_var.get()
        if folder and os.path.isdir(folder):
            os.startfile(folder)  # Windows-specific; fine for this use case

    def log(self, msg):
        """Append a message to the log widget (thread-safe call via .after)."""
        def _append():
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.root.after(0, _append)

    def get_selected_runs(self):
        """Return list of run names whose checkboxes are ticked."""
        return [name for name, var in self.run_vars.items() if var.get()]

    def get_config(self):
        """Collect all GUI values into a dict (will be used in Step 4)."""
        return {
            'raw_dir':             self.raw_dir_var.get(),
            'h5_dir':              self.h5_dir_var.get(),
            'out_dir':             self.out_dir_var.get(),
            'runs':                self.get_selected_runs(),
            'debug_intersection':  self.debug_var.get(),
            'max_random_valid':    self.max_hfo_var.get() if self.limit_hfo_var.get() else None,
        }


def main():
    root = tk.Tk()
    app = HFOValidationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()