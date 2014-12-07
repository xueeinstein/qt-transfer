#!/usr/bin/python

import socket
import threading
"""
 Create two socket TCP server, 
 c1-->socket-1 ---> socket-2-->c2
"""

class Tun(threading.Thread):
	"""docstring for Tun"""
	def __init__(self, port_1, port_2):
		self.tun = threading.Thread(name="tun", target=self.tun)
		self._stop = threading.Event()
		self.sock_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock_1.bind(("0.0.0.0", port_1))
		self.sock_2.bind(("0.0.0.0", port_2))
		self.sock_1.listen(1)
		self.sock_2.listen(1)

	def tun(self):
		while True:
			# wait for connection
			print "sock_2 wait for connection..."
			con_2, c2_addr = self.sock_2.accept()
			print "sock_1 wait for connection..."
			con_1, c1_addr = self.sock_1.accept()
			try:
				while True:
					print "transfering..."
					data = con_1.recv(1024)
					# transfer to con_2
					con_2.send(data)
					if data.endswith(b'FIN'):
						# sender, finish
						res = con_2.recv(6)
						con_1.send(b'ACK')
						break
			finally:
				self.sock_1.close()
				self.sock_2.close()
			break

	def stop(self):
		self._stop.set()

	def stopped(self):
		return self._stop.isSet()

