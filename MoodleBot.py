import client
import manager
import request
import os
import glob

def run_plugin(file):
	f = open(file)
	src = f.read()
	f.close()
	exec(src, {"client": client, "manager": manager, "request": request})

def clear_console():
	if (os.name == "nt"):
		os.system("cls")
	else:
		os.system("clear")

def main_thread_loop():
	while True:
		print("")
		print("Select an option:")
		print("   1. View current chats")
		print("   2. Add a chat")
		print("   3. Edit a chat")
		print("   4. Change chat state")
		print("   5. Delete a chat")
		print("   6. Clear screen")
		print("   7. Exit")
		option = 0
		while (option < 1 or option > 7):
			try:
				option = int(input("Type a number from 1 to 7: "))
			except:
				continue
		if (option == 1):
			manager.display_chat_viewer()
		elif (option == 2):
			print("Create new chat")
			manager.load_chat()
		elif (option == 3):
			item = manager.display_chat_viewer(True)
			if (item == -1):
				continue
			print("Edit the selected chat")
			manager.events[item].friendly_ask()
		elif (option == 4):
			item = manager.display_chat_viewer(True)
			if (item == -1):
				continue
			manager.change_event_state(item)
		elif (option == 5):
			item = manager.display_chat_viewer(True)
			if (item == -1):
				continue
			print("Deleting the chat...")
			manager.remove_chat(item)
		elif (option == 6):
			clear_console()
		elif (option == 7):
			break

print("MoodleBot by Lander")
print("   Version 1.0     ")
print("-------------------")
print("")
print("Loading internal chat settings...")
manager.add_event_setting(manager.event_setting_string("name", "Name of the chat"))
manager.add_event_setting(manager.event_setting_string("url", "URL of the chat"))
manager.add_event_setting(manager.event_setting_string("user_name", "User name"))
manager.add_event_setting(manager.event_setting_string("password", "password"))
manager.add_event_setting(manager.event_setting_weekly_calendar("days", "Select the days of the week to join the chat"))
print("Loading plugins...")
if (not(os.path.exists("plugins"))):
	os.mkdir("plugins")
for file in glob.glob("plugins/*.py"):
	run_plugin(file)
print("Loading chats...")
if (not(os.path.exists("chats"))):
	os.mkdir("chats")
for file in glob.glob("chats/*.json"):
	manager.load_chat(file)
print("Loading chat state manager...")
state_manager_thread = manager.event_state_manager_thread()
state_manager_thread.start()
main_thread_loop()