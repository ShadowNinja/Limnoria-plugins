import re
import time

from supybot import callbacks, conf, ircutils, ircmsgs, ircdb, schedule, world
from supybot.commands import *


MSG_COMMANDS = ("PRIVMSG", "NOTICE")
JOIN_COMMANDS = ("JOIN", "PART", "QUIT")
CHECKED_COMMANDS = MSG_COMMANDS + JOIN_COMMANDS


class RateLimiter:
	"""
	This implements rate limiting using a "leaky bucket" approach.
	Each user is given a bucket.  Each message received "fills" the bucket until
	it "overflows" and the limit is tripped or it "leeks" out at the timeout rate.

	This is implemented by keeping track of two numbers per user:
	 * The last bucket level and
	 * The time of the last bucket level calculation
	Then, when a new message is received we simply subtract 1 for every timeout
	that has ocurred since the last bucket level calculation and add 1 for the
	new message.
	"""
	def __init__(self):
		self.buckets = {}

	def __call__(self, key, timeout, time, count=1):
		if key in self.buckets:
			level, lastUpdate = self.buckets[key]
		else:
			level, lastUpdate = 0, time

		level = self._updateLevel(level, lastUpdate, time, timeout) + count

		self.buckets[key] = (level, time)

		return level

	def _updateLevel(self, level, lastUpdate, time, timeout):
		"""
		Calculate what the current bucket level should be based on its last
		level and the time that has passed since then.
		"""
		timeoutsPassed = (time - lastUpdate) / timeout
		return max(0, level - timeoutsPassed)

	def cleanup(self, timeout):
		"""
		Delete empty buckets.
		"""
		now = time.time()
		toDelete = []

		for key, (level, lastUpdate) in self.buckets.items():
			if self._updateLevel(level, lastUpdate, now, timeout) <= 0:
				toDelete.append(key)

		for key in toDelete:
			del self.buckets[key]


