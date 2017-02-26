PACKET_MAXSIZE = 1024 # 1 kilobyte per packet
PACKET_SIZEINFOBYTES = 4 # 2 16-bit integers for packetNum and totalPackets
PACKET_DATABYTES = PACKET_MAXSIZE - PACKET_SIZEINFOBYTES

RECEIVE_HOST = "localhost"
RECEIVE_PORT = 1337

SEND_HOST = "localhost"
SEND_PORT = 1337

SOCK_RECEIVE = None
SOCK_SEND = None

SOCK_RECEIVE_TIMEOUT = 10.0
SOCK_SEND_TIMEOUT = 1.0 # 1 second to be safe, could make this lower later

MAX_SEND_RETRIES = 10 # if at first you don't succeed, try again

# these will be used to detect incoming file types
COMMON_FILE_BYTES = {}
COMMON_FILE_BYTES["bmp"] = b'\x42\x4d'
COMMON_FILE_BYTES["jpg"] = b'\xff\xd8'
COMMON_FILE_BYTES["png"] = b'\x89\x50\x4e\x47'
#COMMON_FILE_BYTES["mp4"] = b'\x\x'

RECEIVE_FILENAME = "received."
RECEIVE_FILENAME_EXTENSION = "FILE"