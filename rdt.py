import os
import sys

from rdtsender import *
from rdtreceiver import *

if len(sys.argv) < 8:
	print( "Usage: rdt.py [recv_host] [recv_port] [send_host] [send_port] [ack_corrupt_%] [data_corrupt_%] [show_window]" )
	sys.exit()

class RDT:
	def __init__( self, recv_host, recv_port, send_host, send_port, showWindow ):
		self.sender = RDTSender( send_host, send_port )
		self.receiver = RDTReceiver( recv_host, recv_port, showWindow )

# allow the user to enable/disable the image window with the last argument
showWindow = int(sys.argv[7]) == 1
rdt = RDT(sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), showWindow )

rdt.sender.ackCorruptRate = int(sys.argv[5])
rdt.receiver.dataCorruptRate = int(sys.argv[6])
print( "Sender ACK corrupt rate:", rdt.sender.ackCorruptRate )
print( "Receiver data corrupt rate:", rdt.receiver.dataCorruptRate )

# We need the callback to call the TKInter functions in the main loop
# only attach the callback if showWindow is true
if int(sys.argv[7]) == 1:
	rdt.sender.sendLoop(rdt.receiver.update_image)
else:
	rdt.sender.sendLoop()