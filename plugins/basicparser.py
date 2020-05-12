import manager
from html.parser import HTMLParser

def get_attr_from_attrs(attrs, attr):
	for at in attrs:
		if (at[0] == attr):
			return at[1]
	return None

def data_is_valid(data):
	for c in data:
		if (c != "\n" and c != " "):
			return True
	return False

class basic_parser(HTMLParser):
	parsed = ""
	text_div_depth = 0
	parse_complete = False

	def handle_starttag(self, tag, attrs):
		if (self.parse_complete == False and tag == "div" and (get_attr_from_attrs(attrs, "class") == "text" or self.text_div_depth > 0)):
			self.text_div_depth += 1

	def handle_endtag(self, tag):
		if (self.parse_complete == False and self.text_div_depth > 0):
			if (tag == "div"):
				self.text_div_depth -= 1
				if (self.text_div_depth == 0):
					self.parse_complete = True

	def handle_data(self, data):
		if (self.text_div_depth > 0 and data_is_valid(data)):
			self.parsed += data

def basic_message_parser_event_handler(client, message, current):
	if (current != None):
		return current
	parser = basic_parser()
	parser.feed(message["message"])
	if (parser.parsed == ""):
		return None
	else:
		return parser.parsed

manager.add_chat_client_event("parse_message", basic_message_parser_event_handler)