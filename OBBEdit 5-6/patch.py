# Import libraries
from io import BytesIO
import sys, datetime, copy
from traceback import format_exc
from json import load
from struct import pack, unpack
from zlib import compress, decompress
from os import makedirs, listdir, system, getcwd, sep
from os.path import isdir, isfile, realpath, join as osjoin, dirname, relpath, basename, splitext

options = {
# Default options
	# SMF options
	"smfExtensions": (
		".rsb.smf",
	),
	"smfUnpackLevel": 1,
	# RSB options
	"rsbExtensions": (
		".1bsr",
		".rsb1",
		".bsr",
		".rsb",
		".rsb.smf",
		".obb"
	),
	"rsbUnpackLevel": 2,
	"rsgpEndsWith": (),
	"rsgpEndsWithIgnore": True,
	"rsgpStartsWith": (
		"packages",
		"worldpackages_"
	),
	"rsgpStartsWithIgnore": False,
	# RSGP options
	"endsWith": (
		".rton",
	),
	"endsWithIgnore": False,
	"rsgpExtensions": (
		".1bsr",
		".rsb1",
		".bsr",
		".rsb",
		".rsb.smf",
		".obb",
		".pgsr",
		".rsgp"
	),
	"rsgpUnpackLevel": 7,
	"startsWith": (
		"packages/",
	),
	"startsWithIgnore": False,
	# Encryption
	"encryptedExtensions": (
		".rton",
	),
	"encryptedUnpackLevel": 5,
	"encryptionKey": "00000000000000000000000000000000",
	# RTON options
	"comma": 0,
	"doublePoint": 1,
	"encodedUnpackLevel": 6,
	"ensureAscii": False,
	"indent": -1,
	"repairFiles": False,
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
	"sortKeys": False,
	"sortValues": False
}
def error_message(string):
# Print & log error
	string += "\n" + format_exc()
	fail.write(string + "\n")
	fail.flush()
	print("\033[91m" + string + "\033[0m")
def warning_message(string):
# Print & log warning
	fail.write("\t" + string + "\n")
	fail.flush()
	print("\33[93m" + string + "\33[0m")
def blue_print(text):
# Print in blue text
	print("\033[94m"+ text + "\033[0m")
def green_print(text):
# Print in green text
	print("\033[32m"+ text + "\033[0m")
def bold_input(text):
# Input in bold text
	return input("\033[1m"+ text + "\033[0m: ")
def path_input(text):
# Input hybrid path
	string = ""
	newstring = bold_input(text)
	while newstring or string == "":
		string = ""
		quoted = 0
		escaped = False
		tempstring = ""
		confirm = False
		for char in newstring:
			if escaped:
				if quoted != 1 and char == "'" or quoted != 2 and char == '"' or quoted == 0 and char in "\\ ":
					string += tempstring + char
					confirm = True
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
			if confirm:
				newstring = bold_input("Confirm \033[100m" + string)
	return string
def input_level(text, minimum, maximum):
# Set input level for conversion
	try:
		return max(minimum, min(maximum, int(bold_input(text + "(" + str(minimum) + "-" + str(maximum) + ")"))))
	except Exception as e:
		error_message(type(e).__name__ + " : " + str(e))
		warning_message("Defaulting to " + str(minimum))
		return minimum
