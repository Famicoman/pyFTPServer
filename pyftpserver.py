### FTP Server 
### Mike Dank
### v 0.1 11/12/2012
### A concurrent FTP server written in python

import sys    
import os           
import os.path
import socket
import string
import time
from time import strftime, gmtime
import threading
from thread import *

#Globals for the server
port = 21
host = ""
logfilename = ""
user_pass = dict()
srvsock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

#### newclient ####
# Class for a new client. This class holds all of the necessary
# methods and variables for each connecting client. This class
# is threaded, so there can be multiple concurrent instances.
class newclient(threading.Thread):
	#Globals for each connection
	address = ""
	current_user = ""
	perspective_user = ""
	is_authed = 0
	filepath = "."
	datasock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
	conn = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

	#### __init__ ####
	# Thread initialization. Adds the address and connection attributes to
	# the class instance. Sets it up as a new client connection.
	def __init__(self, address, connection):
		self.address = address
		self.connection = connection
		threading.Thread.__init__(self)
		
	#### loggit() ####
	# Custom logging function. loggit takes in a string s which is the message
	# it is to log. A Year/Month/Day/Hour/Minute/Second timestamp is then
	# generated. This timestamp is written to the log, followed by the string
	# s and a newline character.
	def loggit(self,s):
		timestamp = strftime("%Y-%m-%d %H:%M:%S", gmtime()) #Make timestamp
		log.write(timestamp + " " + self.address[0] + ":" + str(self.address[1]) + " " + s + '\n') 

	#### receive() ####
	# Function to receive from the socket. The function starts off with
	# a 1.5 second sleep. There were problems with timeouts when doing a 
	# direct send then receive. Then, the function receives a string. The 
	# string is then sent to be logged (minus its newline char) and is 
	# returned.
	def receive(self):
		rec = conn.recv(1024) #Receive data from socket
		rec = rec[:-2]
		self.loggit("Received: " + rec) #Log the received line
		return rec
		
	#### send() ####
	# Function to send a command to the socket. send takes in a string s
	# which it then writes to the socket with a newline character. After,
	# the string is then sent to be logged.
	
	def send(self,s):
		conn.sendall(s + "\n") #Send string with line return
		self.loggit("Sent: " + s) #Log the sent line

	#### help_cmd() ####
	# Function for handling the HELP command. Keeps a dictionary of valid
	# commands and their descriptions. Function sees if command in is only 
	# "HELP" and if so lists commands. If not, sees if the command help is
	# needed for is in dict. If it is, send the description. If not, send
	# that the command is unsupported.
	def help_cmd(self,s):
		#Keep dict of valid commands that help can be retrieved for
		help_dict = { 'USER' : 'user - send new user information', 'PASS' : 'pass - send new password', 'CD' : 'cd - change current working directory', 'QUIT' : 'quit - terminate ftp session and exit', 'GET' : 'get - receive file', 'PUT' : 'put - send one file', 'PWD' : 'pwd - print working directory on remote machines', 'LS' : 'ls - list contents of remote directory', 'HELP' : 'help - print local help information'}
		
		if s.upper == "HELP":
			out = "215 Commands are:"
			for key in help_dict.keys():
				out = out + " " + key
			self.send(out)
		else:
			s = s[5:].upper() #Convert user command to uppercase and see if it's in list
			if help_dict.has_key(s):
				#If it is, issue help command
				self.send ("215 "+help_dict[s])
			else:
				self.send("500 Invalid help command " + s)
				
	#### user_cmd() ####
	# Function for handling the USER command. Has a perspective user who
	# is not currently logged in. If the user is the same as the one 
	# logged in, report so. If not and the user exists, ask for password
	# If the user doesn't exist in the list, deny them.
	def user_cmd(self,s):
		global perspective_user
		s = s[5:]
		if s == self.current_user:
			self.send("503 user already logged in")
		elif user_pass.has_key(s):
			self.perspective_user = s
			self.send("331 User name okay, need password")
		else:
			self.send("500 User not found")

	#### pass_cmd() ####
	# Function for handling the PASS command. Has a perspective user who
	# is not currently logged in. If the password entered matches the 
	# password for the user, log them in. If not, report back that the
	# login failed.
	def pass_cmd(self,s):
		global is_authed
		s = s[5:]
		
		if user_pass[self.perspective_user] == s:
			self.send("230 User logged in, proceed.")
			self.is_authed = 1 #Set is_authed to 1
		else:
			self.send("530 Not logged in. Your password is being rejected, contact the server administrator.")

	#### cwd_cmd() ####
	# Function for handling the CWD command. Checks to see if
	# the current path plus the new user-sent directory exists
	# If so, change to it. If not, report back not found
	def cwd_cmd(self,s):
		global filepath
		s = s[4:]
		if os.path.isdir(self.filepath+"/"+s):
			self.filepath = self.filepath + '/' + s
			self.send("200 Directory changed successfully")
		else:
			self.send("550 Directory not found")
		
	#### quit_cmd() ####
	# Function for handling the QUIT command. Will report back for 
	# quitting and terminate the connection.
	def quit_cmd(self,s):
		global conn
		self.send("221 Peace out, girl scout")
		conn.close()
		self.loggit("Connection is now closing")

	#### cdup_cmd() ####
	# Function for handling the CDUP command. Command will go back
	# to the [arent directory. First, the method makes sure that the
	# path is not the root directory. If it is not, it searches the
	# filepath string for the last backslash, then truncates the
	# string to not include it. 
	def cdup_cmd(self,s):
		global filepath
		if self.filepath != ".":
			lastslash = self.filepath.rfind('/')
			lastslash = len(self.filepath)-lastslash
			self.filepath = self.filepath[:(-1*lastslash)]
			self.send("250 CDUP successful")
		else:
			self.send("500 CDUP not successful")
		

	#### pwd_cmd() ####
	# Function for handling the PWD command. Command simply 
	# prints the current working directory by outputting the
	# filepath string.
	def pwd_cmd(self,s):
		self.send("200 Current working directory: " + self.filepath)

	#### retr_cmd() ####
	# Function for handling the RETR command. Command will check
	# if the file exists, if so, it will open and read the file
	# and send line by line to the socket. If not, it will report 
	# back that the file is not found.	
	def retr_cmd(self,s):
		global datasock
		s = s[5:]
		#Make sure file exists before retrieving
		if os.path.isfile(self.filepath+"/"+s):
			self.send("150 opening connection to download: " + s)
			#Open the file
			input = open(self.filepath+"/"+s, "r")
			self.loggit("File, " + s + " opened")
			self.loggit("Sending data...")
			#Start send loop
			for line in input:
				self.datasock.send(line)
			self.datasock.close()
			self.send("226 File transfer completed")
			input.close() #close the file
			self.loggit("File, " + s + " closed")
		else:
			self.datasock.close()
			self.send("550 No such file")
				
	#### pasv_cmd() ####
	# Function for handling the PASV command. Command will bind
	# the data sock and send the client back the specifics to use
	# to establish a connection
	def pasv_cmd(self,s):
		global datasock
		self.datasock.bind(('',0))
		#retrieve host port number
		hostport = self.datasock.getsockname()[1]
		#Retreive host ip address
		hostip = socket.gethostbyname(socket.getfqdn())
		p2 = hostport%256 #Create p2 by getting remainder of port divided by 256
		p1 = (hostport-p2)/256 #Create p1 by result of dividing, subtract p2 to avoid a decimal result
			
		#Split the host ip up by periods
		lineparts = hostip.split('.')
		#Send over the command with ip address and port components
		self.send("227 Entering Passive Mode ("+lineparts[0]+","+lineparts[1]+","+lineparts[2]+","+lineparts[3]+","+str(p1)+","+str(p2)+")")

	#### port_cmd() ####
	# Function for handling the PORT command. Command will take the 
	# ip/port portions from the client and use them to form a connection
	# with the data sock.		
	def port_cmd(self,s):
		global datasock
		s = s[5:]

		#Split the six fields up by the comma separation
		lineparts = s.split(',')
		#Make a new string for the ipaddress from the split
		newhost = lineparts[0] + '.' + lineparts[1]+ '.' + lineparts[2] + '.' + lineparts[3]
		#Make an int for the port by multiplying p1 by 256 and adding p2
		newport = int(lineparts[4]) * 256 + int(lineparts[5])
		self.loggit("PORT string processed, host="+newhost+", port="+str(newport))
		
		#Attempt connection to the new socket
		try:
			self.datasock.connect( (newhost, newport) )
			self.send("200 PORT command successful")
			self.loggit("Connection to data socket successful!")
		except socket.gaierror:
			self.loggit("Data socket host or port incorrect, terminating")
		

	#### list_cmd() ####
	# Function for handling the LIST command. This function will
	# make sure that the data connection has been established.
	# Then it will send the listing of the current directory 
	#over the data connection.
	def list_cmd(self,s):
		global datasock
		self.send("150 Opening ASCII mode data connection for file list")
		#For all file names in the directory, send them down the data connection
		for filename in os.listdir(self.filepath):
			self.datasock.sendall(filename + "\n")
		self.datasock.close()
		self.send("226 Transfer complete")

	#### run() ####
	# Function that runs the main parsing loop for each client.
	# Takes command from client and figures out which function
	# to call. Will exit on a quit command.
	def run(self):
		#Setup variables
		global conn
		global address
		conn = self.connection
		address = self.address
		self.loggit("Connected with " + address[0] + ':' + str(address[1]))
		
		#Welcome the client
		self.send("220 Welcome")
		
		#Loop while the client doesn't quit
		loop = 1
		while loop == 1: 
			sendstr = self.receive()
		
			#If they are not authed, only allow the user to log in
			if self.is_authed == 0:
				if sendstr.lower().startswith("user"):
					self.user_cmd(sendstr)
				elif sendstr.lower().startswith("pass"):
					self.pass_cmd(sendstr)
				else:
					self.send("200 Need account for login")
			elif sendstr.lower().startswith("user"):
				self.user_cmd(sendstr)
			elif sendstr.lower().startswith("cwd"):
				self.cwd_cmd(sendstr)
			elif sendstr.lower().startswith("cdup"):
				self.cdup_cmd(sendstr)
			elif sendstr.lower().startswith("pasv"):
				self.pasv_cmd(sendstr)
			elif sendstr.lower().startswith("port"):
				self.port_cmd(sendstr)
			elif sendstr.lower().startswith("retr"):
				self.retr_cmd(sendstr)
			elif sendstr.lower().startswith("pwd"):
				self.pwd_cmd(sendstr)
			elif sendstr.lower().startswith("list"):
				self.list_cmd(sendstr)
			elif sendstr.lower().startswith("help"):
				self.help_cmd(sendstr)
			elif sendstr.lower().startswith("quit"):
				self.quit_cmd(sendstr)
				loop = 0
			else:
				self.send("202 Command invalid or unsuported")
				self.loggit("Incorrect command")
				
#Make sure the application has 3 args
if (len(sys.argv) == 3):
	#Setup variables
	logfilename = sys.argv[1]
	log = open(logfilename, 'a')
	port = int(sys.argv[2])
	client_list = dict()

	#Bind socket
	srvsock.bind( ("", port)) 
	srvsock.listen( 5 )
	
	#Load passwords into a dictionary
	passwords = open("passwords", 'r')
	for line in passwords:
		lines = line.split(',')
		user_pass[lines[0]] = (lines[1])[:-1]
	
	#Loop for connections, spawn thread for each of them.
	while 1:
		connection, address = srvsock.accept()
		client_list[connection] = address
		thread = newclient(address,connection)
		thread.start()

#Incorrect usage
else:
	print "Incorrect usage. Use: python ftpserver.py logfile port"
	print "All arguments are required"