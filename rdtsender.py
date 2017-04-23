import os
import socket

from globals import *

from gui import display_image, create_window, read_image, update_fsm


class RDTSender:
	STATE_SEND_WAIT = 1000
	STATE_SEND_PACKETS = 1001
	STATE_ACK_WAIT = 1002

	TIMEOUT = 0.03  # 30 milliseconds

	def __init__(self, host, port, show_window):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.settimeout(RDTSender.TIMEOUT)
		# self.socket.setblocking( False )
		self.sendHost = host
		self.sendPort = port
		self.state = RDTSender.STATE_SEND_WAIT
		self.doneSending = False
		self.isSending = False
		self.currentFilename = None
		self.totalPacketsToSend = 0
		self.startTime = None
		self.ackPacketCorruptRate = 0
		self.dataPacketDropRate = 0
		self.window = []
		self.windowSize = 5
		self.base = 0
		self.nextSeqNum = self.base + self.windowSize

		self.image_panel = None
		self.fsm_panel = None
		self.panel_root = None
		self.image_updated = False
		self.state_changed_to = ''

		self.max_width = 600
		self.max_height = 600

		if show_window:
			self.panel_root, self.image_panel, self.fsm_panel = create_window('sender')
			self.state_changed_to = 'STATE_WAIT'

	def printProgress(self):
		if self.totalPacketsToSend > 0:
			if self.base % 100 == 0:
				ratio = int((self.base / self.totalPacketsToSend) * 100)
				print(getISO(), "SENDER:", ratio, "percent of packets transmitted and ACK'd")

	def getFileBytes(self, filename, nPacket):
		try:
			fin = open(filename, "rb")
		except:
			print("Error opening file")
			return b''

		startPos = G_PACKET_DATABYTES * nPacket
		fin.seek(startPos, 0)
		output = fin.read(G_PACKET_DATABYTES)
		return output

	def getFileSize(self, filename):
		try:
			fin = open(filename, "rb")
		except:
			print("Error opening file")
			return -1

		fin.seek(0, 2)
		size = fin.tell()
		fin.close()

		return size

	def resetState(self):
		self.socket.settimeout(RDTSender.TIMEOUT)

		self.state = RDTSender.STATE_SEND_WAIT
		self.state_changed_to = 'STATE_WAIT'

		self.isSending = False
		self.currentFilename = None
		self.totalPacketsToSend = 0
		self.currentPacketNumber = 0
		self.buffer = []
		self.windowSize = 5
		self.base = 0
		self.nextSeqNum = self.base + self.windowSize

	def makePacket(self, sequence, data):
		packet = bytearray()

		chksum = checksum(sequence, data)
		chksum = chksum.to_bytes(2, byteorder=G_PACKET_CHECKSUM_BYTE_ORDER)

		packet.append(chksum[0])
		packet.append(chksum[1])
		packet.append(sequence)

		for i in range(len(data)):
			if type(data) == 'str':
				packet.append(ord(data[i]))
			else:
				packet.append(data[i])

		return packet

	def sendToRemote(self, packet):
		self.socket.sendto(packet, (self.sendHost, self.sendPort))

	def handleStateSendWait(self):
		success = False

		while not success:
			filename = input("Type filename: ")
			if filename[-4] == '.':
				if os.path.isfile(filename):
					size = self.getFileSize(filename)
					self.totalPacketsToSend = int(size / G_PACKET_DATABYTES) + 1
					print("Total packets:", self.totalPacketsToSend)
					self.currentPacketNumber = 0
					self.currentFilename = filename
					self.state = RDTSender.STATE_SEND_PACKETS
					self.state_changed_to = 'STATE_SEND_PACKETS'
					self.isSending = True
					success = True

					self.buffer = []
					self.base = 0
					# populate the send buffer with all the packets that will be sent
					for i in range(self.totalPacketsToSend):
						fileData = self.getFileBytes(self.currentFilename, i)
						self.buffer.append(assemblePacket(i, fileData))

					self.startTime = time.time()
				else:
					print("File not found")
			else:
				print("Must enter a filename")

	def handleStateSendPackets(self):
		for i in range(self.windowSize):
			# randomly drop packets according to drop rate variable
			if not randomTrueFromChance(self.dataPacketDropRate):
				# don't attempt to send more packets than there are to send
				if self.base + i < self.totalPacketsToSend:
					self.sendToRemote(self.buffer[self.base+i])

		self.state = RDTSender.STATE_ACK_WAIT
		self.state_changed_to = 'STATE_ACK_WAIT'

	def handleStateAckWait(self, callback=None):
		try:
			while True:  # keep listening for packets
				data, address = self.socket.recvfrom(G_PACKET_ACK_MAXSIZE)

				self.update_image()
				if callback is not None:
					callback()

				packet = bytearray(data)
				corruptPacket(packet, self.ackPacketCorruptRate)
				info = getAssembledPacketInfo(packet)
				seqNum = info['seqnumInt']
				
				# if the ACK has already been received, ignore it
				if seqNum < self.base or isAssembledPacketCorrupt(info['seqnumBytes'], packet):
					continue
				else:
					self.base = seqNum + 1

					if self.base > self.totalPacketsToSend - 1:
						self.isSending = False
						return

					# send the newest packet in the window
					if self.base + self.windowSize - 1 < self.totalPacketsToSend:
						newPacket = self.buffer[self.base + self.windowSize - 1]

						if not randomTrueFromChance(self.dataPacketDropRate):
							self.sendToRemote(newPacket)
							# self.printProgress()

		except socket.timeout:
			if G_LOSS_RECOVERY_ENABLED:
				self.state = RDTSender.STATE_SEND_PACKETS
				self.state_changed_to = 'STATE_SEND_PACKETS'

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

	def sendLoop(self, callback):
		self.handleStateSendWait()

		while self.isSending:
			if self.state == RDTSender.STATE_SEND_PACKETS:
				self.handleStateSendPackets()
			elif self.state == RDTSender.STATE_ACK_WAIT:
				self.handleStateAckWait(callback)

		totalTime = time.time() - self.startTime
		print(getISO(), "Total transmit time:", totalTime, "seconds")
		print("=== SEND FINISHED ===")
		self.resetState()

		self.update_image(True)
		if callback is not None:
			callback(True)