# RSGP Patch functions
def rsgp_patch_data(rsgp_NAME, rsgp_OFFSET, file, pathout_data, patch, patchout, level):
# Patch RGSP file
	if file.read(4) == b"pgsr":
		data = None
		if level < 5:
			try:
				data = open(osjoin(patch, rsgp_NAME + ".section"), "rb").read()
			except FileNotFoundError:
				pass
		else:
			rsgp_VERSION = unpack("<I", file.read(4))[0]
			
			file.seek(8, 1)
			rsgp_TYPE = unpack("<I", file.read(4))[0]
			rsgp_BASE = unpack("<I", file.read(4))[0]
			
			data = None
			DATA_OFFSET = unpack("<I", file.read(4))[0]
			COMPRESSED_SIZE = unpack("<I", file.read(4))[0]
			UNCOMPRESSED_SIZE = unpack("<I", file.read(4))[0]
			if UNCOMPRESSED_SIZE != 0:
				file.seek(rsgp_OFFSET + DATA_OFFSET)
				if rsgp_TYPE <= 1: # Uncompressed files
					data = bytearray(file.read(COMPRESSED_SIZE))
				elif rsgp_TYPE == 3: # Compressed files
					blue_print("Decompressing ...")
					data = bytearray(decompress(file.read(COMPRESSED_SIZE)))
				else: # Unknown files
					raise TypeError(TYPE)
			else:
				file.seek(4, 1)
				DATA_OFFSET = unpack("<I", file.read(4))[0]
				COMPRESSED_SIZE = unpack("<I", file.read(4))[0]
				UNCOMPRESSED_SIZE = unpack("<I", file.read(4))[0]
				if UNCOMPRESSED_SIZE != 0:
					if rsgp_TYPE == 0: # Encrypted files
						# Insert decryption here
						data = bytearray(file.read(COMPRESSED_SIZE))
					elif rsgp_TYPE <= 3: # Compressed files
						file.seek(rsgp_OFFSET + DATA_OFFSET)
						blue_print("Decompressing ...")
						data = bytearray(decompress(file.read(COMPRESSED_SIZE)))
					else: # Unknown files
						raise TypeError(TYPE)
			file.seek(rsgp_OFFSET + 72)
			INFO_SIZE = unpack("<I", file.read(4))[0]
			INFO_OFFSET = rsgp_OFFSET + unpack("<I", file.read(4))[0]
			INFO_LIMIT = INFO_OFFSET + INFO_SIZE
			
			file.seek(INFO_OFFSET)
			DECODED_NAME = None
			NAME_DICT = {}
			FILE_DICT = {}
			while DECODED_NAME != "":
				FILE_NAME = b""
				temp = file.tell()
				for key in list(NAME_DICT.keys()):
					if NAME_DICT[key] + INFO_OFFSET < temp:
						NAME_DICT.pop(key)
					else:
						FILE_NAME = key
				BYTE = b""
				while BYTE != b"\x00":
					FILE_NAME += BYTE
					BYTE = file.read(1)
					LENGTH = 4 * unpack("<I", file.read(3) + b"\x00")[0]
					if LENGTH != 0:
						NAME_DICT[FILE_NAME] = LENGTH

				DECODED_NAME = FILE_NAME.decode().replace("\\", sep)
				if DECODED_NAME:
					PTX = unpack("<I", file.read(4))[0] != 0
					FILE_OFFSET = unpack("<I", file.read(4))[0]
					FILE_SIZE = unpack("<I", file.read(4))[0]
					FILE_DICT[DECODED_NAME] = {
						"FILE_INFO": file.tell(),
						"FILE_OFFSET": FILE_OFFSET
					}
					if PTX != 0:
						file.seek(20, 1)
				else:
					FILE_DICT[""] = {
						"FILE_OFFSET": UNCOMPRESSED_SIZE
					}
			DECODED_NAME = ""
			for DECODED_NAME_NEW in sorted(FILE_DICT, key = lambda key: FILE_DICT[key]["FILE_OFFSET"]):
				FILE_OFFSET_NEW = FILE_DICT[DECODED_NAME_NEW]["FILE_OFFSET"]
				NAME_CHECK = DECODED_NAME.replace("\\", "/").lower()
				if DECODED_NAME and NAME_CHECK.startswith(startsWith) and NAME_CHECK.endswith(endsWith):
					try:
						if level < 7:
							file_name = osjoin(patch, DECODED_NAME)
							patch_data = open(file_name, "rb").read()
						elif NAME_CHECK[-5:] == ".rton":
							file_name = osjoin(patch, DECODED_NAME[:-5] + ".JSON")
							patch_data = parse_json(load(open(file_name, "rb"), object_pairs_hook = encode_object_pairs).data)
						else:
							raise NotImplementedError

						if NAME_CHECK[-5:] == ".rton" and data[FILE_OFFSET: FILE_OFFSET + 2] == b"\x10\x00" and 5 < level:
							patch_data = b'\x10\x00' + rijndael_cbc.encrypt(patch_data)
						
						FILE_INFO = FILE_DICT[DECODED_NAME]["FILE_INFO"]
						FILE_SIZE = len(patch_data)
						MAX_FILE_SIZE = FILE_OFFSET_NEW - FILE_OFFSET
						data[FILE_OFFSET: FILE_OFFSET + MAX_FILE_SIZE] = patch_data + bytes(MAX_FILE_SIZE - FILE_SIZE)
						pathout_data[FILE_INFO - 4: FILE_INFO] = pack("<I", FILE_SIZE)
						print("patched " + relpath(file_name, patchout))
					except FileNotFoundError:
						pass
					except Exception as e:
						error_message(type(e).__name__ + " while patching " + file_name + ": " + str(e))
				FILE_OFFSET = FILE_OFFSET_NEW
				DECODED_NAME = DECODED_NAME_NEW
		if data != None:
			file.seek(rsgp_OFFSET + 16)
			TYPE = unpack("<I", file.read(4))[0]
			rsgp_BASE = unpack("<I", file.read(4))[0]
			
			DATA_OFFSET = unpack("<I", file.read(4))[0]
			COMPRESSED_SIZE = unpack("<I", file.read(4))[0]
			UNCOMPRESSED_SIZE = unpack("<I", file.read(4))[0]
			if UNCOMPRESSED_SIZE != 0:
				data += bytes(UNCOMPRESSED_SIZE - len(data))
				if TYPE == 0: # Encypted files
					# Insert encyption here
					pathout_data[rsgp_OFFSET + DATA_OFFSET: rsgp_OFFSET + DATA_OFFSET + COMPRESSED_SIZE] = data
				elif TYPE == 1: # Uncompressed files
					pathout_data[rsgp_OFFSET + DATA_OFFSET: rsgp_OFFSET + DATA_OFFSET + COMPRESSED_SIZE] = data
				elif TYPE == 3: # Compressed files
					blue_print("Compressing ...")
					compressed_data = compress(data, 9)
					pathout_data[rsgp_OFFSET + DATA_OFFSET: rsgp_OFFSET + DATA_OFFSET + COMPRESSED_SIZE] = compressed_data + bytes(COMPRESSED_SIZE - len(compressed_data))
				else: # Unknown files
					raise TypeError(TYPE)
			else:
				file.seek(4, 1)
				DATA_OFFSET = unpack("<I", file.read(4))[0]
				COMPRESSED_SIZE = unpack("<I", file.read(4))[0]
				UNCOMPRESSED_SIZE = unpack("<I", file.read(4))[0]
				if UNCOMPRESSED_SIZE != 0:
					if TYPE == 0: # Encypted files
						# Insert encyption here
						pathout_data[rsgp_OFFSET + DATA_OFFSET: rsgp_OFFSET + DATA_OFFSET + COMPRESSED_SIZE] = data
					elif TYPE == 1: # Compressed files
						data += bytes(UNCOMPRESSED_SIZE - len(data))
						blue_print("Compressing ...")
						compressed_data = compress(data, 9)
						pathout_data[rsgp_OFFSET + DATA_OFFSET: rsgp_OFFSET + DATA_OFFSET + COMPRESSED_SIZE] = compressed_data + bytes(COMPRESSED_SIZE - len(compressed_data))
					elif TYPE == 3: # Compressed files
						data += bytes(UNCOMPRESSED_SIZE - len(data))
						blue_print("Compressing ...")
						compressed_data = compress(data, 9)
						pathout_data[rsgp_OFFSET + DATA_OFFSET: rsgp_OFFSET + DATA_OFFSET + COMPRESSED_SIZE] = compressed_data + bytes(COMPRESSED_SIZE - len(compressed_data))
					else: # Unknown files
						raise TypeError(TYPE)
			if level < 5:
				print("patched " + relpath(osjoin(patch, rsgp_NAME + ".section"), patchout))
	return pathout_data
