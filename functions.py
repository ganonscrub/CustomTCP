import os
import sys
import socket
import threading

import random
import datetime

import time

from globals import *

def getISO():
	return datetime.datetime.now().isoformat()

def determineFileExtension( packet ):
	if len( packet ) < 4:
		return "FILE"
		
	keys = list(COMMON_FILE_BYTES)
	for i in range( len(COMMON_FILE_BYTES) ):
		n = len( COMMON_FILE_BYTES[keys[i]] )
		if packet[:n] == COMMON_FILE_BYTES[keys[i]]:
			return keys[i]
			
	return "txt"

# setup the sockets with the supplied command-line parameters
# a GUI can be used for the next phase so this isn't so painful for the user
def initSockets():
	if len(sys.argv) < 5:
		print( "Usage: monolith.py [recv_host] [recv_port] [send_host] [send_port]" )
		sys.exit()
	else:
		global SOCK_RECEIVE, SOCK_SEND, RECEIVE_HOST, RECEIVE_PORT, SEND_HOST
		global SEND_PORT, SOCK_RECEIVE_TIMEOUT, SOCK_SEND_TIMEOUT
	
		if sys.argv[1] != "0":
			RECEIVE_HOST = sys.argv[1]
		if sys.argv[2] != "0":
			RECEIVE_PORT = int(sys.argv[2])
		if sys.argv[3] != "0":
			SEND_HOST = sys.argv[3]
		if sys.argv[4] != "0":
			SEND_PORT = int(sys.argv[4])
			
		SOCK_RECEIVE = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		SOCK_RECEIVE.bind( (RECEIVE_HOST, RECEIVE_PORT) )
		SOCK_RECEIVE.settimeout( SOCK_RECEIVE_TIMEOUT )

		SOCK_SEND = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		SOCK_SEND.settimeout( SOCK_SEND_TIMEOUT )

def receivePackets():
	global SOCK_RECEIVE, PACKET_MAXSIZE, RECEIVE_FILENAME_EXTENSION

	# wait for intial packet
	# this will be a daemon thread, it's okay to use while True because
	# this thread will be terminated by the OS if the user causes a 
	# KeyboardInterrupt exception on the main thread
	while True:
		try:
			initData, initAddress = SOCK_RECEIVE.recvfrom( PACKET_MAXSIZE )
		except socket.timeout:
			continue			
		
		initPacketNum = initData[0] | (initData[1]<<8)
		packetsToExpect = initData[2] | (initData[3]<<8)
		
		packetNumsReceived = []
		for i in range( packetsToExpect + 1 ):
			packetNumsReceived.append( False )
		packetNumsReceived[initPacketNum] = initData[4:]
		#don't forget to ACK the initial packet!
		SOCK_RECEIVE.sendto( b'ACK' + initPacketNum.to_bytes(2,byteorder='little'), initAddress ) 

		print( getISO(), "Got initial packet, waiting for the rest!" )
		
		#once we have processed the initial packet, we can handle the rest
		restart = False
		while False in packetNumsReceived:
			try:
				data, address = SOCK_RECEIVE.recvfrom( PACKET_MAXSIZE )
			except socket.timeout:
				print( getISO(), "Receive socket timed out, I'll wait for a new transmission" )
				restart = True
				break
				
			packetNum = data[0] | (data[1]<<8)
			packetNumsReceived[packetNum] = data[4:]
			
			SOCK_RECEIVE.sendto( b'ACK' + packetNum.to_bytes(2,byteorder='little'), initAddress )
		
		if restart:
			continue
			
		RECEIVE_FILENAME_EXTENSION = determineFileExtension( packetNumsReceived[0] )
		
		fout = open( RECEIVE_FILENAME + RECEIVE_FILENAME_EXTENSION, "wb" )
		for p in range( len(packetNumsReceived) ):
			fout.write( packetNumsReceived[p] )
		fout.close()
		RECEIVE_FILENAME_EXTENSION = "FILE"
		print( getISO(), "Got all the packets!" )

