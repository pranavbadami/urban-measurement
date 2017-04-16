#=========================================================
# Collect and store RF Explorer data for a given center 
# frequency and channel width.
# 
# Params: center_fq(in MHz), width(in MHz)
# Usage: python3 rf_collect.py [center_fq] [width]
#
# Author: Pranav Badami (adapted from RFExplore-for-Python)
#=========================================================

import math
import time
from datetime import datetime, timedelta
import RFExplorer
import csv
import serial.tools.list_ports
#---------------------------------------------------------
# global variables and initialization
#---------------------------------------------------------

#SERIALPORT = "/dev/cu.SLAB_USBtoUART"	  #serial port identifier, use None to autodetect
BAUDRATE = 500000
SERIALPORT = "/dev/ttyUSB0"
objRFE = RFExplorer.RFECommunicator()	  #Initialize object and thread
objRFE.m_arrValidCP2102Ports = [s for s in serial.tools.list_ports.comports() if s.device == SERIALPORT]
#TOTAL_SECONDS = 120			 #Initialize time span to display activity
MIN_FREQ = 0
MAX_FREQ = 0
STEP_FREQ = 0
center_fq = 2442

#---------------------------------------------------------
# Helper functions
#---------------------------------------------------------

def PrintData(objRFE):
	"""This function prints the amplitude and frequency peak of the latest received sweep
	"""
	nInd = objRFE.SweepData.Count-1
	objSweepTemp = objRFE.SweepData.GetData(nInd)
	#print("in PrintData")
	#print("start freq", objSweepTemp.m_fStartFrequencyMHZ, "end freq", objSweepTemp.m_fStartFrequencyMHZ + objSweepTemp.m_fStepFrequencyMHZ*len(objSweepTemp.m_arrAmplitude))
	print(objSweepTemp.m_arrAmplitude)
	#nStep = objSweepTemp.GetPeakStep()		 #Get index of the peak
	#fAmplitudeDBM = objSweepTemp.GetAmplitude_DBM(nStep)	 #Get amplitude of the peak
	#fCenterFreq = objSweepTemp.GetFrequencyMHZ(nStep)	 #Get frequency of the peak

	#print("Sweep[" + str(nInd)+"]: Peak: " + "{0:.3f}".format(fCenterFreq) + "MHz	" + str(fAmplitudeDBM) + "dBm")

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


def log_data(objRFE, writer): 
	global MIN_FREQ
	global MAX_FREQ
	global STEP_FREQ
	
	nInd = objRFE.SweepData.Count - 1
	objSweepTemp = objRFE.SweepData.GetData(nInd)
	
	now = datetime.now() - timedelta(hours=3)
	
	#initialize constants, if needed
	if not MIN_FREQ:
		MIN_FREQ = objSweepTemp.m_fStartFrequencyMHZ
		STEP_FREQ = objSweepTemp.m_fStepFrequencyMHZ
		MAX_FREQ = MIN_FREQ + STEP_FREQ*(len(objSweepTemp.m_arrAmplitude)-1)
		#MAX_FREQ = round(MAX_FREQ, 0)

	for index, signal in enumerate(objSweepTemp.m_arrAmplitude):
		if not (index % 3):
			freq = int(round(MIN_FREQ + index*STEP_FREQ))
			row = {'time': now, 'freq': freq, 'dBm': signal}
			writer.writerow(row)


#---------------------------------------------------------
# Main processing loop
#---------------------------------------------------------

try:
	#Find and show valid serial ports
	#objRFE.GetConnectedPorts()	  

	#Connect to available port
	if (objRFE.ConnectPort(SERIALPORT, BAUDRATE)):

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

			fields = ['time', 'freq', 'dBm']
			start_time = datetime.now().strftime('%m_%d_at_%H_%M')
			log = open('/home/pi/data/test_' + start_time +  '.csv', 'w')
			writer = csv.DictWriter(log, fieldnames=fields)			

			#Process until we complete scan time
			nLastDisplayIndex=0
			startTime=datetime.now()
			
			#while ((datetime.now() - startTime).seconds<TOTAL_SECONDS):    
			while True:
				#Process all received data from device 
				objRFE.ProcessReceivedString(True)
				
				#Log data if received new sweep only
				if (objRFE.SweepData.Count>nLastDisplayIndex):
					log_data(objRFE, writer)
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
if nLastDisplayIndex is not None:
	print("points", nLastDisplayIndex)
objRFE.Close()	  #Finish the thread and close port
objRFE = None 