# Encryption algorithm based on https://en.m.wikipedia.org/wiki/Advanced_Encryption_Standard
shifts = [
	[[0, 0], [1, 3], [2, 2], [3, 1]],
	[[0, 0], [1, 5], [2, 4], [3, 3]],
	[[0, 0], [1, 7], [3, 5], [4, 4]]
]

# [encryptionKey_size][block_size] number of rounds
num_rounds = {
	16: {16: 10, 24: 12, 32: 14},
	24: {16: 12, 24: 12, 32: 14},
	32: {16: 14, 24: 14, 32: 14}
}

A = [
	[1, 1, 1, 1, 1, 0, 0, 0],
	[0, 1, 1, 1, 1, 1, 0, 0],
	[0, 0, 1, 1, 1, 1, 1, 0],
	[0, 0, 0, 1, 1, 1, 1, 1],
	[1, 0, 0, 0, 1, 1, 1, 1],
	[1, 1, 0, 0, 0, 1, 1, 1],
	[1, 1, 1, 0, 0, 0, 1, 1],
	[1, 1, 1, 1, 0, 0, 0, 1]
]
# field GF(2^m) (generator = 3)
a_log = [1]
for i in range(255):
	j = (a_log[-1] << 1) ^ a_log[-1]
	if j & 0x100 != 0:
		j ^= 0x11B
	a_log.append(j)

log = [0] * 256
for i in range(1, 255):
	log[a_log[i]] = i

# Multiply by GF(2^m)
def mul(a, b):
	if a == 0 or b == 0:
		return 0
	return a_log[(log[a & 0xFF] + log[b & 0xFF]) % 255]

# F^{-1}(x)
box = [[0] * 8 for i in range(256)]
box[1][7] = 1
for i in range(2, 256):
	j = a_log[255 - log[i]]
	for t in range(8):
		box[i][t] = (j >> (7 - t)) & 0x01

B = [0, 1, 1, 0, 0, 0, 1, 1]

# box[i] <- B + A*box[i]
cox = [[0] * 8 for i in range(256)]
for i in range(256):
	for t in range(8):
		cox[i][t] = B[t]
		for j in range(8):
			cox[i][t] ^= A[t][j] * box[i][j]

S = [0] * 256
Si = [0] * 256
for i in range(256):
	S[i] = cox[i][0] << 7
	for t in range(1, 8):
		S[i] ^= cox[i][t] << (7-t)
	Si[S[i] & 0xFF] = i

# T-Box
G = [
	[2, 1, 1, 3],
	[3, 2, 1, 1],
	[1, 3, 2, 1],
	[1, 1, 3, 2]
]