# this function gets PACKET_DATABYTES number of bytes from the given
# filename at nPacket position offset from the file's beginning.
# since we are loading PACKET_DATABYTES bytes at a time, large files
# can still be sent without having to load all of the contents into memory
# TODO: implement similar behavior for handlePackets
def getFileBytes( filename, nPacket ):
	global PACKET_DATABYTES

	try:
		fin = open( filename, "rb" )
	except:
		print( "Error opening file" )
		return b''
	
	startPos = PACKET_DATABYTES * nPacket
	fin.seek( startPos, 0 )
	output = fin.read( PACKET_DATABYTES )
	return output

def getFileSize( filename ):
	try:
		fin = open( filename, "rb" )
	except:
		print( "Error opening file" )
		return -1
		
	fin.seek( 0, 2 )
	size = fin.tell()
	fin.close()
	
	return size
	
def sendPackets():
	global SOCK_SEND, SEND_HOST, SEND_PORT
	
	while True:
		print( "Enter the message to send:" )
		message = input()
		
		isFile = False
		
		# naively detect if the message is a filename
		# use commas/semicolons in string messages if you want multiple sentences
		if message.find( "." ) != -1:
			isFile = True
		
		if isFile:
			messageLength = getFileSize( message )
			print( "File length is", messageLength )
		else:
			messageLength = len(message)
			print( "Message length is", messageLength )
		
		# don't bother sending an empty message
		if messageLength > 0:
			numPackets = int( messageLength / PACKET_DATABYTES ) + 1
		else:
			continue
			
		print( "Packets needed:", numPackets )
		
		# for testing packets arriving out of order
		randomizePacketOrder = True
		
		if randomizePacketOrder:
			randomArray = []
			for i in range( numPackets ):
				randomArray.append( i )
			random.shuffle( randomArray )
		
		print( getISO(), "Beginning packets transmission..." )
		
		# this is for reporting progress to the user
		targetNum = 20
		numParts = numPackets if numPackets < targetNum else targetNum
		partSize = int(numPackets / numParts)
		pieces = {}
		for i in range( numParts - 1 ):
			pieces[partSize*(i+1)] = int( 100 / numParts ) * ( i + 1 )
		
		for p in range( numPackets ):
			
			try:
				print( getISO(), pieces[p], "percent transmitted" )
			except KeyError:
				pass
			except OverflowError:
				print( "Number was too big to print?" )
		
			curPacket = bytearray()
			
			if randomizePacketOrder:
				currentPacketNum = randomArray[p].to_bytes(2,byteorder='little')
			else:
				currentPacketNum = p.to_bytes(2,byteorder='little')
			
			totalPacketNum = (numPackets-1).to_bytes(2,byteorder='little')
			
			# here is where the packet is constructed as a bytearray			
			# prepend the bytes for packet num and total num of packets
			curPacket.append( currentPacketNum[0] )
			curPacket.append( currentPacketNum[1] )
			curPacket.append( totalPacketNum[0] )
			curPacket.append( totalPacketNum[1] )
			
			if isFile:			
				if randomizePacketOrder:
					packetBytes = getFileBytes( message, randomArray[p] )
				else:
					packetBytes = getFileBytes( message, p )
					
				for b in range( len(packetBytes) ):
					curPacket.append( packetBytes[b] )			
			else:
				start = p * PACKET_DATABYTES
				end = p * PACKET_DATABYTES + PACKET_DATABYTES - 1
				if ( messageLength < end ):
					end = messageLength
					
				for i in range( start, end ):
					curPacket.append( ord(message[i]) )	
			
			if tryPacketUntilSuccess( curPacket, MAX_SEND_RETRIES ) == False:
				print( getISO(), "Couldn't send a packet, cancelling transmission..." )
				break
				
		print( getISO(), "Transmission done" )
				
def tryPacketUntilSuccess( packet, max ):
	success = False
	while not success and max > 0:
		SOCK_SEND.sendto( packet, (SEND_HOST, SEND_PORT) )
		try:
			data, address = SOCK_SEND.recvfrom( 32 )
		except socket.timeout:
			print( getISO(), "Fail#", MAX_SEND_RETRIES - max + 1, "retrying send..." )
			max -= 1
			if max == 0:
				return success
			continue
		#print( "Response:", data )
		success = True
		
	return success

