import os
import sys

from rdtsender import *
from rdtreceiver import *

if len(sys.argv) < 7:
	print( "Usage: rdt.py [recv_host] [recv_port] [send_host] [send_port] [ack_corrupt_%] [data_corrupt_%]" )
	sys.exit()

class RDT:
	def __init__( self, recv_host, recv_port, send_host, send_port ):
		self.sender = RDTSender( send_host, send_port )
		self.receiver = RDTReceiver( recv_host, recv_port )
		

rdt = RDT( sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]) )

rdt.sender.ackCorruptRate = int(sys.argv[5])
rdt.receiver.dataCorruptRate = int(sys.argv[6])
print( "Sender ACK corrupt rate:", rdt.sender.ackCorruptRate )
print( "Receiver data corrupt rate:", rdt.receiver.dataCorruptRate )

rdt.sender.sendLoop()