import time
import datetime
import random

G_PACKET_CHECKSUMBYTES = 2
G_PACKET_SEQUENCEBYTES = 4
G_PACKET_DATABYTES = 1018
G_PACKET_MAXSIZE = G_PACKET_CHECKSUMBYTES + G_PACKET_SEQUENCEBYTES + G_PACKET_DATABYTES
G_PACKET_DATASTART = G_PACKET_MAXSIZE - G_PACKET_DATABYTES

G_PACKET_ACK_CHECKSUMBYTES = 2
G_PACKET_ACK_SEQUENCEBYTES = 4
G_PACKET_ACK_DATABYTES = len( b'ACK' )
G_PACKET_ACK_MAXSIZE = G_PACKET_ACK_CHECKSUMBYTES + G_PACKET_ACK_SEQUENCEBYTES + G_PACKET_ACK_DATABYTES

# these two should probably be the same but don't have to
G_PACKET_CHECKSUM_BYTE_ORDER = 'big'
G_PACKET_SEQNUM_BYTE_ORDER = 'big'

G_COMMON_FILE_BYTES = {}
G_COMMON_FILE_BYTES["bmp"] = b'\x42\x4d'
G_COMMON_FILE_BYTES["jpg"] = b'\xff\xd8'
G_COMMON_FILE_BYTES["png"] = b'\x89\x50\x4e\x47'

G_SENDER_WINDOW_SIZE = 5

# custom checksum function so we aren't just copying the algorithm from RFC 793
def checksum( sequence, bytes ):
	sum = 0
	sum = sequence
	for i in range( len(bytes) ):
		sum += bytes[i]
	return sum % pow(2,16)
	
def checksumArr( seqNum, bytes ):
	sum = 0
	for i in range( len(seqNum) ):
		sum += seqNum[i]
	for i in range( len(bytes) ):
		sum += bytes[i]
	return sum % pow(2,16)
	
def getISO():
	return datetime.datetime.now().isoformat()

def corruptPacket( packet, chance ):	
	if random.randint( 1, 100 ) <= chance:
		packet[0] = 255
		
def randomTrueFromChance( chance ): # used for dropping packets
	if random.randint( 1, 100 ) <= chance:
		return True
	else:
		return False
		
def isPacketCorrupt( sequence, packet ):			
	chksum = checksum( sequence, packet[G_PACKET_DATASTART:] )
	packetSum = packet[0] | (packet[1]<<8)
	if chksum == packetSum:
		return False
	else:
		return True

def isAssembledPacketCorrupt( seqNum, packet ):
	chksum = checksumArr( seqNum, packet[G_PACKET_DATASTART:] )
	packetSum = int.from_bytes( packet[:2], byteorder=G_PACKET_CHECKSUM_BYTE_ORDER )
	if not chksum == packetSum or packet == b'':
		return True
	else:
		return False
			
def assemblePacket( seqNum, data ):
	if type( seqNum ) == int:
		seqNum = seqNum.to_bytes(4, byteorder=G_PACKET_SEQNUM_BYTE_ORDER)
	elif type( seqNum ) == bytes:
		pass # we want seqNum to be a bytes array
	else:
		print( "Unhandled type for seqNum:", type(seqNum) )
		return b''
	
	packet = bytearray()
		
	if type(data) == 'str':
		data = bytearray(data)
	
	chksum = checksumArr( seqNum, data )
	chksum = chksum.to_bytes(2,byteorder=G_PACKET_CHECKSUM_BYTE_ORDER)
	
	packet.append( chksum[0] )
	packet.append( chksum[1] )
	
	for i in range( len( seqNum ) ):
		packet.append( seqNum[i] )
	
	for i in range( len(data) ):
		packet.append( data[i] )
	
	return packet
	
def getAssembledPacketInfo( packet ):
	dict = {}
	dict['checksum'] = packet[:2]
	dict['seqnum'] = packet[2:6]
	dict['seqnumBytes'] = dict['seqnum']
	dict['seqnumInt'] = int.from_bytes( dict['seqnum'], byteorder=G_PACKET_SEQNUM_BYTE_ORDER )
	dict['data'] = packet[G_PACKET_DATASTART:]
	return dict