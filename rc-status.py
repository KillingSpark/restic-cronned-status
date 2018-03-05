import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GLib
import httplib2
import json
import threading
import time
import datetime

QUEUE_BASE_URL = "http://127.0.0.1:8080"
QUEUE_UPDATE_TIMER = 1 #seconds

class TrayIcon(Gtk.StatusIcon):
    def __init__(self):
        Gtk.StatusIcon.__init__(self)
        self.set_from_icon_name('help-about')
        self.set_visible(True)
        self.connect("button-press-event", self.on_click)
        self.job_progbars = {}
        self.job_menu = Gtk.Menu() #progressbars leftclick
        self.service_menu = Gtk.Menu() #exitbutton rightclick
        
        
        self.conn = httplib2.Http("/home/moritz/.cache")
        self.init_menu()

    def init_menu(self):
        btn = Gtk.MenuItem(label="Exit")
        btn.connect("activate", Gtk.main_quit)
        self.service_menu.append(btn)

        btn = Gtk.MenuItem(label = "Stop all jobs (stops the queue!)")
        def stopAll(w):
            self.conn.request(QUEUE_BASE_URL+"/stopall", "GET")
        btn.connect("activate", stopAll)
        self.service_menu.append(btn)

        self.readQueue()

    def readQueue(self):
        try:
            (_, content) = self.conn.request(QUEUE_BASE_URL+"/queue", "GET")
            data = json.loads(content.decode("UTF-8"))
            for job in data["Jobs"]:
                name = job["JobName"]
                if name not in self.job_progbars:
                    self.prepare_new_job_menu_item(name)
                self.update_progressbar(name, job)
        except Exception as e:
            print(e)

    def update_progressbar(self, name, job):
        #if it is a periodic job display waitprogress. Otherwise the values are unuseful
        status = job["status"]
        text = name+": "+status
        reg_timer = job["regularTimer"]
        current_retry = job["CurrentRetry"]
        max_failed_retries = job["maxFailedRetries"]
        if int(current_retry) > 0:
            text += "  retry: " + str(current_retry) + "/" + str(max_failed_retries)

        if status == "waiting":
            if (reg_timer > 0 or current_retry > 0):
                wait_start = job["WaitStart"]
                wait_end = job["WaitEnd"]
                start = float(time.time()*1000000000 - wait_start)
                end = float(wait_end - wait_start)
                if end == 0:
                    end += 0.1
                self.job_progbars[name].set_fraction(start/end)
                
                remainingSecs = (end - start)//1000000000+1
                seconds =   int(remainingSecs % 60)
                minutes =   int((remainingSecs // 60) % 60)
                hours =     int((remainingSecs // 3600) % 3600)
                days =      int((remainingSecs // (3600*24)))
                text += " (remaining: " + "{}:{}:{}:{}".format(days, hours, minutes, seconds) + ")"
            else:
                self.job_progbars[name].set_fraction(0)
        elif status == "working":
            self.job_progbars[name].set_fraction(1)
        else:
            self.job_progbars[name].set_fraction(0)

        self.job_progbars[name].set_text(text)

    def prepare_new_job_menu_item(self, name):
        self.job_progbars[name] = Gtk.ProgressBar()
        self.job_progbars[name].set_show_text(True)
        box = Gtk.HBox()
        box.pack_start(self.job_progbars[name],True,True,0)
        item = Gtk.MenuItem()
        item.add(box)
        submenu = Gtk.Menu()
        stopItem = Gtk.MenuItem(label="Stop")
        submenu.append(stopItem)
        stopItem.name = name
        def stopJob(item):
            self.conn.request(QUEUE_BASE_URL+"/stop?name="+item.name, "GET")
        stopItem.connect("activate",stopJob)
        restartItem = Gtk.MenuItem(label="Restart")
        submenu.append(restartItem)
        restartItem.name = name
        def restartJob(item):
            self.conn.request(QUEUE_BASE_URL+"/restart?name="+item.name, "GET")
        restartItem.connect("activate",restartJob)
        item.set_submenu(submenu)
        self.job_menu.append(item)

    def loop_queue_update(self):
        while True:
            GLib.idle_add(lambda w: self.readQueue(), None)
            time.sleep(QUEUE_UPDATE_TIMER)

    def on_click(self, data, event):
        if event.button == 1:
            self.job_menu.show_all()
            self.job_menu.popup(None,None,None,self,event.button,event.time)
        else:
            self.service_menu.show_all()
            self.service_menu.popup(None,None,None,self,event.button,event.time)

if __name__ == '__main__':
    GObject.threads_init()
    tray = TrayIcon()
    t = threading.Thread(target=tray.loop_queue_update)
    t.daemon = True
    t.start()
    Gtk.main()
