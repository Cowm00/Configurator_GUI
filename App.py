# -*- coding: utf-8 -*-
# Written by Rune Johannesen, (c)2021-2023
import ttkbootstrap as ttk
from Main import Main
from datetime import datetime

class App(ttk.Window):
	def __init__(self, title):
		super().__init__(themename='darkly')
		self.title(title)
		w, h = self.winfo_screenwidth()-10, self.winfo_screenheight()-75
		self.geometry(f"{w}x{h}+0+0")
		self.minsize(w,h)
		self.main = Main(self)
		self.mainloop()

def main() -> None:
	App(f'Configurator by Rune Johannesen © {datetime.now().year}') #

if __name__ == "__main__":
	main()