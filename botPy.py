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
			messagePayload = None
		else:
			messageData = self.ServerSocket.recv(messageLen)
			logging.debug("*** {}".format(messageData))
			messagePayload = json.loads(messageData.decode('utf-8'))

		logging.debug('Turned message {} into type {} payload {}'.format(
			binascii.hexlify(messageData),
			self.MessageTypes.toString(messageType),
			messagePayload))
		return messagePayload

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
parser.add_argument('-n', '--name', default='RandomBot', help='Name of bot')
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
#aiming functions
def aimAngle(message, aimHeading):

	GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount': 360 - aimHeading})

def fireCoord(message, x, y, Tx, Ty):
	print("THis should print")
	aimHeading = getHeading(x, y, Tx, Ty)
	if (abs(message['TurretHeading'] - aimHeading) < 10.0):
		logging.info("Firing")
		GameServer.sendMessage(ServerMessageTypes.FIRE)
	else:
		aimAngle(message, aimHeading)

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


#definitions to invoke in main_loop
def start(message):
	return message['Id']


def goToCampPoints(x, y, campPoints):
	#firstPart iterates over save points and look for the closest one
	closestDist = 0
	iPoint = 0
	for point in campPoints:
		distance = calculateDistance(x, y, point[0], point[1])
		if iPoint == 0 or distance < closestDist:
			closestDist = distance
			closestPoint = point
		iPoint += 1

	#second part sets tank on the right course
	electedHeading = getHeading(x, y, closestPoint[0], closestPoint[1])

	logging.info("Turning towards destination")
	GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': 360 - electedHeading})
	time.sleep(3)

	#third part moves tank to that points

	logging.info("Moving to point")
	GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': closestDist})

	#fourth part sets tank on the course to goal
	 #tba


def updatePos():
	x = message['X']
	y = message['Y']
	our_heading = message['Heading']

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
	print(str(id) + " | "+str(x) + " | " + str(y))
	print("Start Head: "+str(current_heading))
	for i in range(18):
		message_in_function = message
		if message_in_function is None:
			pass
		elif "Id" in message_in_function:
			t_id = message_in_function["Id"]
			if (t_id != id):
				type = message_in_function["Type"]
				t_x = message_in_function["X"]
				t_y = message_in_function["Y"]
				dist = calculateDistance(our_x,our_y,x,y)

				#for each t
				scan_result[type][t_id] = {"x":t_x,"y":t_y,"dist": dist}

				if type=="Tank":
					scan_result[type][t_id]["hp"] = message_in_function["Health"]
					if (dist <= 15):
						scan_result["Emergency"] = True
						break

		current_heading =(current_heading + 20) % 360
		GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING,{'Amount':current_heading})

	print("End Head: " + str(current_heading))
	return scan_result

# Main loop
gameStart = True
gameLoaded = False
campPoints = [[15,90]]#[[0,100], [0,-100]]
message = {}
i = 0
x = 0
y = 0
Tx = random.randint(-70,70)
Ty = random.randint(-100,100)
our_heading = 0
has_target = False
Target = {}
while True:
	#lines till except continue guarantee robust start
	message = GameServer.readMessage()
	print(message)

	if message != {} and gameStart:
		id = start(message)
		gameStart = False
		print("firstMessageRecieved")


	try:
		if gameLoaded == False and message["Id"] == id and message['X'] != 0:
			updatePos()
			gameLoad = True
			print("gameLoaded")
		else:
			continue
	except:
		print("waiting for data")
		continue

	if message['Id'] == id:
		updatePos()


	if has_target:
		fireCoord(message, Ty, Ty, x, y)
	else:
		scan_result = scan()
		if scan_result["Tank"] != {}:
			for tank in scan_result["Tank"]:
				print(tank)

	time.sleep(0.01)
	print("ye")
	#here we should start applying multithreading
	print(str(x) + " <- x, y -> " + str(y))
	goToCampPoints(x,y,campPoints)


	i += 1
	if i > 10:
		i = 0

'''
randX = random.randint(-70,70)
randY = random.randint(-100,100)
i = 0
message = GameServer.readMessage()
Tx = 0
Ty = 0
our_id = 0
target_x = 0
target_y = 0
while True:
	#print("---")
	message = GameServer.readMessage()
	#GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount': i})
	if message['Id'] == id:
		updatePos()
	else:

	fireCoord(message,0,0, Tx, Ty)
	if i == 14:
		randX = random.randint(-70, 70)
		randY = random.randint(-100, 100)
	i = i + 10
	if i > 359:
		i = 0
"""
gameStart = True
campPoints = [[15,90]]#[[0,100], [0,-100]]
message = {}
i = 0
while True:
	message = GameServer.readMessage()
	print("here")



	if message != {} and gameStart:
		id = start(message)
		messageTemp = message
#		print(messageTemp)
		gameStart = False



#	GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': 90})
	#print(message)

#	if id not in message and message["Type"] == "Tank":
#		print(getHeading(messageTemp['X'], messageTemp['Y'], message['X'], message['Y']))
#		print("above get heading result")


	#id = start(message)

	#goToCampPoints(messageTemp, campPoints)

	#time.sleep(1000)



	#
	#if i == 5:
		#if random.randint(0, 10) > 5:
			#pass
			#logging.info("Firing")
			#GameServer.sendMessage(ServerMessageTypes.FIRE)
	#elif i == 10:
		#logging.info("Turning randomly")
		#GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': random.randint(0, 359)})
	#elif i == 15:
	#	logging.info("Moving randomly")
	#	GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': random.randint(0, 10)})
'''
