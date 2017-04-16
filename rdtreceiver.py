import socket
import threading
from time import sleep

from globals import *

class RDTReceiver:
	STATE_WAIT_0 = 2000
	STATE_WAIT_1 = 2001
	
	#if socket does not receive a packet after this interval,
	#the socket assumes the transmission is finished
	TIMEOUT = 3.0

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
		self.dataPacketCorruptRate = 0
		self.ackPacketDropRate = 0
		self.expectedSeqNum = 0
		
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

	def makePacket( self, sequence, data ):
		packet = bytearray()
		
		if type(data) == 'str':
			data = bytearray(data)
		
		chksum = checksum( sequence, data )
		chksum = chksum.to_bytes(2,byteorder=G_PACKET_CHECKSUM_BYTE_ORDER)
		
		packet.append( chksum[0] )
		packet.append( chksum[1] )
		packet.append( sequence )
		
		for i in range( len(data) ):
			packet.append( data[i] )
		
		return packet
	
	def handleStateWait0( self, data, addr ):
		if self.isReceiving == False:
			self.currentFilename = 'output_' + getISO()[:19].replace(':','_') + '.'
			self.currentFilename += self.determineFileExtension( data[G_PACKET_DATASTART:] )
			print( getISO(), "RECEIVER: Packet received, awaiting the rest of the transmission..." )
			
			self.isReceiving = True
			
		if data[2] == 0 and not isPacketCorrupt( 0, data ): # data[2] is the sequence byte			
			# drop ACK packet based on user-supplied drop percentage
			if not randomTrueFromChance( self.ackPacketDropRate ): # drop packet if we get a True
				self.socket.sendto( self.makePacket( 0, b'ACK' ), addr )
				
			self.packetsReceived += 1
			self.appendToFile( data[G_PACKET_DATASTART:] )
			self.state = RDTReceiver.STATE_WAIT_1
		else:			
			# drop ACK packet based on user-supplied drop percentage
			if not randomTrueFromChance( self.ackPacketDropRate ):
				self.socket.sendto( self.makePacket( 1, b'ACK' ), addr )
	
	def receiveLoop( self ):
		while True:
			try:
				data, address = self.socket.recvfrom( G_PACKET_MAXSIZE )
				
				packet = bytearray( data )
				corruptPacket( packet, self.dataPacketCorruptRate )
				info = getAssembledPacketInfo( packet )
				seqNum = info['seqnumInt']
				self.expectedSeqNum = 0
				if not self.expectedSeqNum == seqNum or isAssembledPacketCorrupt( info['seqnumBytes'], data ):
					continue
				else:				
					self.currentFilename = 'output_' + getISO()[:19].replace(':','_') + '.'
					self.currentFilename += self.determineFileExtension( data[G_PACKET_DATASTART:] )
					print( getISO(), "RECEIVER: Packet received, awaiting the rest of the transmission..." )
					self.appendToFile( info['data'] )
					self.expectedSeqNum += 1
					self.isReceiving = True
					if not randomTrueFromChance( self.ackPacketDropRate ):
						self.socket.sendto( assemblePacket( info['seqnumInt'], b'ACK' ), address )
				
				while self.isReceiving:
					data, address = self.socket.recvfrom( G_PACKET_MAXSIZE )
					
					info = getAssembledPacketInfo( data )
					seqNum = info['seqnumInt']
					if self.expectedSeqNum == seqNum and not isAssembledPacketCorrupt( info['seqnumBytes'], data ):
						self.appendToFile( info['data'] )
						self.expectedSeqNum += 1
					else:
						if not randomTrueFromChance( self.ackPacketDropRate ):
							self.socket.sendto( assemblePacket( info['seqnum'], b'ACK' ), address )
					
					if not randomTrueFromChance( self.ackPacketDropRate ):
						self.socket.sendto( assemblePacket( info['seqnum'], b'ACK' ), address )

			except socket.timeout:
				if self.isReceiving:
					print( "\n", getISO(), "RECEIVER: timed out, waiting for a new transmission; packets received:", self.packetsReceived )
					self.isReceiving = False
					self.packetsReceived = 0
					self.currentFilename = None