import time
from datetime import datetime, timedelta
import RFExplorer
import serial
import glob
import math
import csv
import pynmea2
import threading
import random

BAUDRATE_RFE = 500000
BAUDRATE_GPS = 9600
SERIALPORT_RFE = "/dev/ttyUSB0"
SERIALPORT_GPS = "/dev/ttyAMA0"
objRFE = RFExplorer.RFECommunicator()	  #Initialize object and thread
objRFE.m_arrValidCP2102Ports = [s for s in serial.tools.list_ports.comports() if s.device == SERIALPORT_RFE]

TOTAL_SECONDS = 10			 #Initialize time span to display activity
MIN_FREQ = 0
MAX_FREQ = 0
STEP_FREQ = 0
center_fq = 2442



latitude = None
longitude = None
lat_dir = None
lon_dir = None

#---------------------------------------------------------
# RFExplorer Helper functions
#---------------------------------------------------------

def print_data(objRFE):
	"""This function prints the amplitude and frequency peak of the latest received sweep
	"""
	nInd = objRFE.SweepData.Count-1
	objSweepTemp = objRFE.SweepData.GetData(nInd)
	# print("in PrintData")
	# print("start freq", objSweepTemp.m_fStartFrequencyMHZ, "end freq", objSweepTemp.m_fStartFrequencyMHZ + objSweepTemp.m_fStepFrequencyMHZ*len(objSweepTemp.m_arrAmplitude))
	nStep = objSweepTemp.GetPeakStep()		 #Get index of the peak
	fAmplitudeDBM = objSweepTemp.GetAmplitude_DBM(nStep)	 #Get amplitude of the peak
	fCenterFreq = objSweepTemp.GetFrequencyMHZ(nStep)	 #Get frequency of the peak

	print("Sweep[" + str(nInd)+"]: Peak: " + "{0:.3f}".format(fCenterFreq) + "MHz	" + str(fAmplitudeDBM) + "dBm")

def sweep_index(freq):
	"""
	Helper function to calculate index of frequency 
	in sweep amplitude array. Index 0 is the min 
	frequency and each subsequent index adds STEP_FREQ
	"""
	diff = freq - MIN_FREQ
	index = math.floor(diff/STEP_FREQ)
	return index

def signal_strength(objRFE, freq):
	"""
	This function takes a target frequency and gets the 
	corresponding signal strength from sweep data.
	"""
	global MIN_FREQ
	global STEP_FREQ
	global MAX_FREQ

	nInd = objRFE.SweepData.Count - 1
	objSweepTemp = objRFE.SweepData.GetData(nInd)

	#initialize constants, if needed
	if not MIN_FREQ:
		MIN_FREQ = objSweepTemp.m_fStartFrequencyMHZ
		STEP_FREQ = objSweepTemp.m_fStepFrequencyMHZ
		MAX_FREQ = MIN_FREQ + STEP_FREQ*len(objSweepTemp.m_arrAmplitude)
		MAX_FREQ = round(MAX_FREQ, 0)

	if (freq < MIN_FREQ) or (freq > MAX_FREQ):
		print("Invalid frequency")
		return None

	else:
		index = sweep_index(freq)
		return objSweepTemp.m_arrAmplitude[index]

#---------------------------------------------------------
# GPS Threading
#---------------------------------------------------------
class GPSData(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
	
	def run(self):
		global latitude
		global longitude
		global lat_dir
		global lon_dir
	
		# serial definition for GPS Breakout
		gps_ser = serial.Serial(
			port = SERIALPORT_GPS,
			baudrate = BAUDRATE_GPS,
			parity = serial.PARITY_NONE,
			stopbits = serial.STOPBITS_ONE,
			bytesize = serial.EIGHTBITS,
			timeout = 1
		)	

		while True:
			#Read GPS data and save latest, valid RMC data
			try:
				gps_bytes = gps_ser.readline()
				gps_data = str(gps_bytes, 'utf-8')
				print("data", gps_data)
				gps_msg = pynmea2.parse(gps_data)

				if type(gps_msg) == pynmea2.RMC and gps_msg.status == 'A':
				#if type(gps_msg) == pynmea2.RMC:
					latitude = float(gps_msg.lat)
					longitude = float(gps_msg.lon)
					lon_dir = gps_msg.lon_dir
					lat_dir = gps_msg.lat_dir
					#latitude = random.random()
					#print("latitude", latitude)
					#longitude = random.random()
					#lon_dir = "W"
					#lat_dir = "N"
			except:
				pass

#---------------------------------------------------------
# Main processing loop
#---------------------------------------------------------
time.sleep(5)

try:

	#Connect to available port
	if (objRFE.ConnectPort(SERIALPORT_RFE, BAUDRATE_RFE)):
 
		#open log file
		num_log = len(glob.glob1("/home/pi/urban-measurement/data/", "log*.csv"))
		fields = ['time', 'frequency', 'dBm', 'latitude', 'lat_dir', 'longitude', 'lon_dir']
		log = open("/home/pi/urban-measurement/data/log" +str(num_log+1) + ".csv", "w")
		writer = csv.DictWriter(log, fieldnames=fields)
		writer.writeheader()

		#Reset the unit to start fresh
		objRFE.SendCommand("r")
		#Wait for unit to notify reset completed
		while(objRFE.IsResetEvent):
			pass
		#Wait for unit to stabilize
		time.sleep(3)

		#Request RF Explorer configuration
		objRFE.SendCommand_RequestConfigData()
		#Wait to receive configuration and model details
		while(objRFE.ActiveModel == RFExplorer.RFE_Common.eModel.MODEL_NONE):
			objRFE.ProcessReceivedString(True)	  #Process the received configuration

		#If object is an analyzer, we can scan for received sweeps
		if (objRFE.IsAnalyzer()):
			print("Receiving data...")
			#Process indefinitely
			nLastDisplayIndex=0
			startTime=datetime.now()
			
			GPSData().start()
			print("Hey")
			while True:    
				time_elapsed = (datetime.now() - startTime).seconds

								#Process all received data from RFE device 
				objRFE.ProcessReceivedString(True)
				
				#Log data if received new sweep only
				if (objRFE.SweepData.Count>nLastDisplayIndex):
					#print("whoa")
					dBm = signal_strength(objRFE, center_fq)
					if dBm is None:
						break
					#Log when new sweep data and valid RMC data
					#print("above lat check")
					if latitude is not None:
						print("passed lat check")
						
						writer.writerow({
										'time': time_elapsed,
										'frequency': center_fq, 
										'dBm': dBm,
										'latitude': latitude,
										'lat_dir': lat_dir,
										'longitude': longitude,
										'lon_dir': lon_dir
										})

						print("after writerow", dBm, latitude)
				nLastDisplayIndex=objRFE.SweepData.Count
		else:
			print("Error: Device connected is a Signal Generator. \nPlease, connect a Spectrum Analyzer")
	else:
		print("Not Connected")
except Exception as obEx:
	print("Error: " + str(obEx))

#---------------------------------------------------------
# Close object and release resources
#---------------------------------------------------------

objRFE.Close()	  #Finish the thread and close port
objRFE = None 





