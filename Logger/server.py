import time
import calendar
import datetime
from urllib.parse import unquote
from io import open
from cgi import escape

from jinja2 import Environment, PackageLoader

from supybot.httpserver import SupyHTTPServerCallback

from .storage import LogDB


SECONDS_IN_DAY = datetime.timedelta(days=1).total_seconds()

class HTTPLogCallback(SupyHTTPServerCallback):
	name = "Channel log callback"
	fullpath = True

	def __init__(self, plugin):
		self.plugin = plugin
		self.db = plugin.db

		self.jinjaEnv = Environment(loader=PackageLoader(__name__, "templates"))
		self.templates = {}
		for name in ("index", "calendar", "log"):
			self.templates[name] = self.jinjaEnv.get_template(name + ".xhtml")

	def doGet(self, handle, path):
		info = path.split("/")[2:]
		if len(info) > 0 and info[-1] == "":
			info.pop()
		info = [unquote(x) for x in info]
		response = None
		if len(info) == 3:  # /network/channel/day
			response = self.getLog(info[0], info[1], info[2])
		elif len(info) == 2:  # /network/channel
			response = self.getCalendar(info[0], info[1])
		elif len(info) == 1:  # /network
			response = "Network channel list not implemented."
		elif len(info) == 0:  # /
			response = self.getIndex()
		else:
			self.send_response(400)
			return
		self.send_response(200)
		self.send_header('Content-type', 'text/html; charset=utf-8')
		self.send_header('Content-Length', len(response))
		self.end_headers()
		self.wfile.write(response.encode("UTF-8"))

	def getIndex(self):
		bufs = self.db.getBuffers()
		buffers = {}
		for buf in bufs:
			bufferName = buf["name"]
			if not self.plugin.registryValue("web.public", bufferName):
				continue
			networkName = buf["network_name"]
			if not networkName in buffers:
				buffers[networkName] = []
			buffers[networkName].append(bufferName)

		maxChannels = 0
		for net in buffers:
			if len(buffers[net]) > maxChannels:
				maxChannels = len(buffers[net])

		return self.templates["index"].render(
			buffers = buffers,
			maxChannels = maxChannels
		)

	def getCalendar(self, network, channel):
		buf = self.db.getBuffer(network, channel, create=False)
		if not buf:
			return "Buffer not found."
		t1 = time.clock()
		dates = self.db.getDates(buf["id"])
		print(time.clock() - t1)
		months = []
		monthDays = []
		for date in dates:
			month = datetime.date(date.year, date.month, 1)
			if month not in months: months.append(month)
			monthDays[months.index(month)].append(date.day)
		l = ["<table border=\"0\" width=\"100%\"><tbody><tr>"]
		hPos = 0
		for month, days in months.items():
			hPos += 1
			if hPos >= 6:
				l.append("</tr><tr>")
				hPos = 0
			l.append("<td>")
			l.append(self.getMonthCalendar(month, days))
			l.append("</td>")
		l.append("</tr></tbody></table>")
		return self.templates["calendar"].render(
			calendar = "".join(l)
		)

	def getMonthCalendar(self, month, days):
		l = ["<table class=\"month\"><thead class=\"month-name\"><td colspan=\"7\">"]
		l.append(str(month.year) + "-" + str(month.month))
		l.append("</td></thead><thead>")
		for weekDayLetter in "SMTWTFS":
			l.append("<td>" + weekDayLetter + "</td>")
		l.append("</thead><tbody><tr>")
		hPos = 0
		for monthDay in range(calendar.monthrange(month.year, month.month)[1]):
			hPos += 1
			if hPos >= 7:
				l.append("</tr><tr>")
				hPos = 0
			l.append("<td>")
			monthDay += 1
			if monthDay in days:
				l.append("<a href=\"%d-%d-%d\">%d</a>" %
					(month.year, month.month, monthDay, monthDay))
			else:
				l.append(str(monthDay))
			l.append("</td>")
		l.append("</tr></tbody></table>")
		return "".join(l)

	def getLog(self, network, channel, day):
		st = time.time()
		buf = self.db.getBuffer(network, channel, create=False)
		if not buf:
			return "Buffer not found."
		date = self.strToDate(day)
		startTime = time.mktime(date.timetuple())
		daydelta = datetime.timedelta(days=1)

		log = self.db.get(buf["id"], startTime, SECONDS_IN_DAY)

		renderst = time.time()
		logLines = []
		for message in log:
			logLines.append(self.formatMessage(message))

		return self.templates["log"].render(
			log = "".join(logLines),
			yesterday = (date - daydelta).isoformat(),
			tommorow = (date + daydelta).isoformat(),
			today = date.isoformat(),
			rendertime = time.time() - renderst,
			dbtime = renderst - st,
			logsize = len(log)
		)

	def strToDate(self, day):
		try:
			dt = datetime.datetime.strptime(day, "%Y-%m-%d")
			return datetime.date(dt.year, dt.month, dt.day)
		except ValueError:
			return datetime.date.today()

	message_strs = [
		"&lt;{nick}&lt;{sep}{message}",
		"-{nick}-{sep}{message}",
		"-*-{sep}{nick} {message}",
		"--&gt;{sep}{nick}!{user}@{host} has joined {channel}.",
		"&lt;--{sep}{nick}!{user}@{host} has parted ({message}).",
		"&lt;--{sep}{nick}!{user}@{host} has quit ({message}).",
		"***{sep}{nick} kicked {message}",
		"<->{sep}{nick} is now known as {message}.",
		"***{sep}Mode/{channel} [{message}] by {nick}.",
		"***{sep}Topic for {channel} changed by {nick} to {message}",
	]

	column_sep = "</td><td class=\"message\">"
	def formatMessage(self, message):
		return "<tr><td class=\"time\">" +\
			time.strftime("[%H:%M:%S]", time.gmtime(message["timestamp"])) +\
			"</td><td class=\"nick\">" +\
			self.message_strs[message["type"]].format(
				nick = escape(message["nick"] or ""),
				user = escape(message["user"] or ""),
				host = escape(message["host"] or ""),
				sep = self.column_sep,
				channel = escape(message["buffer_name"]),
				message = escape(message["message"] or "")
			) + "</td></tr>\n"

