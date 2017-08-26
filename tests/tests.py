from nose.tools import *
from .context imort weatherer

def setup():
	print "SETUP!"

def teardown():
	print "TEARDOWN!"
	
def test_basic():
	print "I RAN!"
