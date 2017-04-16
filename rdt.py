import os
import sys

from rdtsender import *
from rdtreceiver import *

if len(sys.argv) < 4:
	print( "Usage: rdt.py [recv_host] [send_host] [app_port] <show_window>" )
	sys.exit()

showWindow = False
if len(sys.argv) == 5:
	if sys.argv[4] == '1':
		showWindow = True

class RDT:
	def __init__( self, recv_host, send_host, app_port, showWindow ):
		self.sender = RDTSender( send_host, app_port )
		self.receiver = RDTReceiver( recv_host, app_port, showWindow )
		
rdt = RDT( sys.argv[1], (sys.argv[2]), int(sys.argv[3]), showWindow )

print( "Receive host (this machine):", sys.argv[1] )
print( "Send host (remote machine):", sys.argv[2] )
print( "Application port: ", sys.argv[3] )
print( "" )

success = False

print( "When entering the following percentages, please use whole integers\n" )
print( "=== RECEIVER CONFIGURATION ===" )
print( "Before we send stuff, let's configure the local receiver" )

try:
	while not success:
		rdt.receiver.dataPacketCorruptRate = int( input( "Receiver data corrupt rate: " ) )
		rdt.receiver.ackPacketDropRate = int( input( "Receiver ACK packet drop rate: " ) )
		success = True
except ValueError:
	print( "Invalid user input. Please try again." )

resp = input( "Would you like to run in receive-only mode? (y/n): " )
if resp == "y" or resp == "Y":
	print( "Alright, this program will sit and wait for packets to come in" );
	try:
		while True:
			pass
	except KeyboardInterrupt:
		print( "Shutting down..." )
		sys.exit(0)

# implement try-except to (hopefully) exit program gracefully on Ctrl+C
try:
	while not rdt.sender.doneSending:
		try:
			print( "\n=== SENDER CONFIGURATION ===" )
			
			rdt.sender.ackPacketCorruptRate = int( input( "Sender ACK corrupt rate: " ) )
			rdt.sender.dataPacketDropRate = int( input( "Sender data packet drop rate: " ) )
			rdt.sender.windowSize = int( input( "Sender window size: " ) )
			
			rdt.sender.sendLoop()
		except ValueError:
			print( "Invalid user input. Please try again." )
except (KeyboardInterrupt, EOFError): #EOFError thrown when Ctrl+C pressed while input() is waiting for user input
	rdt.sender.doneSending = True
	print( "Done sending, exiting program..." )