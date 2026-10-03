"""Reversible layout mirroring, with explicit exceptions for spatial/media controls."""
import tkinter as tk
import customtkinter as ctk
from ui.i18n import is_rtl


def opposite(value):
    return {'left': 'right', 'right': 'left', 'w': 'e', 'e': 'w',
            'nw': 'ne', 'ne': 'nw', 'sw': 'se', 'se': 'sw'}.get(value, value)


def apply_direction(root, mirror=True):
    """Remember LTR geometry once; switching languages never accumulates flips."""
    rtl = is_rtl()
    if isinstance(root, ctk.CTkScrollableFrame) and root._orientation == 'vertical':
        parent = root._parent_frame
        spacing = root._apply_widget_scaling(parent.cget('corner_radius') + parent.cget('border_width'))
        parent.grid_columnconfigure(0, weight=0 if rtl else 1)
        parent.grid_columnconfigure(1, weight=1 if rtl else 0)
        root._parent_canvas.grid_configure(column=1 if rtl else 0,
                                           padx=(0, spacing) if rtl else (spacing, 0))
        border_width = parent.cget('border_width')
        root._scrollbar.grid_configure(column=0 if rtl else 1,
                                      padx=(border_width + 1, 0) if rtl else (0, border_width + 1))
    if isinstance(root, ctk.CTkBaseClass):
        if not hasattr(root, '_fb_direction_baseline'):
            baseline = {}
            for option in ('anchor', 'justify', 'compound'):
                try:
                    baseline[option] = root.cget(option)
                except (ValueError, tk.TclError):
                    pass
            if root.winfo_manager() == 'pack':
                info = root.pack_info()
                baseline['pack'] = {key: info[key] for key in ('side', 'anchor')}
            if root.winfo_manager() == 'place':
                info = root.place_info()
                baseline['place'] = {key: info[key] for key in ('relx', 'anchor')}
            root._fb_direction_baseline = baseline
        baseline = root._fb_direction_baseline
        options = {key: opposite(value) if rtl else value for key, value in baseline.items()
                   if key in ('anchor', 'justify', 'compound')}
        if isinstance(root, ctk.CTkEntry):
            options.pop('justify', None)
        if options:
            root.configure(**options)
        if mirror and 'pack' in baseline and root.winfo_manager() == 'pack':
            root.pack_configure(**{key: opposite(value) if rtl else value
                                   for key, value in baseline['pack'].items()})
        if mirror and 'place' in baseline and root.winfo_manager() == 'place':
            info = baseline['place']
            root.place_configure(relx=1-float(info['relx']) if rtl else info['relx'],
                                 anchor=opposite(info['anchor']) if rtl else info['anchor'])
        if hasattr(root, 'set_direction'):
            root.set_direction(rtl and mirror)
        if isinstance(root, (ctk.CTkCheckBox, ctk.CTkRadioButton)):
            root.grid_columnconfigure(0, weight=1 if rtl else 0)
            root.grid_columnconfigure(2, weight=0 if rtl else 1)
            root._canvas.grid_configure(column=2 if rtl else 0, sticky='w' if rtl else 'e')
            root._text_label.grid_configure(column=0 if rtl else 2, sticky='e' if rtl else 'w')
    # Playback remains LTR: transport, timeline, timecodes and seek keys retain
    # their conventional order. Numeric input retains right alignment.
    children_mirror = mirror and not getattr(root, '_fb_keep_ltr', False)
    for child in root.winfo_children():
        apply_direction(child, children_mirror)
