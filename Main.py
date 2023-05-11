# -*- coding: utf-8 -*-
# Written by Rune Johannesen, (c)2021-2023
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter.filedialog import askopenfilename
from PIL import Image, ImageTk
from os.path import splitext, basename, dirname, realpath, join, exists
from os import getcwd, chdir, mkdir, startfile
from subprocess import Popen
from threading import Thread
from Configurator_Object import Configurator
from sys import version_info, platform
from asyncio import set_event_loop, set_event_loop_policy, get_event_loop, sleep, gather
from re import search, findall
from itertools import chain
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from ScrollableFrame import ScrollableFrame

class Main(ttk.Frame):
	def __init__(self, parent):
		if version_info[0] == 3 and version_info[1] >= 8 and platform.startswith('win'):
			from asyncio import ProactorEventLoop, WindowsSelectorEventLoopPolicy
			set_event_loop(ProactorEventLoop())
			set_event_loop_policy(WindowsSelectorEventLoopPolicy())
		super().__init__(parent)
		self.place(x=0, y=0, relwidth=1, relheight=1)
		self.loop = get_event_loop()
		self.script_name: str = splitext(basename(__file__))[0]
		self.script_dir: str = dirname(realpath(__file__))
		self.current_dir: str = getcwd()
		if self.current_dir != self.script_dir:
			chdir(self.script_dir)
			self.current_dir: str = self.script_dir
		device_show_config: str = "SHOW_CONFIGURATIONS"
		device_check_config: str = "CHECK_CONFIGURATIONS"
		device_config: str = "DEVICE_CONFIGURATIONS"
		self.show_config_dir: str = join(self.current_dir, device_show_config)
		self.check_config_dir: str = join(self.current_dir, device_check_config)
		self.device_config_dir: str = join(self.current_dir, device_config)
		if not exists(self.show_config_dir):
			mkdir(self.show_config_dir)
		if not exists(self.check_config_dir):
			mkdir(self.check_config_dir)
		if not exists(self.device_config_dir):
			mkdir(self.device_config_dir)
		self.txt_file_icon: str = ImageTk.PhotoImage(Image.open(join(self.current_dir, "txt-file-icon.png")).resize((15,15), Image.ANTIALIAS))
		self.folder_file_icon: str = ImageTk.PhotoImage(Image.open(join(self.current_dir, "folder-open-icon.png")).resize((15,15), Image.ANTIALIAS))
		self.device_help: str = "devices.help"
		self.show_check_help: str = "show_check.help"
		self.global_config_help: str = "global_config.help"
		self.port_config_help: str = "port.help"
		self.about_help: str = "about.help"
		self.help_help: str = "help.help"
		self.shorten_int: dict = {"FastEthernet": "Fa", "GigabitEthernet": "Gi", "TwoGigabitEthernet": "Tw", "TenGigabitEthernet": "Te", "TwentyFiveGigE": "Twe", "FortyGigabitEthernet": "Fo", "HundredGigE": "Hu", "FourHundredGigE": "F", "Loopback": "Lo"}
		self.devices: list = []
		self.show_cmd: list = []
		self.check_cmd: list = []
		self.global_config: list = []
		self.port_include: list = []
		self.port_exclude: list = []
		self.port_config: list = []
		self.widgets: list = []
		self.title_width: list = [20,40,84,10]
		self.title_placement: list = [0.01,0.139,0.391,0.914]
		self.create_menu()
		self.create_main()

	def menu_item_selected(self, action):
		if action == "Exit": self.quit()
		if action == "About": self.msgBox(self.about_help)
		if action == "Help": self.msgBox(self.help_help)

	def msgBox(self, filename: str) -> None:
		win = ttk.Toplevel(title=filename, resizable=(False,False))
		win.geometry("800x800")
		win.position_center()
		frame1 = ttk.Frame(master=win)
		frame1.place(x=0, y=0, relwidth=1, relheight=1)
		ttk.Button(frame1, text="OK", command=win.destroy).place(relx=0.939, rely=0.935)
		v=ttk.Scrollbar(frame1, orient='vertical')
		v.place(relx=0.989, rely=0.02, relheight=0.9)
		textbox = ttk.Text(master=frame1, font='Calibri 14', wrap=WORD, yscrollcommand=v.set)
		textbox.place(relx=0.015, rely=0.02, relheight=0.9, relwidth=0.974)
		with open(join(self.current_dir, filename)) as msg:
			textbox.insert(END,msg.read())
		v.config(command=textbox.yview)
		textbox.config(state='disabled')

	def open_file(self, path: str) -> None:
		if platform.startswith('win'):
			startfile(path)
		else:
			opener = "open" if platform == "darwin" else "xdg-open"
			Popen([opener, path])

	def open_devices(self) -> None:
		path: str = askopenfilename(title='Select Device list')
		if path:
			self.devices: list = []
			with open(path) as r:
				self.devices: list = [[search(r"(^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})", x.strip()).group(1)] for x in r.readlines() if x.strip() and search(r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", x.strip())]
				if self.devices:
					self.device_path.set(path)
					self.device_preview.set(", ".join([x for i,x in enumerate(chain(*self.devices)) if i <= 4]))
					self.menu_device1.config(foreground='lime')
					self.menu_device2.config(foreground="lime")
					self.device_total.set(f"Total devices: {len(self.devices)}")
					self.menu_check_btn.config(state='normal')
				else:
					path_file = path.split("/")[-1]
					self.device_path.set(f"No devices found in file: {path_file}")
					self.device_preview.set(f"No devices found in file: {path_file}")
					self.menu_device1.config(foreground='orange')
					self.menu_device2.config(foreground="orange")
		else:
			if not "\\" in self.device_path.get() and not "/" in self.device_path.get():
				self.device_path.set("No device file selected yet.")
				self.device_preview.set("No device file selected yet.")
				self.device_total.set("Total devices: 0")
				self.menu_device1.config(foreground='')
				self.menu_device2.config(foreground='')

	def open_show_check(self) -> None:
		path: str = askopenfilename(title='Select Show/Check Commands list')
		if path:
			self.show_cmd: list = []
			self.check_cmd: list = []
			with open(path) as r:
				line: str = r.readline().strip()
				while line:
					if not line.strip() or line.startswith("#") or line.startswith("!"):
						line: str = r.readline().strip()
						continue
					if line.lower() == ";; show ;;":
						line: str = r.readline().strip()
						while line:
							if not line.strip() or line.startswith("#") or line.startswith("!"):
								line: str = r.readline().strip()
								continue
							if line.lower() == ";; check ;;": break
							self.show_cmd.append(line.strip())
							line: str = r.readline().strip()
					if line.lower() == ";; check ;;":
						line: str = r.readline().strip()
						while line:
							if not line.strip() or line.startswith("#") or line.startswith("!"):
								line: str = r.readline().strip()
								continue
							if line.lower() == ";; show ;;": break
							self.check_cmd.append(line.strip())
							line: str = r.readline().strip()
					if line.lower() == ";; show ;;" or line.lower() == ";; check ;;":
						continue
					try: line: str = r.readline().strip()
					except: break
			if self.show_cmd or self.check_cmd:
				if self.show_cmd: self.show_cmd = ["terminal length 0"]+self.show_cmd
				self.show_check_path.set(path)
				self.menu_show.config(foreground='lime')
			else:
				path_file = path.split("/")[-1]
				self.show_check_path.set(f"No Show/Check commands (;; SHOW ;; or ;; CHECK ;;) found in file: {path_file}")
				self.menu_show.config(foreground='orange')
		else:
			if not "\\" in self.show_check_path.get() and not "/" in self.show_check_path.get():
				self.show_check_path.set("No Show/Check commands file selected yet.")
				self.menu_show.config(foreground='')

	def open_global(self) -> None:
		path: str = askopenfilename(title='Select Global Configuration list')
		if path:
			self.global_config: list = []
			with open(path) as r:
				self.global_config: list = [x.strip() for x in r.readlines() if x.strip() and not x.strip().startswith("#") and not x.strip().startswith("!")]
			if self.global_config:
				self.menu_check_config.set(1)
				self.global_path.set(path)
				self.menu_global.config(foreground='lime')
			else:
				path_file = path.split("/")[-1]
				self.global_path.set(f"No Global Configurations found in file: {path_file}")
				self.menu_global.config(foreground='orange')
		else:
			if not "\\" in self.global_path.get() and not "/" in self.global_path.get():
				self.global_path.set("No Global configuration file selected yet.")
				self.menu_global.config(foreground='')

	def open_port(self) -> None:
		path: str = askopenfilename(title='Select Port Configuration list')
		if path:
			self.port_config: list = []
			self.port_include: list = []
			self.port_exclude: list = []
			with open(path) as r:
				if not ";; config ;;" in r.read().lower():
					path_file = path.split("/")[-1]
					self.port_path.set(f"No Port Configuration commands (;; CONFIG ;;) found in file: {path_file}")
					self.menu_port.config(foreground="orange")
					return
				else:
					r.seek(0)
					line: str = r.readline().strip()
					while line:
						if not line.strip() or line.startswith("#") or line.startswith("!"):
							line: str = r.readline().strip()
							continue
						if line.lower() == ";; include ;;":
							line: str = r.readline().strip()
							while line:
								if not line.strip() or line.startswith("#") or line.startswith("!"):
									line: str = r.readline().strip()
									continue
								if line.lower() == ";; exclude ;;" or line.lower() == ";; config ;;":
									break
								self.port_include.append(line.strip())
								line: str = r.readline().strip()
						if line.lower() == ";; exclude ;;":
							line: str = r.readline().strip()
							while line:
								if not line.strip() or line.startswith("#") or line.startswith("!"):
									line: str = r.readline().strip()
									continue
								if line.lower() == ";; include ;;" or line.lower() == ";; config ;;":
									break
								self.port_exclude.append(line.strip())
								line: str = r.readline().strip()
						if line.lower() == ";; config ;;":
							line: str = r.readline().strip()
							while line:
								if not line.strip() or line.startswith("#") or line.startswith("!"):
									line: str = r.readline().strip()
									continue
								if line.lower() == ";; include ;;" or line.lower() == ";; exclude ;;":
									break
								self.port_config.append(line.strip())
								line: str = r.readline().strip()
						if line.lower() == ";; include ;;" or line.lower() == ";; exclude ;;" or line.lower() == ";; config ;;":
							continue
						try: line: str = r.readline().strip()
						except: break
			if self.port_config:
				self.menu_check_config.set(1)
				self.port_path.set(path)
				self.menu_port.config(foreground="lime")
			else:
				path_file = path.split("/")[-1]
				self.port_path.set(f"No Port Configuration commands found in file: {path_file}")
				self.menu_port.config(foreground="orange")
		else:
			if not "\\" in self.port_path.get() and not "/" in self.port_path.get():
				self.port_path.set("No Port configuration file selected yet.")

	def reset_menu(self) -> None:
		self.menu_error.set("")
		self.menu_username.delete(0,"end")
		self.menu_username.insert(0,"Enter TACACS SSH credentials to use for logging into devices.")
		self.menu_password.delete(0,"end")
		self.devices: list = []
		self.device_path.set("No device file selected yet.")
		self.device_preview.set("No device file selected yet.")
		self.device_total.set("Total devices: 0")
		self.show_cmd: list = []
		self.check_cmd: list = []
		self.show_check_path.set("No Show/Check commands file selected yet.")
		self.global_config: list = []
		self.global_path.set("No Global configuration file selected yet.")
		self.port_config: list = []
		self.port_include: list = []
		self.port_exclude: list = []
		self.port_path.set("No Port configuration file selected yet.")
		self.menu_port.config(foreground="")
		self.menu_device1.config(foreground="")
		self.menu_device2.config(foreground="")
		self.menu_show.config(foreground="")
		self.menu_global.config(foreground="")
		self.menu_error_label.config(foreground="orange")
		self.menu_check_btn.config(state='disabled')
		self.menu_check_config.set(0)

	def build_save_results(self, frame: ttk.Frame, results: list) -> None:
		def place_objects(frame: ttk.Frame, entry: list, style: str, row: float) -> None:
			error: str = ""
			for i, value in enumerate(entry):
				if isinstance(value, list):
					if not any("Error" in x for x in value):
						_ = ttk.Label(frame, text="OK", bootstyle=style, width=self.title_width[i], font='Calibri 11', foreground='lime')
					else:
						for err in value:
							if search(r"Error:\s.+?(\s\[ SKIPPED \]|\n|$)", err):
								error: str = search(r"Error:\s(.+?)(\s\[ SKIPPED \]|\n|$)", err).group(1)
								_ = ttk.Label(frame, text=error, bootstyle=style, width=self.title_width[i], font='Calibri 11', foreground='orange')
								break
							else: _ = ttk.Label(frame, text="FAILED", bootstyle=style, width=self.title_width[i], font='Calibri 11', foreground='orange')
				else:
					_ = ttk.Label(frame, text=value, bootstyle=style, width=self.title_width[i], font='Calibri 11')
				self.widgets.append(_)
				_.place(relx=self.title_placement[i], rely=row)
		row: float = 0.05
		for index, entry in enumerate(["IP Address","Hostname","Write Memory Status"]):
			_ = ttk.Label(frame, text=entry, bootstyle="inverse-secondary", width=self.title_width[index], font='Calibri 11 bold')
			self.widgets.append(_)
			_.place(relx=self.title_placement[index], rely=row)
		for index, entry in enumerate(results):
			row += 0.025
			if (index % 2) == 0:
				place_objects(frame, entry, "inverse-secondary", row)
			else:
				place_objects(frame, entry, "inverse-dark", row)

	def build_show_results(self, frame: ttk.Frame, results: list) -> None:
		def place_objects(frame: ttk.Frame, entry: list, style: str, row: float) -> None:
			error: str = ""
			for i, value in enumerate(entry):
				if isinstance(value, list):
					if not any("Error" in x for x in value):
						_ = ttk.Label(frame, text="OK", bootstyle=style, width=self.title_width[i], font='Calibri 11', foreground='lime')
					else:
						for err in value:
							if search(r"Error:\s.+?(\s\[ SKIPPED \]|\n|$)", err):
								error: str = search(r"Error:\s(.+?)(\s\[ SKIPPED \]|\n|$)", err).group(1)
								_ = ttk.Label(frame, text=error, bootstyle=style, width=self.title_width[i], font='Calibri 11', foreground='orange')
								break
							else: _ = ttk.Label(frame, text="FAILED", bootstyle=style, width=self.title_width[i], font='Calibri 11', foreground='orange')
				else:
					if "\\" in r"%r" % value or "/" in value:
						_ = ttk.Button(frame, image=self.txt_file_icon, compound='top', bootstyle='secondary-outline', padding=0, command=lambda j=value: self.open_file(j))
						self.widgets.append(_)
						_.place(relx=self.title_placement[i], rely=row, height=20, width=35)
						_ = ttk.Button(frame, image=self.folder_file_icon, compound='top', bootstyle='secondary-outline', padding=0, command=lambda: self.open_file(self.show_config_dir))
						self.widgets.append(_)
						_.place(relx=self.title_placement[i]+0.033, rely=row, height=20, width=35)
						continue
					else: _ = ttk.Label(frame, text=value, bootstyle=style, width=self.title_width[i], font='Calibri 11')
				self.widgets.append(_)
				_.place(relx=self.title_placement[i], rely=row)
		row: float = 0.05
		for index, entry in enumerate(["IP Address","Hostname","Command Status","Actions"]):
			_ = ttk.Label(frame, text=entry, bootstyle="inverse-secondary", width=self.title_width[index], font='Calibri 11 bold')
			if entry == "Actions": _ = ttk.Label(frame, text=entry, bootstyle="inverse-secondary", width=self.title_width[index], font='Calibri 11 bold', anchor='center')
			self.widgets.append(_)
			_.place(relx=self.title_placement[index], rely=row)
		for index, entry in enumerate(results):
			row += 0.025
			if (index % 2) == 0:
				place_objects(frame, entry, "inverse-secondary", row)
			else:
				place_objects(frame, entry, "inverse-dark", row)

	def build_device_results(self, frame: ttk.Frame, reload_start: list, scp_ena: list, scp_transfer: list, copy: list, scp_dis: list, reload_cancel: list, results: list) -> None:
		def place_objects(frame: ttk.Frame, entry: list, style: str, row: float, title_width: list, title_placement: list, subjects: list, sub_results: list) -> None:
			error: str = ""
			if not any("Error" in x for x in entry[2]):
				_ = ttk.Label(frame, text=entry[0], bootstyle=style, width=title_width[0], font='Calibri 10')
				self.widgets.append(_)
				_.place(relx=title_placement[0], rely=row)
				_ = ttk.Label(frame, text=entry[1].rstrip("#"), bootstyle=style, width=title_width[1], font='Calibri 10')
				self.widgets.append(_)
				_.place(relx=title_placement[1], rely=row)
				for i in range(len(subjects)):
					if i > 1:
						for data in sub_results[i]:
							if entry[0] == data[0]:
								if not any("Error" in x for x in data[2]):
									if i == 4:
										flash: str = data[2].split(":")[1] if ":" in data[2] else data[2]
										_ = ttk.Label(frame, text=flash, bootstyle=style, width=title_width[i], font='Calibri 10', foreground='lime')
									else: _ = ttk.Label(frame, text="OK", bootstyle=style, width=title_width[i], font='Calibri 10', foreground='lime')
									self.widgets.append(_)
									_.place(relx=title_placement[i], rely=row)
									break
								else:
									if i == 4:
										flash: str = data[2].split(":")[1] if ":" in data[2] else data[2]
										_ = ttk.Label(frame, text=flash, bootstyle=style, width=title_width[i], font='Calibri 10', foreground='orange')
									else: _ = ttk.Label(frame, text="FAILED", bootstyle=style, width=title_width[i], font='Calibri 10', foreground='orange')
									self.widgets.append(_)
									_.place(relx=title_placement[i], rely=row)
			else:
				_ = ttk.Label(frame, text=entry[0], bootstyle=style, width=title_width[0], font='Calibri 10')
				self.widgets.append(_)
				_.place(relx=title_placement[0], rely=row)
				for err in entry[2]:
					if search(r"Error:\s.+?(\s\[ SKIPPED \]|\n|$)", err):
						error: str = search(r"Error:\s(.+?)(\s\[ SKIPPED \]|\n|$)", err).group(1)
						_ = ttk.Label(frame, text=error, bootstyle=style, width=136, font='Calibri 10', foreground='orange')
						break
					else: _ = ttk.Label(frame, text="FAILED", bootstyle=style, width=136, font='Calibri 10', foreground='orange')
				self.widgets.append(_)
				_.place(relx=title_placement[1], rely=row)
		sub_results: list = [None, None, reload_start, scp_ena, scp_transfer, copy, scp_dis, reload_cancel]
		row: float = 0.05
		title_width: list = [20,30,16,10,35,15,11,13]
		title_placement: list = [0.01,0.139,0.3295,0.434,0.502,0.7235,0.822,0.8955]
		subjects: list = ["IP Address","Hostname","Reload in 30 Mins","SCP Enable","SCP Transfer","Config->Running","SCP Disable","Reload Cancel"]
		for index, entry in enumerate(subjects):
			_ = ttk.Label(frame, text=entry, bootstyle="inverse-secondary", width=title_width[index], font='Calibri 10 bold')
			self.widgets.append(_)
			_.place(relx=title_placement[index], rely=row)
		btn1 = ttk.Button(frame, text='Open Device Config', bootstyle="success", command=lambda: self.open_file(self.device_config_dir))
		btn1.place(relx=0.85, rely=0.95)
		self.widgets.append(btn1)
		for index, entry in enumerate(results):
			row += 0.0235
			if (index % 2) == 0:
				place_objects(frame, entry, "inverse-secondary", row, title_width, title_placement, subjects, sub_results)
			else:
				place_objects(frame, entry, "inverse-dark", row, title_width, title_placement, subjects, sub_results)

	def build_check_results(self, frame: ttk.Frame, results: list) -> None:
		def place_objects(frame: ttk.Treeview, results: list) -> None:
			for result in results:
				commands: tuple = tuple(["OK" if "OK" in x else "NOT FOUND" if "NOT FOUND" in x else x for x in result[2]])
				frame.insert('', END, values=(result[0], result[1])+commands, )
			self.widgets.append(frame)
		columns: tuple = ("IP_Address","Hostname")+tuple([x.replace(" ","_") for x in self.check_cmd])
		my_tree = ttk.Treeview(frame, style='primary.Treeview', columns=columns, show='headings')
		my_tree.place(relx=0.01, rely=0.05, width=1105, height=848)
		my_scroll = ttk.Scrollbar(frame, orient=HORIZONTAL, command=my_tree.xview)
		my_scroll.place(relx=0.01, rely=0.98, height=22, width=1105)
		self.widgets.append(my_scroll)
		my_tree.configure(xscrollcommand=my_scroll.set)
		for index, column in enumerate(columns):
			my_tree.heading(column, text=column.replace("_", " "), anchor='w')
			if index == 0: my_tree.column(column, minwidth=0, width=105, anchor='w', stretch=False)
			elif index == 1: my_tree.column(column, minwidth=0, width=150, anchor='w', stretch=False)
			else: my_tree.column(column, minwidth=0, anchor='w', stretch=False)
		file_path: str = results[0][-1]
		btn1 = ttk.Button(frame, text='Open CSV', bootstyle="success", command=lambda: self.open_file(file_path))
		btn1.place(relx=0.913, rely=0.94)
		self.widgets.append(btn1)
		btn2 = ttk.Button(frame, text='Open Dir', bootstyle="success", command=lambda: self.open_file(self.check_config_dir))
		btn2.place(relx=0.83, rely=0.94)
		self.widgets.append(btn2)
		place_objects(my_tree, results)

	async def save_files(self, results: list, operation: str = "show") -> list:
		def normalizefilename(fn: str) -> str:
			validchars: str = "-_.() "
			out: str = ""
			for c in fn:
				if str.isalpha(c) or str.isdigit(c) or (c in validchars):
					out += c
			return out 
		returnResults: list = []
		today: str = datetime.now().strftime("%d-%m-%Y_%H-%M")
		with ThreadPoolExecutor() as executor:
			if operation == "check":
				filename: str = f"Check_Configurations_{today}.csv"
				with open(join(self.check_config_dir, filename), "w") as w:
					for device in results:
						cmd_found: list = []
						if not "Error" in device[2][0]:
							show_run: str = device[2][0].replace("show run","").strip()
							interfaces: list = findall(r"(interface [A-Z].+[\S\n ]+?!)", show_run)
							for check in self.check_cmd:
								tmpint: list = []
								found: bool = False
								for interface in interfaces:
									if check.lower() in interface.lower():
										i: str = interface.splitlines()[0].split(" ")[1]
										for key, value in self.shorten_int.items():
											if i.startswith(key):
												i: str = i.replace(key,value)
										tmpint.append(i)
								if tmpint:
									found: bool = True
									tmpstr: str = ",".join(tmpint)
									cmd_found.append(f"OK ({tmpstr})")
									continue
								for line in show_run.splitlines():
									if check.lower() in line.lower():
										cmd_found.append(f"OK ({line.strip()})")
										found: bool = True
								if not found:
									cmd_found.append(f"NOT FOUND ({check})")
						else: cmd_found.append(search(r"Error:\s(.+?)(\s\[ SKIPPED \]|\n|$)", device[2][0]).group(1))
						await self.loop.run_in_executor(executor, w.write, f"{device[0]};{device[1].rstrip('#')};{';'.join(cmd_found)}\n")
						returnResults.append([device[0], device[1].rstrip("#"), cmd_found, join(self.check_config_dir, filename)])
			else:
				for device in results:
					filename: str = f"{device[0]}_{normalizefilename(device[1])}_{today}.txt"
					with open(join(self.show_config_dir, filename), "w") as w:
						for command in device[2]:
							await self.loop.run_in_executor(executor, w.write, f"{command}\n\n")
					returnResults.append([device[0], device[1].rstrip("#"), device[2], join(self.show_config_dir, filename)])
		return(returnResults)

	async def create_device_configurations(self, config_prechecks: list) -> tuple:
		scp_transfer: list = []; scp_ena: list = []; scp_dis: list = []; copy: list = []; reload_start: list = []; reload_cancel: list = []
		today: str = datetime.now().strftime("%d-%m-%Y_%H-%M")
		with ThreadPoolExecutor() as executor:
			for device in config_prechecks:
				if any("Error" in x for x in device[2]):
					continue
				show_run: str = ""; flash: str = ""
				enableScp: list = []; disableScp: list = []; interfaces: list = []; interfacelist: list = []
				for config in device[2]:
					if "show run" in config:
						show_run: str = config.replace("show run","").strip()
					elif "dir all-filesystems" in config:
						flash: str = config.replace("dir all-filesystems | in (Directory of flash|Directory of bootflash)","").strip().splitlines()[0].split(" ")[-1].replace("/","")
				if "ip scp server enable" not in show_run:
					enableScp: list = ["conf t", "ip scp server enable", "end"]
					disableScp: list = ["conf t", "no ip scp server enable", "end"]
				interfaces: list = findall(r"(interface G.+[\S\n ]+?!|interface F.+[\S\n ]+?!|interface T.+[\S\n ]+?!|interface H.+[\S\n ]+?!)", show_run)
				if self.port_include:
					interfacelist: list = [x for x in interfaces if any(y.lower() in x.lower() for y in self.port_include)]
				if self.port_exclude:
					if interfacelist: interfacelist: list = [x for x in interfacelist if not any(y.lower() in x.lower() for y in self.port_exclude)]
					else: interfacelist: list = [x for x in interfaces if not any(y.lower() in x.lower() for y in self.port_exclude)]
				if not interfacelist:
					interfacelist: list = interfaces
				filename: str = f"{device[0]}_{today}.cfg"
				flash_copy: str = f"copy {flash}{filename} running-config\n\n"
				with open(join(self.device_config_dir, filename), "w") as w:
					if self.global_config:
						for globalcfg in self.global_config:
							await self.loop.run_in_executor(executor, w.write, f"{globalcfg}\n")
					if self.port_config:
						for interface in interfacelist:
							if any(";; default ;;" in x.lower() for x in self.port_config):
								await self.loop.run_in_executor(executor, w.write, f"default {interface.splitlines()[0]}\n")
							await self.loop.run_in_executor(executor, w.write, f"{interface.splitlines()[0]}\n")
							for portcfg in self.port_config:
								if portcfg.lower() != ";; default ;;":
									await self.loop.run_in_executor(executor, w.write, f"{portcfg}\n")
					await self.loop.run_in_executor(executor, w.write, f"end")
				with open(join(self.device_config_dir, f"{device[0]}_{today}_backup.cfg"), "w") as w:
					await self.loop.run_in_executor(executor, w.write, show_run)
				reload_start.append([device[0], ["reload in 30\ny\n\n"]])
				scp_transfer.append([device[0], join(self.device_config_dir, filename), flash+filename])
				copy.append([device[0], [flash_copy]])
				reload_cancel.append([device[0], ["reload cancel\n\n"]])
				if enableScp:
					scp_ena.append([device[0], enableScp])
					scp_dis.append([device[0], disableScp])
		return(reload_start, scp_ena, scp_transfer, copy, scp_dis, reload_cancel)

	async def do_work(self) -> None:
		self.menu_error_label.config(foreground='lime')
		Config = Configurator(self.menu_username.get(), self.menu_password.get())
		show_results: list = []
		check_results: list = []
		run: bool = False
		sleep_time: float = 1.5
		if self.show_cmd and self.check_cmd:
			self.menu_error.set("Show & Check Commands: Execution started...")
			show_results, check_results = await gather(Config.InitiateExecution(self.devices, self.show_cmd), Config.InitiateExecution(self.devices, ["terminal length 0", "show run"]),)
			self.menu_error.set("Show & Check Commands: Execution completed!")
			run: bool = True
		if self.show_cmd:
			if not show_results:
				self.menu_error.set("Show Commands: Execution started...")
				show_results: list = await Config.InitiateExecution(self.devices, self.show_cmd)
				self.menu_error.set("Show Commands: Execution completed!")
				run: bool = True
			if show_results:
				save_show_results: list = await self.save_files(show_results)
				self.main_show_config.set("Show Configurations:")
				self.build_show_results(self.main_show, save_show_results)
			else:
				self.main_show_label.config(foreground='orange')
				self.main_show_config.set(f"No results returned or operation failed, check the logs under: {self.current_dir}")
		if self.check_cmd:
			if not check_results:
				self.menu_error.set("Check Commands: Execution started...")
				check_results: list = await Config.InitiateExecution(self.devices, ["terminal length 0", "show run"])
				self.menu_error.set("Check Commands: Execution completed!")
				run: bool = True
			if check_results:
				save_check_results: list = await self.save_files(check_results, "check")
				self.main_check_config.set("Check Configurations:")
				self.build_check_results(self.main_check, save_check_results)
			else:
				self.main_check_label.config(foreground='orange')
				self.main_check_config.set(f"No results returned or operation failed, check the logs under: {self.current_dir}")
		if self.global_config or self.port_config:
			self.menu_error.set("Device configurations started...")
			if run: await sleep(sleep_time)
			self.config_prechecks: list = await Config.InitiateExecution(self.devices, ["terminal length 0", "show run", "dir all-filesystems | in (Directory of flash|Directory of bootflash)"])
			reload_start, scp_ena, scp_transfer, copy, scp_dis, reload_cancel = await self.create_device_configurations(self.config_prechecks)
			await sleep(sleep_time)
			self.menu_error.set("Device configurations: setting reload in 30 mins...")
			reload_start_result = await Config.InitiateExecution(reload_start)
			if scp_ena:
				await sleep(sleep_time)
				self.menu_error.set(f"Device configurations: enabling SCP transfer...")
				scp_ena_result = await Config.InitiateExecution(scp_ena)
			await sleep(sleep_time)
			self.menu_error.set("Device configurations: Starting SCP transfers...")
			scp_transfer_result = await Config.InitiateScpTransfer(scp_transfer)
			await sleep(sleep_time)
			self.menu_error.set("Device configurations: copying config to running-config...")
			copy_result = await Config.InitiateExecution(copy)
			if scp_dis:
				await sleep(sleep_time)
				self.menu_error.set(f"Device configurations: disabling SCP transfer...")
				scp_dis_result = await Config.InitiateExecution(scp_dis)
			await sleep(sleep_time)
			self.menu_error.set("Device configurations: cancelling reloads...")
			reload_cancel_result = await Config.InitiateExecution(reload_cancel)
			self.menu_error.set("Device configurations completed!")
			run: bool = True
			self.main_global_config.set("Device Configurations:")
			self.build_device_results(self.main_global, reload_start_result, scp_ena_result, scp_transfer_result, copy_result, scp_dis_result, reload_cancel_result, self.config_prechecks)
		if self.menu_check_config.get():
			if run: await sleep(sleep_time)
			self.menu_error.set("Saving configurations (write memory) started...")
			write_mem: list = await Config.InitiateExecution(self.devices, ["write memory"])
			self.menu_error.set("Saving configurations (write memory) completed!")
			if write_mem:
				self.main_save_config.set("Save Configurations Status:")
				self.build_save_results(self.main_save, write_mem)
			else:
				self.main_save_label.config(foreground='orange')
				self.main_save_config.set(f"No results returned or operation failed, check the logs under: {self.current_dir}")
		await sleep(sleep_time)
		self.menu_error.set("")
		self.menu_error_label.config(foreground='orange')

	def _asyncio_thread(self) -> None:
		self.loop.run_until_complete(self.do_work())

	def do_tasks(self) -> None:
		show: bool = False
		if not self.devices or self.menu_username.get() == "Enter TACACS SSH credentials to use for logging into devices." or not self.menu_password.get():
			self.menu_error.set("You must select devices, enter username and password and at least select one configuration option.")
			return
		if self.show_cmd or self.check_cmd:
			show: bool = True
		if show or self.global_config or self.port_config or self.menu_check_config.get():
			self.menu_error.set("")
			if self.widgets:
				for x in self.widgets:
					x.destroy()
				self.main_show_label.config(foreground='')
				self.main_check_label.config(foreground='')
				self.main_global_label.config(foreground='')
				self.main_save_label.config(foreground='')
				self.main_show_config.set("No Show Configurations to display.")
				self.main_check_config.set("No Check Configurations to display.")
				self.main_global_config.set("No Device Configurations to display.")
				self.main_save_config.set("No Configurations have been saved yet.")
				self.widgets: list = []
			Thread(target=self._asyncio_thread, name="tkinter_thread").start()
		else:
			self.menu_error.set("You must select at least one configuration option: Show/Check, Global or Port.")

	def create_menu(self):
		# Init Notebook
		my_notebook = ttk.Notebook(self)
		my_notebook.place(x=4, y=0, relwidth=0.395, relheight=0.994)
		# Init menu Frame
		menu_button = ttk.Menubutton(my_notebook, text='Menu', style='info.TMenubutton')
		my_menu = ttk.Menu(menu_button)
		for option in ('Help', 'About', 'Exit'):
			my_menu.add_command(label=option, command=lambda j=option:self.menu_item_selected(j))
		menu_button["menu"] = my_menu
		menu_button.place(relx=0.0, rely=0.0)
		menu = ttk.Frame(my_notebook)
		# Devices
		self.device_path = ttk.StringVar(value='No device file selected yet.')
		self.device_preview = ttk.StringVar(value='No device file selected yet.')
		self.device_total = ttk.StringVar(value='Total devices: 0')
		ttk.Label(menu, text='Select devices to execute on:', font='Calibri 18 bold').place(relx=0.02, rely=0.02)
		ttk.Label(menu, text='Loaded File:', font='Calibri 12').place(relx=0.02, rely=0.10)
		ttk.Label(menu, text='Device preview (First 5 devices):', font='Calibri 12').place(relx=0.02, rely=0.14)
		ttk.Button(menu, text='Select Devices...', bootstyle="light", command=lambda:self.open_devices()).place(relx=0.02, rely=0.06)
		ttk.Button(menu, text='Device Help', bootstyle="light", command=lambda:self.msgBox(self.device_help)).place(relx=0.32, rely=0.06)
		ttk.Label(menu, textvariable=self.device_total, font='Calibri 11').place(relx=0.80, rely=0.06)
		self.menu_device1 = ttk.Entry(menu, state='readonly', textvariable=self.device_path)
		self.menu_device1.place(relx=0.32, rely=0.10, relwidth=0.65)
		self.menu_device2 = ttk.Entry(menu, state='readonly', textvariable=self.device_preview)
		self.menu_device2.place(relx=0.32, rely=0.14, relwidth=0.65)
		# Separator
		ttk.Separator(menu).place(relx=0, rely=0.19, relwidth=1)
		# TACACS
		ttk.Label(menu, text='Enter TACACS Credentials to use:', font='Calibri 18 bold').place(relx=0.02, rely=0.20)
		ttk.Label(menu, text='Username:', font='Calibri 12').place(relx=0.02, rely=0.25)
		self.menu_username = ttk.Entry(menu)
		self.menu_username.insert(0,"Enter TACACS SSH credentials to use for logging into devices.")
		self.menu_username.bind("<FocusIn>", lambda event: self.menu_username.delete(0,"end") if self.menu_username.get() == "Enter TACACS SSH credentials to use for logging into devices." else None)
		self.menu_username.bind("<FocusOut>", lambda event: self.menu_username.insert(0,"Enter TACACS SSH credentials to use for logging into devices.") if not self.menu_username.get() else None)
		self.menu_username.place(relx=0.32, rely=0.25, relwidth=0.65)
		ttk.Label(menu, text='Password:', font='Calibri 12').place(relx=0.02, rely=0.29)
		self.menu_password = ttk.Entry(menu, show='*')
		self.menu_password.place(relx=0.32, rely=0.29, relwidth=0.65)
		# Separator
		ttk.Separator(menu).place(relx=0, rely=0.34, relwidth=1)
		# Show/Check config
		self.show_check_path = ttk.StringVar(value='No Show/Check commands file selected yet.')
		ttk.Label(menu, text='Show Configuration/Check Commands (Optional):', font='Calibri 18 bold').place(relx=0.02, rely=0.35)
		ttk.Button(menu, text='Select Show/Check Commands...', bootstyle="light", command=lambda:self.open_show_check()).place(relx=0.02, rely=0.39)
		ttk.Button(menu, text='Show/Check Help', bootstyle="light", command=lambda:self.msgBox(self.show_check_help)).place(relx=0.32, rely=0.39)
		ttk.Label(menu, text='Loaded File:', font='Calibri 12').place(relx=0.02, rely=0.43)
		self.menu_show = ttk.Entry(menu, state='readonly', textvariable=self.show_check_path)
		self.menu_show.place(relx=0.32, rely=0.43, relwidth=0.65)
		# Separator
		ttk.Separator(menu).place(relx=0, rely=0.48, relwidth=1)
		# Global Configuration
		self.global_path = ttk.StringVar(value='No Global configuration file selected yet.')
		ttk.Label(menu, text='Global Configuration (Optional):', font='Calibri 18 bold').place(relx=0.02, rely=0.49)
		ttk.Button(menu, text='Select Global Config...', bootstyle="light", command=lambda:self.open_global()).place(relx=0.02, rely=0.53)
		ttk.Button(menu, text='Global Config Help', bootstyle="light", command=lambda:self.msgBox(self.global_config_help)).place(relx=0.32, rely=0.53)
		ttk.Label(menu, text='Loaded File:', font='Calibri 12').place(relx=0.02, rely=0.57)
		self.menu_global = ttk.Entry(menu, state='readonly', textvariable=self.global_path)
		self.menu_global.place(relx=0.32, rely=0.57, relwidth=0.65)
		# Separator
		ttk.Separator(menu).place(relx=0, rely=0.62, relwidth=1)
		# Port Configuration
		self.port_path = ttk.StringVar(value='No Port configuration file selected yet.')
		ttk.Label(menu, text='Port Configuration (Optional):', font='Calibri 18 bold').place(relx=0.02, rely=0.63)
		ttk.Button(menu, text='Select Port Config...', bootstyle="light", command=lambda:self.open_port()).place(relx=0.02, rely=0.67)
		ttk.Button(menu, text='Port Config Help', bootstyle="light", command=lambda:self.msgBox(self.port_config_help)).place(relx=0.32, rely=0.67)
		ttk.Label(menu, text='Loaded File:', font='Calibri 12').place(relx=0.02, rely=0.71)
		self.menu_port = ttk.Entry(menu, state='readonly', textvariable=self.port_path)
		self.menu_port.place(relx=0.32, rely=0.71, relwidth=0.65)
		# Separator
		ttk.Separator(menu).place(relx=0, rely=0.76, relwidth=1)
		# Error messaging
		self.menu_error = ttk.StringVar(value='')
		self.menu_error_label = ttk.Label(menu, textvariable=self.menu_error, font='Calibri 12 bold', foreground='orange')
		self.menu_error_label.place(relx=0.02, rely=0.87)
		# Separator
		ttk.Separator(menu).place(relx=0, rely=0.925, relwidth=1)
		# Execute
		self.menu_check_config = ttk.IntVar()
		self.menu_check_config.set(0)
		self.menu_check_btn = ttk.Checkbutton(menu, text='Save device configuration.', style='Roundtoggle.Toolbutton', variable=self.menu_check_config, onvalue=1, offvalue=0)
		self.menu_check_btn.place(relx=0.02, rely=0.955)
		self.menu_check_btn.config(state='disabled')
		ttk.Button(menu, text='Reset Options', bootstyle="info", command=lambda:self.reset_menu()).place(relx=0.650, rely=0.945)
		ttk.Button(menu, text='Start Execution', bootstyle="danger", command=lambda:self.do_tasks()).place(relx=0.835, rely=0.945)
		# Add tabs
		my_notebook.add(menu)

	def create_main(self):
		my_notebook = ttk.Notebook(self)
		my_notebook.place(relx=0.4, y=0, relwidth=0.598, relheight=0.994)
		# Init main Frame
		self.main_show = ScrollableFrame(my_notebook)
		self.main_check = ScrollableFrame(my_notebook)
		self.main_global = ScrollableFrame(my_notebook)
		self.main_save = ScrollableFrame(my_notebook)
		# Show Config pane
		self.main_show_config = ttk.StringVar(value='No Show Configurations to display.')
		self.main_show_label = ttk.Label(self.main_show, textvariable=self.main_show_config, font='Calibri 14', wraplength=550)
		self.main_show_label.place(relx=0.01, rely=0.01)
		# Check Config pane
		self.main_check_config = ttk.StringVar(value='No Check Configurations to display.')
		self.main_check_label = ttk.Label(self.main_check, textvariable=self.main_check_config, font='Calibri 14', wraplength=550)
		self.main_check_label.place(relx=0.01, rely=0.01)
		# Device Config pane
		self.main_global_config = ttk.StringVar(value='No Device Configurations to display.')
		self.main_global_label = ttk.Label(self.main_global, textvariable=self.main_global_config, font='Calibri 14', wraplength=550)
		self.main_global_label.place(relx=0.01, rely=0.01)
		# Save Config pane
		self.main_save_config = ttk.StringVar(value='No Configurations have been saved yet.')
		self.main_save_label = ttk.Label(self.main_save, textvariable=self.main_save_config, font='Calibri 14', wraplength=550)
		self.main_save_label.place(relx=0.01, rely=0.01)
		# Add tabs
		my_notebook.add(self.main_show, text="Show Config")
		my_notebook.add(self.main_check, text="Check Config")
		my_notebook.add(self.main_global, text="Device Config")
		my_notebook.add(self.main_save, text="Save Config")