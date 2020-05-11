from os import path
import os
import json
import datetime
import time
import client
import importlib.util
import traceback
from threading import Thread

background_mode = False
plugins = {}
events = []
event_settings = []
chat_client_events = {
	"receive_message": [],
	"parse_message": [],
	"user_chage": [],
	"join_chat": [],
	"leave_chat": []
}

class event_setting():
	def __init__(self, name, namespace=None):
		self.name = name
		if (namespace == None):
			namespace = get_current_plugin_name()
		self.namespace = namespace

	def get_setting(self, event):
		if (not(self.namespace in event.cfg)):
			event.cfg[self.namespace] = {}
		if (not(self.name in event.cfg[self.namespace])):
			return None
		return event.cfg[self.namespace][self.name]

	def set_setting(self, event, value):
		if (not(self.namespace in event.cfg)):
			event.cfg[self.namespace] = {}
		event.cfg[self.namespace][self.name] = value

	def ask_setting(self, event):
		pass

class event_setting_string(event_setting):
	def __init__(self, name, question, namespace=None):
		super().__init__(name, namespace)
		self.question = question

	def ask_setting(self, event):
		current = self.get_setting(event)
		return friendly_input(self.question, current)

class event_setting_int(event_setting):
	def __init__(self, name, question, min_bound=-1, max_bound=-1, namespace=None):
		super().__init__(name, namespace)
		self.question = question
		self.min_bound = min_bound
		self.max_bound = max_bound

	def ask_setting(self, event):
		current = self.get_setting(event)
		return friendly_input_int(self.question, current, self.min_bound, self.max_bound)

class event_setting_time(event_setting):
	def __init__(self, name, question, namespace=None):
		super().__init__(name, namespace)
		self.question = question

	def get_setting(self, event):
		data = super().get_setting(event)
		if (data == None):
			return None
		return datetime.time(data[0], data[1], data[2])

	def set_setting(self, event, time):
		if (time == None):
			return super().set_setting(event, None)
		data = [
			time.hour,
			time.minute,
			time.second
		]
		return super().set_setting(event, data)

	def ask_setting(self, event):
		current = self.get_setting(event)
		return friendly_input_time(self.question, current)

class event_setting_select(event_setting):
	def __init__(self, name, options, question, multiple=False, max_items=-1, namespace=None):
		super().__init__(name, namespace)
		self.options = options
		self.question = question
		self.multiple = multiple
		self.max_items = max_items

	def ask_setting(self, event):
		current = self.get_setting(event)
		return friendly_input_select(self.question, current, self.options, self.multiple, self.max_items)

class event_setting_weekly_calendar(event_setting_select):
	def __init__(self, name, question, multiple=True, namespace=None):
		options = [
			"Monday",
			"Tuesday",
			"Wednesday",
			"Tursday",
			"Friday",
			"Saturday",
			"Sunday"
		]
		super().__init__(name, options, question, multiple, -1, namespace)

	def get_template(self, parsed_mode):
		if (parsed_mode == True):
			return {
				0: {"start": None, "end": None},
				1: {"start": None, "end": None},
				2: {"start": None, "end": None},
				3: {"start": None, "end": None},
				4: {"start": None, "end": None},
				5: {"start": None, "end": None},
				6: {"start": None, "end": None}
			}
		return {
			0: [None, None],
			1: [None, None],
			2: [None, None],
			3: [None, None],
			4: [None, None],
			5: [None, None],
			6: [None, None]
		}

	def get_setting(self, event):
		final = self.get_template(True)
		unparsed = super().get_setting(event)
		if (unparsed == None):
			return None
		for day in unparsed:
			if (unparsed[day][0] == None or unparsed[day][1] == None):
				continue
			start_time = datetime.time(unparsed[day][0][0], unparsed[day][0][1], unparsed[day][0][2])
			end_time = datetime.time(unparsed[day][1][0], unparsed[day][1][1], unparsed[day][1][2])
			final[int(day)] = {
				"start": start_time,
				"end": end_time
			}
		return final

	def set_setting(self, event, setting):
		final = self.get_template(False)
		if (setting == None):
			return super().set_setting(event, None)
		for day in setting:
			if (setting[day]["start"] == None or setting[day]["end"] == None):
				continue
			time_start = [
				setting[day]["start"].hour,
				setting[day]["start"].minute,
				setting[day]["start"].second
			]
			time_end = [
				setting[day]["end"].hour,
				setting[day]["end"].minute,
				setting[day]["end"].second
			]
			final[int(day)][0] = time_start
			final[int(day)][1] = time_end
		return super().set_setting(event, final)

	def ask_setting(self, event):
		current = self.get_setting(event)
		current_days = []
		if (current == None):
			current = self.get_template(True)
		for day in current:
			if (current[day]["start"] != None and current[day]["end"] != None):
				current_days.append(day)
		if (len(current_days) == 0):
			current_days = None
		final = self.get_template(True)
		week_days = friendly_input_select(self.question, current_days, self.options, self.multiple, self.max_items)
		for day in week_days:
			start_time = friendly_input_time("Start time for " + self.options[int(day)].lower(), current[day]["start"])
			end_time = friendly_input_time("End time for " + self.options[int(day)].lower(), current[day]["end"])
			final[int(day)]["start"] = start_time
			final[int(day)]["end"] = end_time
		return final

