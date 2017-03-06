import operator
def checksum(sentence):
    sentence = sentence.strip('\n')
    nmeadata,cksum = sentence.split('*', 1)
    calc_cksum = reduce(operator.xor, (ord(s) for s in nmeadata), 0)

    return nmeadata,int(cksum,16),calc_cksum



write = open("./valid1.txt", "w")
with open("./log1.txt", "r") as orig:
	for line in orig.readlines():
		if "GPRMC" in line and "V" not in line:
			write.write(line)
			nmeadata, cksum, calc_cksum = checksum(line)
			print("nmeadata:" + nmeadata + " cksum:" + str(cksum) + " calc_cksum:" + str(calc_cksum))
			

