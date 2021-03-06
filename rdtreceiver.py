import socket
import threading
from time import sleep

from globals import *

from gui import display_image, create_window, read_image, update_fsm


class RDTReceiver:
	# if socket does not receive a packet after this interval,
	# the socket assumes the transmission is finished
	TIMEOUT = 3.0

	def __init__(self, host, port, show_window):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.bind((host, port))
		self.socket.settimeout(RDTReceiver.TIMEOUT)
		self.state = None  # doesn't really apply to this phase
		self.thread = threading.Thread(name="receive", target=self.receiveLoop)
		self.thread.daemon = True
		self.thread.start()
		self.isReceiving = False
		self.currentFilename = None
		self.dataPacketCorruptRate = 0
		self.ackPacketDropRate = 0
		self.expectedSeqNum = 0

		self.image_panel = None
		self.fsm_panel = None
		self.panel_root = None
		self.image_updated = False
		self.state_changed_to = ''

		self.max_width = 600
		self.max_height = 600

		if show_window:
			self.panel_root, self.image_panel, self.fsm_panel = create_window('receiver')
			self.state_changed_to = 'STATE_WAIT_0'

	def determineFileExtension(self, packet):
		if len(packet) < 4:
			return "FILE"

		keys = list(G_COMMON_FILE_BYTES)
		for i in range(len(G_COMMON_FILE_BYTES)):
			n = len(G_COMMON_FILE_BYTES[keys[i]])
			if packet[:n] == G_COMMON_FILE_BYTES[keys[i]]:
				return keys[i]

		return "txt"

	def appendToFile(self, data):
		file = open(self.currentFilename, 'ab')
		file.write(data)
		file.close()

		self.image_updated = True

	def makePacket(self, sequence, data):
		packet = bytearray()

		if type(data) == 'str':
			data = bytearray(data)

		chksum = checksum(sequence, data)
		chksum = chksum.to_bytes(2, byteorder=G_PACKET_CHECKSUM_BYTE_ORDER)

		packet.append(chksum[0])
		packet.append(chksum[1])
		packet.append(sequence)

		for i in range(len(data)):
			packet.append(data[i])

		return packet

	def update_image(self, force=False):
		if self.panel_root is None:
			return

		try:
			if self.state_changed_to != '':
				update_fsm(self.fsm_panel, self.state_changed_to)
				self.state_changed_to = ''

			if self.image_updated or force:

				# open cv can read corrupted files
				image = read_image(self.currentFilename)

				if image is not None:
					display_image(self.image_panel, image, self.max_width, self.max_height)

				self.image_updated = False

			self.panel_root.update()
		except Exception as ex:
			print(ex)

	def receiveLoop(self):
		while True:
			try:
				# wait to receive initial packet from sender
				data, address = self.socket.recvfrom(G_PACKET_MAXSIZE)

				packet = bytearray(data)
				corruptPacket(packet, self.dataPacketCorruptRate)
				info = getAssembledPacketInfo(packet)
				seqNum = info['seqnumInt']
				self.expectedSeqNum = 0

				if not self.expectedSeqNum == seqNum or isAssembledPacketCorrupt(info['seqnumBytes'], packet):
					# do nothing if it's a bad packet
					continue
				else:
					self.currentFilename = 'output_' + getISO()[:19].replace(':', '_') + '.'
					self.currentFilename += self.determineFileExtension(data[G_PACKET_DATASTART:])
					print(getISO(), "RECEIVER: Packet received, awaiting the rest of the transmission...")
					self.appendToFile(info['data'])
					self.expectedSeqNum += 1
					self.isReceiving = True
					if not randomTrueFromChance(self.ackPacketDropRate):
						self.socket.sendto(assemblePacket(info['seqnumInt'], b'ACK'), address)

				while self.isReceiving:
					data, address = self.socket.recvfrom(G_PACKET_MAXSIZE)

					packet = bytearray(data)
					corruptPacket(packet, self.dataPacketCorruptRate)

					info = getAssembledPacketInfo(data)
					seqNum = info['seqnumInt']
					if self.expectedSeqNum == seqNum and not isAssembledPacketCorrupt(info['seqnumBytes'], packet):
						self.appendToFile(info['data'])
						self.expectedSeqNum += 1
						if not randomTrueFromChance(self.ackPacketDropRate):
							self.socket.sendto(assemblePacket(info['seqnum'], b'ACK'), address)
					else:
						if G_LOSS_RECOVERY_ENABLED:
							# if it's not the expected seqnum, ACK the last correct seqnum
							if not seqNum == self.expectedSeqNum:
								if not randomTrueFromChance(self.ackPacketDropRate):
									self.socket.sendto(assemblePacket(self.expectedSeqNum-1, b'ACK'), address)

			except socket.timeout:
				if self.isReceiving:
					# print( "\n", getISO(), "RECEIVER: timed out, waiting for a new transmission; packets received:", self.expectedSeqNum )
					self.isReceiving = False
					self.expectedSeqNum = 0
					self.currentFilename = None
