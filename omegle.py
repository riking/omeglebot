import socket
import thread
import traceback

class Event:
    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def call(self, *args, **keywargs):
        for handler in self.__handlers:
            handler(*args, **keywargs)


class Omegle:
	server = 'omegle.com'
	port = 1365
	status = 'disconnected' # disconnected, connecting, connected, disconnected
	
	on_connected = Event()
	on_disconnected = Event()
	on_msg = Event()
	on_error = Event()
	
	def connect(self):
		if self.status == 'disconnected':
			self.status == 'connecting'
			thread.start_new_thread(self.event_loop, ())
		
	def event_loop(self):
		try:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.connect((self.server, self.port))
			self.sock.send('\x0BomegleStart\x00\x15web-flash?rcs=1&spid=')
			
			while True:
				# firstly try to receive one byte
				# if we receive nothing then we probably got disconnected
				c = self.sock.recv(1)
				if c == '': # if we got nothing then we probably disconnected earlier
					self.on_disconnected.call()
					self.status = 'disconnected'
					return
				# read opcode length
				len = ord(c)
				# read the opcode
				opcode = ''
				for i in range(0, len):
					opcode += self.sock.recv(1)
				# read the message length
				len = ord(self.sock.recv(1)) << 8 | ord(self.sock.recv(1))
				# read the message
				msg = ''
				for i in range(0, len):
					msg += self.sock.recv(1)
				print opcode + ' ' + msg
				if opcode == 'c': # connected
					self.status = 'connected'
					self.on_connected.call()
				elif opcode == 'm': # message
					self.on_msg.call(msg)
				elif opcode == 'd': # stranger disconnected
					self.sock.close()
					self.on_disconnected.call('strangerDisconnected')
					self.status = 'disconnected'
					return
				# other not yet implemented opcodes
				# 't' == typing
				# 'st' == stopped typing
				# 'recaptchaRequired' == recaptcha is required
		except:
			self.on_error.call(traceback.format_exc())
			self.on_disconnected.call('Error')
			self.status = 'disconnected'
				
	def msg(self, msg):
		if self.status == 'connected':
			try:
				self.sock.send('\x01s' + chr(len(msg)>>8) + chr(len(msg)&0xFF) + msg)
			except:
				self.on_error.call(traceback.format_exc())
				
	def disconnect(self):
		if self.status == 'connected':
			#self.status = 'disconnected'
			try:
				# send a disconnect packet and just wait for the event loop to die due to disconnection
				self.sock.send('\x01d\x00\x00')
			except:
				self.on_error.call(traceback.format_exc())
