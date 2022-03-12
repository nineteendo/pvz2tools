# Import libraries
import sys, datetime
from traceback import format_exc
from json import load, dumps
from struct import unpack, error
from os import makedirs, listdir, system, getcwd
from os.path import isdir, isfile, realpath, join as osjoin, dirname, relpath, basename, splitext

# Default Options
options = {
	"binObjClasses": (
		"drapersavedata",
		"globalsavedata",
		"playerinfolocalsavedata",
		"lootsavedata",
		"savegameheader"
	),
	"comma": 0,
	"confirmPath": True,
	"datObjClasses": (
		"playerinfo",
	),
	"DEBUG_MODE": True,
	"doublepoint": 1,
	"ensureAscii": False,
	"enteredPath": False,
	"indent": -1,
	"RTONExtensions": (
		".bin",
		".dat",
		".json",
		".rton",
		".section"
	),
	"RTONNoExtensions": (
		"draper_",
		"local_profiles",
		"loot",
		"_saveheader_rton"
	),
	"repairFiles": False,
	"shortNames": True,
	"sortKeys": False,
	"sortValues": False
}

# Print & log error
def error_message(string):
	if options["DEBUG_MODE"]:
		string += "\n" + format_exc()
	
	fail.write(string + "\n")
	fail.flush()
	print("\033[91m" + string + "\033[0m")

# Print & log warning
def warning_message(string):
	fail.write("\t" + string + "\n")
	fail.flush()
	print("\33[93m" + string + "\33[0m")

# Print in blue text
def blue_print(text):
	print("\033[94m"+ text + "\033[0m")

# Print in green text
def green_print(text):
	print("\033[32m"+ text + "\033[0m")

# Input in bold text
def bold_input(text):
	return input("\033[1m"+ text + "\033[0m: ")

# Input hybrid path
def path_input(text):
	string = ""
	newstring = bold_input(text)
	while newstring or string == "":
		if options["enteredPath"]:
			string = newstring
		else:
			string = ""
			quoted = 0
			escaped = False
			tempstring = ""
			for char in newstring:
				if escaped:
					if quoted != 1 and char == "'" or quoted != 2 and char == '"' or quoted == 0 and char in "\\ ":
						string += tempstring + char
					else:
						string += tempstring + "\\" + char
					
					tempstring = ""
					escaped = False
				elif char == "\\":
					escaped = True
				elif quoted != 2 and char == "'":
					quoted = 1 - quoted
				elif quoted != 1 and char == '"':
					quoted = 2 - quoted
				elif quoted != 0 or char != " ":
					string += tempstring + char
					tempstring = ""
				else:
					tempstring += " "

		if string == "":
			newstring = bold_input("\033[91mEnter a path")
		else:
			newstring = ""
			string = realpath(string)
			if options["confirmPath"]:
				newstring = bold_input("Confirm \033[100m" + string)

	return string

# type 08
def parse_int8(fp):
	return repr(unpack("b", fp.read(1))[0])

# type 0a
def parse_uint8(fp):
	return repr(fp.read(1)[0])
	
# type 10
def parse_int16(fp):
	return repr(unpack("<h", fp.read(2))[0])

# type 12
def parse_uint16(fp):
	return repr(unpack("<H", fp.read(2))[0])
	
# type 20
def parse_int32(fp):
	return repr(unpack("<i", fp.read(4))[0])

# type 22
def parse_float(fp):
	return repr(unpack("<f", fp.read(4))[0]).replace("inf", "Infinity").replace("nan", "NaN")

# type 24, 28, 44 and 48
def parse_uvarint(fp):
	return repr(parse_number(fp))

