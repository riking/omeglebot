from irc import Irc
from omegle import Omegle
from pyborg import pyborg
import pyborg as pyborgmodule
import ConfigParser
from datetime import datetime, date, time

config = ConfigParser.RawConfigParser()
omegle = Omegle()
irc = Irc()
pyborg = pyborg()
pyborg_on = False

class emptyclass:
	pass

def main():
	config.read('bot.cfg')
	
	omegle.on_connected += omegle_connected
	omegle.on_disconnected += omegle_disconnected
	omegle.on_msg += omegle_msg
	omegle.on_error += omegle_error
	
	irc.nick = config.get('IRC', 'nick')
	irc.ident = config.get('IRC', 'ident')
	irc.realname = config.get('IRC', 'name')
	
	irc.on_ready += ready
	irc.on_channel_msg += channel_msg
	irc.on_output += irc_output
	irc.on_private_msg += private_msg
	
	global omegle_channel
	omegle_channel = config.get('Omegle', 'channel')
	global allow
	allow = config.get('Omegle', 'allow')
	global status_color
	status_color = '\x03' + config.get('Omegle', 'status_color')
	global msg_color
	msg_color = '\x03' + config.get('Omegle', 'msg_color')
	global pyborg_color
	pyborg_color = '\x03' + config.get('Omegle', 'pyborg_color')
	
	global log_path
	log_path = config.get('Logging', 'path')
	global log_url
	log_url = config.get('Logging', 'url')
	global timestamp_format
	timestamp_format = config.get('Logging', 'timestamp')
	
	# try to read the log index file
	global log_index
	try:
		index_file = open('logindex', 'r')
		log_index = int(index_file.read())
		index_file.close()
	except:
		# if we couldnt open or read the index then start at 0
		log_index = 0
	
	irc.connect('irc.esper.net', 6667)
	
def write_log_index():
	index_file = open('logindex', 'w')
	index_file.write(str(log_index))
	index_file.close()

def ready():
	if config.get('NickServ', 'identify').lower() == 'true':
		irc.msg('NickServ', 'identify ' + config.get('NickServ', 'password'))
	irc.join(omegle_channel)

def private_msg(sender, msg):
	user = sender[0:sender.find('!')]
	if '@' in irc.users[omegle_channel][user]: #user is op in the channel the message came from?
		irc.send_raw(msg)

def channel_msg(sender, channel, msg):
	user = sender[0:sender.find('!')]
	
	if channel == omegle_channel:
		if msg == '!connect':
			if user_allowed(irc.users[channel][user]):
				omegle.connect()
			else:
				irc.notice(user, 'ACCESS DENIED')
		elif msg == '!disconnect':
			if user_allowed(irc.users[channel][user]):
				omegle.disconnect()
			else:
				irc.notice(user, 'ACCESS DENIED')
		elif msg == '!help':
			if '@' in irc.users[channel][user]:
				irc.notice(user, 'Omegle operator commands: !allow all|voice|op, !quit, !pyborg on|off')
			else:
				irc.notice(user, '!connect connects to omegle, !disconnect disconnects the current omegle conversation. Channel messages prefixed with \'>\' are sent to the stranger. Only voiced users may use these commands')
		elif msg[0] == '>':
			if user_allowed(irc.users[channel][user]):
				if omegle.status == 'connected':
					omegle_log.write('You: ' + msg[1:] + '\n')
					omegle.msg(msg[1:])
					pyborg.learn(pyborgmodule.filter_message(msg[1:], pyborg))
				else:
					irc.notice(user, 'Omegle chat is disconnected!')
			else:
				irc.notice(user, 'ACCESS DENIED')
	
		if user in irc.users[channel].keys() and '@' in irc.users[channel][user]: #user is op in the channel the message came from?
			if msg == '!quit':
				irc.quit()
			if msg[:msg.find(' ')+1] == '!allow ':
				new_allow = msg[msg.find(' ')+1:]
				if new_allow == 'all' or new_allow == 'voice' or new_allow == 'op':
					global allow
					allow = new_allow
					irc.notice(user, 'Allow has been set to ' + allow)
				else:
					irc.notice(user, 'Unknown allow mode \'%s\'' % (new_allow))
					irc.notice(user, 'Allow modes are all, voice or op')
			elif msg[:msg.find(' ')+1] == '!pyborg ':
				global pyborg_on
				if msg[msg.find(' ')+1:] == 'on':
					pyborg_on = True
					irc.notice(user, 'pyborg is now on')
				else:
					pyborg_on = False
					irc.notice(user, 'pyborg is now off')
			elif msg[0] == '!':
				io_module = emptyclass()
				io_module.output = pyborg_irc_output
				io_module.commanddict = {}
				io_module.commandlist = ''
				pyborg.do_commands(io_module, msg, (), True)
		
