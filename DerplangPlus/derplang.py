
import time

def run(code, env = None, limit = 10000):
	env = initEnv(env)
	(commands, env) = preProcess(code, env)
	cmdNum = 0
	i = 0
	while cmdNum < len(commands) and i < limit:
		cmd = commands[cmdNum]
		if cmd[0] == "var": # Variable assignment
			if len(cmd) < 2:
				raise DerplangError("Not enough arguments.")
			env["mem"][cmd[1]] = getVal(env, cmd[2])
		elif cmd[0] == "add": # Addtion and concatenation
			env = mathOp(env, cmd, "add")
		elif cmd[0] == "subtract":
			env = mathOp(env, cmd, "subtract")
		elif cmd[0] == "multiply":
			env = mathOp(env, cmd, "multiply")
		elif cmd[0] == "divide":
			try: env = mathOp(env, cmd, "divide")
			except ZeroDivisionError: raise DerplangError("Attempt to divide by zero.")
		elif cmd[0] == "input":
			if len(cmd) < 2: raise DerplangError("No variable for input.")
			if len(cmd) > 4: raise DerplangError("Too many variables for input.")
			if isinstance(env["input"], str):
				env["mem"][cmd[1]] = env["input"]
			elif env["input"]:
				env["mem"][cmd[1]] = env["input"]()
			else:
				env["mem"][cmd[1]] = ""
		elif cmd[0] == "print":
			for arg in cmd[1:]:
				toprint = getVal(env, arg)
				if toprint is None:
					raise DerplangError("Unable to get value for " + arg + " to output")
				env["output"] += str(toprint)
		elif cmd[0] == "goto":
			if len(cmd) < 2: raise DerplangError("No label to go to.")
			if not cmd[1] in env["labels"]:
				raise DerplangError("The label " + cmd[1] + " does not exist.")
			cmdNum = env["labels"][cmd[1]]
			i += 1
			continue  # Bypass cmdNum increment
		elif cmd[0] == "if":
			if len(cmd) < 5:
				raise DerplangError("Not enough arguments for if.")
			if (not (cmd[3] in env["labels"] or cmd[3] == "continue")) or\
			   (not (cmd[4] in env["labels"] or cmd[4] == "continue")):
				raise DerplangError("Labels for the if command do not exist.")
			arg = 4
			if getVal(env, cmd[1]) == getVal(env, cmd[2]):
				arg = 3
			if cmd[arg] == "continue":
				cmdNum += 1
			else:
				cmdNum = env["labels"][cmd[arg]]
			i += 1
			continue # Bypass cmdNum increment
		elif cmd[0] == "sleep":
			if len(cmd) < 2: 
				raise DerplangError("No sleep time.")
			time.sleep(float(cmd[1]))
		elif cmd[0] == "label":
			pass
		elif cmd[0] != '':
			raise DerplangError("Invalid command: " + cmd[0])
		cmdNum += 1
		i += 1
	return env

def initEnv(env):
	if not env:
		env = {}
	if not "output" in env:
		env["output"] = ""
	if not "mem" in env:
		env["mem"] = {}
	if not "labels" in env:
		env["labels"] = {}
	return env

def preProcess(commands, env):
	cmdNum = 0
	commands = commands.split(";")
	commands = list(splitCmd(x) for x in commands)
	for cmd in commands:
		if cmd[0] == "label":
			if len(cmd) < 2: raise DerplangError("No label name.")
			env["labels"][cmd[1]] = cmdNum + 1
		cmdNum += 1
	return (commands, env)

def getVal(env, s):
	# String literal
	if (s[0] == '"' and s[-1] == '"') or\
	   (s[0] == "'" and s[-1] == "'"):
		return unescape(env, s[1:-1])
	if s in env["mem"]:
		return env["mem"][s]
	if s.lower() == "true": return True
	if s.lower() == "false": return False
	try: return int(s)
	except ValueError: pass
	try: return float(s)
	except ValueError: pass
	raise DerplangError("Could not evaluate value of " + s)

def unescape(env, s):
	return s

# Split a command and remove whitespace.
def splitCmd(cmd):
	cmd = cmd.split(":")
	cmd = list(x.strip() for x in cmd)
	return cmd

def mathOp(env, cmd, op):
	if len(cmd) < 4: raise DerplangError("Nothing to " + op + ".")
	env["mem"][cmd[1]] = getVal(env, cmd[2])
	for arg in cmd[3:]:
		val = getVal(env, arg)
		if   op == "add":      env["mem"][cmd[1]] += val
		elif op == "subtract": env["mem"][cmd[1]] -= val
		elif op == "multiply": env["mem"][cmd[1]] *= val
		elif op == "divide":   env["mem"][cmd[1]] /= val
		else: raise DerplangError("Invalid mathOP " + op)
	return env

class DerplangError(Exception):
	def __init__(self, s):
		self.value = s
	def __str__(self):
		return self.value

