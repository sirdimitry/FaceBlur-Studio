"""Behavior checks for Fluent sliders without modifying system settings."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import customtkinter as ctk
from ui.fluent_slider import FluentSlider
from ui.theme import initialize_theme

class SliderTest(unittest.TestCase):
    def setUp(self):
        self.root=ctk.CTk()
        self.root.geometry('400x150')
        self.values=[]
        self.slider=FluentSlider(self.root,from_=0,to=100,number_of_steps=100,command=self.values.append)
        self.slider.pack(fill='x',padx=20,pady=30)
        self.root.update()
    def tearDown(self):
        self.slider.destroy()
        for timer in self.root.tk.call('after','info'):self.root.tk.call('after','cancel',timer)
        self.root.destroy();initialize_theme()
    def test_endpoints_steps_keyboard_and_disabled(self):
        for x,value in ((0,0),(self.slider._canvas.winfo_width(),100)):
            self.slider._clicked(SimpleNamespace(x=x))
            self.assertEqual(self.slider.get(),value)
        self.slider.set(25);self.slider._key(1)
        self.assertEqual(self.slider.get(),26)
        self.assertEqual(self.values[-1],26)
        self.slider.configure(state='disabled')
        count=len(self.values)
        self.slider._clicked(SimpleNamespace(x=0));self.slider._key(-1)
        self.assertEqual(self.slider.get(),26)
        self.assertEqual(len(self.values),count)
        self.assertIsNone(self.slider._tip)
    def test_rtl_endpoints_visual_direction_and_keyboard(self):
        self.slider.set(25)
        self.root.update()
        original_x = self.slider._thumb_x
        self.slider.set_direction(True)
        self.assertEqual(self.slider.get(), 25)
        self.assertGreater(self.slider._thumb_x, original_x)
        self.slider._clicked(SimpleNamespace(x=0))
        self.assertEqual(self.slider.get(), 100)
        self.slider._clicked(SimpleNamespace(x=self.slider._canvas.winfo_width()))
        self.assertEqual(self.slider.get(), 0)
        self.slider._canvas.focus_force()
        self.root.update()
        self.slider._canvas.event_generate('<Left>')
        self.root.update()
        self.assertEqual(self.slider.get(), 1)
        self.slider.set_direction(False)
        self.assertEqual(self.slider.get(), 1)
        self.slider._clicked(SimpleNamespace(x=0))
        self.assertEqual(self.slider.get(), 0)

    def test_hover_press_release_and_reduced_motion(self):
        with patch('ui.fluent_slider.animations_enabled',return_value=False):
            self.slider._on_enter()
            self.assertEqual(self.slider._inner_radius,6)
            self.assertIsNotNone(self.slider._tip)
            self.slider._clicked(SimpleNamespace(x=100))
            self.assertEqual(self.slider._inner_radius,4)
            self.slider._release()
            self.assertEqual(self.slider._inner_radius,6)
            self.assertIsNone(self.slider._tip)
            self.slider._on_leave()
            self.assertEqual(self.slider._inner_radius,5)
    def test_both_themes_preserve_value(self):
        self.slider.set(37)
        for mode in ('Dark','Light'):
            ctk.set_appearance_mode(mode);self.root.update()
            self.assertEqual(self.slider.get(),37)
            self.assertGreater(self.slider._thumb_image.width(),200)

if __name__=='__main__':unittest.main()