def corruptPacket( packet, chance ):	
	if random.randint( 1, 100 ) <= chance:
		packet[0] = 255
	
def sendLoop():
	global SOCK_SEND, SEND_HOST, SEND_PORT, SENDER_STATE, SENDER_CORRUPT_RATE
	
	curPacket = 0
	numPackets = 0
	message = None
	isFile = False
	fileSize = 0

	startTime = None
	endTime = None
	
	while True:				
		if SENDER_STATE == SEND_STATE_WAIT0:			
			if numPackets == 0: # prompt for something to send							
				print( getISO(), "SENDER: WAIT0 for input..." )
				message = input( "Enter path of file to send: ")
				
				startTime = time.time()
				
				data = None
				
				if message[-4] == '.':
					if os.path.isfile( message ):						
						isFile = True
						fileSize = getFileSize( message )
						numPackets = int( (fileSize / PACKET_DATABYTES) + 1 )
						print( getISO(), "SENDER: isFile", isFile, "fileSize:", fileSize, "numPackets:", numPackets )
						data = getFileBytes( message, curPacket )
					else:
						print( "Given filename does not exist" )
						continue
					
				else: # continue sending remaining packets
					data = bytearray( message.encode() )
					numPackets = int( len(data) / PACKET_DATABYTES ) + 1
				
				packet = make_packet( checksum( 0, data ), 0, data )
				
				SOCK_SEND.sendto( packet, (SEND_HOST, SEND_PORT) )
				SENDER_STATE = SEND_STATE_WAITACK0
			elif curPacket == numPackets:
					curPacket = 0
					numPackets = 0
					message = None
					isFile = False
					fileSize = 0
					SENDER_STATE = SEND_STATE_WAIT0
					endTime = time.time()
					print( "Total time:", endTime - startTime )
			else:
				if isFile:
					data = getFileBytes( message, curPacket )
					packet = make_packet( checksum( 0, data ), 0, data )
					
					SOCK_SEND.sendto( packet, (SEND_HOST, SEND_PORT) )
					SENDER_STATE = SEND_STATE_WAITACK0
					if curPacket % 100 == 0:
						print( getISO(), int(((100 * curPacket / 100) / numPackets)*100), "percent of packets sent" )
				
		elif SENDER_STATE == SEND_STATE_WAIT1:		
			if numPackets == 0: # prompt for something to send
				print( getISO(), "SENDER: Something went horribly wrong" )
			elif curPacket == numPackets:
					curPacket = 0
					numPackets = 0
					message = None
					isFile = False
					fileSize = 0
					SENDER_STATE = SEND_STATE_WAIT0
					endTime = time.time()
					print( "Total time:", endTime - startTime )
			else:
				if isFile:
					data = getFileBytes( message, curPacket )
					packet = make_packet( checksum( 1, data ), 1, data )
					SOCK_SEND.sendto( packet, (SEND_HOST, SEND_PORT) )
					SENDER_STATE = SEND_STATE_WAITACK1
					if curPacket % 100 == 0:
						print( getISO(), int(((100 * curPacket / 100) / numPackets)*100), "percent of packets sent" )
			
		elif SENDER_STATE == SEND_STATE_WAITACK0:
			#print( getISO(), "SENDER: Waiting for ACK 0" )
			try:
				data, address = SOCK_SEND.recvfrom( 32 )
				
				packet = bytearray( data )
				corruptPacket( packet, SENDER_CORRUPT_RATE )
				
				if packet == b'ACK0':
					#print( getISO(), "SENDER: ACK 0 Success" )
					curPacket += 1
					SENDER_STATE = SEND_STATE_WAIT1
				else:
					#print( getISO(), "SENDER: ACK 0 Failure, resending..." )
					SENDER_STATE = SEND_STATE_WAIT0					
			except socket.timeout:
				print( getISO(), "SENDER: timeout" );
			
		elif SENDER_STATE == SEND_STATE_WAITACK1:
			#print( getISO(), "SENDER: Waiting for ACK 1" )
			try:
				data, address = SOCK_SEND.recvfrom( 32 )
				
				packet = bytearray( data )
				corruptPacket( packet, SENDER_CORRUPT_RATE )
				
				if packet == b'ACK1':
					#print( getISO(), "SENDER: ACK 1 Success" )
					curPacket += 1
					SENDER_STATE = SEND_STATE_WAIT0
				else:
					#print( getISO(), "SENDER: ACK 1 Failure, resending..." )
					SENDER_STATE = SEND_STATE_WAIT1					
			except socket.timeout:
				print( getISO(), "SENDER: timeout" );
			
