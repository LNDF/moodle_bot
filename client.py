import request
import json
import time
from threading import Thread

class moodle_chat_pool_thread(Thread):
	should_leave_chat = False
	def __init__(self, client):
		Thread.__init__(self)
		self.daemon = True
		self.client = client

	def run(self):
		time.sleep(1)
		while not(self.should_leave_chat):
			new_messages = self.client.pull_chat()
			time.sleep(1)

class moodle_client():
	logged_in = False
	ín_chat = False
	chat_last_row = 0
	chat_last_time = 0
	chat_message_history = {}
	chat_event_on_message = None
	chat_event_parse = None
	chat_event_user = None
	chat_event_join = None
	chat_event_leave = None

	def __init__(self, user, password, url):
		self.user = user
		self.password = password
		self.url = url

	def login(self):
		search_key = "name=\"logintoken\" value=\""
		first_request = request.make_http_request(self.url + "/login/index.php", "GET")
		if (first_request == False):
			return False
		if (first_request.status_code != 200):
			return False
		login_token_start = first_request.body.find(search_key) + 25
		login_token = first_request.body[login_token_start:(login_token_start + 32)]
		session_cookie = first_request.get_header("Set-Cookie")[22:48]
		parameters = {
			"username": self.user,
			"password": self.password,
			"logintoken": login_token,
			"anchor": ""
		}
		headers = {
			"Cookie": "MoodleSessionmoodle04=" + session_cookie
		}
		final_request = request.make_http_form_request(self.url + "/login/index.php", headers, parameters)
		if (final_request == False):
			return False
		if (final_request.status_code == 303):
			if (final_request.get_header("Location").find("testsession") != -1):
				self.logged_in = True
				self.session_cookie = final_request.get_header("Set-Cookie")[22:48]
				return True
		return False

	def chat_api_interact(self, action, data={}):
		if (self.in_chat == False):
			return False
		ajax_url = self.url + "/mod/chat/chat_ajax.php?sesskey=" + self.sesskey
		headers = {
			"Cookie": "MoodleSessionmoodle04=" + self.session_cookie
		}
		data["chat_sid"] = self.chat_sid
		data["theme"] = "course_theme"
		data["action"] = action
		req = request.make_http_form_request(ajax_url, headers, data)
		if (req == False):
			return False
		if (req.status_code == 200):
			return req
		return False

	def join_chat(self, url):
		if (self.logged_in == False):
			return False
		headers = {
			"Cookie": "MoodleSessionmoodle04=" + self.session_cookie
		}
		chat_sid_search_key = "\"sid\":\""
		sesskey_search_key = "\"sesskey\":\""
		get_data_request = request.make_http_request(url, "GET", headers, redirect=True)
		if (get_data_request == False):
			return False
		chat_sid_start = get_data_request.body.find(chat_sid_search_key) + 7
		chat_sid = get_data_request.body[chat_sid_start:(chat_sid_start + 32)]
		sesskey_start = get_data_request.body.find(sesskey_search_key) + 11
		sesskey = get_data_request.body[sesskey_start:(sesskey_start + 10)]
		if (get_data_request.status_code == 200):
			self.sesskey = sesskey
			self.chat_sid = chat_sid
			self.in_chat = True
			init_resp = self.chat_api_interact("init", {"chat_init": 1})
			if (init_resp == False):
				self.in_chat = False
				return False
			self.users = json.loads(init_resp.body)["users"]
			self.pulling_thread = moodle_chat_pool_thread(self)
			self.pulling_thread.should_leave_chat = False
			self.chat_event_join(self)
			self.pulling_thread.start()
			return True
		return False

	def leave_chat(self, wait=False):
		if (self.in_chat == False):
			return False
		self.chat_event_leave(self)
		self.pulling_thread.should_leave_chat = True
		self.in_chat = False
		self.chat_last_row = 0
		self.chat_last_time = 0
		self.chat_message_history = {}
		self.users = {}
		if (wait):
			self.pulling_thread.join()
		return True

	def send_message(self, message):
		if (self.in_chat == False):
			return False
		resp = self.chat_api_interact("chat", {"chat_message": message})
		if (resp != False):
			if (resp == "true"):
				return True
		return False

	def pull_chat(self):
		if (self.in_chat == False):
			return False
		last_row = "false"
		if (self.chat_last_row > 0):
			last_row = str(self.chat_last_row)
		resp = self.chat_api_interact("update", {"chat_lastrow": last_row, "chat_lasttime": self.chat_last_time})
		if (resp == False):
			return False
		parsed = json.loads(resp.body)
		if ("error" in parsed):
			return parsed
		self.chat_last_row = parsed["lastrow"]
		self.chat_last_time = int(parsed["lasttime"])
		if ("users" in parsed):
			users = parsed["users"]
			if (self.chat_event_user != None):
				users_joining = []
				users_leaving = []
				for user in users:
					if (not(user in self.users)):
						users_joining.append(user)
				for user in self.users:
					if (not(user in users)):
						users_leaving.append(user)
				self.chat_event_user(self, users_joining, users_leaving)
			self.users = parsed["users"]
		new_messages = {}
		if ("msgs" in parsed):
			msgs = parsed["msgs"]
			for msg in msgs:
				if (not(msg in self.chat_message_history)):
					if (self.chat_event_parse != None):
						msgs[msg]["parsed"] = self.chat_event_parse(self, msgs[msg])
					else:
						msgs[msg]["parsed"] = None
					self.chat_message_history[msg] = msgs[msg]
					new_messages[msg] = msgs[msg]
					if (self.chat_event_on_message != None):
						self.chat_event_on_message(self, msgs[msg])
		
		return new_messages