# type 25, 29, 45 and 49
def parse_varint(fp):
	num = parse_number(fp)
	if num % 2:
		num = -num -1

	return repr(num // 2)

def parse_number(fp):
	num = fp.read(1)[0]
	result = num & 0x7f
	i = 128
	while num > 127:
		num = fp.read(1)[0]
		result += i * (num & 0x7f)
		i *= 128
	
	return result

# type 26
def parse_uint32(fp):
	return repr(unpack("<I", fp.read(4))[0])

# type 40
def parse_int64(fp):
	return repr(unpack("<q", fp.read(8))[0])

# type 42
def parse_double(fp):
	return repr(unpack("<d", fp.read(8))[0]).replace("inf", "Infinity").replace("nan", "NaN")

# type 46
def parse_uint64(fp):
	return repr(unpack("<Q", fp.read(8))[0])

# types 81, 90
def parse_str(fp):
	byte = fp.read(parse_number(fp))
	try:
		return dumps(byte.decode('utf-8'), ensure_ascii = ensureAscii)
	except Exception:
		return dumps(byte.decode('latin-1'), ensure_ascii = ensureAscii)

# type 82, 92
def parse_printable_str(fp):
	return dumps(parse_utf8_str(fp), ensure_ascii = ensureAscii)

def parse_utf8_str(fp):
	i1 = parse_number(fp) # Character length
	string = fp.read(parse_number(fp)).decode()
	i2 = len(string)
	if i1 != i2:
		warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() - 1) + ": Unicode string of character length " + str(i2) + " found, expected " + str(i1))
	
	return string

# types 90, 91, 92, 93
def parse_cached_str(fp, code, chached_strings, chached_printable_strings):
	if code == b"\x90":
		result = parse_str(fp)
		chached_strings.append(result)
	elif code in b"\x91":
		result = chached_strings[parse_number(fp)]
	elif code in b"\x92":
		result = parse_printable_str(fp)
		chached_printable_strings.append(result)
	elif code in b"\x93":
		result = chached_printable_strings[parse_number(fp)]
	
	return (result, chached_strings, chached_printable_strings)

# type 83
def parse_ref(fp):
	ch = fp.read(1)
	if ch == b"\x00":
		return '"RTID()"'
	elif ch == b"\x02":
		p1 = parse_utf8_str(fp)
		i2 = parse_uvarint(fp)
		i1 = parse_uvarint(fp)
		return dumps("RTID(" + i1 + "." + i2 + "." + fp.read(4)[::-1].hex() + "@" + p1 + ")", ensure_ascii = ensureAscii)
	elif ch == b"\x03":
		p1 = parse_utf8_str(fp)
		return dumps("RTID(" + parse_utf8_str(fp) + "@" + p1 + ")", ensure_ascii = ensureAscii)
	else:
		raise TypeError("unexpected subtype for type 83, found: " + ch.hex())

# root object
def root_object(fp, currrent_indent):
	VER = unpack("<I", fp.read(4))[0]
	string = "{"
	new_indent = currrent_indent + indent
	items = []
	end = "}"
	try:
		key, chached_strings, chached_printable_strings = parse(fp, new_indent, [], [])
		value, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
		string += new_indent 
		items = [key + doublepoint + value]
		end = currrent_indent + end
		while True:
			key, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
			value, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
			items.append(key + doublepoint + value)
	except KeyError as k:
		if str(k) == 'b""':
			if repairFiles:
				warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() - 1) + ": end of file")
			else:
				raise EOFError
		elif k.args[0] != b'\xff':
			raise TypeError("unknown tag " + k.args[0].hex())
	except (error, IndexError):
		if repairFiles:
			warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() - 1) + ": end of file")
		else:
			raise EOFError
	
	if sortKeys:
		items = sorted(items)

	return string + (comma + new_indent).join(items) + end

# type 85
def parse_object(fp, currrent_indent, chached_strings, chached_printable_strings):
	string = "{"
	new_indent = currrent_indent + indent
	items = []
	end = "}"
	try:
		key, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
		value, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
		string += new_indent 
		items = [key + doublepoint + value]
		end = currrent_indent + end
		while True:
			key, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
			value, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
			items.append(key + doublepoint + value)
	except KeyError as k:
		if str(k) == 'b""':
			if repairFiles:
				warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() - 1) + ": end of file")
			else:
				raise EOFError
		elif k.args[0] != b'\xff':
			raise TypeError("unknown tag " + k.args[0].hex())
	except (error, IndexError):
		if repairFiles:
			warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() - 1) + ": end of file")
		else:
			raise EOFError
	
	if sortKeys:
		items = sorted(items)

	return (string + (comma + new_indent).join(items) + end, chached_strings, chached_printable_strings)

