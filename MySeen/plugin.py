
import supybot.callbacks as callbacks
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *

import time
import sqlalchemy
import sqlalchemy.ext
import sqlalchemy.ext.declarative


filename = conf.supybot.directories.data.dirize('Seen.sqlite')

Base = sqlalchemy.ext.declarative.declarative_base()

class Network(Base):
	__tablename__ = "networks"

	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String)

class Channel(Base):
	__tablename__ = "channels"

	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String)

class Entry(Base):
	__tablename__ = "seen"

	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	timestamp = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
	networkid = sqlalchemy.Column(sqlalchemy.Integer,
			sqlalchemy.ForeignKey("networks.id"), nullable=False)
	channelid = sqlalchemy.Column(sqlalchemy.Integer,
			sqlalchemy.ForeignKey("channels.id"), nullable=False)
	nick = sqlalchemy.Column(sqlalchemy.String, nullable=False)
	message = sqlalchemy.Column(sqlalchemy.String)

	network = sqlalchemy.orm.relationship("Network")
	channel = sqlalchemy.orm.relationship("Channel")

	def update(self, networkid, channelid, nick, message):
		self.networkid = networkid
		self.channelid = channelid
		self.nick      = nick.lower()
		self.message   = message
		self.timestamp = time.time()

	def __init__(self, networkid, channelid, nick, message):
		return self.update(networkid, channelid, nick, message)


class MySeen(callbacks.Plugin):
	"""
	Records the last time a nick is seen
	"""

	noIgnore = True

	def __init__(self, irc):
		self.__parent = super(MySeen, self)
		self.__parent.__init__(irc)
		self.engine = sqlalchemy.create_engine("sqlite:///" + filename)
		sessionmaker = sqlalchemy.orm.sessionmaker()
		sessionmaker.configure(bind=self.engine)
		self.session = sessionmaker()
		# We have to execute a command on the DB for it to actually be opened
		assert(self.engine.execute("SELECT 1;").scalar() == 1)
		Base.metadata.create_all(self.engine)

	def seen(self, irc, msg, network, channel, nick):
		"""[channel] <nick>

		Finds the last time a nick was seen and what they said.
		"""
		entry = self.getChan(irc.network, channel, nick)
		if not entry:
			irc.reply("I haven't seen %s in %s." % (nick, channel))
			return
		t = time.time()
		irc.reply("I saw %s in %s %s ago saying \"%s\"." % (
				nick,
				entry.channel.name,
				utils.timeElapsed(t - entry.timestamp),
				entry.message))

	seen = wrap(seen, ["channel", "nick"])

	def Get(self, network, nick):
		try:
			return self.session.query(Entry)\
				.join(Entry.network)\
				.filter(
					Network.name == network,
					Entry.nick == nick.lower()
				).order_by(Entry.timestamp.desc()).first()
		except sqlalchemy.orm.exc.NoResultFound:
			return None

	def getChan(self, network, channel, nick):
		try:
			return self.session.query(Entry)\
				.join(Entry.network)\
				.join(Entry.channel)\
				.filter(
					Network.name == network,
					Channel.name == channel,
					Entry.nick == nick.lower()
				).one()
		except sqlalchemy.orm.exc.NoResultFound:
			return None

	def getNetworkId(self, network):
		try:
			net = self.session.query(Network).filter_by(name=network).one()
			return net.id
		except sqlalchemy.orm.exc.NoResultFound:
			net = Network(name=network)
			self.session.add(net)
			self.session.commit()
			return net.id

	def getChannelId(self, channel):
		try:
			chan = self.session.query(Channel).filter_by(name=channel).one()
			return chan.id
		except sqlalchemy.orm.exc.NoResultFound:
			chan = Channel(name=channel)
			self.session.add(chan)
			self.session.commit()
			return chan.id

	def doPrivmsg(self, irc, msg): self.Add(irc, msg)
	def doNotice (self, irc, msg): self.Add(irc, msg)

	def Add(self, irc, msg):
		if not irc.isChannel(msg.args[0]):
			return

		entry = self.getChan(irc.network, msg.args[0], msg.nick)
		if entry is None:
			entry = Entry(self.getNetworkId(irc.network),
					self.getChannelId(msg.args[0]),
					msg.nick,
					msg.args[1])
			self.session.add(entry)
		else:
			entry.update(self.getNetworkId(irc.network),
					self.getChannelId(msg.args[0]),
					msg.nick,
					msg.args[1])

		self.session.commit()

Class = MySeen

