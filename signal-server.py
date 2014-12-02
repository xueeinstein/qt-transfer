#!/usr/bin/python

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import json
import cgi

class UsersModel():
    """ Model: define user data structure"""
    def __init__(self):
        self.users = dict()

    def addUser(self, name, passwd):
        # check whether use already exist
        if name in self.users:
            return "error->"
        else:
            self.users[name] = dict()
            self.users[name]['passwd'] = passwd
            print self.users
            return self.login(name, passwd)

    def login(self, name, passwd):
        if name in self.users:
            if self.users[name]['passwd'] == passwd:
                return "redirect->ctrlpanel"
            else:
                return "redirect->login"
        else:
            print "no user"

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

        # Echo back information about what was posted in the form
        print form.getvalue('action')
        if "action" in form:
            if form.getvalue('action') == "signup":
                username = form.getvalue('username')
                passwd = form.getvalue('passwd')
                msg = usersData.addUser(username, passwd)
                self.wfile.write(msg)
            elif form.getvalue('action') == "login":
                username = form.getvalue('username')
                passwd = form.getvalue('passwd')
                msg = usersData.login(username, passwd)
                self.wfile.write(msg)
            else:
                pass
        else:
            print "no action in form"
        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

usersData = UsersModel()

if __name__ == '__main__':
    server = ThreadedHTTPServer(('localhost', 8080), Handler)
    print 'Starting server, use <Ctrl-C> to stop'
    server.serve_forever()