class FloodProtector(callbacks.Plugin):
	"""Protects a channel by kicking or banning users who flood the channel"""

	def __init__(self, irc):
		super().__init__(irc)
		# Regex for each channel.  Used for mass highlight detection.
		self.nickRegexes = {}
		self.offenseLimit = RateLimiter()
		self.messageLimit = RateLimiter()
		self.joinLimit = RateLimiter()
		self.quitLimit = RateLimiter()
		self.highlightLimit = RateLimiter()
		self.slapLimit = RateLimiter()
		# Users are immune shortly after triggering protection to prevent
		# double kicks and bans if the bot sees a few messages come through
		# right after it sends the kick or ban.
		self.punishTime = {}

		world.flushers.append(self.cleanup)

		self.makeNickRegex(irc)

	def cleanup(self):
		now = time.time()

		self.offenseLimit.cleanup(self.registryValue("offenseTimeout"))
		self.messageLimit.cleanup(self.registryValue("floodTimeout"))
		self.joinLimit.cleanup(self.registryValue("joinFloodTimeout"))
		self.quitLimit.cleanup(self.registryValue("badConnectionTimeout"))
		self.highlightLimit.cleanup(self.registryValue("highlightTimeout"))
		self.slapLimit.cleanup(self.registryValue("slapTimeout"))

		immunityTime = self.registryValue("immunityTime")
		self.punishTime = {
			k: v for k, v in self.punishTime.items()
			if now - v < immunityTime
		}

	def inFilter(self, irc, msg):
		if not msg.prefix:
			# Outgoing message from the bot
			return msg
		if msg.command not in CHECKED_COMMANDS:
			return msg
		channel = msg.args[0]
		if ircutils.isChannel(channel) and \
				self.registryValue("enabled", channel):
			if msg.command in MSG_COMMANDS:
				self.checkMessageFlood(irc, msg)
			elif msg.command == "JOIN":
				self.checkJoinFlood(irc, msg)
			elif msg.command == "QUIT":
				self.checkbadConnectionFlood(irc, msg)
		return msg

	def generateRecent(self, irc, msg, commands, maxNeeded=5):
		recent = []
		# Sorted in order of arrival
		for item in reversed(irc.state.history):
			if item.command in commands and \
					item.nick == msg.nick and \
					item.args[0] == msg.args[0]:
				recent.insert(0, item)
				if len(recent) >= maxNeeded:
					break
		return recent

	def checkJoinFlood(self, irc, msg):
		channel = msg.args[0]
		joinFloodLimit = self.registryValue("joinFloodLimit")
		joinFloodTimeout = self.registryValue("joinFloodTimeout")
		joinKey = (irc.network, channel, msg.host)
		if not msg.user.startswith("~"):
			joinKey += (msg.user,)

		if self.joinLimit(joinKey, joinFloodTimeout, msg.time) > joinFloodLimit:
			self.ban(irc, msg)

	def getBadConnectionChannel(self, irc):
		config = self.registryValue("badConnectionChannel")
		for chan in config:
			if "/" in chan:
				network, chan = chan.split("/", 1)
				if network == irc.network:
					return chan
			else:
				return chan
		return None

	def checkbadConnectionFlood(self, irc, msg):
		badConnectionLimit = self.registryValue("badConnectionLimit")
		badConnectionTimeout = self.registryValue("badConnectionTimeout")
		badConnectionBanTime = self.registryValue("badConnectionBanTime")
		badConnectionChannel = self.getBadConnectionChannel(irc)
		quitKey = (irc.network, msg.host)

		if self.quitLimit(quitKey, badConnectionTimeout, msg.time) > badConnectionLimit:
			self.banForward(irc, msg, badConnectionChannel, badConnectionBanTime)

	def ban(self, irc, msg, forwardChannel=None, banLength=None):
		channel = msg.args[0]
		msg_chan_state = irc.state.channels[channel]
		if irc.nick not in msg_chan_state.ops and \
				irc.nick not in msg_chan_state.halfops:
			self.log.warning("Tried to ban %s from %s, but not oped.",
				msg.nick, channel)
			return

		hostmask = irc.state.nickToHostmask(msg.nick)
		banmaskStyle = conf.supybot.protocols.irc.banmask
		banmask = banmaskStyle.makeBanmask(hostmask)
		if forwardChannel is not None:
			banmask += "$" + forwardChannel

		irc.queueMsg(ircmsgs.ban(channel, banmask))

		self.log.warning("Banned %s (%s) from %s.",
				banmask, msg.nick, channel)

		if banLength:
			schedule.addEvent(self.unBan, time.time() + banLength,
					args=[irc, channel, banmask, msg.nick])

	def unBan(self, irc, channel, banmask, nick):
		irc.queueMsg(ircmsgs.mode(channel, ("-b", banmask)))

		self.log.warning("Unbanned %s (%s) from %s.", banmask, nick, channel)

	def checkMessageFlood(self, irc, msg):
		channel = msg.args[0]
		message = ircutils.stripFormatting(msg.args[1])
		recentMessages = self.generateRecent(irc, msg, MSG_COMMANDS)
		channelKey = (irc.network, channel)
		userKey = (irc.network, channel, msg.host)
		if not msg.user.startswith("~"):
			userKey += (msg.user,)

		if len(msg.nick) == 12 and msg.ident == "~" + msg.nick[:9]:
			m = re.search(r'fr[e3][e3]n[o0]d[e3]', message, re.IGNORECASE)
			if m and re.search(r'\d', m.group(0)):
				ban(irc, msg, None, 3600 * 6)

		# Regular message flood
		floodLimit = self.registryValue("floodLimit")
		floodTimeout = self.registryValue("floodTimeout")
		if self.messageLimit(userKey, floodTimeout, msg.time) > floodLimit:
			self.floodPunish(irc, msg, "Message")

		# Message repetition flood
		repeatLimit = self.registryValue("repeatLimit")
		repeatTime = self.registryValue("repeatTime")
		if len(recentMessages) > repeatLimit:
			firstIdx = int(len(recentMessages) - repeatLimit - 1)
			firstTime = recentMessages[firstIdx].receivedAt
			curTime = recentMessages[-1].receivedAt
			curText = recentMessages[-1].args[1]
			matching = (msg.args[1] == curText for msg in recentMessages[firstIdx:-1])
			if curTime - firstTime < repeatTime and all(matching):
				self.floodPunish(irc, msg, "Message repetition")
				return

		# Slap flood
		slapLimit = self.registryValue("slapLimit")
		slapTimeout = self.registryValue("slapTimeout")
		if ircmsgs.isAction(msg) and "slaps" in message and \
				self.slapLimit(userKey, slapTimeout, msg.time) > slapLimit:
			self.floodPunish(irc, msg, "Slap")
			return

		# Mass highlight
		highlightLimit = self.registryValue("highlightLimit")
		highlightTimeout = self.registryValue("highlightTimeout")
		if channelKey in self.nickRegexes:
			matches = self.nickRegexes[channelKey].findall(message)
			if self.highlightLimit(userKey, highlightTimeout, msg.time, len(matches)) > highlightLimit:
				self.floodPunish(irc, msg, "Highlight")
				return

	def floodPunish(self, irc, msg, floodType):
		channel = msg.args[0]
		channel_state = irc.state.channels[channel]
		offenseKey = (irc.network, channel, msg.host)

		immunityTime = self.registryValue("immunityTime")

		if offenseKey in self.punishTime and \
				msg.time - self.punishTime[offenseKey] < immunityTime:
			self.log.debug("Not punishing %s, they are immune.", msg.nick)
			return

		if msg.nick in channel_state.ops or \
				msg.nick in channel_state.halfops or \
				msg.nick in channel_state.voices:
			self.log.debug("%s flood by %s detected in %s, but "
				"I will not punish them because they have "
				"special access.", floodType, msg.nick, channel)
			return

		if ircdb.checkCapability(msg.prefix, 'trusted') or \
				ircdb.checkCapability(msg.prefix, 'admin') or \
				ircdb.checkCapability(msg.prefix, channel + ',op'):
			self.log.debug("%s flood by %s detected in %s, but "
				"I will not punish them because they are "
				"trusted.", floodType, msg.nick, channel)
			return

		if irc.nick not in channel_state.ops and \
				irc.nick not in channel_state.halfops:
			self.log.warning("%s flood by %s detected in %s, but not oped.",\
				floodType, msg.nick, channel)
			return

		banIssued = False
		offenseLimit = self.registryValue("offenseLimit")
		offenseTimeout = self.registryValue("offenseTimeout")
		if self.offenseLimit(offenseKey, offenseTimeout, msg.time) > offenseLimit:
			hostmask = irc.state.nickToHostmask(msg.nick)
			banmaskstyle = conf.supybot.protocols.irc.banmask
			banmask = banmaskstyle.makeBanmask(hostmask)

			irc.queueMsg(ircmsgs.ban(channel, banmask))

			banIssued = True
			self.log.warning("Banned %s (%s) from %s for repeated flooding.",
				banmask, msg.nick, channel)

		reason = floodType + " flood detected."

		if floodType == "Message":
			pastebin = self.registryValue("suggestedPastebin")
			reason += " Use a pastebin like {}.".format(pastebin)

		irc.queueMsg(ircmsgs.kick(channel, msg.nick, reason))

		self.punishTime[offenseKey] = msg.time

		if not banIssued:
			self.log.warning("Kicked %s from %s for %s flooding.",
					msg.nick, channel, floodType)

	def makeNickRegex(self, irc, channels=None):
		if channels is None:
			channels = irc.state.channels.keys()

		for channelName in channels:
			channelKey = (irc.network, channelName)
			if channelName not in irc.state.channels:
				del self.nickRegexes[channelKey]
				continue

			chan = irc.state.channels[channelName]
			# Include minimum nick length to avoid matching nicks that are common words
			longNicks = [x for x in chan.users if len(x) > 3]
			regex = "|".join(map(re.escape, longNicks))

			self.nickRegexes[channelKey] = re.compile(regex, re.IGNORECASE)

	def doJoin(self, irc, msg):
		for channel in msg.args[0].split(","):
			self.makeNickRegex(irc, [channel])

	def doPart(self, irc, msg):
		if msg.nick == irc.nick:
			return
		for channel in msg.args[0].split(","):
			self.makeNickRegex(irc, [channel])

	def doQuit(self, irc, msg):
		if msg.nick == irc.nick:
			return
		self.makeNickRegex(irc, None)

	def doKick(self, irc, msg):
		if msg.nick == irc.nick:
			return
		self.makeNickRegex(irc, [msg.args[0]])

	def doNick(self, irc, msg):
		self.makeNickRegex(irc, None)

Class = FloodProtector
