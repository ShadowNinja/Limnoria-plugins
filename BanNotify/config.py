
import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
	from supybot.questions import expect, anything, something, yn
	conf.registerPlugin("BanNotify", True)


BanNotify = conf.registerPlugin("BanNotify")
conf.registerChannelValue(BanNotify, "notice",
	registry.String("", "The message to send to an op when a ban is added.  Disabled if empty."))
