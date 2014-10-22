import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
	from supybot.questions import expect, anything, something, yn
	conf.registerPlugin('Logger', True)


Logger = conf.registerPlugin('Logger')

conf.registerChannelValue(Logger, "enable",
	registry.Boolean(True, """Determines whether logging is enabled."""))

conf.registerGroup(Logger, "web")

conf.registerChannelValue(Logger.web, "public",
	registry.Boolean(True, """Determines whether the web logs for the channel
		are publicly visible."""))

conf.registerChannelValue(Logger.web, "key",
	registry.String("", """Determines the key (password) required to view
		web logs for the channel.""", private=True))

