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

class UsersModel():
    """ Model: define user data structure"""
    def __init__(self):
        self.users = dict()

    def addUser(self, name, passwd):
        # check whether use already exist
        if name in self.users:
            return "error->user already exist"
        else:
            self.users[name] = dict()
            self.users[name]['passwd'] = passwd
            self.users[name]['files'] = []
            self.users[name]['status'] = "active"
            print self.users
            return self.login(name, passwd)

    def login(self, name, passwd):
        if name in self.users:
            if self.users[name]['passwd'] == passwd:
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
            else:
                pass
        else:
            print "no action in form"
        return

    def generateFilesNetData(self):
        filesNetData = []
        for i in usersData.users:
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
                sent = self.sock.sendto("Ok", address)
                print "res Ok"

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
                usersData.users[name]['lastActive'] = time.time()
        # to give them the same standard, and increase efficiency
        curr = time.time()
        for user in usersData.users:
            if curr - usersData.users[user]['lastActive'] > 8 and\
                usersData.users[user]['status'] == "active":
                usersData.users[user]['status'] = "disconnect"
                isChanged = True

        if isChanged:
            # broadcast this change
            print usersData.users
            pass

        return

    def broadcast(self):
        pass

    def serve_forever(self):
        self.daemonThread.start()
        self.server.serve_forever()

usersData = UsersModel()
server_http = ThreadedHTTPServer(('', 8080), Handler)
if __name__ == '__main__':
    print 'Starting server, use <Ctrl-C> to stop'
    server_http.serve_forever()