AA = [[0] * 8 for i in range(4)]

for i in range(4):
	for j in range(4):
		AA[i][j] = G[i][j]
		AA[i][i+4] = 1

for i in range(4):
	pivot = AA[i][i]
	for j in range(8):
		if AA[i][j] != 0:
			AA[i][j] = a_log[(255 + log[AA[i][j] & 0xFF] - log[pivot & 0xFF]) % 255]
	for t in range(4):
		if i != t:
			for j in range(i+1, 8):
				AA[t][j] ^= mul(AA[i][j], AA[t][i])
			AA[t][i] = 0

iG = [[0] * 4 for i in range(4)]

for i in range(4):
	for j in range(4):
		iG[i][j] = AA[i][j + 4]

def mul4(a, bs):
	if a == 0:
		return 0
	rr = 0
	for b in bs:
		rr <<= 8
		if b != 0:
			rr = rr | mul(a, b)
	return rr

T1 = []
T2 = []
T3 = []
T4 = []
T5 = []
T6 = []
T7 = []
T8 = []
U1 = []
U2 = []
U3 = []
U4 = []

for t in range(256):
	s = S[t]
	T1.append(mul4(s, G[0]))
	T2.append(mul4(s, G[1]))
	T3.append(mul4(s, G[2]))
	T4.append(mul4(s, G[3]))

	s = Si[t]
	T5.append(mul4(s, iG[0]))
	T6.append(mul4(s, iG[1]))
	T7.append(mul4(s, iG[2]))
	T8.append(mul4(s, iG[3]))

	U1.append(mul4(t, iG[0]))
	U2.append(mul4(t, iG[1]))
	U3.append(mul4(t, iG[2]))
	U4.append(mul4(t, iG[3]))

r_con = [1]
r = 1
for t in range(1, 30):
	r = mul(2, r)
	r_con.append(r)

