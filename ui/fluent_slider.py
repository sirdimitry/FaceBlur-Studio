"""Windows-style horizontal slider with ring thumb and value feedback."""
import ctypes
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
from ui.theme import UI_FONT, ACCENT, TRACK, DISABLED_TEXT, SURFACE, TEXT


def animations_enabled():
    if sys.platform != 'win32':
        return True
    enabled = ctypes.c_int(1)
    ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)
    return bool(enabled.value)


class FluentSlider(ctk.CTkSlider):
    def __init__(self, *args, value_format=None, **kwargs):
        self._inner_radius = 5.0
        self._animation = None
        self._pressed = False
        self._focused = False
        self._tip = None
        self._value_format = value_format or (lambda value: f'{value:.0f}%')
        kwargs['height'] = 24
        super().__init__(*args, **kwargs)
        self._canvas.configure(takefocus=1)
        self._canvas.bind('<ButtonRelease-1>', self._release)
        self._canvas.bind('<FocusIn>', self._focus_in)
        self._canvas.bind('<FocusOut>', self._focus_out)
        for key, direction in (('Left', -1), ('Down', -1), ('Right', 1), ('Up', 1)):
            self._canvas.bind('<'+key+'>', lambda e, d=direction: self._key(d))
        self._canvas.bind('<Home>', lambda e: self._key_value(self._from_))
        self._canvas.bind('<End>', lambda e: self._key_value(self._to))
        self._canvas.bind('<Escape>', lambda e: self._hide_tip())

    def _draw(self, no_color_updates=False):
        if not hasattr(self, '_canvas'):
            return
        scale = self._apply_widget_scaling(1)
        w=max(1,round(self._current_width*scale));h=max(1,round(self._current_height*scale))
        bg=self._apply_appearance_mode(self._bg_color)
        self._canvas.configure(bg=bg)
        rgb = tuple(component // 256 for component in self.winfo_rgb(bg))
        image=Image.new('RGB',(w*3,h*3),rgb);draw=ImageDraw.Draw(image)
        margin=11*scale;cy=h/2;x=margin+self._value*max(1,w-2*margin)
        accent=self._apply_appearance_mode(ACCENT if self._state=='normal' else DISABLED_TEXT)
        track=self._apply_appearance_mode(TRACK)
        def line(a,b,color):draw.line((a*3,cy*3,b*3,cy*3),fill=color,width=max(1,round(4*scale*3)))
        line(margin,w-margin,track);line(margin,x,accent)
        def circle(radius,color,outline=None):
            r=radius*scale
            draw.ellipse(((x-r)*3,(cy-r)*3,(x+r)*3,(cy+r)*3),fill=color,outline=outline,width=max(1,round(scale*3)))
        circle(10,self._apply_appearance_mode(SURFACE),track)
        circle(self._inner_radius,accent)
        if self._focused:circle(11,None,self._apply_appearance_mode(TEXT))
        self._thumb_image=ImageTk.PhotoImage(image.resize((w,h),Image.Resampling.LANCZOS),master=self._canvas)
        self._canvas.delete('all');self._canvas.create_image(0,0,image=self._thumb_image,anchor='nw')
        self._thumb_x=x
        if self._tip is not None:self._position_tip()

    def _animate_radius(self,target):
        if self._animation is not None:self.after_cancel(self._animation)
        if not animations_enabled():
            self._inner_radius=target;self._draw();return
        start=self._inner_radius;frame=0
        def tick():
            nonlocal frame
            frame+=1;t=min(1,frame/8);self._inner_radius=start+(target-start)*(1-(1-t)**3)
            self._draw();self._animation=self.after(15,tick) if t<1 else None
        tick()

    def _on_enter(self,event=None):
        if self._state=='normal':
            self._hover_state=True;self._animate_radius(6);self._show_tip()

    def _on_leave(self,event=None):
        self._hover_state=False
        if not self._pressed:self._animate_radius(5);self._hide_tip()

    def _clicked(self,event=None):
        if self._state!='normal':return
        self._canvas.focus_set()
        if not self._pressed:self._pressed=True;self._animate_radius(4)
        margin=self._apply_widget_scaling(11)
        width=self._apply_widget_scaling(self._current_width)
        fraction=max(0,min(1,(event.x-margin)/max(1,width-2*margin)))
        self._key_value(self._from_+fraction*(self._to-self._from_))

    def _release(self,event=None):
        self._pressed=False;self._animate_radius(6 if self._hover_state else 5);self._hide_tip()

    def _key(self,direction):
        step=(self._to-self._from_)/(self._number_of_steps or 100)
        return self._key_value(self.get()+direction*step)

    def _key_value(self,value):
        if self._state!='normal':return 'break'
        self.set(value)
        self._show_tip()
        if self._command is not None:self._command(self.get())
        return 'break'

    def _focus_in(self,event):self._focused=True;self._draw()
    def _focus_out(self,event):self._focused=False;self._draw();self._hide_tip()

    def _show_tip(self):
        if self._tip is None:
            self._tip=tk.Toplevel(self);self._tip.withdraw();self._tip.overrideredirect(True)
            self._tip_label=tk.Label(self._tip,font=(UI_FONT,12),padx=8,pady=4)
            self._tip_label.pack()
        self._position_tip();self._tip.deiconify()

    def _position_tip(self):
        self._tip_label.configure(text=self._value_format(self.get()),bg=self._apply_appearance_mode(SURFACE),fg=self._apply_appearance_mode(TEXT))
        self._tip.update_idletasks()
        x=self._canvas.winfo_rootx()+self._thumb_x-self._tip.winfo_reqwidth()/2
        x=max(0,min(x,self.winfo_screenwidth()-self._tip.winfo_reqwidth()))
        y=max(0,self._canvas.winfo_rooty()-self._tip.winfo_reqheight()-6)
        self._tip.geometry(f'+{int(x)}+{int(y)}')

    def _hide_tip(self):
        if self._tip is not None:self._tip.destroy();self._tip=None

    def configure(self,require_redraw=False,**kwargs):
        if kwargs.get('state')=='disabled':self._hide_tip();self._pressed=False
        kwargs.pop('height',None)
        super().configure(require_redraw=True,**kwargs)

    def destroy(self):
        if self._animation is not None:self.after_cancel(self._animation)
        self._hide_tip();super().destroy()
