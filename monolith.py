# any and all assistance with code provided by Python.org reference pages
from functions import *
			
# Here is the beginning of the program			
initSockets()
		
# Launch the listener in its own thread since it doesn't require user interaction	
receiveThread = threading.Thread( name="receive", target=receivePackets )
receiveThread.daemon = True
receiveThread.start()

# sendPackets is essentially the main function of this program
# it will keep prompting the user for data to send until the program is killed
sendPackets()