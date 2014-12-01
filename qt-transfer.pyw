#!/usr/bin/env python

import sys
import logging
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *

import config
import assets_rc

""" views
register.html: first-time register, unique username
about.html: about page of qt-transfer
help.html: help page of qt-transfer
controlPanel.html: auto-login and redirect to this page, 
	graph shows available resources 
"""

class PyJs(QWebPage):
    """
    Makes it possible to use a Python logger to print javascript console messages
    """
    def __init__(self, window, logger=None, parent=None):
        super(PyJs, self).__init__(parent)
        if not logger:
            logger = logging
        self.logger = logger
        self.ctrl = Controller(window)

    def javaScriptConsoleMessage(self, msg, lineNumber, sourceID):
        if sourceID == "qrc:/":
            self.ctrl.resolve(msg)
            self.logger.warning("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))
        else:
            self.logger.warning("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))

class Controller():
    """Controller class"""
    def __init__(self, window):
        self.window = window

    def resolve(self, msg):
        """ classify action """
        action = msg.split('->')[0]
        if action == "redirect":
            self.redirect(msg.split('->')[1])
        else:
            pass

    def redirect(self, dest):
        if str(dest) in config.router:
            try:
                html = open(config.router[str(dest)]).read()
            except Exception, e:
                raise e
            self.window.view.setHtml(html, QUrl('qrc:/'))
        else:
            self.window.callback.cometError("No router!");
            print "no router"

class Callback(QObject):
    """Callback to font-end"""
    def __init__(self, Qo):
        super(Callback, self).__init__(Qo)
        self.err = ""

    def cometError(self, err):
        self.err = err
        print "cometError"

    @pyqtSlot(result=str)
    def error(self):
        return self.err
                        
class MainWindow(QWidget):
    """ define main window """
    def __init__(self):
        super(MainWindow, self).__init__()
        self.view = QWebView(self)
        self.callback = Callback(self)
        self.view.setPage(PyJs(self))
        self.view.page().mainFrame().\
            addToJavaScriptWindowObject("callback", self.callback)
        
        self.resize(800, 600)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    html = open(sys.argv[1]).read()
    window.show()
    window.view.setHtml(html, QUrl('qrc:/'))
    sys.exit(app.exec_())
