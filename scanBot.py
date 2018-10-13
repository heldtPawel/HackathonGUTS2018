#!/usr/bin/python

import json
import socket
import logging
import binascii
import struct
import argparse
import random
import math   #needed for math fns
import time


class ServerMessageTypes(object):
	TEST = 0
	CREATETANK = 1
	DESPAWNTANK = 2
	FIRE = 3
	TOGGLEFORWARD = 4
	TOGGLEREVERSE = 5
	TOGGLELEFT = 6
	TOGGLERIGHT = 7
	TOGGLETURRETLEFT = 8
	TOGGLETURRETRIGHT = 9
	TURNTURRETTOHEADING = 10
	TURNTOHEADING = 11
	MOVEFORWARDDISTANCE = 12
	MOVEBACKWARSDISTANCE = 13
	STOPALL = 14
	STOPTURN = 15
	STOPMOVE = 16
	STOPTURRET = 17
	OBJECTUPDATE = 18
	HEALTHPICKUP = 19
	AMMOPICKUP = 20
	SNITCHPICKUP = 21
	DESTROYED = 22
	ENTEREDGOAL = 23
	KILL = 24
	SNITCHAPPEARED = 25
	GAMETIMEUPDATE = 26
	HITDETECTED = 27
	SUCCESSFULLHIT = 28

	strings = {
		TEST: "TEST",
		CREATETANK: "CREATETANK",
		DESPAWNTANK: "DESPAWNTANK",
		FIRE: "FIRE",
		TOGGLEFORWARD: "TOGGLEFORWARD",
		TOGGLEREVERSE: "TOGGLEREVERSE",
		TOGGLELEFT: "TOGGLELEFT",
		TOGGLERIGHT: "TOGGLERIGHT",
		TOGGLETURRETLEFT: "TOGGLETURRETLEFT",
		TOGGLETURRETRIGHT: "TOGGLETURRENTRIGHT",
		TURNTURRETTOHEADING: "TURNTURRETTOHEADING",
		TURNTOHEADING: "TURNTOHEADING",
		MOVEFORWARDDISTANCE: "MOVEFORWARDDISTANCE",
		MOVEBACKWARSDISTANCE: "MOVEBACKWARDSDISTANCE",
		STOPALL: "STOPALL",
		STOPTURN: "STOPTURN",
		STOPMOVE: "STOPMOVE",
		STOPTURRET: "STOPTURRET",
		OBJECTUPDATE: "OBJECTUPDATE",
		HEALTHPICKUP: "HEALTHPICKUP",
		AMMOPICKUP: "AMMOPICKUP",
		SNITCHPICKUP: "SNITCHPICKUP",
		DESTROYED: "DESTROYED",
		ENTEREDGOAL: "ENTEREDGOAL",
		KILL: "KILL",
		SNITCHAPPEARED: "SNITCHAPPEARED",
		GAMETIMEUPDATE: "GAMETIMEUPDATE",
		HITDETECTED: "HITDETECTED",
		SUCCESSFULLHIT: "SUCCESSFULLHIT"
	}

	def toString(self, id):
		if id in self.strings.keys():
			return self.strings[id]
		else:
			return "??UNKNOWN??"


class ServerComms(object):
	'''
	TCP comms handler

	Server protocol is simple:

	* 1st byte is the message type - see ServerMessageTypes
	* 2nd byte is the length in bytes of the payload (so max 255 byte payload)
	* 3rd byte onwards is the payload encoded in JSON
	'''
	ServerSocket = None
	MessageTypes = ServerMessageTypes()


	def __init__(self, hostname, port):
		self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ServerSocket.connect((hostname, port))

	def readMessage(self):
		'''
		Read a message from the server
		'''
		messageTypeRaw = self.ServerSocket.recv(1)
		messageLenRaw = self.ServerSocket.recv(1)
		messageType = struct.unpack('>B', messageTypeRaw)[0]
		messageLen = struct.unpack('>B', messageLenRaw)[0]

		if messageLen == 0:
			messageData = bytearray()
			messagePayload = {'messageType': messageType}
		else:
			messageData = self.ServerSocket.recv(messageLen)
			logging.debug("*** {}".format(messageData))
			messagePayload = json.loads(messageData.decode('utf-8'))
			messagePayload['messageType'] = messageType

		logging.debug('Turned message {} into type {} payload {}'.format(
			binascii.hexlify(messageData),
			self.MessageTypes.toString(messageType),
			messagePayload))
		return messagePayload, messageType

	def sendMessage(self, messageType=None, messagePayload=None):
		'''
		Send a message to the server
		'''
		message = bytearray()


		if messageType is not None:
			message.append(messageType)
		else:
			message.append(0)

		if messagePayload is not None:
			messageString = json.dumps(messagePayload)
			message.append(len(messageString))
			message.extend(str.encode(messageString))

		else:
			message.append(0)

		logging.debug('Turned message type {} payload {} into {}'.format(
			self.MessageTypes.toString(messageType),
			messagePayload,
			binascii.hexlify(message)))
		return self.ServerSocket.send(message)

