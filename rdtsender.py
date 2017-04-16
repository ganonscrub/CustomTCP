import os
import socket

from globals import *

class RDTSender:
	STATE_SEND_WAIT = 1000
	STATE_SEND_PACKETS = 1001
	STATE_ACK_WAIT = 1002

	TIMEOUT = 0.03 # 30 milliseconds
	
	def __init__( self, host, port ):
		self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		self.socket.settimeout( RDTSender.TIMEOUT )
		#self.socket.setblocking( False )
		self.sendHost = host
		self.sendPort = port
		self.state = RDTSender.STATE_SEND_WAIT
		self.doneSending = False
		self.isSending = False
		self.currentFilename = None
		self.totalPacketsToSend = 0
		self.currentPacketNumber = 0
		self.startTime = None
		self.ackPacketCorruptRate = 0
		self.dataPacketDropRate = 0
		self.window = []
		self.windowSize = 5
		self.base = 0
		self.nextSeqNum = self.base + self.windowSize
	
	def printProgress( self ):
		if self.totalPacketsToSend > 0:
			if self.currentPacketNumber % 100 == 0:
				ratio = int( (self.currentPacketNumber / self.totalPacketsToSend) * 100 )
				print( getISO(), "SENDER:", ratio, "percent of packets transmitted and ACK'd" )			
	
	def getFileBytes( self, filename, nPacket ):
		try:
			fin = open( filename, "rb" )
		except:
			print( "Error opening file" )
			return b''
		
		startPos = G_PACKET_DATABYTES * nPacket
		fin.seek( startPos, 0 )
		output = fin.read( G_PACKET_DATABYTES )
		return output

	def getFileSize( self, filename ):
		try:
			fin = open( filename, "rb" )
		except:
			print( "Error opening file" )
			return -1
			
		fin.seek( 0, 2 )
		size = fin.tell()
		fin.close()
		
		return size
	
	def resetState( self ):
		self.socket.settimeout( RDTSender.TIMEOUT )
		self.state = RDTSender.STATE_SEND_WAIT
		self.isSending = False
		self.currentFilename = None
		self.totalPacketsToSend = 0
		self.currentPacketNumber = 0
		self.window = []
		self.windowSize = 5
		self.base = 0
		self.nextSeqNum = self.base + self.windowSize
	
	def makePacket( self, sequence, data ):
		packet = bytearray()
		
		chksum = checksum( sequence, data )
		chksum = chksum.to_bytes(2,byteorder=G_PACKET_CHECKSUM_BYTE_ORDER)
		
		packet.append( chksum[0] )
		packet.append( chksum[1] )
		packet.append( sequence )
		
		for i in range( len(data) ):
			if type(data) == 'str':
				packet.append( ord(data[i]) )
			else:
				packet.append( data[i] )
		
		return packet
	
	def sendToRemote( self, packet ):
		self.socket.sendto( packet, (self.sendHost, self.sendPort) )
			
	def handleStateSendWait( self ):
		success = False
		
		while not success:
			filename = input("Type filename: ")	
			if filename[-4] == '.':
				if os.path.isfile( filename ):
					size = self.getFileSize( filename )
					self.totalPacketsToSend = int(size / G_PACKET_DATABYTES) + 1
					print( "Total packets:", self.totalPacketsToSend )
					self.currentPacketNumber = 0
					self.currentFilename = filename
					self.state = RDTSender.STATE_SEND_PACKETS
					self.isSending = True					
					success = True
					
					self.window = []
					self.base = 0
					self.nextSeqNum = self.base + self.windowSize
					# populate the initial send window for send state
					for i in range( self.windowSize ):
						fileData = self.getFileBytes( self.currentFilename, i )
						self.window.append( assemblePacket( i, fileData ) )
						
					self.startTime = time.time()
				else:
					print( "File not found" )
			else:
				print( "Must enter a filename" )
	
	def handleStateSendPackets( self ):
		for i in range( self.windowSize ):
			# randomly drop packets according to drop rate variable
			if not randomTrueFromChance( self.dataPacketDropRate ):
				# don't attempt to send more packets than there are to send
				if self.base + i < self.totalPacketsToSend:
					self.sendToRemote( self.window[i] )
				
		self.state = RDTSender.STATE_ACK_WAIT
		
	def handleStateAckWait( self ):
		try:
			while True: # keep listening for packets
				data, address = self.socket.recvfrom( G_PACKET_ACK_MAXSIZE )
			
				packet = bytearray( data )
				corruptPacket( packet, self.ackPacketCorruptRate )
				info = getAssembledPacketInfo( packet )
				seqNum = info['seqnumInt']
				
				if not seqNum == self.base or isAssembledPacketCorrupt( info['seqnumBytes'], packet ):
					#print( "Out-of-order or corrupt packet", seqNum )
					continue
				else:
					# get rid of first element in our buffer
					self.window.pop(0)
					
					self.base += 1
					self.nextSeqNum += 1
					
					if self.base == self.totalPacketsToSend:
						print( "Sent all the packets!" )
						self.isSending = False
						return
					
					# append the next packet to the window
					fileData = self.getFileBytes( self.currentFilename, self.base + self.windowSize - 1 )
					self.window.append( assemblePacket( self.base + self.windowSize - 1, fileData ) )
				
		except socket.timeout:
			if G_LOSS_RECOVERY_ENABLED:
				self.state = RDTSender.STATE_SEND_PACKETS
		
	def sendLoop( self ):
		self.handleStateSendWait()
	
		while self.isSending:
			if self.state == RDTSender.STATE_SEND_PACKETS:
				self.handleStateSendPackets()					
			elif self.state == RDTSender.STATE_ACK_WAIT:
				self.handleStateAckWait()
				
		totalTime = time.time() - self.startTime
		print( getISO(), "Total transmit time:", totalTime, "seconds" )
		print( "=== SEND FINISHED ===" )
		self.resetState()