def receiveLoop():
	global SOCK_RECEIVE, PACKET_MAXSIZE, RECEIVER_STATE, RECEIVER_CORRUPT_RATE

	FILE_NAME = None
	FILE_EXTENSION = None
	updateFilename = True
	packetsReceived = 0
	
	while True:
		try:				
			if RECEIVER_STATE == RECEIVE_STATE_WAIT0:			
				data, address = SOCK_RECEIVE.recvfrom( PACKET_MAXSIZE )
				
				packet = bytearray( data )
				corruptPacket( packet, RECEIVER_CORRUPT_RATE )
				
				packetSum = packet[0] | (packet[1] << 8)
				chksum = checksum( packet[2], packet[3:] )
				
				if packet[2] == 0 and packetSum == chksum: # sequence number is byte at position 2
					#print( getISO(), "RECEIVER: Got 0" )
					
					if updateFilename:
						FILE_NAME = 'output_' + getISO()[:19].replace(':','_') + '.'
						FILE_EXTENSION = determineFileExtension( packet[3:] )
						FILE_NAME = FILE_NAME + FILE_EXTENSION
						updateFilename = False
					
					file = open( FILE_NAME, 'ab' )
					packet = packet[3:]					
					file.write( packet )
					file.close()
					
					SOCK_RECEIVE.sendto( b'ACK0', address )
					RECEIVER_STATE = RECEIVE_STATE_WAIT1
					packetsReceived += 1
				else:
					#print( getISO(), "RECEIVER: Got 1 when expecting 0" )
					SOCK_RECEIVE.sendto( b'ACK1', address )
				
			elif RECEIVER_STATE == RECEIVE_STATE_WAIT1:
				data, address = SOCK_RECEIVE.recvfrom( PACKET_MAXSIZE )
				
				packet = bytearray( data )
				corruptPacket( packet, RECEIVER_CORRUPT_RATE )
				
				packetSum = packet[0] | (packet[1] << 8)
				chksum = checksum( packet[2], packet[3:] )
				
				if packet[2] == 1 and packetSum == chksum: # sequence number is byte at position 2
					#print( getISO(), "RECEIVER: Got 1" )					
					
					file = open( FILE_NAME, 'ab' )
					packet = packet[3:]
					file.write( packet )
					file.close()
					
					SOCK_RECEIVE.sendto( b'ACK1', address )
					RECEIVER_STATE = RECEIVE_STATE_WAIT0
					packetsReceived += 1
				else:
					#print( getISO(), "RECEIVER: Corrupt packet" )
					SOCK_RECEIVE.sendto( b'ACK0', address )
		except socket.timeout:
			RECEIVER_STATE = RECEIVE_STATE_WAIT0
			updateFilename = True
				
def checksum( sequence, bytes ):
	sum = sequence
	for i in range( len(bytes) ):
		sum += bytes[i]
	return sum % pow(2,16)
	
def make_packet( checksum, sequence, data ):
	packet = bytearray()
	
	checksum = checksum.to_bytes(2,byteorder='little')
	
	packet.append( checksum[0] )
	packet.append( checksum[1] )
	
	packet.append( sequence )
	
	# handle data being string instead of bytes
	for i in range( len(data) ):
		if type(data) == str:
			packet.append( ord(data[i]) )
		else:
			packet.append( data[i] )
	
	return packet

def rdt_send( data ):
	checksum = chksum( data )
	packet = make_packet( 0, data, checksum )
	SOCK_SEND.sendto( packet, (SEND_HOST, SEND_PORT) )
	try:
		data, address = SOCK_SEND.recvfrom( 32 )
	except socket.timeout:
		print( getISO(), "Socket timed out waiting to receive a response" )