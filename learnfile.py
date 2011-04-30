import pyborg
import sys

borg = pyborg.pyborg()

for line in open(sys.argv[1], "r"):
	if line != '':
		print line
		borg.learn(pyborg.filter_message(line, borg))
		
borg.save_all()