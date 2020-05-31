import manager
import os
import datetime

def chat_file_write(client, text):
	strtime = str(datetime.datetime.now())
	client.chat2file_out_file.write("[" + strtime + "]: " + text + "\n")
	client.chat2file_out_file.flush()

def user_from_id(client, user_id):
	for user in client.users:
		if (user_id == int(user["id"])):
			return user
	return None

def chat_join(client):
	if (client.chat.get_setting("enable") == True):
		if (not(os.path.exists("chat_history"))):
			os.mkdir("chat_history")
		name = "chat_history/" + os.path.splitext(os.path.basename(client.chat.filename))[0]
		if (not(os.path.exists(name))):
			os.mkdir(name)
		name += "/" + str(datetime.datetime.now()).replace(":", "-") + ".txt"
		client.chat2file_out_file = open(name, "w")
		chat_file_write(client, "The bot joins the chat.")
		chat_file_write(client, "Currently " + str(len(client.users)) + " online users:")
		for user in client.users:
			chat_file_write(client, "    " + user["name"])
	else:
		client.chat2file_out_file = None

def chat_leave(client):
	if (client.chat.get_setting("enable") == True and client.chat2file_out_file != None):
		chat_file_write(client, "The bot leaves the chat.")
		client.chat2file_out_file.close()

def chat_user_activity(client, joining, leaving):
	if (client.chat.get_setting("enable") == True and client.chat2file_out_file != None):
		for user in joining:
			chat_file_write(client, user["name"] + " joins the chat.")
		for user in leaving:
			chat_file_write(client, user["name"] + " leaves the chat.")

def chat_message(client, msg):
	if (msg["issystem"] == "0" and client.chat.get_setting("enable") == True and client.chat2file_out_file != None):
		for msg in msgs:
			user = user_from_id(client, int(msg["userid"]))
			if (user == None):
				user_name = "Unknown"
			else:
				user_name = user["name"]
			if (msg["parsed"] != None):
				final_msg = msg["parsed"]
			else:
				final_msg = "(Unsupported message format) " + msg["message"]
			chat_file_write(client, "<" + user_name + ">: " + final_msg)

manager.add_event_setting(manager.event_setting_boolean("enable", "Save all messages to a text file?"))
manager.add_chat_client_event("join_chat", chat_join)
manager.add_chat_client_event("leave_chat", chat_leave)
manager.add_chat_client_event("user_change", chat_user_activity)
manager.add_chat_client_event("receive_message", chat_message)