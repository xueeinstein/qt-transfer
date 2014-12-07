#!/usr/bin/python

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import socket
import select
import time
import threading
import json
import cgi
import ast

from tun import *

class UsersModel():
    """ Model: define user data structure"""
    def __init__(self):
        self.users = dict()
        self.userFilesUpate = False

    def addUser(self, name, passwd):
        # check whether use already exist
        if name in self.users:
            return "error->user already exist"
        else:
            self.users[name] = dict()
            self.users[name]['passwd'] = passwd
            self.users[name]['files'] = []
            self.users[name]['fileFrom'] = []
            self.users[name]['fileRes'] = ""
            self.users[name]['status'] = "active"
            self.users[name]['lastActive'] = 0 # mark as just login
            print self.users
            return self.login(name, passwd)

    def login(self, name, passwd):
        if name in self.users:
            if self.users[name]['passwd'] == passwd:
                self.users[name]['status'] = "active"
                print "new user login!!"
                print self.users
                return "redirect->ctrlpanel->" + name
            else:
                return "error->password error"
        else:
            return "error->user doesn\'t exist"

    def updateFiles(self, name, files):
        if name in self.users:
            self.users[name]['files'] = files
            self.userFilesUpate = True
            print "user files update!!"
            print self.users
            return

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)
        message_parts = [
                'CLIENT VALUES:',
                'client_address=%s (%s)' % (self.client_address,
                                            self.address_string()),
                'command=%s' % self.command,
                'path=%s' % self.path,
                'real path=%s' % parsed_path.path,
                'query=%s' % parsed_path.query,
                'request_version=%s' % self.request_version,
                '',
                'SERVER VALUES:',
                'server_version=%s' % self.server_version,
                'sys_version=%s' % self.sys_version,
                'protocol_version=%s' % self.protocol_version,
                '',
                'HEADERS RECEIVED:',
                ]
        for name, value in sorted(self.headers.items()):
            message_parts.append('%s=%s' % (name, value.rstrip()))
        message_parts.append('')
        message = '\r\n'.join(message_parts)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(message)
        return
    def do_POST(self):
    	# Parse the form data posted
        form = cgi.FieldStorage(
            fp=self.rfile, 
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })

        # Begin the response
        self.send_response(200)
        self.end_headers()
        # self.wfile.write('Client: %s\n' % str(self.client_address))
        # self.wfile.write('User-agent: %s\n' % str(self.headers['user-agent']))
        # self.wfile.write('Path: %s\n' % self.path)
        # self.wfile.write('Form data:\n')
        print "============="
        print self.client_address[0]
        print self.client_address[1]
        print "============="

        # Echo back information about what was posted in the form
        print form.getvalue('action')
        if "action" in form:
            action = form.getvalue('action')
            if  action == "signup":
                username = form.getvalue('username')
                passwd = form.getvalue('passwd')
                # currIP = 
                msg = usersData.addUser(username, passwd)
                self.wfile.write(msg)
            elif action == "login":
                username = form.getvalue('username')
                passwd = form.getvalue('passwd')
                msg = usersData.login(username, passwd)
                self.wfile.write(msg)
            elif action == "updateFiles":
                # print type(form.getvalue('name'))
                name = form.getvalue('name')
                print name
                # I don't know the reason why here files list str is unicode
                uStr = form.getvalue('files')
                files_list = ast.literal_eval(uStr)
                encode = lambda x: {'name': x['name'].encode('ascii'), 'key': x['key'].encode('ascii')}
                files_list = [encode(x) for x in files_list]
                print type(files_list), files_list
                msg = usersData.updateFiles(name, files_list)
                self.wfile.write("redirect->ctrlpanel")
            elif action == "queryFilesData":
                lastUpdateTime = float(form.getvalue('lastUpdateTime'))
                print "file-net data lastUpdateTime:", lastUpdateTime
                if lastUpdateTime < time.time():
                    newData = self.generateFilesNetData()
                    print "====new file-net===="
                    print newData
                    print "====new file-net===="
                    self.wfile.write("data->"+newData)
                else:
                    print "get file-net error!!!!!!!!!!!"
            elif action == "sendFile":
                # call receiver through recording receivers' fileFrom
                tmp_thread = Tun(8000, 8888)
                receiver = form.getvalue('receiver')
                sender = form.getvalue('sender')
                usersData.users[receiver]['fileFrom'].append(sender)
                tmp_thread.tun.start()
                # self.wfile.write()
            elif action == "accept":
                sender = form.getvalue('sender')
                usersData.users[sender]['fileRes'] = "accept"
            else:
                pass
        else:
            print "no action in form"
        return

    def generateFilesNetData(self):
        filesNetData = []
        for i in usersData.users:
            if usersData.users[i]['status'] == "active":
                tmp_dict = dict()
                tmp_dict['name'] = i
                tmp_dict['key'] = i
                tmp_dict['count'] = len(usersData.users[i]['files'])
                tmp_dict['files'] = usersData.users[i]['files']
                filesNetData.append(tmp_dict)
        strJson = json.dumps(filesNetData)
        return strJson


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    def __init__(self, addr, handler):
        self.server = HTTPServer(addr, handler)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # set unblock socket
        # self.sock.setblocking(0)
        self.daemonThread = threading.Thread(name="daemon", target=self.daemon)
        self.daemonThread.setDaemon(True)
        print "udp recv"
        self.server_addr = ('0.0.0.0', 1337)
        print 'starting up on %s port %s' % self.server_addr
        self.sock.bind(self.server_addr)

    def daemon(self):
        # counter, record total board casted users 
        # clients diagram in format: 'name:active'
        while True:
            data = ""
            address = ""
            print '\nwaiting to receive message'
            ready = select.select([self.sock], [], [], 6)
            if ready[0]:
                data, address = self.sock.recvfrom(4096)
    
            self.updateUserStatus(data, address)
            print 'received %s bytes from %s: %s' % (len(data), address, data)
            if data:
                user = data.split(':')[0]
                if len(usersData.users[user]['fileFrom']) != 0:
                    # here, this user got some send-file query
                    tmp_list = []
                    for i in usersData.users[user]['fileFrom']:
                        tmp_dict = dict()
                        tmp_dict['sender'] = i
                        tmp_dict['address'] = usersData.users[i]['address']
                        tmp_list.append(tmp_dict)
                    tmp_str = json.dumps(tmp_list)
                    for j in range(4):
                        # try multi-times
                        sent = self.sock.sendto("Ok->query->"+tmp_str, address)
                    usersData.users[user]['fileFrom'] = []
                else:
                    sent = self.sock.sendto("Ok->", address)
                    print "res Ok"

                if usersData.users[user]['fileRes'] == "accept":
                    receiverAddr = usersData.users[user]['address'][0] + "->" +\
                        str(usersData.users[user]['address'][1])
                    for i in range(1):
                        sent = self.sock.sendto("Ok->accept->"+receiverAddr, address)
                    usersData.users[user]['fileRes'] = ""

    def updateUserStatus(self, data, address):
        """ 
        according to data & address, update active time
        scan all user, check timeout
        """
        isChanged = False
        if data != "" and address != "":
            data_list = data.split(':')
            name = data_list[0]
            userStatus = data_list[1]
            if userStatus == "active":
                # update 
                if usersData.users[name]['lastActive'] == 0:
                    # user just login 
                    isChanged = True
                usersData.users[name]['lastActive'] = time.time()
                usersData.users[name]['address'] = address
        # to give them the same standard, and increase efficiency
        curr = time.time()
        # disconnect update
        for user in usersData.users:
            if curr - usersData.users[user]['lastActive'] > 8 and\
                usersData.users[user]['status'] == "active":
                usersData.users[user]['status'] = "disconnect"
                isChanged = True
        # files update
        if usersData.userFilesUpate:
            isChanged = True
            usersData.userFilesUpate = False

        if isChanged:
            # broadcast this change
            self.broadcast(time.time())
            print usersData.users

        return

    def broadcast(self, time):
        # set broadcast times
        counter = 3
        for j in range(counter):
            for i in usersData.users:
                if usersData.users[i]['status'] == "active":
                    self.sock.sendto(str(time), usersData.users[i]['address'])
        return

    def serve_forever(self):
        self.daemonThread.start()
        self.server.serve_forever()

usersData = UsersModel()
server_http = ThreadedHTTPServer(('', 8080), Handler)
if __name__ == '__main__':
    print 'Starting server, use <Ctrl-C> to stop'
    server_http.serve_forever()