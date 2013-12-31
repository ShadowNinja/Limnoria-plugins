from supybot.test import *

class MinetestServerUpTestCase(ChannelPluginTestCase):
    plugins = ('MinetestServerUp')
    if network:
        def testSearch(self):
            pass  #we can't realy guarantee anything
