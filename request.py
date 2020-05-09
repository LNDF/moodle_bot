from urllib import parse
from http import client

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"

class http_request_response():
	def __init__(self, resp, url):
		self.url = url
		self.headers = resp.getheaders()
		self.http_version = resp.version
		self.status_code = resp.status
		self.reason = resp.reason
		self.body = resp.read().decode("utf-8")
	def get_header(self, name):
		for x in self.headers:
			if (x[0] == name):
				return x[1]
		return None

def make_http_request(url, method, headers={}, body=None, redirect=False, force_http=False):
	headers["User-agent"] = USER_AGENT
	url_parsed = parse.urlsplit(url)
	path = ""
	if (url_parsed.path != ""):
		path += url_parsed.path
	if (url_parsed.query != ""):
		path += "?" + url_parsed.query
	if (url_parsed.fragment != ""):
		path += "#" + url_parsed.fragment
	try:
		if (url_parsed.scheme == "https" and force_http == False):
			con = client.HTTPSConnection(url_parsed.netloc)
		else:
			con = client.HTTPConnection(url_parsed.netloc)
		con.request(method, path, body, headers)
		resp = con.getresponse()
		if (redirect == True):
			if (resp.status >= 301 and resp.status <= 303):
				con.close()
				return make_http_request(resp.getheader("Location"), "GET", {}, None, True, force_http)
			if (resp.status == 307 or resp.status == 308):
				con.close()
				return make_http_request(resp.getheader("Location"), method, headers, body, True, force_http)
	except:
		return False

	http_response = http_request_response(resp, url)
	con.close()
	return http_response

def make_http_form_request(url, headers={}, parameters={}, redirect=False, force_http=False):
	body = parse.urlencode(parameters)
	headers["Content-type"] = "application/x-www-form-urlencoded"
	return make_http_request(url, "POST", headers, body, redirect, force_http)