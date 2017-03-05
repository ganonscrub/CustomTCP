import os
import sys

import random

import time

from rdtsender import *
from rdtreceiver import *

if len(sys.argv) < 5:
	print( "Usage: rdt.py [recv_host] [recv_port] [send_host] [send_port]" )
	sys.exit()

class RDT:
	def __init__( self, recv_host, recv_port, send_host, send_port ):
		self.sender = RDTSender( send_host, send_port )
		self.receiver = RDTReceiver( recv_host, recv_port )
		
rdt = RDT( sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]) )
rdt.sender.sendLoop()