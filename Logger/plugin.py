
import supybot.callbacks as callbacks
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.world as world
import supybot.irclib as irclib
from supybot.commands import *

import time

from .storage import LogDB, MessageType

filename = conf.supybot.directories.log.dirize("Log.sqlite")

class Logger(callbacks.Plugin):
	"""
	An SQLite3 channel logger
	"""

	noIgnore = True
	threaded = True

	lastMsgs = {}
	lastStates = {}

	def __init__(self, irc):
		self.__parent = super(Logger, self)
		self.__parent.__init__(irc)
		self.db = LogDB(filename)
		world.flushers.append(self.flush)

	def _seen(self, irc, msg, channel, nick, findAny):
		if nick == irc.nick:
			irc.reply("Of course I've seen myself!")
			return
		bufid = self.db.getBuffer(irc.network, channel)["id"]
		if findAny:
			entry = self.db.getLast(bufid, nick)
		else:
			entry = self.db.getLastMessage(bufid, nick)
		if not entry:
			irc.reply("I haven't seen %s in %s." % (nick, channel))
			return
		t = time.time()
		rpl = "I saw %s in %s %s ago " % (
			nick,
			channel,
			utils.timeElapsed(t - entry["timestamp"])
		)
		tp = entry["type"]
		if tp == MessageType.privmsg or\
				tp == MessageType.notice:
			rpl += "saying \"%s\"" % (entry["message"],)
		elif tp == MessageType.action:
			rpl += "saying * %s %s" % (entry["nick"], entry["message"])
		elif tp == MessageType.join:
			rpl += "joining."
		elif tp == MessageType.part:
			rpl += "parting (%s)." % (entry["message"],)
		elif tp == MessageType.quit:
			rpl += "quiting"
			if entry["message"] != "":
				rpl += " (%s)" % (entry["message"],)
			rpl += "."
		elif tp == MessageType.kick:
			kicked, space, reason = entry["message"].partition(" ")
			rpl += "kicking %s (%s)." % (kicked, reason)
		elif tp == MessageType.nick:
			rpl += "changing nick to %s." % (entry["message"],)
		elif tp == MessageType.mode:
			rpl += "setting mode(s) %s." % (entry["message"],)
		elif tp == MessageType.topic:
			rpl += "setting the topic to \"%s\"" % (entry["message"],)
		else:
			rpl += "doing who knows what."
		irc.reply(rpl)

	def seen(self, irc, msg, args, channel, nick):
		"""[channel] <nick>

		Finds the last time a nick was seen speaking and what they said.
		"""
		self._seen(irc, msg, channel, nick, False)
	seen = wrap(seen, ["channel", "nick"])

	def seenany(self, irc, msg, args, channel, nick):
		"""[channel] <nick>

		Finds the last time a nick was seen and what they were doing.
		"""
		self._seen(irc, msg, channel, nick, True)
	seenany = wrap(seenany, ["channel", "nick"])

	def __call__(self, irc, msg):
		try:
			self.__parent.__call__(irc, msg)
			if irc in self.lastMsgs:
				if irc not in self.lastStates:
					self.lastStates[irc] = irc.state.copy()
				self.lastStates[irc].addMsg(irc, self.lastMsgs[irc])
		finally:
			self.lastMsgs[irc] = msg

	def reset(self):
		self.lastMsgs.clear()
		self.lastStates.clear()

	def die(self):
		self.__parent.die()
		world.flushers.remove(self.flush)
		del self.db

	def flush(self):
		self.db.commit()

	def shouldLog(self, irc, msg, msgtype):
		if not self.registryValue("enable"):
			return False
		if msgtype == MessageType.privmsg or msgtype == MessageType.notice:
			if not irc.isChannel(msg.args[0]):
				return False
			if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
				return False
		if msgtype == MessageType.mode and msg.args[0] == irc.nick:
			return False
		return True

	def _add(self, irc, msg, msgtype):
		if not self.shouldLog(irc, msg, msgtype):
			return

		channel = msg.args[0]
		if not self.registryValue("enable", channel):
			return

		text = None
		if len(msg.args) > 1:
			text = msg.args[1]

		if msgtype == MessageType.mode:
			text = " ".join(msg.args[1:])
		elif msgtype == MessageType.kick:
			# Add reason to text
			text += " " + msg.args[2]
		elif ircmsgs.isAction(msg):
			msgtype = MessageType.action
			text = msg.args[1][8:-1]

		self.db.add(msgtype, irc.network, channel, msg, text)
		self.db.commit()

	def doPrivmsg(self, irc, msg): self._add(irc, msg, MessageType.privmsg)
	def doNotice (self, irc, msg): self._add(irc, msg, MessageType.notice)
	def doJoin   (self, irc, msg): self._add(irc, msg, MessageType.join)
	def doPart   (self, irc, msg): self._add(irc, msg, MessageType.part)
	def doKick   (self, irc, msg): self._add(irc, msg, MessageType.kick)
	def doMode   (self, irc, msg): self._add(irc, msg, MessageType.mode)
	def doTopic  (self, irc, msg): self._add(irc, msg, MessageType.topic)

	def doNick(self, irc, msg):
		if not self.shouldLog(irc, msg, MessageType.nick):
			return
		oldNick = msg.nick
		newNick = msg.args[0]
		for (channel, chan) in irc.state.channels.items():
			if newNick in chan.users:
				if not self.registryValue("enable", channel):
					continue
				self.db.add(MessageType.nick,
					irc.network,
					channel,
					msg,
					newNick)
		self.db.commit()

	def doQuit(self, irc, msg):
		if not self.shouldLog(irc, msg, MessageType.quit):
			return
		reason = None
		if len(msg.args) == 1:
			reason = msg.args[0]
		if not isinstance(irc, irclib.Irc):
			irc = irc.getRealIrc()
		if not irc in self.lastStates:
			return
		for (channel, chan) in self.lastStates[irc].channels.items():
			if not self.registryValue("enable", channel) or\
					msg.nick not in chan.users:
				continue
			self.db.add(MessageType.quit,
				irc.network,
				channel,
				msg,
				reason)
		self.db.commit()

	def outFilter(self, irc, msg):
		# Log our own messages
		if msg.command in ('PRIVMSG', 'NOTICE'):
			# Other messages should be sent back to us.
			self(irc, ircmsgs.IrcMsg(msg=msg, prefix=irc.prefix))
		return msg

Class = Logger

