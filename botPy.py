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
import threading



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

def find_Shoot(has_target, target):
	if has_target:
		fireCoord(messageServer, target['X'], target['Y'], x, y)
		if 'Id' in messageServer and messageServer['Id'] == target['Id']:
			target = messageServer
	# if target
	else:
		scan_result = scan()
		if scan_result["Tank"] != {}:
			print("detectank")
			has_target = True
			low_hp = 6
			low_dist = 200
			for tank in scan_result["Tank"]:
				if tank['hp'] < low_hp:
					low_hp = tank['hp']
					target = tank
				elif tank['hp'] == low_hp:
					if tank['dist'] < low_dist:
						low_dist = tank['dist']
						target = tank
		else:
			has_target = False

	return has_target, target
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
def goToForLists(x, y, places):
	#firstPart iterates over save points and look for the closest one

	closestDist = 0
	iPoint = 0
	for point in places:
		distance = calculateDistance(x, y, point[0], point[1])
		if iPoint == 0 or distance < closestDist:
			closestDist = distance
			closestPoint = point
		iPoint += 1

	#zigzagging towards destination

	print(point)
	i = 0

	while (math.fabs(point[0] - x) > 2 and math.fabs(point[1] - y) > 2):
		if (math.fabs(point[0] - x) < 25 or math.fabs(point[1] - y) < 25):
			electedHeading = getHeading(x, y, closestPoint[0], closestPoint[1])
			distance = calculateDistance(x, y, closestPoint[0], closestPoint[1])
			GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': 360 - electedHeading})
			time.sleep(2)
			GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': distance})
			break

		electedHeading = getHeading(x, y, closestPoint[0], closestPoint[1])
		logging.info("Turning towards destination (with zigzag)")
		if i%2 == 0:
			GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': 360 - electedHeading - 45})
		else:
			GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': 360 - electedHeading + 45})
		logging.info("Moving to point")
		GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': 20})
		time.sleep(2.25)

		x = messageServer['X']
		y = messageServer['Y']

		i+=1

'''
def updatePos():
	x = message['X']
	y = message['Y']
	our_heading = message['Heading']
'''

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
	print(messageServer)
	initial_turret_head = messageServer['TurretHeading']
	current_turret_heading = initial_turret_head
	print("Start Head: "+str(current_turret_heading))
	message_in_function = None
	turn = True
	while (turn):
		if serverResponse[1] == 18:
			message_in_function = serverResponse[0]

		if message_in_function is None:
			continue
		elif "Id" in message_in_function:
			t_id = message_in_function["Id"]
			if (t_id != idTank):
				category = message_in_function["Type"]
				t_x = message_in_function["X"]
				t_y = message_in_function["Y"]
				dist = calculateDistance(messageServer['X'],messageServer['Y'],t_x,t_y)
				#for each t
				scan_result[category][t_id] = {"x":t_x,"y":t_y,"dist": dist}
				if category=="Tank":
					scan_result[category][t_id]["hp"] = message_in_function["Health"]
					if (dist <= 15):
						scan_result["Emergency"] = True
						break
		current_turret_heading =(current_turret_heading + 5) % 360
		GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING,{'Amount':current_turret_heading})
		time.sleep(0.05)
		if (math.fabs(current_turret_heading-initial_turret_head) < 1):
			turn = False

	print("End Head: " + str(current_turret_heading))
	return scan_result


def got_shot():
	for i in range(1,3):
		GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': random.randint(210,330)})
		#GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': random.randint(80,120)})


#getting our tank id
messageTemp = GameServer.readMessage()
if messageTemp[1] == 18:
	global idTank
	idTank = messageTemp[0]['Id']
	print(str(idTank)+" idtank")


def readServer():
	global messageServer
	global serverResponse
	while True:
		try:
			serverResponse = GameServer.readMessage()
			if serverResponse[0]['Id'] == idTank:
				messageServer = serverResponse[0]
		except:
			continue


def main():
	iMain = 15
	while True:
		#time.sleep(100)
		if (iMain % 15)==0:
			scan_out = scan()
			#print(scan_out)
		iMain+=1
		time.sleep(1)

'''
		print(scan_out)
		if messageServer["Health"] <6:
			print("here")
			print(scan_out["HealthPickup"])
			if scan_out["HealthPickup"]:
				print("here1")
				outer_list=[]
				for v in scan_out["HealthPickup"].values():
					inner_list=[]
					print(v[0])
					print(v[1])
					inner_list.append(v[0])
					inner_list.append(v[1])
					outer_list.append([inner_list])
				print(outer_list)
				goToForLists(x,y,outer_list)
'''
		'''
		if safePos == False:
			goToCampPoints(x,y,campPoints)
			print("safe pos reached")
			while True:
				pass
			safePos = True
		'''

def movement():
	while True:
		#goToForLists(messageServer['X'], messageServer['Y'], [[60,0]])#[[15,90],[-15,90],[15,-90],[-15,-90]])
		print("arrived")
		if serverResponse[1] == 18:
			pass#print("its bout me")
		elif serverResponse[1] == 27:
			print("got shot")
			#got_shot()
		time.sleep(70)
'''
def movement():
	while True:
		print('move')
		#print(messageServer)
		goToForLists(messageServer['X'], messageServer['Y'], [[15,90],[-15,90],[15,-90],[-15,-90]])

		#GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {'Amount': 15})
		time.sleep(70)

'''

t1 = threading.Thread(target=readServer)
t2 = threading.Thread(target=main)
t3 = threading.Thread(target=movement)

t1.start()
time.sleep(1)
t2.start()
t3.start()
