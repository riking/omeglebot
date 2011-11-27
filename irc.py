import socket
import sys
from event import Event

class Irc:
	nick = 'nick'
	ident = 'ident'
	realname = 'smith'
	
	channels = set([]) # set of channel names we are in
	users = {} # dictionary of channels each containing a dictionary of users, each containing a set of their channel modes
	
	on_ready = Event()
	on_channel_msg = Event()
	on_private_msg = Event()
	on_nick_changed = Event()
	on_output = Event()
	
	#def __init__(self):
		
	def connect(self, host, port):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect((host, port))
		self.send_raw('NICK ' + self.nick)
		self.send_raw('USER %s * * :%s' % (self.ident, self.realname))
		self.mainloop()
	
	def mainloop(self):
		# main irc reading loop
		while True:
			# let's receive one line of data
			line = ''
			# receive one byte until we hit \r
			while True:
				data = self.sock.recv(1)
				if data == '':
					# disconnected
					return
				elif data == '\r':
					self.sock.recv(1)
					break
				line += data
			#print repr(line)
			linepos = 0
			
			# if the line begins with : then the first part is who sent the message to us
			if line[0] == ':':
				sender = line[1:line.find(' ')]
				linepos = line.find(' ') + 1
				
			# get the message type (privmsg, notice, etc.)
			msg = line[linepos:line.find(' ', linepos)]
			linepos = line.find(' ', linepos) + 1
			
			# get the parameters
			params = []
			while True:
				# param starting with ':' denotes the final parameter and may include spaces
				if line[linepos] == ':':
					params.append(line[linepos+1:])
					break
				if line.find(' ', linepos) == -1:
					params.append(line[linepos:])
					break
				params.append(line[linepos:line.find(' ', linepos)])
				linepos = line.find(' ', linepos) + 1
				if linepos >= len(line):
					break
			
			# always respond to ping with pong
			if msg == 'PING':
				self.send_raw('PONG ' + params[0])
				
			# end of motd, or motd not found
			# this means we are ready to indetify and join channels
			if msg == '376' or msg == '422': #376 = end of motd, 422 = motd missing
				self.on_ready.call()
				
			# a user joined a channel we are in, or we joined a channel
			if msg == 'JOIN':
				user = sender[0:sender.find('!')]
				# was it us joining the channel
				if user == self.nick:
					self.channels.add(params[0])
					self.users[params[0]] = {}
				# it was someone else then
				else:
					self.users[params[0]][user] = set([])
				self.on_output.call(params[0], '%s has joined %s' % (user, params[0]))
				
			# userlist upon channel join
			if msg == '353':
				userlist = params[3].split(' ')
				for user in userlist:
					if user[0] == '+' or user[0] == '@':
						self.users[params[2]][user[1:]] = set([user[0]])
					else:
						self.users[params[2]][user] = set([])
				
			# user channel mode
			if msg == 'MODE':
				user = sender[0:sender.find('!')]
				i = 2
				for c in params[1]:
					if c == '+' or c == '-':
						a = c
					elif c == 'v':
						if a == '+':
							self.users[params[0]][params[i]].add('+')
							self.on_output.call(params[0], '%s gives voice to %s' % (user, params[i]))
							i = i + 1
						elif a == '-':
							if '+' in self.users[params[0]][params[i]]:
								self.users[params[0]][params[i]].discard('+')
							self.on_output.call(params[0], '%s takes voice from %s' % (user, params[i]))
							i = i + 1
					elif c == 'o':
						if a == '+':
							self.users[params[0]][params[i]].add('@')
							self.on_output.call(params[0], '%s gives operator status to %s' % (user, params[i]))
							i = i + 1
						elif a == '-':
							if '@' in self.users[params[0]][params[i]]:
								self.users[params[0]][params[i]].discard('@')
							self.on_output.call(params[0], '%s takes operator status from %s' % (user, params[i]))
							i = i + 1
					else:
						# self.msg(params[0], params[0] + ' ' + a + c)
				'''
				if params[1][0] == '+':
					for i in range(1,len(params[1])):
						if params[1][i] == 'o':
							self.users[params[0]][params[i+1]].add('@')
							self.on_output.call(params[0], '%s gives operator status to %s' % (user, params[i+1]))
						elif params[1][i] == 'v':
							self.users[params[0]][params[i+1]].add('+')
							self.on_output.call(params[0], '%s gives voice to %s' % (user, params[i+1]))
				elif params[1][0] == '-':
					for i in range(1,len(params[1])):
						if params[1][i] == 'o':
							if '@' in self.users[params[0]][params[i+1]]:
								self.users[params[0]][params[i+1]].discard('@')
							self.on_output.call(params[0], '%s takes operator status from %s' % (user, params[i+1]))
						elif params[1][i] == 'v':
							if '+' in self.users[params[0]][params[i+1]]:
								self.users[params[0]][params[i+1]].discard('+')
							self.on_output.call(params[0], '%s takes voice from %s' % (user, params[i+1]))
							'''
			
			# someone changes their nick (could be us)
			if msg == 'NICK':
				user = sender[0:sender.find('!')]
				for channel in self.channels:
					if self.users[channel].has_key(user):
						self.users[channel][params[0]] = self.users[channel][user]
						del self.users[channel][user]
						self.on_output.call(channel, '%s is now known as %s' % (user, params[0]))
					if user == self.nick:
						self.nick = params[0]
				self.on_nick_changed.call(user, params[0])
			
			if msg == 'PART':
				user = sender[0:sender.find('!')]
				del self.users[params[0]][user]
				if len(params) == 2:
					self.on_output.call(params[0], '%s has left %s (%s)' % (user, params[0], params[1]))
				else:
					self.on_output.call(params[0], '%s has left %s' % (user, params[0]))
			
			if msg == 'QUIT':
				user = sender[0:sender.find('!')]
				for channel in self.channels:
					if self.users[channel].has_key(user):
						del self.users[channel][user]
						if len(params) == 1:
							self.on_output.call(channel, '%s has left %s (%s)' % (user, channel, params[0]))
						else:
							self.on_output.call(channel, '%s has left %s' % (user, channel))
						
			if msg == 'PRIVMSG':
				user = sender[0:sender.find('!')]
				# message from a channel or private message?
				if params[0][0] == '#':
					self.on_output.call(params[0], '<%s%s> %s' % (self.get_mode_char(user, params[0]), user, params[1]))
					self.on_channel_msg.call(sender, params[0], params[1])
				else:
					self.on_output.call('server', '<%s> %s' % (user, params[1]))
					self.on_private_msg.call(sender, params[1])
					
	def get_mode_char(self, user, channel):
		if self.users[channel].has_key(user):
			if '@' in self.users[channel][user]:
				return '@'
			if '+' in self.users[channel][user]:
				return '+'
		return ''
		
	def send_raw(self, msg):
		self.sock.send(msg + '\r\n')
	
	def join(self, channel, passwd = ''):
		self.send_raw('JOIN %s %s' % (channel, passwd))
	
	def msg(self, dest, msg):
		self.send_raw('PRIVMSG %s :%s' % (dest, msg))
		if dest[0] == '#':
			self.on_output.call(dest, '<%s%s> %s' % (self.get_mode_char(self.nick, dest), self.nick, msg))
		else:
			self.on_output.call('server', '<%s> -> <%s> %s' % (self.nick, dest, msg))
			
	
	def notice(self, dest, msg):
		self.send_raw('NOTICE %s :%s' % (dest, msg))
		if dest[0] == '#':
			self.on_output.call(dest, '-%s%s- %s' % (self.get_mode_char(self.nick, dest), self.nick, msg))
		else:
			self.on_output.call('server', '-%s- -> <%s> %s' % (self.nick, dest, msg))
	
	def quit(self, msg = ''):
		self.send_raw('QUIT :' + msg)
		
	@staticmethod
	def color(front = -1, back = -1):
		if front == -1 and back == -1:
			return ''
		ret = '\x03'
		if front != -1:
			ret += '%02d' % (front)
		if back != -1:
			ret += ',%02d' % (back)
		return ret
