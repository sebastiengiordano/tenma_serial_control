import threading


class Bms3_Sequencer(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
