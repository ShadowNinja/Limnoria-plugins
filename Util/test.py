
from supybot.test import *

class UtilTestCase(PluginTestCase):
	plugins = ("Util",)
	def testStripTo(self):
		self.assertResponse("stripto - foo-bar", "foo")
		self.assertError("stripto - foobar")

