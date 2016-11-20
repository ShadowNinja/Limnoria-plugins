import time

import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs


class BanNotify(callbacks.Plugin):
	"""Sends a message to an op when they add a ban or quiet.
	"""

	threaded = True
	ban_times = {}
	ban_modes = ("b", "q")

	def doMode(self, irc, msg):
		if not irc.isChannel(msg.args[0]) or \
				msg.nick == irc.nick or \
				not self.isBanning(msg):
			return
		# TODO: Ignore bots
		notice = self.registryValue("notice", msg.args[0])
		if not notice:
			return
		# Don't flood the op is they set a lot of bans in a row.
		if msg.nick in self.ban_times and time.time() - self.ban_times[msg.nick] < 600:
			return
		irc.queueMsg(ircmsgs.notice(msg.nick, notice))
		self.ban_times[msg.nick] = time.time()

	def isBanning(self, msg):
		adding = True
		for c in msg.args[1]:
			if c == "+":
				adding = True
			elif c == "-":
				adding = False
			elif c in self.ban_modes and adding == True:
				return True
		return False

Class = BanNotify

