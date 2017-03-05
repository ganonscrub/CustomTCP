import os
import socket

from globals import *

class RDTSender:
	STATE_WAIT_0 = 1000
	STATE_WAIT_1 = 1002
	STATE_WAITACK_0 = 1001
	STATE_WAITACK_1 = 1003

	TIMEOUT = 0.5
	
	def __init__( self, host, port ):
		self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		self.socket.settimeout( RDTSender.TIMEOUT )
		self.sendHost = host
		self.sendPort = port
		self.state = RDTSender.STATE_WAIT_0
		self.isSending = False
		self.currentFilename = None
		self.totalPacketsToSend = 0
		self.currentPacketNumber = 0
	
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
		self.state = RDTSender.STATE_WAIT_0
		self.isSending = False
		self.currentFilename = None
		self.totalPacketsToSend = 0
		self.currentPacketNumber = 0
	
	def makePacket( self, sequence, data ):
		packet = bytearray()
		
		chksum = checksum( sequence, data )
		chksum = chksum.to_bytes(2,byteorder='little')
		
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
		self.sendToRemote( packet )
		self.state = RDTSender.STATE_WAITACK_0
	
	def handleStateWait1( self ):
		fileData = self.getFileBytes( self.currentFilename, self.currentPacketNumber )
		packet = self.makePacket( 1, fileData )
		self.sendToRemote( packet )
		self.state = RDTSender.STATE_WAITACK_1
	
	def handleStateWaitAck0( self ):
		try:
			data, address = self.socket.recvfrom( 32 )
			if data == b'ACK0':
				#print("SENDER: Got ACK0")
				self.state = RDTSender.STATE_WAIT_1
				self.currentPacketNumber += 1
			else:
				print("SENDER: Did not get ACK0")
		except socket.timeout:
			self.state = RDTSender.STATE_WAIT_0
	
	def handleStateWaitAck1( self ):
		try:
			data, address = self.socket.recvfrom( 32 )
			if data == b'ACK1':
				#print("SENDER: Got ACK1")
				self.state = RDTSender.STATE_WAIT_0
				self.currentPacketNumber += 1
			else:
				print("SENDER: Did not get ACK1")
		except socket.timeout:
			self.state = RDTSender.STATE_WAIT_1
		
	def sendLoop( self ):
		while True:
			if self.isSending:
				if self.state == RDTSender.STATE_WAIT_0:
					self.handleStateWait0()					
				elif self.state == RDTSender.STATE_WAIT_1:
					self.handleStateWait1()					
				elif self.state == RDTSender.STATE_WAITACK_0:
					self.handleStateWaitAck0()						
				elif self.state == RDTSender.STATE_WAITACK_1:
					self.handleStateWaitAck1()
					
				if self.currentPacketNumber >= self.totalPacketsToSend:
					self.resetState()
			else:
				data = input("Type filename: ")
				
				if data[-4] == '.':
					if os.path.isfile( data ):
						size = self.getFileSize( data )
						self.totalPacketsToSend = int(size / G_PACKET_DATABYTES) + 1
						print( "Total packets:", self.totalPacketsToSend )
						self.currentPacketNumber = 0
						self.currentFilename = data
						self.state = RDTSender.STATE_WAIT_0
						self.isSending = True
					else:
						print( "File not found" )
				else:
					print( "Must enter a filename" )