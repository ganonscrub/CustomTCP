import socket
import threading

from globals import *

class RDTReceiver:
	STATE_WAIT_0 = 2000
	STATE_WAIT_1 = 2001
	
	#if socket does not receive a packet after this interval,
	#the socket assumes the transmission is over
	TIMEOUT = 2.0

	def __init__( self, host, port ):
		self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		self.socket.bind( (host, port) )
		self.socket.settimeout( RDTReceiver.TIMEOUT )
		self.state = RDTReceiver.STATE_WAIT_0
		self.thread = threading.Thread( name="receive", target=self.receiveLoop )
		self.thread.daemon = True
		self.thread.start()
		self.isReceiving = False
		self.packetsReceived = 0
		self.currentFilename = None
		self.dataCorruptRate = 0
		
	def determineFileExtension( self, packet ):
		if len( packet ) < 4:
			return "FILE"
			
		keys = list(G_COMMON_FILE_BYTES)
		for i in range( len(G_COMMON_FILE_BYTES) ):
			n = len( G_COMMON_FILE_BYTES[keys[i]] )
			if packet[:n] == G_COMMON_FILE_BYTES[keys[i]]:
				return keys[i]
				
		return "txt"
		
	def appendToFile( self, data ):
		file = open( self.currentFilename, 'ab' )
		file.write( data )
		file.close()
	
	def handleStateWait0( self, data, addr ):
		if self.isReceiving == False:
			self.currentFilename = 'output_' + getISO()[:19].replace(':','_') + '.'
			self.currentFilename += self.determineFileExtension( data[G_PACKET_DATASTART:] )
			
			self.isReceiving = True
			
		if data[2] == 0: # data[2] is the sequence byte
			#print( "RECEIVER: Got SEQ0" )
			self.socket.sendto( b'ACK0', addr )
			self.packetsReceived += 1
			self.appendToFile( data[G_PACKET_DATASTART:] )
			self.state = RDTReceiver.STATE_WAIT_1
		else:
			#print( "RECEIVER: Did not get SEQ0" )
			self.socket.sendto( b'ACK1', addr )
	
	def handleStateWait1( self, data, addr ):
		if self.isReceiving == False:
			print( "We have some very serious problems" )
	
		if data[2] == 1: # data[2] is the sequence byte
			#print( "RECEIVER: Got SEQ1" )
			self.socket.sendto( b'ACK1', addr )
			self.packetsReceived += 1
			self.appendToFile( data[G_PACKET_DATASTART:] )
			self.state = RDTReceiver.STATE_WAIT_0
		else:
			#print( "RECEIVER: Did not get SEQ1" )
			self.socket.sendto( b'ACK0', addr )
	
	def receiveLoop( self ):
		while True:
			try:
				data, address = self.socket.recvfrom( G_PACKET_MAXSIZE )
				
				packet = bytearray( data )
				corruptPacket( packet, self.dataCorruptRate )
				
				if self.state == RDTReceiver.STATE_WAIT_0:
					self.handleStateWait0( data, address )
				elif self.state == RDTReceiver.STATE_WAIT_1:
					self.handleStateWait1( data, address )
			except socket.timeout:
				if self.isReceiving:
					print( "\nReceiver timed out, waiting for a new transmission; packets received:", self.packetsReceived )
					self.isReceiving = False
					self.packetsReceived = 0
					self.currentFilename = None
					self.state = RDTReceiver.STATE_WAIT_0