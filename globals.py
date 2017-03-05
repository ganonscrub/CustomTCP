import time
import datetime
import random

G_PACKET_CHECKSUMBYTES = 2
G_PACKET_SEQUENCEBYTES = 1
G_PACKET_DATABYTES = 1021
G_PACKET_MAXSIZE = G_PACKET_CHECKSUMBYTES + G_PACKET_SEQUENCEBYTES + G_PACKET_DATABYTES
G_PACKET_DATASTART = G_PACKET_MAXSIZE - G_PACKET_DATABYTES

G_COMMON_FILE_BYTES = {}
G_COMMON_FILE_BYTES["bmp"] = b'\x42\x4d'
G_COMMON_FILE_BYTES["jpg"] = b'\xff\xd8'
G_COMMON_FILE_BYTES["png"] = b'\x89\x50\x4e\x47'

def checksum( sequence, bytes ):
	sum = sequence
	for i in range( len(bytes) ):
		sum += bytes[i]
	return sum % pow(2,16)
	
def getISO():
	return datetime.datetime.now().isoformat()

def corruptPacket( packet, chance ):	
	if random.randint( 1, 100 ) <= chance:
		packet[0] = 255