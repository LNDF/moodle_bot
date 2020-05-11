import client
import manager
import request
import os
import sys
import glob

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
print("Warning:")
print("This software is licensed under the GPLv3 (GNU Public License)")
print("so comes with absolutely no waranty.")
print("By using this software, you agree with the license. You should have")
print("received a copy of the license along with this software.")
print("")
print("Loading internal chat settings...")
manager.add_event_setting(manager.event_setting_string("name", "Name of the chat"))
manager.add_event_setting(manager.event_setting_string("url", "URL of the chat"))
manager.add_event_setting(manager.event_setting_string("user_name", "User name"))
manager.add_event_setting(manager.event_setting_string("password", "password"))
manager.add_event_setting(manager.event_setting_weekly_calendar("days", "Select the days of the week to join the chat"))
if (not(os.path.exists("plugins"))):
	os.mkdir("plugins")
for file in glob.glob("plugins/*.py"):
	print("Loading plugin " + file + "...")
	manager.run_plugin(file)
if (not(os.path.exists("chats"))):
	os.mkdir("chats")
for file in glob.glob("chats/*.json"):
	print("Loading chat " + file + "...")
	manager.load_chat(file)
print("Loading chat state manager...")
state_manager_thread = manager.event_state_manager_thread()
state_manager_thread.start()
if (len(sys.argv) == 2 and sys.argv[1] == "background"):
	manager.background_mode = True
	print("Running in background mode")
	state_manager_thread.join()
else:
	print("Use \"background\" argument to run in background and stop interactions.")
	main_thread_loop()