class event_manager():
	start_time = None
	end_time = None
	joined = False
	locked = False
	moodle_client = None

	def __init__(self, filename):
		self.cfg = {}
		self.filename = filename
		self.load()
	
	def get_root_url(self):
		url = self.get_setting("url")
		if (url == None):
			return False
		pos = url.find("/mod/")
		if (pos == -1):
			return False
		return url[:pos]

	def get_setting(self, name, namespace=None):
		if (namespace == None):
			namespace = get_current_plugin_name()
		for setting in event_settings:
			if (setting.name == name and setting.namespace == namespace):
				return setting.get_setting(self)
		return None

	def set_setting(self, value, name, namespace=None):
		if (namespace == None):
			namespace = get_current_plugin_name()
		for setting in event_settings:
			if (setting.name == name and setting,namespace == namespace):
				setting.set_setting(self, value)
				return True
		return False

	def is_defined(self):
		settings = []
		for setting in event_settings:
			if (setting.get_setting(self) == None):
				settings.append(setting)
		return settings

	def friendly_ask(self, create=False, settings=[]):
		if (len(settings) == 0):
			settings = event_settings
		for setting in settings:
			value = setting.ask_setting(self)
			setting.set_setting(self, value)
		if (create == True):
			self.filename = get_filename_from_name(self.get_setting("name", "main"), "chats/", ".json")
		self.save()
		if (create == True):
			print("Chat created")
		else:
			print("Chat modified")

	def save(self):
		file = open(self.filename, "w")
		file.write(json.dumps(self.cfg))
		file.close()

	def load(self):
		if (self.filename == False):
			self.friendly_ask(True)
			return
		if (not(path.exists(self.filename))):
			self.friendly_ask()
			return
		file = open(self.filename)
		self.cfg = json.loads(file.read())
		file.close()
		undefined = self.is_defined()
		if (len(undefined) > 0):
			print("Some settings are undefined in the " + self.get_setting("name", "main") + " chat")
			self.friendly_ask(False, undefined)

	def should_join_chat(self, date):
		days = self.get_setting("days", "main")
		week_day = date.weekday()
		if (week_day in days):
			if (days[week_day]["start"] == None or days[week_day]["end"] == None):
				return False
			start_time = days[week_day]["start"]
			end_time = days[week_day]["end"]
			return time_in_range(start_time, end_time, date.time())
		return False

	def join_chat(self, lock=False):
		user = self.get_setting("user_name", "main")
		password = self.get_setting("password", "main")
		url = self.get_root_url()
		moodle_client = client.moodle_client(user, password, url)
		if (moodle_client.login()):
			moodle_client.chat = self
			moodle_client.chat_event_user = user_chage
			moodle_client.chat_event_parse = parse_message
			moodle_client.chat_event_on_message = receive_message
			moodle_client.chat_event_join = join_chat
			moodle_client.chat_event_leave = leave_chat
			if (moodle_client.join_chat(self.get_setting("url", "main"))):
				self.moodle_client = moodle_client
				self.joined = True
				self.locked = lock
				return True
		return False

	def leave_chat(self, lock=False):
		if (self.joined):
			self.joined = False
			self.locked = lock
			self.moodle_client.leave_chat(True)

class event_state_manager_thread(Thread):
	def __init__(self):
		Thread.__init__(self)
		self.daemon = True

	def run(self):
		while True:
			now = datetime.datetime.now()
			for event in events:
				if (not(event.locked)):
					should_join_chat = event.should_join_chat(now)
					if (not(event.joined) and should_join_chat):
						event.join_chat()
					elif (event.joined and not(should_join_chat)):
						event.leave_chat()
			time.sleep(1)


def time_in_range(time_1, time_2, time_check=datetime.datetime.now().time()):
	if (time_1 < time_2):
		return (time_check >= time_1 and time_check <= time_2)
	else:
		return (time_check >= time_1 or time_check <= time_2)

def receive_message(client, msg):
	if ("receive_message" in chat_client_events):
		for callback in chat_client_events["receive_message"]:
			callback(client, msg)

def parse_message(client, msg):
	if ("parse_message" in chat_client_events):
		for callback in chat_client_events["parse_message"]:
			callback(client, msg)

def user_chage(client, joining_users, leaving_users):
	if ("user_chage" in chat_client_events):
		for callback in chat_client_events["user_chage"]:
			callback(client, msg)

def join_chat(client):
	if ("join_chat" in chat_client_events):
		for callback in chat_client_events["join_chat"]:
			callback(client)

def leave_chat(client):
	if ("leave_chat" in chat_client_events):
		for callback in chat_client_events["leave_chat"]:
			callback(client)