class RijndaelCBC:
# Only CBC is defined, others are not necessary
	def __init__(self, block_size):
		if len(iv) not in (16, 24, 32):
			# The offset is not in these three and throws an exception
			raise ValueError('The iv you set (you set %s) is not within the definition requirements (16, 24, 32)!' % str(iv))
		if block_size not in (16, 24, 32):
			# Block size does not throw an exception in these three
			raise ValueError('The block_size you set (you set it as %s) is not within the definition requirement (16,24,32)!' % str(block_size))

		if len(encryptionKey) not in (16, 24, 32):
			# encryptionKey length is not in range throw exception
			raise ValueError('The encryptionKey you set (you set %s) is not within the definition requirements (16, 24, 32)!' % str(len(encryptionKey)))

		self.block_size = block_size
		rounds = num_rounds[len(encryptionKey)][block_size]
		b_c = block_size // 4
		k_e = [[0] * b_c for _ in range(rounds + 1)]
		k_d = [[0] * b_c for _ in range(rounds + 1)]
		roundEncryptionKeyCount = (rounds + 1) * b_c
		k_c = len(encryptionKey) // 4
		tk = []
		for i in range(0, k_c):
			tk.append((ord(encryptionKey[i * 4:i * 4 + 1]) << 24) | (ord(encryptionKey[i * 4 + 1:i * 4 + 1 + 1]) << 16) |
					(ord(encryptionKey[i * 4 + 2: i * 4 + 2 + 1]) << 8) | ord(encryptionKey[i * 4 + 3:i * 4 + 3 + 1]))
		t = 0
		j = 0
		while j < k_c and t < roundEncryptionKeyCount:
			k_e[t // b_c][t % b_c] = tk[j]
			k_d[rounds - (t // b_c)][t % b_c] = tk[j]
			j += 1
			t += 1
		r_con_pointer = 0
		while t < roundEncryptionKeyCount:
			tt = tk[k_c - 1]
			tk[0] ^= (S[(tt >> 16) & 0xFF] & 0xFF) << 24 ^ \
					(S[(tt >> 8) & 0xFF] & 0xFF) << 16 ^ \
					(S[tt & 0xFF] & 0xFF) << 8 ^ \
					(S[(tt >> 24) & 0xFF] & 0xFF) ^ \
					(r_con[r_con_pointer] & 0xFF) << 24
			r_con_pointer += 1
			if k_c != 8:
				for i in range(1, k_c):
					tk[i] ^= tk[i - 1]
			else:
				for i in range(1, k_c // 2):
					tk[i] ^= tk[i - 1]
				tt = tk[k_c // 2 - 1]
				tk[k_c // 2] ^= (S[tt & 0xFF] & 0xFF) ^ \
								(S[(tt >> 8) & 0xFF] & 0xFF) << 8 ^ \
								(S[(tt >> 16) & 0xFF] & 0xFF) << 16 ^ \
								(S[(tt >> 24) & 0xFF] & 0xFF) << 24
				for i in range(k_c // 2 + 1, k_c):
					tk[i] ^= tk[i - 1]
			j = 0
			while j < k_c and t < roundEncryptionKeyCount:
				k_e[t // b_c][t % b_c] = tk[j]
				k_d[rounds - (t // b_c)][t % b_c] = tk[j]
				j += 1
				t += 1
		for r in range(1, rounds):
			for j in range(b_c):
				tt = k_d[r][j]
				k_d[r][j] = (
					U1[(tt >> 24) & 0xFF] ^
					U2[(tt >> 16) & 0xFF] ^
					U3[(tt >> 8) & 0xFF] ^
					U4[tt & 0xFF]
				)
		self.Ke = k_e
		self.Kd = k_d
	def encrypt(self, source: bytes):
		# padding way
		pad_size = self.block_size - ((len(source) + self.block_size - 1) % self.block_size + 1)
		ppt = source + b'\0' * pad_size
		offset = 0

		ct = bytes()
		v = iv
		while offset < len(ppt):
			block = ppt[offset:offset + self.block_size]
			block = self.x_or_block(block, v)
			# Encrypt a group of data The size of a group is block_size
			if len(block) != self.block_size:
				raise ValueError(
					'The self.block_size: %s you set does not match the current block data size: %s' % (
						str(self.block_size),
						str(len(block))
					)
				)

			k_e = self.Ke

			b_c = self.block_size // 4
			rounds = len(k_e) - 1
			if b_c == 4:
				s_c = 0
			elif b_c == 6:
				s_c = 1
			else:
				s_c = 2
			s1 = shifts[s_c][1][0]
			s2 = shifts[s_c][2][0]
			s3 = shifts[s_c][3][0]
			a = [0] * b_c
			t = []
			for i in range(b_c):
				t.append((ord(block[i * 4: i * 4 + 1]) << 24 |
						ord(block[i * 4 + 1: i * 4 + 1 + 1]) << 16 |
						ord(block[i * 4 + 2: i * 4 + 2 + 1]) << 8 |
						ord(block[i * 4 + 3: i * 4 + 3 + 1])) ^ k_e[0][i])
			for r in range(1, rounds):
				for i in range(b_c):
					a[i] = (T1[(t[i] >> 24) & 0xFF] ^
							T2[(t[(i + s1) % b_c] >> 16) & 0xFF] ^
							T3[(t[(i + s2) % b_c] >> 8) & 0xFF] ^
							T4[t[(i + s3) % b_c] & 0xFF]) ^ k_e[r][i]
				t = copy.copy(a)
			result = []
			for i in range(b_c):
				tt = k_e[rounds][i]
				result.append((S[(t[i] >> 24) & 0xFF] ^ (tt >> 24)) & 0xFF)
				result.append((S[(t[(i + s1) % b_c] >> 16) & 0xFF] ^ (tt >> 16)) & 0xFF)
				result.append((S[(t[(i + s2) % b_c] >> 8) & 0xFF] ^ (tt >> 8)) & 0xFF)
				result.append((S[t[(i + s3) % b_c] & 0xFF] ^ tt) & 0xFF)
			block = bytes()
			for xx in result:
				block += bytes([xx])
			ct += block
			offset += self.block_size
			v = block
		return ct
	def x_or_block(self, b1, b2):
		i = 0
		r = bytes()
		while i < self.block_size:
			r += bytes([ord(b1[i:i+1]) ^ ord(b2[i:i+1])])
			i += 1
		return r
def file_to_folder(inp, out, patch, level, extensions, pathout, patchout):
# Recursive file convert function
	if isdir(inp):
		makedirs(out, exist_ok = True)
		makedirs(patch, exist_ok = True)
		for entry in sorted(listdir(inp)):
			input_file = osjoin(inp, entry)
			output_file = osjoin(out, entry)
			patch_file = osjoin(patch, entry)
			if isfile(input_file):
				file_to_folder(input_file, output_file, splitext(patch_file)[0], level, extensions, pathout, patchout)
			elif input_file != pathout and inp != patchout:
				file_to_folder(input_file, output_file, patch_file, level, extensions, pathout, patchout)
	elif isfile(inp) and inp.lower().endswith(extensions):
		try:
			file = open(inp, "rb")
			HEADER = file.read(4)
			COMPRESSED = HEADER == b"\xD4\xFE\xAD\xDE" and 2 < level
			if COMPRESSED:
				UNCOMPRESSED_SIZE = unpack("<I", file.read(4))[0]
				blue_print("Decompressing ...")
				pathout_data = decompress(file.read())
				file = BytesIO(pathout_data)
				file.name = inp
				HEADER = file.read(4)

			if HEADER == b"1bsr":
				if not COMPRESSED:
					pathout_data = HEADER + file.read()
				
				if level < 3:
					out += ".smf"
				else:
					blue_print("Preparing ...")
					pathout_data = bytearray(pathout_data)
					file.seek(40)
					FILES = unpack("<I", file.read(4))[0]
					OFFSET = unpack("<I", file.read(4))[0]
					file.seek(OFFSET)
					for i in range(0, FILES):
						FILE_NAME = file.read(128).strip(b"\x00").decode()
						FILE_NAME_TESTS = FILE_NAME.lower()
						FILE_OFFSET = unpack("<I", file.read(4))[0]
						FILE_SIZE = unpack("<I", file.read(4))[0]
						
						file.seek(68, 1)
						if FILE_NAME_TESTS.startswith(rsgpStartsWith) and FILE_NAME_TESTS.endswith(rsgpEndsWith):
							temp = file.tell()
							file.seek(FILE_OFFSET)
							try:
								if level < 4:
									file_path = osjoin(patch, FILE_NAME + ".rsgp")
									patch_data = open(file_path, "rb").read()
									pathout_data[FILE_OFFSET: FILE_OFFSET + FILE_SIZE] = patch_data + bytes(FILE_SIZE - len(patch_data))
									print("applied " + relpath(file_path, patchout))
								else:
									pathout_data = rsgp_patch_data(FILE_NAME, FILE_OFFSET, file, pathout_data, patch, patchout, level)
							except FileNotFoundError:
								pass
							except Exception as e:
								error_message(type(e).__name__ + " while patching " + relpath(file_path, patchout) + ".rsgp: " + str(e))
							file.seek(temp)
				if level < 3 or COMPRESSED:
					blue_print("Compressing ...")
					pathout_data = b"\xD4\xFE\xAD\xDE" + pack("<I", len(pathout_data)) + compress(pathout_data, level = 9)
				
				open(out, "wb").write(pathout_data)
				print("patched " + relpath(out, pathout))
			elif HEADER == b"pgsr":
				try:
					if not COMPRESSED:
						blue_print("Preparing ...")
						pathout_data = bytearray(HEADER + file.read())
					
					file.seek(0)
					pathout_data = rsgp_patch_data("data", 0, file, pathout_data, patch, patchout, level)
					open(out, "wb").write(pathout_data)
					print("patched " + relpath(out, pathout))
				except Exception as e:
					error_message(type(e).__name__ + " while patching " + relpath(file_path, patchout) + ".rsgp: " + str(e))
		except Exception as e:
			error_message("Failed OBBPatch " + type(e).__name__ + " in " + inp + " pos " + str(file.tell()) + ": " + str(e))
# JSON Encode functions
class list2:
# Extra list class
	def __init__(self, data):
		self.data = data
Infinity = [float("Infinity"), float("-Infinity")] # Inf and -inf values
def encode_bool(boolean):
# Boolian
	if boolean:
		return b"\x01"
	else:
		return b"\x00"
def encode_number(integ):
# Number with variable length
	integ, i = divmod(integ, 128)
	if (integ):
		i += 128
	string = pack("B", i)
	while integ:
		integ, i = divmod(integ, 128)
		if (integ):
			i += 128
		string += pack("B", i)
	return string
def encode_unicode(string):
# Unicode string
	encoded_string = string.encode()
	return encode_number(len(string)) + encode_number(len(encoded_string)) + encoded_string
def encode_rtid(string):
# RTID
	if "@" in string:
		name, type = string[5:-1].split("@")
		if name.count(".") == 2:
			i2, i1, i3 = name.split(".")
			return b"\x83\x02" + encode_unicode(type) + encode_number(int(i1)) + encode_number(int(i2)) + bytes.fromhex(i3)[::-1]
		else:
			return b"\x83\x03" + encode_unicode(type) + encode_unicode(name)
	else:
		return b"\x84"
def encode_int(integ):
# Number
	if integ == 0:
		return b"\x21"
	elif 0 <= integ <= 2097151:
		return b"\x24" + encode_number(integ)
	elif -1048576 <= integ <= 0:
		return b"\x25" + encode_number(-1 - 2 * integ)
	elif -2147483648 <= integ <= 2147483647:
		return b"\x20" + pack("<i", integ)
	elif 0 <= integ < 4294967295:
		return b"\x26" + pack("<I", integ)
	elif 0 <= integ <= 562949953421311:
		return b"\x44" + encode_number(integ)
	elif -281474976710656 <= integ <= 0:
		return b"\x45" + encode_number(-1 - 2 * integ)
	elif -9223372036854775808 <= integ <= 9223372036854775807:
		return b"\x40" + pack("<q", integ)
	elif 0 <= integ <= 18446744073709551615:
		return b"\x46" + pack("<Q", integ)
	elif 0 <= integ:
		return b"\x44" + encode_number(integ)
	else:
		return b"\x45" + encode_number(-1 - 2 * integ)
def encode_float(dec):
# Float
	if dec == 0:
		return b"\x23"
	elif dec != dec or dec in Infinity or -340282346638528859811704183484516925440 <= dec <= 340282346638528859811704183484516925440 and dec == unpack("<f", pack("<f", dec))[0]:
		return b"\x22" + pack("<f", dec)
	else:
		return b"\x42" + pack("<d", dec)
def encode_string(string, cached_strings):
# String
	if string in cached_strings:
		data = b"\x91" + encode_number(cached_strings[string])
	else:
		cached_strings[string] = len(cached_strings)
		encoded_string = string.encode()
		data = b"\x90" + encode_number(len(encoded_string)) + encoded_string
	return (data, cached_strings)
def parse_array(data, cached_strings):
# Array
	string = encode_number(len(data))
	for v in data:
		v, cached_strings = parse_data(v, cached_strings)
		string += v
	return (b"\x86\xfd" + string + b"\xfe", cached_strings)
def parse_object(data, cached_strings):
# Object
	string = b"\x85"
	for key, value in data:
		key, cached_strings = encode_string(key, cached_strings)
		value, cached_strings = parse_data(value, cached_strings)
		string += key + value
	return (string + b"\xff", cached_strings)
def parse_json(data):
# JSON -> RTON
	cached_strings = {}
	string = b"RTON\x01\x00\x00\x00"
	for key, value in data:
		key, cached_strings = encode_string(key, cached_strings)
		value, cached_strings = parse_data(value, cached_strings)
		string += key + value
	return string + b"\xffDONE"
def parse_data(data, cached_strings):
# Data
	if isinstance(data, str):
		if "RTID()" == data[:5] + data[-1:]:
			return (encode_rtid(data), cached_strings)
		else:
			return encode_string(data, cached_strings)
	elif isinstance(data, bool):
		return (encode_bool(data), cached_strings)
	elif isinstance(data, int):
		return (encode_int(data), cached_strings)
	elif isinstance(data, float):
		return (encode_float(data), cached_strings)
	elif isinstance(data, list):
		return parse_array(data, cached_strings)
	elif isinstance(data, list2):
		return parse_object(data.data, cached_strings)
	elif data == None:
		return (b"\x84", cached_strings)
	else:
		raise TypeError(type(data))
def conversion(inp, out, pathout, level, extension):
# Convert file
	if isfile(inp) and inp.lower()[-5:] == extension:
		try:
			file = open(inp, "rb")
			if file.read(4) != b"RTON": # Ignore CDN files
				file.seek(0)
				data = load(file, object_pairs_hook = encode_object_pairs).data
				encoded_data = parse_json(data)
				# No extension
				if out.lower()[-5:] == ".json":
					out = out[:-5]
				if "" == splitext(out)[1] and not basename(out).lower().startswith(RTONNoExtensions):
					out += ".rton"
				open(out, "wb").write(encoded_data)
				print("wrote " + relpath(out, pathout))
			elif level < 7:
				open(out,"wb").write(b'\x10\x00' + rijndael_cbc.encrypt(b"RTON" + file.read()))
				print("wrote " + relpath(out, pathout))
		except Exception as e:
			error_message(type(e).__name__ + " in " + inp + ": " + str(e))
	elif isdir(inp):
		makedirs(out, exist_ok = True)
		for entry in listdir(inp):
			input_file = osjoin(inp, entry)
			if isfile(input_file) or input_file != pathout:
				conversion(input_file, osjoin(out, entry), pathout, level, extension)
def encode_object_pairs(pairs):
# Object to list of tuples
	return list2(pairs)
# Start of the code
try:
	system("")
	if getattr(sys, "frozen", False):
		application_path = dirname(sys.executable)
	else:
		application_path = sys.path[0]
	fail = open(osjoin(application_path, "fail.txt"), "w")
	if sys.version_info[0] < 3:
		raise RuntimeError("Must be using Python 3")
	
	print("\033[95m\033[1mOBBUnpatcher v1.1.4\n(C) 2022 by Nineteendo, Luigi Auriemma, Small Pea, 1Zulu, YingFengTingYu & h3x4n1um\033[0m\n")
	try:
		newoptions = load(open(osjoin(application_path, "options.json"), "rb"))
		for key in options:
			if key in newoptions and newoptions[key] != options[key]:
				if type(options[key]) == type(newoptions[key]):
					options[key] = newoptions[key]
				elif isinstance(options[key], tuple) and isinstance(newoptions[key], list):
					options[key] = tuple([str(i).lower() for i in newoptions[key]])
				elif key == "indent" and newoptions[key] == None:
					options[key] = newoptions[key]
	except Exception as e:
		error_message(type(e).__name__ + " in options.json: " + str(e))
	
	if options["encodedUnpackLevel"] < 1:
		options["encodedUnpackLevel"] = input_level("ENCODED Unpack Level", 6, 7)
	if options["rsgpUnpackLevel"] < 1:
		options["rsgpUnpackLevel"] = input_level("RSGP/OBB/RSB/SMF Unpack Level", 3, 7)
	if options["rsbUnpackLevel"] < 1:
		options["rsbUnpackLevel"] = input_level("OBB/RSB/SMF Unpack Level", 2, 3)
	if options["smfUnpackLevel"] < 1:
		options["smfUnpackLevel"] = input_level("SMF Unpack Level", 1, 2)
	
	if options["rsgpStartsWithIgnore"]:
		rsgpStartsWith = ""
	else:
		rsgpStartsWith = options["rsgpStartsWith"]	
	if options["rsgpEndsWithIgnore"]:
		rsgpEndsWith = ""
	else:
		rsgpEndsWith = options["rsgpEndsWith"]
	
	encryptionKey = str.encode(options["encryptionKey"])
	iv = encryptionKey[4: 28]
	rijndael_cbc = RijndaelCBC(24)
	if options["endsWithIgnore"]:
		endsWith = ""
	else:
		endsWith = options["endsWith"]
	if options["startsWithIgnore"]:
		startsWith = ""
	else:
		startsWith = options["startsWith"]
	RTONNoExtensions = options["RTONNoExtensions"]

	level_to_name = ["SPECIFY", "SMF", "RSB", "RSGP", "SECTION", "ENCRYPTED", "ENCODED", "DECODED (beta)"]

	blue_print("Working directory: " + getcwd())
	if 7 >= options["encodedUnpackLevel"] > 6:
		encoded_input = path_input("ENCODED " + level_to_name[options["encodedUnpackLevel"]] + " Input file or directory")
		if isfile(encoded_input):
			encoded_output = path_input("ENCODED Output file").removesuffix(".json")
		else:
			encoded_output = path_input("ENCODED Output directory")
	if 6 >= options["encryptedUnpackLevel"] > 5:
		encrypted_input = path_input("ENCRYPTED " + level_to_name[options["encryptedUnpackLevel"]] + " Input file or directory")
		if isfile(encrypted_input):
			encrypted_output = path_input("ENCRYPTED Output file").removesuffix(".json")
		else:
			encrypted_output = path_input("ENCRYPTED Output directory")
	if 7 >= options["rsgpUnpackLevel"] > 3:
		rsgp_input = path_input("RSGP/OBB/RSB/SMF Input file or directory")
		if isfile(rsgp_input):
			rsgp_output = path_input("RSGP/OBB/RSB/SMF Modded file")
		else:
			rsgp_output = path_input("RSGP/OBB/RSB/SMF Modded directory")
		rsgp_patch = path_input("RSGP/OBB/RSB/SMF " + level_to_name[options["rsgpUnpackLevel"]] + " Patch directory")
	if 3 >= options["rsbUnpackLevel"] > 2:
		rsb_input = path_input("OBB/RSB/SMF Input file or directory")
		if isfile(rsb_input):
			rsb_output = path_input("OBB/RSB/SMF Modded file")
		else:
			rsb_output = path_input("OBB/RSB/SMF Modded directory")
		rsb_patch = path_input("OBB/RSB/SMF " + level_to_name[options["rsbUnpackLevel"]] + " Patch directory")
	
	if 2 >= options["smfUnpackLevel"] > 1:
		smf_input = path_input("SMF " + level_to_name[options["smfUnpackLevel"]] + " Input file or directory")
		if isfile(smf_input):
			smf_output = path_input("SMF Output file")
		else:
			smf_output = path_input("SMF Output directory")

	# Start file_to_folder
	start_time = datetime.datetime.now()
	if 7 >= options["encodedUnpackLevel"] > 6:
		conversion(encoded_input, encoded_output, dirname(encoded_output), options["encodedUnpackLevel"], ".json")
	if 6 >= options["encryptedUnpackLevel"] > 5:
		conversion(encrypted_input, encrypted_output, dirname(encrypted_output), options["encryptedUnpackLevel"], ".rton")
	if 7 >= options["rsgpUnpackLevel"] > 3:
		file_to_folder(rsgp_input, rsgp_output, rsgp_patch, options["rsgpUnpackLevel"], options["rsgpExtensions"], dirname(rsgp_output), rsgp_patch)
	if 3 >= options["rsbUnpackLevel"] > 2:
		file_to_folder(rsb_input, rsb_output, rsb_patch, options["rsbUnpackLevel"], options["rsbExtensions"], dirname(rsb_output), rsb_patch)
	if 2 >= options["smfUnpackLevel"] > 1:
		file_to_folder(smf_input, smf_output, smf_output, options["smfUnpackLevel"], options["rsbExtensions"], dirname(smf_output), dirname(smf_output))

	green_print("finished patching in " + str(datetime.datetime.now() - start_time))
	if fail.tell() > 0:
		print("\33[93m" + "Errors occured, check: " + fail.name + "\33[0m")
	bold_input("\033[95mPRESS [ENTER]")
except Exception as e:
	error_message(type(e).__name__ + " : " + str(e))
except BaseException as e:
	warning_message(type(e).__name__ + " : " + str(e))
fail.close() # Close log