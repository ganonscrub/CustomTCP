import os
import socket

from globals import *

class RDTSender:
	STATE_WAIT_0 = 1000
	STATE_WAIT_1 = 1002
	STATE_WAITACK_0 = 1001
	STATE_WAITACK_1 = 1003

	TIMEOUT = 0.03 # 30 milliseconds
	
	def __init__( self, host, port ):
		self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		self.socket.settimeout( RDTSender.TIMEOUT )
		self.sendHost = host
		self.sendPort = port
		self.state = RDTSender.STATE_WAIT_0
		self.doneSending = False
		self.isSending = False
		self.currentFilename = None
		self.totalPacketsToSend = 0
		self.currentPacketNumber = 0
		self.startTime = None
		self.ackPacketCorruptRate = 0
		self.dataPacketDropRate = 0
	
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
		
		if not randomTrueFromChance( self.dataPacketDropRate ):
			self.sendToRemote( packet )
		
		self.state = RDTSender.STATE_WAITACK_0
	
	def handleStateWait1( self ):
		fileData = self.getFileBytes( self.currentFilename, self.currentPacketNumber )
		packet = self.makePacket( 1, fileData )
		
		if not randomTrueFromChance( self.dataPacketDropRate ):
			self.sendToRemote( packet )
		
		self.state = RDTSender.STATE_WAITACK_1
	
	def handleStateWaitAck0( self ):
		try:
			data, address = self.socket.recvfrom( 32 )
			
			packet = bytearray( data )
			corruptPacket( packet, self.ackPacketCorruptRate )
			
			if packet[3:] == b'ACK' and not isPacketCorrupt( 0, packet ):
				#self.printProgress()
				self.state = RDTSender.STATE_WAIT_1
				self.currentPacketNumber += 1
			else:
				pass # state doesn't change, so this function will be run again on the next loop iteration
				# this is where we can increment a triple ACK counter
		except socket.timeout: # RDT3.0: if we timeout waiting for an ACK0, resend the 0 packet
			self.state = RDTSender.STATE_WAIT_0
	
	def handleStateWaitAck1( self ):
		try:
			data, address = self.socket.recvfrom( 32 )
			
			packet = bytearray( data )
			corruptPacket( packet, self.ackPacketCorruptRate )
			
			if packet[3:] == b'ACK' and not isPacketCorrupt( 1, packet ):
				#self.printProgress()
				self.state = RDTSender.STATE_WAIT_0
				self.currentPacketNumber += 1
			else:
				pass # state doesn't change, so this function will be run again on the next loop iteration
				# this is where we can increment a triple ACK counter
		except socket.timeout: # RDT3.0: if we timeout waiting for an ACK1, resend the 1 packet
			self.state = RDTSender.STATE_WAIT_1
		
	def sendLoop( self ):	
		data = input("Type filename: ")
				
		if data[-4] == '.':
			if os.path.isfile( data ):
				size = self.getFileSize( data )
				self.totalPacketsToSend = int(size / G_PACKET_DATABYTES) + 1
				print( "Total packets:", self.totalPacketsToSend, "\n" )
				self.currentPacketNumber = 0
				self.currentFilename = data
				self.state = RDTSender.STATE_WAIT_0
				self.isSending = True
				self.startTime = time.time()
			else:
				print( "File not found" )
		else:
			print( "Must enter a filename" )
	
		while self.isSending:
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
					totalTime = time.time() - self.startTime
					print( getISO(), "Total transmit time:", totalTime, "seconds" )
					print( "=== SEND FINISHED ===" )
					self.resetState() # this will set self.isSending to false, among other things