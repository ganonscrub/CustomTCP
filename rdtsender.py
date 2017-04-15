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
		self.windowSize = G_SENDER_WINDOW_SIZE
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
		self.windowSize = G_SENDER_WINDOW_SIZE
		self.base = 0
	
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
		
	def handleStateWait0( self ):
		fileData = self.getFileBytes( self.currentFilename, self.currentPacketNumber )
		packet = self.makePacket( 0, fileData )
		
		if not randomTrueFromChance( self.dataPacketDropRate ):
			self.sendToRemote( packet )
		
		self.state = RDTSender.STATE_WAITACK_0
	
	def handleStateWaitAck0( self ):
		try:
			data, address = self.socket.recvfrom( 32 )
			
			packet = bytearray( data )
			corruptPacket( packet, self.ackPacketCorruptRate )
			
			if packet[3:] == b'ACK' and not isPacketCorrupt( 0, packet ):
				self.printProgress()
				self.state = RDTSender.STATE_WAIT_1
				self.currentPacketNumber += 1
			else:
				pass # state doesn't change, so this function will be run again on the next loop iteration
				# this is where we can increment a triple ACK counter
		except socket.timeout: # RDT3.0: if we timeout waiting for an ACK0, resend the 0 packet
			self.state = RDTSender.STATE_WAIT_0

	def getSeqNumFromAck( self, packet ):
		pass
			
	def handleStateSendWait( self ):
		print( "handleStateSendWait" )
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
			self.sendToRemote( self.window[i] )
		self.state = RDTSender.STATE_ACK_WAIT
		
	def handleStateAckWait( self ):
		try:
			while True: # keep listening for packets
				data, address = self.socket.recvfrom( G_PACKET_ACK_MAXSIZE )
			
				packet = bytearray( data )
				info = getAssembledPacketInfo( packet )
				seqNum = int.from_bytes(info['seqnum'],byteorder=G_PACKET_SEQNUM_BYTE_ORDER)
				
				if seqNum == self.base:
					self.window.pop(0) # get rid of first element in our buffer
					
					self.base += 1
					
					if self.base == self.totalPacketsToSend:
						print( "Sent all the packets!" )
						self.isSending = False
						return
						
					fileData = self.getFileBytes( self.currentFilename, self.base + self.windowSize - 1 )
					self.window.append( assemblePacket( self.base + self.windowSize - 1, fileData ) )
					
				else:
					print( "Out-of-order packet", seqNum )
				
		except socket.timeout:
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
		self.resetState() # this will set self.isSending to false, among other things