"""Native Tk theme for a calm, professional Windows desktop interface."""

from tkinter import ttk


COLORS = {
    "navy": "#16324A",
    "navy_dark": "#0F2537",
    "blue": "#2176AE",
    "blue_light": "#EAF3F9",
    "green": "#2D7D5A",
    "orange": "#C77721",
    "red": "#B94A48",
    "ink": "#172430",
    "muted": "#687987",
    "line": "#D8E1E8",
    "surface": "#FFFFFF",
    "background": "#F2F5F7",
    "preview": "#FFF3CD",
}


def configure_theme(root) -> None:
    root.configure(bg=COLORS["background"])
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Segoe UI", 10), foreground=COLORS["ink"])
    style.configure("App.TFrame", background=COLORS["background"])
    style.configure("Card.TFrame", background=COLORS["surface"])
    style.configure("Hero.TFrame", background=COLORS["navy"])
    style.configure("Card.TLabel", background=COLORS["surface"], foreground=COLORS["ink"])
    style.configure("Field.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=("Segoe UI", 9, "bold"))
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("Title.TLabel", background=COLORS["surface"], foreground=COLORS["navy"], font=("Segoe UI Semibold", 17))
    style.configure("Section.TLabel", background=COLORS["surface"], foreground=COLORS["navy"], font=("Segoe UI Semibold", 12))
    style.configure("HeroTitle.TLabel", background=COLORS["navy"], foreground="white", font=("Segoe UI Semibold", 20))
    style.configure("HeroText.TLabel", background=COLORS["navy"], foreground="#D5E3EC", font=("Segoe UI", 10))
    style.configure("Metric.TLabel", background=COLORS["surface"], foreground=COLORS["navy"], font=("Segoe UI Semibold", 20))
    style.configure("TNotebook", background=COLORS["background"], borderwidth=0)
    style.configure("TNotebook.Tab", padding=(17, 10), font=("Segoe UI Semibold", 9), background="#E1E8ED")
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["surface"])],
        foreground=[("selected", COLORS["navy"])],
    )
    style.configure(
        "Treeview",
        rowheight=30,
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        bordercolor=COLORS["line"],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["navy"],
        foreground="white",
        font=("Segoe UI Semibold", 9),
        relief="flat",
        padding=(7, 7),
    )
    style.map(
        "Treeview",
        background=[("selected", "#DCECF7")],
        foreground=[("selected", COLORS["ink"])],
    )
    for name, colour in (
        ("Primary", COLORS["blue"]),
        ("Success", COLORS["green"]),
        ("Warning", COLORS["orange"]),
        ("Danger", COLORS["red"]),
        ("Secondary", "#5C6E7C"),
    ):
        style.configure(
            f"{name}.TButton",
            background=colour,
            foreground="white",
            padding=(13, 8),
            font=("Segoe UI Semibold", 9),
            borderwidth=0,
        )
        style.map(
            f"{name}.TButton",
            background=[("active", colour), ("disabled", "#AAB4BE")],
        )
    style.configure("Tool.TButton", padding=(10, 7), font=("Segoe UI Semibold", 9))
