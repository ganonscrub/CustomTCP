# any and all assistance with code provided by Python.org reference pages
from functions import *
			
# Here is the beginning of the program			
initSockets()
		
# Launch the listener in its own thread since it doesn't require user interaction	
receiveThread = threading.Thread( name="receive", target=receiveLoop )
receiveThread.daemon = True
receiveThread.start()

sendLoop()