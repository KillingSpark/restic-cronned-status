import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GLib
import httplib
import json
import threading
import time

GObject.threads_init()


class TrayIcon(Gtk.StatusIcon):
    def __init__(self):
        Gtk.StatusIcon.__init__(self)
        self.set_from_icon_name('help-about')
        self.set_has_tooltip(True)
        self.set_visible(True)
        self.connect("activate", self.on_click)
        self.window = Gtk.Window()
        self.job_box = Gtk.VBox()
        self.main_box = Gtk.VBox()
        self.main_box.add(self.job_box)
        self.job_labels = {}
        self.job_buttons = {}
        self.init_window()

    def init_window(self):
        self.window.set_gravity(Gdk.Gravity.SOUTH_EAST)
        self.win_show = False
        self.window.set_decorated(False)
        self.window.resize(600, 300)
        self.update_window_placement()
        self.window.connect("focus-out-event", lambda w, s: self.on_click(1))

        control_box = Gtk.HBox()

        btn = Gtk.Button(label="Exit")
        btn.connect("clicked", Gtk.main_quit)
        btn.set_size_request(-1, 20)
        control_box.add(btn)

        self.main_box = Gtk.VBox()
        self.main_box.pack_start(self.job_box,True,True,0)
        self.main_box.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL),False,False,0)
        self.main_box.pack_end(control_box,False,False,0)

        self.window.add(self.main_box)
        self.readQueue()

    def readQueue(self):
        conn = httplib.HTTPConnection("127.0.0.1:8080")
        conn.request("GET", "/queue")
        res = conn.getresponse()
        data = json.loads(res.read())
        for job in data["Jobs"]:
            name = job["JobName"]
            status = job["status"]
            current_retry = job["CurrentRetry"]
            if name not in self.job_labels:
                self.job_labels[name] = Gtk.ProgressBar()
                self.job_labels[name].set_show_text(True)
                self.job_buttons[name] = Gtk.Button()
                box = Gtk.HBox()
                box.pack_start(self.job_labels[name],True,True,0)
                box.pack_start(self.job_buttons[name],False,False,0)
                self.job_box.pack_start(box, True, True, 2)
                self.job_box.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL),False,False,0)
            text = name+": "+status
            if int(current_retry) > 0:
                text += "  retry: " + str(current_retry) + "/" + str(job["maxFailedRetries"])
            self.job_labels[name].set_text(text)
            
            start = float(time.time()*1000000000 - job["WaitStart"])
            end = float(job["WaitEnd"] - job["WaitStart"])
            
            self.job_labels[name].set_fraction(start/end)
            if status in ["ready", "finished"]:
                self.job_buttons[name].set_label("start")
            if status in ["working", "waiting"]:
                self.job_buttons[name].set_label("stop")

        return False

    def updateQueue(self):
        while True:
            GLib.idle_add(lambda w: self.readQueue(), None)
            time.sleep(0.2)

    def on_click(self, data):

        if self.win_show:
            self.window.hide()
        else:
            self.window.show_all()
            self.update_window_placement()
        self.win_show = not self.win_show

    def update_window_placement(self):
        self.window.move(Gdk.Screen.width() - self.window.get_size().width, Gdk.Screen.height() - self.window.get_size().height - 30)


if __name__ == '__main__':
    tray = TrayIcon()
    t = threading.Thread(target=tray.updateQueue)
    t.daemon = True
    t.start()
    Gtk.main()