def add_chat_client_event(event_type, callback):
	if (not(event_type in chat_client_events)):
		chat_client_events[event_type] = {}
	chat_client_events[event_type].append(callback)

def load_chat(filename=False):
	event = event_manager(filename)
	events.append(event)
	return event

def remove_chat(index):
	event = events[index]
	if (event.joined):
		event.leave_chat(True)
	filename = event.filename
	os.remove(filename)
	events.pop(index)

def display_chat_viewer(select=False):
	if (len(events) == 0):
		print("No chats are loaded")
		return -1
	i = 0
	if (select == True):
		i = 1
	sel = -1
	print("Current loaded chats:")
	if (select == True):
		print("   0. Cancel")
	for event in events:
		print("   " + str(i) + ". " + event.get_setting("name", "main") + " joined=" + str(event.joined) + ", locked=" + str(event.locked))
		i += 1
	if (select == False):
		return -1
	i -= 1
	while (sel < 0 or sel > i):
		try:
			sel = int(input("Type a number between 0 and " + str(i) + ": ")) - 1
			if (sel == -1):
				return sel
		except:
			continue
	return sel

def change_event_state(index):
	joined = events[index].joined
	locked = events[index].locked
	join_str = "Join chat"
	lock_str = "Lock chat state"
	if (joined == True):
		join_str = "Leave chat"
	if (locked == True):
		lock_str = "Unlock chat state"
	option = friendly_input_select("Select an option", None, [join_str, lock_str])
	if (option == 0):
		if (joined == False):
			print("Joining the chat...")
			if (not(events[index].join_chat(True))):
				print("Failed to join the chat")
		else:
			print("Leaving the chat...")
			events[index].leave_chat(True)
	elif (option == 1):
		events[index].locked = not(locked)
		if (locked == True):
			print("Unlocking the chat state...")
		else:
			print("Locking the chat state...")

def get_filename_from_name(filename, prepend, append):
	while (path.exists(prepend + filename.replace(" ", "_") + append)):
		filename += "_"
	return prepend + filename.replace(" ", "_") + append

def add_event_setting(setting):
	event_settings.append(setting)

def friendly_input(text, empty):
	if (background_mode == True):
		return None
	got_text = ""
	if (empty != None):
		return (input(text + " (empty: " + str(empty) + "): ") or empty)
	while (got_text == ""):
		got_text = input(text + ": ")
	return got_text

def friendly_input_int(text, empty, min_bound=-1, max_bound=-1):
	if (min_bound != -1 and max_bound != -1):
		text += " (from " + str(min_bound) + " to " + str(max_bound) + ")"
	while True:
		try:
			i = int(friendly_input(text, empty))
			if (min_bound != -1 and max_bound != -1):
				if (i < min_bound or i > max_bound):
					continue
			return i
		except:
			continue

def friendly_input_time(text, empty):
	text += " (hh:mm:ss)"
	while True:
		try:
			time_input = friendly_input(text, empty)
			if (type(time_input) == str):
				time_array = [int(x) for x in time_input.split(":")]
				if (len(time_array) != 3):
					continue
				time_obj = datetime.time(time_array[0], time_array[1], time_array[2])
			else:
				time_obj = time_input
		except:
			continue
		return time_obj

def friendly_input_select(text, empty, options, multiple=False, max_items=-1):
	count = 0
	exit_loop = False
	print(text + ":")
	for option in options:
		print("   " + str(count) + ". " + str(option))
		count += 1
	text = "Type "
	if (multiple):
		text += "numbers"
	else:
		text += "a number"
	text += " between 0 to " + str(count - 1)
	if (multiple):
		text += " separated by commas"
	if (max_items != -1):
		text += " (maximum " + str(max_items) + ")"
	while (not(exit_loop)):
		try:
			if (multiple == False):
				selected = int(friendly_input(text, empty))
				if (selected < 0 or selected > count):
					continue
				return selected
			else:
				selected = friendly_input(text, empty)
				if (type(selected) == str):
					selected_array = [int(x.strip()) for x in selected.split(",")]
					if (max_items != -1 and len(selected_array) > max_items):
						continue
					selected_array.sort()
					check = 0
					exit_loop = True
					while (check < len(selected_array)):
						if (selected_array[check] < 0 or selected_array[check] > count):
							exit_loop = False
							break
						if (check + 1 != len(selected_array)):
							if (selected_array[check] == selected_array[check + 1]):
								selected_array.pop(check)
								continue
						check += 1
				else:
					selected_array = selected
					break
		except:
			continue
	return selected_array

def run_plugin(file):
	name = os.path.splitext(os.path.basename(file))[0]
	spec = importlib.util.spec_from_file_location("plubin_" + name, file)
	module = importlib.util.module_from_spec(spec)
	plugins[file] = module
	spec.loader.exec_module(module)

def get_current_plugin_name():
	stack = traceback.extract_stack()
	for frame in stack:
		if (frame.filename in plugins):
			return plugins[frame.filename].__name__
	return "main"