def omegle_connected():
	global log_index
	global irc_log
	irc_log = open(log_path.replace('$1', 'irc').replace('$2', str(log_index)), 'w')
	irc_log.write('#Log started at %s\n' % (datetime.utcnow().strftime('%d/%m/%y %H:%M:%S')))
	global omegle_log
	omegle_log = open(log_path.replace('$1', 'omegle').replace('$2', str(log_index)), 'w')
	omegle_log.write('#Log started at %s\n' % (datetime.utcnow().strftime('%d/%m/%y %H:%M:%S')))
	
	log_index = log_index + 1
	write_log_index()
	
	irc.msg(omegle_channel, status_color + 'Connected!')
	
def omegle_disconnected(msg = ''):
	if msg == '':
		irc.msg(omegle_channel, status_color + 'Disconnected!')
	else:
		irc.msg(omegle_channel, status_color + 'Disconnected! (%s)' % (msg))	
				
	if msg == 'strangerDisconnected':
		omegle_log.write('Your conversational partner has disconnected.\n')
	else:
		omegle_log.write('You have disconnected.\n')
			
	irc.msg(omegle_channel, status_color + log_url.replace('$1','irc').replace('$2',str(log_index-1)) + ' ' + log_url.replace('$1','omegle').replace('$2',str(log_index-1)))
			
	irc_log.write('#Log finished at %s\n' % (datetime.utcnow().strftime('%d/%m/%y %H:%M:%S')))
	irc_log.close()
	omegle_log.write('#Log finished at %s\n' % (datetime.utcnow().strftime('%d/%m/%y %H:%M:%S')))
	omegle_log.close()
		
def omegle_msg(msg):
	print repr(msg)
	irc.msg(omegle_channel, msg_color + msg)
	
	io_module = emptyclass()
	io_module.output = pyborg_omegle_output
	pyborg.process_msg(io_module, msg, pyborg_on * 100, True, ())
	
	if omegle.status == 'connected':
		omegle_log.write('Stranger: ' + msg + '\n')

def pyborg_irc_output(msg, args):
	irc.msg(omegle_channel, msg)

def pyborg_omegle_output(msg, args):
	if omegle.status == 'connected':
		omegle_log.write('You: ' + msg + '\n')
		omegle.msg(msg)
		irc.msg(omegle_channel, pyborg_color + msg)
	
def omegle_error(msg):
	print msg
	irc.msg(omegle_channel, status_color + 'Error!')
	'''for line in msg.split('\n'):
		if line != '':
			for user, modes in irc.users[omegle_channel].iteritems():
				if '@' in modes:
					irc.notice(user, line)'''

def irc_output(channel, text):
	print text
	if omegle.status == 'connected' and channel == omegle_channel:
		irc_log.write(datetime.utcnow().strftime(timestamp_format) + ' ' + text + '\n')
					
# user_allowed
# is user allowed to talk to the omegler
def user_allowed(modes):
	if allow == 'all':
		return True;
	elif allow == 'voice':
		return '+' in modes or '@' in modes
	elif allow == 'op':
		return '@' in modes
	else:
		return False
	
if __name__ == '__main__':
	main()
