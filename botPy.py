#!/usr/bin/python

import json
import socket
import logging
import binascii
import struct
import argparse
import random
import math   #needed for math fns


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

        if isTurnLeft(message['TurretHeading'], aimHeading):
                logging.info("Turning turret  left")
                GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount': aimHeading})
        else:
                logging.info("Turning turret right")
                GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount': aimHeading})

def fireCoord(message,x,y):
    tankX = message['X']
    tankY = message['Y']
    aimHeading = getHeading(tankX, tankY, x, y)
    if (abs(message['Heading'] - aimHeading) < 10.0):
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


def isTurnLeft(currentHeading, desiredHeading):
	diff = desiredHeading - currentHeading
	if diff >= 0 and diff <= 180:
		return True
	else:
		return False


#definitions to invoke in main_loop
def start(message):
	return message['Id']


def goToCampPoints(message, campPoints):
	x = message['X']
	y = message['Y']
	#firstPart iterates over save points and look for the closest one
	closestDist = 0
	iPoint = 0
	for point in campPoints:
		print(point)
		distance = calculateDistance(x, y, point[0], point[1])
		if iPoint == 0 or distance < closestDist:
			closestDist = distance
			closestPoint = point
		iPoint += 1
	#print(closestPoint)#+" distance is " + str(closestDist))
	#second part sets tank on the right course
	electedHeading = getHeading(x, y, closestPoint[0], closestPoint[1])

	if isTurnLeft(message['Heading'], electedHeading):
		logging.info("Turning left")
		GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': message['Heading'] - electedHeading})
	else:
		logging.info("Turning right")
		GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': electedHeading - message['Heading']})

	#third part moves tank to that points
	logging.info("Moving to point")
	GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': -closestDist})

	#fourth part sets tank on the course to goal
	 #tba





# Main loop - read game messages, ignore them and randomly perform actions
randX = random.randint(0,70)
randY = random.randint(0,100)
i = 0
while True:
	message = GameServer.readMessage()
	#print(message)
	print(str(randX) + str(randY))
	fireCoord(message,randX,randY)
	if i == 99:
		randX = random.randint(0, 70)
		randY = random.randint(0, 100)
	elif i == 10:
		logging.info("Turning randomly")
		GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': random.randint(0, 359)})
	elif i == 15:
		logging.info("Moving randomly")
		GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': random.randint(0, 10)})
	i = i + 1
	if i > 100:
		i = 0
"""
gameStart = True
campPoints = [[0,100], [0,-100]]
message = {}
i = 0
while True:
	message = GameServer.readMessage()
	print("here")
	

	
	if message != {} and gameStart:
		#print("here")
		id = start(message)
		goToCampPoints(message, campPoints)
		gameStart = False
	#print("\nllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllll\n")
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
"""