import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageGrab
from ui.main_window import MainWindow
from ui.dialogs import show_about_dialog
from ui.theme import initialize_theme
import customtkinter as ctk
app=MainWindow();app.state('normal')
app.unique_faces={i:{'enabled':i!=2,'pil_image':Image.open('AutoBlureFace_icon.png')} for i in range(1,10)}
app.populate_gallery_ui()
for mode in ('Light','Dark'):
    ctk.set_appearance_mode(mode)
    for size in ('1280x820','1040x740'):
        app.geometry(size+'+20+20');app.update()
        for state in ('normal','disabled'):
            for button in (app.btn_export,app.btn_save_proj,app.btn_analyze,app.btn_play):button.configure(state=state)
            app.update()
            assert app.btn_about.winfo_ismapped()
            assert app.unique_faces[1]['widget'].winfo_ismapped()
            x,y=app.winfo_rootx(),app.winfo_rooty()
            ImageGrab.grab(bbox=(x,y,x+app.winfo_width(),y+app.winfo_height())).save(f'assets/theme-{mode.lower()}-{size}-{state}.png')
    show_about_dialog(app,'hand2');app.update();time.sleep(.35);app.update()
    dialog=[w for w in app.winfo_children() if isinstance(w,ctk.CTkToplevel)][-1]
    x,y=dialog.winfo_rootx(),dialog.winfo_rooty()
    ImageGrab.grab(bbox=(x,y,x+dialog.winfo_width(),y+dialog.winfo_height())).save(f'assets/theme-{mode.lower()}-about.png')
    dialog.destroy()
for timer in app.tk.call("after", "info"):app.tk.call("after", "cancel", timer)
app.on_closing()
from unittest.mock import patch
from main import SmartSplashScreen
for mode in ('Light','Dark'):
    ctk.set_appearance_mode(mode)
    with patch('threading.Thread.start'):
        splash=SmartSplashScreen()
    splash.reveal_if_slow();splash.update();time.sleep(.25);splash.update()
    x,y=splash.winfo_rootx(),splash.winfo_rooty()
    ImageGrab.grab(bbox=(x,y,x+splash.winfo_width(),y+splash.winfo_height())).save(f'assets/theme-{mode.lower()}-splash.png')
    for timer in splash.tk.call("after", "info"):splash.tk.call("after", "cancel", timer)
    splash.destroy()
initialize_theme();print('Both themes rendered at 1280x820 and 1040x740, enabled/disabled and About.')