# type 86
def parse_list(fp, currrent_indent, chached_strings, chached_printable_strings):
	code = fp.read(1)
	if code == b"":
		if repairFiles:
			warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() - 1) + ": end of file")
		else:
			raise EOFError
	elif code != b"\xfd":
		raise TypeError("List starts with " + code.hex())
	
	string = "["
	new_indent = currrent_indent + indent
	items = []
	end = "]"
	i1 = parse_number(fp)
	try:
		value, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
		string += new_indent
		items = [value]
		end = currrent_indent + end
		while True:
			value, chached_strings, chached_printable_strings = parse(fp, new_indent, chached_strings, chached_printable_strings)
			items.append(value)
	except KeyError as k:
		if str(k) == 'b""':
			if repairFiles:
				warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() - 1) + ": end of file")
			else:
				raise EOFError
		elif k.args[0] != b'\xfe':
			raise TypeError("unknown tag " + k.args[0].hex())
	except (error, IndexError):
		if repairFiles:
			warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() - 1) + ": end of file")
		else:
			raise EOFError
	
	i2 = len(items)
	if i1 != i2:
		warning_message("SilentError: " + fp.name + " pos " + str(fp.tell() -1) + ": Array of length " + str(i1) + " found, expected " + str(i2))
	
	if sortValues:
		items = sorted(sorted(items), key = lambda key : len(key))
	
	return (string + (comma + new_indent).join(items) + end, chached_strings, chached_printable_strings)

def parse(fp, current_indent, chached_strings, chached_printable_strings):
	code = fp.read(1)
	if code == b"\x85":
		return parse_object(fp, current_indent, chached_strings, chached_printable_strings)
	elif code == b"\x86":
		return parse_list(fp, current_indent, chached_strings, chached_printable_strings)
	elif code in cached_codes:
		return parse_cached_str(fp, code, chached_strings, chached_printable_strings)

	return (mappings[code](fp), chached_strings, chached_printable_strings)

cached_codes = [
	b"\x90",
	b"\x91",
	b"\x92",
	b"\x93"
]

mappings = {	
	b"\x00": lambda x: "false",
	b"\x01": lambda x: "true",
	b"\x08": parse_int8,  
	b"\x09": lambda x: "0", # int8_zero
	b"\x0a": parse_uint8,
	b"\x0b": lambda x: "0", # uint8_zero
	b"\x10": parse_int16,
	b"\x11": lambda x: "0",  # int16_zero
	b"\x12": parse_uint16,
	b"\x13": lambda x: "0", # uint16_zero
	b"\x20": parse_int32,
	b"\x21": lambda x: "0", # int32_zero
	b"\x22": parse_float,
	b"\x23": lambda x: "0.0", # float_zero
	b"\x24": parse_uvarint, # int32_uvarint
	b"\x25": parse_varint, # int32_varint
	# # only in NoBackup RTONs
	b"\x26": parse_uint32,
	b"\x27": lambda x: "0", #uint_32_zero
	b"\x28": parse_uvarint, # uint32_uvarint
	b"\x29": parse_varint, # uint32_varint?
	b"\x40": parse_int64,
	b"\x41": lambda x: "0", #int64_zero
	b"\x42": parse_double,
	b"\x43": lambda x: "0.0", # double_zero
	b"\x44": parse_uvarint, # int64_uvarint
	b"\x45": parse_varint, # int64_varint
	b"\x46": parse_uint64,
	b"\x47": lambda x: "0", # uint64_zero
	b"\x48": parse_uvarint, # uint64_uvarint
	b"\x49": parse_varint, # uint64_varint
	
	b"\x81": parse_str, # uncached string
	b"\x82": parse_printable_str, # uncached printable string
	b"\x83": parse_ref,
	b"\x84": lambda x: "null" # null reference
}