# Parse command line args
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
parser.add_argument('-H', '--hostname', default='127.0.0.1', help='Hostname to connect to')
parser.add_argument('-p', '--port', default=8052, type=int, help='Port to connect to')
parser.add_argument('-n', '--name', default='ScanBot', help='Name of bot')
args = parser.parse_args()

# Set up console logging
if args.debug:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)
else:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.INFO)

# Connect to game server
GameServer = ServerComms(args.hostname, args.port)

# Spawn our tank
logging.info("Creating tank with name '{}'".format(args.name))
GameServer.sendMessage(ServerMessageTypes.CREATETANK, {'Name': args.name})

#math and helper functions
def calculateDistance(ownX, ownY, otherX, otherY):
	headingX = otherX - ownX
	headingY = otherY - ownY
	return math.sqrt((headingX * headingX) + (headingY * headingY))


#fns to calculate how many degree there is need to rotate
def getHeading(x1, y1, x2, y2):
   	heading = math.atan2(y2 - y1, x2 - x1)
   	heading = radianToDegree(heading)
   	heading = (heading - 360) % 360
   	return math.fabs(heading)


def radianToDegree(angle):
	return angle * (180.0 / math.pi)


def isTurnLeft(currentHeading, desiredHeading):
	diff = desiredHeading - currentHeading
	if diff >= 0 and diff <= 180:
		return True
	else:
		return False

#definitions to invoke in main_loop
def start(message):
	return message['Id']

our_id = 0;
our_x = 0;
our_y = 0;
our_heading = 0;


def scan():
	#main output variable, initialize with primary keys which are types of objects
	#each type will have a dictionary for value where they store each object and in that dictionary,
	#the keys will be id and will be mapped to its attributes
	#the form is: scan_result = {type1: 	{id:{attr1:val, attr2:val},
											#id2:{attr1:val, attr2:val}},
								 #type2: 	{id3:{attr1:val, attr2:val},
											#id4:{attr1:val, attr2:val}}}
	scan_result = {}
	scan_result["Tank"] = {}
	scan_result["HealthPickup"] = {}
	scan_result["AmmoPickup"] = {}
	scan_result["Snitch"] = {}
	scan_result["Emergency"] = False
	current_heading = our_heading
	print(str(our_id) + " | "+str(our_x) + " | " + str(our_y))
	print("Start Head: "+str(current_heading))
	for i in range(18):
		message_in_function = GameServer.readMessage()
		if message_in_function is None:
			pass
		elif "Id" in message_in_function:
			id = message_in_function["Id"]
			if (id != our_id):
				type = message_in_function["Type"]
				x = message_in_function["X"]
				y = message_in_function["Y"]
				dist = calculateDistance(our_x,our_y,x,y)

				#for each t
				scan_result[type][id] = {"x":x,"y":y,"dist": dist}

				if type=="Tank":
					scan_result[type][id]["hp"] = message_in_function["Health"]
					if (dist <= 15):
						scan_result["Emergency"] = True
						break

		current_heading =(current_heading + 20) % 360
		GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING,{'Amount':current_heading})

	print("End Head: " + str(current_heading))
	print(scan_result)
	return scan_result



def got_shot():
	for i in range(1,3):
		GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': random.randint(210,330)})
		GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': random.randint(80,120)})

# Main loop - read game messages, ignore them and randomly perform actions
campPoints = [[0,100], [0,-100]]

i=0

while True:

	if GameServer.readMessage()[1]==18:
		message = GameServer.readMessage()[0]

	if GameServer.readMessage()[1]==27:
		got_shot()


	if i == 0:
		our_id = message['Id']

	if message is None:
		pass
	else:
		if 'Id' in message:
			if (message['Id'] == our_id):
				our_x = message['X']
				our_y = message['Y']
				our_heading = message['Heading']

				if (i % 20)==0:
					logging.info("scanning")
					scan()

	i+=1