import time
import serial
import glob

time.sleep(10)

ser = serial.Serial(
	port = '/dev/ttyAMA0',
	baudrate = 9600,
	parity = serial.PARITY_NONE,
	stopbits = serial.STOPBITS_ONE,
	bytesize = serial.EIGHTBITS,
	timeout = 1
)

count = 0

num_log = len(glob.glob1("/home/pi/urban-measurement/", "log*.txt"))

with open("/home/pi/urban-measurement/log" +str(num_log) + ".txt", "wb") as f:
	while 1:
		x = ser.readline()	
		f.write(x)
		f.write(str.encode("\n"))	