# Recursive file convert function
def conversion(inp, out, pathout):
	check = inp.lower()
	if isfile(inp) and (check.endswith(RTONExtensions) or basename(check).startswith(RTONNoExtensions)):
		noCDN = check[-5:] != ".json"
		if shortNames and noCDN:
			out = splitext(out)[0]
			 
		jfn = out + ".json"
		file = open(inp, "rb")
		try:
			if file.read(4) == b"RTON":
				data = root_object(file, current_indent)
				open(jfn, "w", encoding = "utf-8").write(data)
				print("wrote " + relpath(jfn, pathout))
			elif noCDN:
				warning_message("No RTON " + inp)
		except Exception as e:
			error_message(type(e).__name__ + " in " + inp + " pos " + str(file.tell() -1) + ": " + str(e))
	elif isdir(inp):
		makedirs(out, exist_ok = True)
		for entry in listdir(inp):
			input_file = osjoin(inp, entry)
			if isfile(input_file) or input_file != pathout:
				conversion(input_file, osjoin(out, entry), pathout)

# Start code
try:
	system("")
	if getattr(sys, "frozen", False):
		application_path = dirname(sys.executable)
	else:
		application_path = sys.path[0]

	fail = open(osjoin(application_path, "fail.txt"), "w")
	if sys.version_info[:2] < (3, 9):
		raise RuntimeError("Must be using Python 3.9")
	
	print("\033[95m\033[1mFast RTONParser v1.1.0\n(C) 2022 by 1Zulu & Nineteendo\033[0m\n")
	try:
		newoptions = load(open(osjoin(application_path, "options.json"), "rb"))
		for key in options:
			if key in newoptions:
				if type(options[key]) == type(newoptions[key]):
					options[key] = newoptions[key]
				elif isinstance(options[key], tuple) and isinstance(newoptions[key], list):
					options[key] = tuple([str(i).lower() for i in newoptions[key]])
				elif key == "Indent" and newoptions[key] == None:
					options[key] = newoptions[key]
	except Exception as e:
		error_message(type(e).__name__ + " in options.json: " + str(e))
	
	if options["comma"] > 0:
		comma = "," + " " * options["comma"]
	else:
		comma = ","

	if options["doublepoint"] > 0:
		doublepoint = ":" + " " * options["doublepoint"]
	else:
		doublepoint = ":"

	if options["indent"] == None:
		indent = current_indent = ""
	elif options["indent"] < 0:
		current_indent = "\n"
		indent = "\t"
	else:
		current_indent = "\n"
		indent = " " * options["indent"]

	ensureAscii = options["ensureAscii"]
	repairFiles = options["repairFiles"]
	RTONExtensions = options["RTONExtensions"]
	RTONNoExtensions = options["RTONNoExtensions"]
	shortNames = options["shortNames"]
	sortKeys = options["sortKeys"]
	sortValues = options["sortValues"]
	blue_print("Working directory: " + getcwd())
	pathin = path_input("Input file or directory")
	if isfile(pathin):
		pathout = path_input("Output file").removesuffix(".json")
	else:
		pathout = path_input("Output directory")
		
	# Start conversion
	start_time = datetime.datetime.now()
	conversion(pathin, pathout, dirname(pathout))
	green_print("finished converting " + pathin + " in " + str(datetime.datetime.now() - start_time))
	if fail.tell() > 0:
		print("\33[93m" + "Errors occured, check: " + fail.name + "\33[0m")

	bold_input("\033[95mPRESS [ENTER]")
except Exception as e:
	error_message(type(e).__name__ + " : " + str(e))
except BaseException as e:
	warning_message(type(e).__name__ + " : " + str(e))

# Close log
fail.close()
