from supybot import conf, registry


def configure(advanced):
	from supybot.questions import output, expect, anything, something, yn
	conf.registerPlugin('FloodProtector', True)


FloodProtector = conf.registerPlugin('FloodProtector')

# Misc

conf.registerChannelValue(FloodProtector, "enabled",
	registry.Boolean(True, "Whether to check floods in the channel."))

conf.registerChannelValue(FloodProtector, "suggestedPastebin",
	registry.String("paste.ubuntu.com", "Pastebin to suggest when kicking a user for a paste flood."))

conf.registerChannelValue(FloodProtector, "immunityTime",
	registry.PositiveFloat(1, "Number of seconds to ignore a user after a kick/ban to avoid double kicks/bans due to a race."))

# Escalation

conf.registerChannelValue(FloodProtector, "offenseLimit",
	registry.PositiveFloat(2, "Maximum number of times to kick a user before escalating to a ban.",
		private=True))

conf.registerChannelValue(FloodProtector, "offenseTimeout",
	registry.PositiveFloat(60 * 60, "Number of seconds after which an offense is forgotten.",
		private=True))

# Bad connection forwarding

conf.registerGlobalValue(FloodProtector, "badConnectionChannel",
	registry.SpaceSeparatedListOfStrings("", """
Channel to forward users to if they join and quit too much.
Format: Space seperated list of [network/]#channel
"""))

conf.registerChannelValue(FloodProtector, "badConnectionLimit",
	registry.PositiveInteger(6, "Number of quits allowed before a bad connection is detected."))

conf.registerChannelValue(FloodProtector, "badConnectionTimeout",
	registry.PositiveInteger(10 * 60, "Time until a quit is forgotten."))

conf.registerChannelValue(FloodProtector, "badConnectionBanTime",
	registry.PositiveInteger(24 * 60 * 60, "Number of seconds to ban-forward if a bad connection is detected."))

# Join flood

conf.registerChannelValue(FloodProtector, "joinFloodLimit",
	registry.PositiveInteger(4, "Number of joins allowed before a join flood is detected."))

conf.registerChannelValue(FloodProtector, "joinFloodTimeout",
	registry.PositiveInteger(60, "Time until a join is forgotten."))

# Message flood

conf.registerChannelValue(FloodProtector, "floodLimit",
	registry.PositiveFloat(4, "Number of messages that can be sent at once before a message flood is detected.",
		private=True))

conf.registerChannelValue(FloodProtector, "floodTimeout",
	registry.PositiveFloat(5, "Number of seconds until a message is forgetten.",
		private=True))

# Repetition flood

conf.registerChannelValue(FloodProtector, "repeatLimit",
	registry.PositiveFloat(2, "Number of repetitions that will be allowed.",
		private=True))

conf.registerChannelValue(FloodProtector, "repeatTime",
	registry.PositiveFloat(60, "Max number of seconds for repetitions to be detected in.",
		private=True))

# Mass highlight

conf.registerChannelValue(FloodProtector, "highlightLimit",
	registry.PositiveFloat(8, "Number of users that can be highlighted before a highlight flood is detected.",
		private=True))

conf.registerChannelValue(FloodProtector, "highlightTimeout",
	registry.PositiveFloat(5, "Number of seconds until a highlight is forgetten.",
		private=True))

# Slap flood

conf.registerChannelValue(FloodProtector, "slapLimit",
	registry.PositiveFloat(2, "Number slap messages allowed before a slap flood is detected.",
		private=True))

conf.registerChannelValue(FloodProtector, "slapTimeout",
	registry.PositiveFloat(30, "Number of seconds until a slap message is forgetten.",
		private=True))
