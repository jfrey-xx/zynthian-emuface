#!/usr/bin/python3
# -*- coding: utf-8 -*-


from zynthian_emuface import MainWindow

import threading, time, liblo, sys, os, signal, QtGui

OSC_PORT=4567


class OSCWindow(MainWindow):
    """ let's put some OSC in the mix """
    
    def __init__(self):       
         # create server, listening on port 1234
        try:
            self.server = liblo.Server(OSC_PORT)
        except liblo.ServerError as err:
            print(str(err))
            sys.exit()
    
        # register method taking an int and a float
        self.server.add_method("/zyn/encoder", 'if', self.osc_encoder)
        self.server.add_method("/zyn/press", 'i', self.osc_press)
        self.server.add_method("/zyn/release", 'i', self.osc_release)

        # default callback
        self.server.add_method(None, None, self.osc_fallback)
        # start to listen
        self.stop_event=threading.Event()
        self.c_thread=threading.Thread(target=self.OSCListener, args=(self.stop_event,))
        self.c_thread.start() 
        
        print("launch OSC server")
        super(OSCWindow, self).__init__()


    def OSCListener(self,stop_event):
        state=True
        while state and not stop_event.isSet():
            print("listen")
            self.server.recv(100)
        
    def closeEvent(self, event):
        # terminating OSC thread
        self.stop_event.set()
        self.close()   
        super(OSCWindow, self).closeEvent(event)

    def osc_press(self, path, args):
        i = args
        print("received press message '%s' with arguments '%d'" % (path, i))
        if i < 0:
            i = 0
        elif i > 3:
            i = 3
        self.cb_switch_press(i)
        
    def osc_release(self, path, args):
        i = args
        print("received release message '%s' with arguments '%d'" % (path, i))
        if i < 0:
            i = 0
        elif i > 3:
            i = 3
        self.cb_switch_release(i)
        
    def osc_encoder(self, path, args):
        i, v = args
        print("received encoder message '%s' with arguments '%d' and '%f'" % (path, i, v))
        
        # sanitize encoder number
        if i < 0:
            i = 0
        elif i > 3:
            i = 3
            
        # sanitize encoder value, don't try to change more than 127
        if v > 127:
            v = 127
        elif v < -127:
            v = -127
        
        # change value
        if v > 0:
            while v > 0:
                self.inc_encoder(i)
                v-=1
        elif v < 0:
            while v < 0:
                self.dec_encoder(i)
                v+=1      
    
    def inc_encoder(self, i):
        print("inc")
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i]+1)
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i]+1)
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i])
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i])
        time.sleep(0.01)

    def dec_encoder(self, i):
        print("dec")
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i]+1)
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i]+1)
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_b[i])
        time.sleep(0.01)
        os.kill(self.zynthian_pid, signal.SIGRTMIN+2*self.rencoder_pin_a[i])
        time.sleep(0.01)

        
    def osc_fallback(self, path, args, types, src):
        print("got unknown message '%s' from '%s'" % (path, src.url))
        
        for a, t in zip(args, types):
            print("argument of type '%s': %s" % (t, a))
        

print("Go OSC")
app = QtGui.QApplication(sys.argv)

my_mainWindow = OSCWindow()
my_mainWindow.show()

sys.exit(app.exec_())
