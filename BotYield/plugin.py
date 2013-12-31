import supybot.callbacks as callbacks
from supybot.commands import *
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs

class BotYield(callbacks.Plugin):
	"""Sleeps in a channel when annother bot joins
	"""

	noIgnore = True #We don't want lobotomies to get in our way

	def doJoin(self, irc, msg):
		channel = msg.args[0]
		if msg.nick == self.registryValue("nick", channel):
			self.Sleep(channel)

	def reActivate(self, irc, nick, channel):
		#self.log.info("reActivate called. Nick:"+nick+" ConfNick:"+self.registryValue("nick", channel))
		if channel is None:
			for channel in irc.state.channels.keys():
				if nick == self.registryValue("nick", channel):
					self.WakeUp(channel)
			return
		#self.log.info("reActivate Channel: "+channel)
		if nick == self.registryValue("nick", channel):
			self.WakeUp(channel)

	def doKick(self, irc, msg): self.reActivate(irc, msg.args[1], msg.args[0])
	def doPart(self, irc, msg): self.reActivate(irc, msg.nick, msg.args[0])
	def doQuit(self, irc, msg): self.reActivate(irc, msg.nick, None)

	def do366(self, irc, msg): 
		'''End of /NAMES list (after joining a channel)
		Here instead of doJoin so that the userlist is populated
		'''
		channel = msg.args[1]
		botNick = self.registryValue("nick", channel)
		if botNick == self.registryValue("nick"): return
		users = list(irc.state.channels[channel].users)
		BotOnline = False
		for nick in users:
			if nick == botNick:
				BotOnline = True
				break
		if BotOnline:
			self.Sleep(channel)
		else:
			self.WakeUp(channel)

	def doNick(self, irc, msg):
		oldNick = msg.nick
		newNick = msg.args[0]
		defaultBotNick = self.registryValue("nick")
		for channel in irc.state.channels:
			botNick = self.registryValue("nick", channel)
			if botNick == defaultBotNick:
				continue
			if newNick == botNick:
				self.Sleep(channel)
			elif oldNick == botNick:
				self.WakeUp(channel)

	def Sleep(self, channel):
		print("Sleep in "+channel+".")
		chan = ircdb.channels.getChannel(channel)
		if not chan.lobotomized:
			chan.lobotomized = True
			ircdb.channels.setChannel(channel, chan)

	def WakeUp(self, channel):
		print("Wake up in "+channel+".")
		chan = ircdb.channels.getChannel(channel)
		if chan.lobotomized:
			chan.lobotomized = False
			ircdb.channels.setChannel(channel, chan)

Class = BotYield
