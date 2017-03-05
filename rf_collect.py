#=========================================================
# Collect and store RF Explorer data for a given center 
# frequency and channel width.
# 
# Params: center_fq(in MHz), width(in MHz)
# Usage: python3 rf_collect.py [center_fq] [width]
#
# Author: Pranav Badami (adapted from RFExplore-for-Python)
#=========================================================

import time
from datetime import datetime, timedelta
import RFExplorer

#---------------------------------------------------------
# global variables and initialization
#---------------------------------------------------------

#SERIALPORT = "/dev/cu.SLAB_USBtoUART"    #serial port identifier, use None to autodetect
BAUDRATE = 500000
SERIALPORT = "/dev/ttyUSB0"
objRFE = RFExplorer.RFECommunicator()     #Initialize object and thread
TOTAL_SECONDS = 10           #Initialize time span to display activity
PRINT_COUNT = 0
#---------------------------------------------------------
# Helper functions
#---------------------------------------------------------

def PrintData(objRFE):
    """This function prints the amplitude and frequency peak of the latest received sweep
	"""
    nInd = objRFE.SweepData.Count-1
    objSweepTemp = objRFE.SweepData.GetData(nInd)
    print("in PrintData")
    print("start freq", objSweepTemp.m_fStartFrequencyMHZ, "end freq", objSweepTemp.m_fStartFrequencyMHZ + objSweepTemp.m_fStepFrequencyMHZ*len(objSweepTemp.m_arrAmplitude))
    #nStep = objSweepTemp.GetPeakStep()      #Get index of the peak
    #fAmplitudeDBM = objSweepTemp.GetAmplitude_DBM(nStep)    #Get amplitude of the peak
    #fCenterFreq = objSweepTemp.GetFrequencyMHZ(nStep)   #Get frequency of the peak

    #print("Sweep[" + str(nInd)+"]: Peak: " + "{0:.3f}".format(fCenterFreq) + "MHz  " + str(fAmplitudeDBM) + "dBm")

#---------------------------------------------------------
# Main processing loop
#---------------------------------------------------------

try:
    #Find and show valid serial ports
    objRFE.GetConnectedPorts()    

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
            objRFE.ProcessReceivedString(True)    #Process the received configuration

        #If object is an analyzer, we can scan for received sweeps
        if (objRFE.IsAnalyzer()):     
            print("Receiving data...")
            #Process until we complete scan time
            nLastDisplayIndex=0
            startTime=datetime.now()
            while ((datetime.now() - startTime).seconds<TOTAL_SECONDS):    
                #Process all received data from device 
            	objRFE.ProcessReceivedString(True)
                #Print data if received new sweep only
            	if (objRFE.SweepData.Count>nLastDisplayIndex):
                	PrintData(objRFE)
                	PRINT_COUNT += 1      
            	nLastDisplayIndex=objRFE.SweepData.Count
            	if (PRINT_COUNT): break
        else:
            print("Error: Device connected is a Signal Generator. \nPlease, connect a Spectrum Analyzer")
    else:
        print("Not Connected")
except Exception as obEx:
    print("Error: " + str(obEx))

#---------------------------------------------------------
# Close object and release resources
#---------------------------------------------------------

objRFE.Close()    #Finish the thread and close port
objRFE = None 
