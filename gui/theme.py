"""
Modern theme for ZedNet GUI, inspired by Notion.
Provides color palettes for light and dark modes.
"""

import tkinter as tk

class Theme:
    """Notion-inspired color and font theme for the ZedNet GUI."""

    # Color Palette (Light Mode)
    LIGHT_BACKGROUND = "#FFFFFF"
    LIGHT_SURFACE = "#F7F7F7"  # Slightly off-white for frames
    LIGHT_TEXT = "#333333"
    LIGHT_TEXT_SECONDARY = "#777777"
    LIGHT_PRIMARY = "#007AFF"  # A modern blue for interactive elements
    LIGHT_PRIMARY_HOVER = "#0056b3"
    LIGHT_SEPARATOR = "#EAEAEA"
    LIGHT_ERROR = "#E53935"
    LIGHT_SUCCESS = "#43A047"
    LIGHT_WARNING = "#FFA000"

    # Color Palette (Dark Mode)
    DARK_BACKGROUND = "#2F2F2F"
    DARK_SURFACE = "#3A3A3A"
    DARK_TEXT = "#EAEAEA"
    DARK_TEXT_SECONDARY = "#AAAAAA"
    DARK_PRIMARY = "#0A84FF"
    DARK_PRIMARY_HOVER = "#0060df"
    DARK_SEPARATOR = "#444444"
    DARK_ERROR = "#EF5350"
    DARK_SUCCESS = "#66BB6A"
    DARK_WARNING = "#FFB74D"

    # Fonts
    FONT_FAMILY = "Segoe UI"  # A clean, modern sans-serif font
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_LARGE = 12
    FONT_SIZE_HEADER = 14

    @staticmethod
    def apply_theme(style, mode='light'):
        """
        Applies the selected theme to the ttk Style object.

        Args:
            style: The ttk.Style() object.
            mode: 'light' or 'dark'.
        """
        if mode == 'dark':
            bg = Theme.DARK_BACKGROUND
            surface = Theme.DARK_SURFACE
            text = Theme.DARK_TEXT
            text_secondary = Theme.DARK_TEXT_SECONDARY
            primary = Theme.DARK_PRIMARY
            primary_hover = Theme.DARK_PRIMARY_HOVER
            separator = Theme.DARK_SEPARATOR
        else: # Default to light
            bg = Theme.LIGHT_BACKGROUND
            surface = Theme.LIGHT_SURFACE
            text = Theme.LIGHT_TEXT
            text_secondary = Theme.LIGHT_TEXT_SECONDARY
            primary = Theme.LIGHT_PRIMARY
            primary_hover = Theme.LIGHT_PRIMARY_HOVER
            separator = Theme.LIGHT_SEPARATOR

        # Configure root style
        style.theme_use('clam')
        style.configure('.',
            background=bg,
            foreground=text,
            fieldbackground=surface,
            borderwidth=1,
            relief=tk.FLAT,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL)
        )

        # Notebook (Tabs)
        style.configure('TNotebook', background=bg, borderwidth=0)
        style.configure('TNotebook.Tab',
            background=bg,
            foreground=text_secondary,
            padding=[8, 4],
            borderwidth=0,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL)
        )
        style.map('TNotebook.Tab',
            background=[('selected', surface)],
            foreground=[('selected', text)]
        )

        # Treeview (Lists)
        style.configure('Treeview',
            background=surface,
            foreground=text,
            fieldbackground=surface,
            rowheight=25,
            borderwidth=0
        )
        style.configure('Treeview.Heading',
            background=bg,
            foreground=text,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, 'bold'),
            padding=[5, 5]
        )
        style.map('Treeview.Heading',
            background=[('active', surface)],
        )
        style.map('Treeview',
            background=[('selected', primary)],
            foreground=[('selected', '#FFFFFF')]
        )

        # Buttons
        style.configure('TButton',
            background=primary,
            foreground='#FFFFFF',
            padding=[10, 5],
            borderwidth=0,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, 'bold')
        )
        style.map('TButton',
            background=[('active', primary_hover), ('disabled', surface)],
            foreground=[('disabled', text_secondary)]
        )

        # Frames and Labels
        style.configure('TFrame', background=bg)
        style.configure('TLabel', background=bg, foreground=text)
        style.configure('Status.TLabel', font=(Theme.FONT_FAMILY, 9)) # For status bar

        # Entry fields
        style.configure('TEntry',
            borderwidth=1,
            relief=tk.SOLID,
            bordercolor=separator,
            padding=5
        )
        style.map('TEntry',
            bordercolor=[('focus', primary)],
        )

        # Separators
        style.configure('TSeparator', background=separator)

        # Scrollbars
        style.configure('TScrollbar',
            background=surface,
            troughcolor=bg,
            relief=tk.FLAT,
            arrowsize=12
        )
        style.map('TScrollbar',
            background=[('active', text_secondary)]
        )
