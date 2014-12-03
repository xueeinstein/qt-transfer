""" signal server """
signal_server_host = "127.0.0.1"
signal_server_port = 8080
signal_server_port_udp = 1337

""" router """

""" views
register.html: first-time register, unique username
about.html: about page of qt-transfer
help.html: help page of qt-transfer
controlPanel.html: auto-login and redirect to this page, 
	graph shows available resources 
"""
router = {
	"login": "views/login.html",
	"signup": "views/signup.html",
	"ctrlpanel": "views/control-panel.html",
	"recvfile": "views/recv-file.html"
}

""" transferDir """
transferDir = "transferDir"
