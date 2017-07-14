
import time
import random 
import math 

class Channel():
    def __init__(self, desc):
        self.nodeList = [] 
        self.desc = desc
        self.occupiedId = None

    def add_node(self, node):
        self.nodeList.append(node)

    def rem_node(self, node):
        self.nodeList.remove(node)

    @property
    def description(self):
        return self.desc 

    def occupy(self, nodeId):
        self.occupiedId = nodeId 

    def release(self, nodeId):
        '''
        Only the node that occupy the channel can release it
        '''
        if self.occupiedId == nodeId:
            self.occupiedId = None 

    def is_busy(self):
        if self.occupiedId is None:
            return False 
        else:
            return True

class Node():
    globalDevList = []
    def __init__(self, devId, periodTicks, occupyTicks, channel):
        if devId in Node.globalDevList:
            raise ValueError("This device id already exists")
        else:
            self.devId = devId
            Node.globalDevList.append(self.devId) 
        self.periodTicks = periodTicks
        self.occupyTicks = occupyTicks
        self.delayTicks = 0
        self.startTicks = 0
        self.channel = channel 
        self.state = "wait"
        self.failCount = 0
        self.successCount = 0

    def start_send(self, globalTicks):
        if self.channel.is_busy() == False:
            print("Tick {}: Node {} starts to send".format(globalTicks/1000, self.devId))
            self.state = "sending"
            self.startTicks = globalTicks
            self.channel.occupy(self.devId)
            self.successCount += 1
        else:
            print("Tick {}: Node {} is stuck".format(globalTicks/1000, self.devId))
            self.state = "stuck"
            self.startTicks = globalTicks
            self.failCount += 1
            self.delayTicks = 5000 + random.randint(0, 5000) # s

    def end_send(self, globalTicks):
        print("Tick {}: Node {} ends sending".format(globalTicks/1000, self.devId))
        self.state = "wait"
        self.startTicks = globalTicks
        self.channel.release(self.devId)
    
    def update(self, globalTicks):
        if self.state == "sending":
            if globalTicks - self.startTicks >= self.occupyTicks:
                self.end_send(globalTicks) 
        elif self.state == "wait":
            if globalTicks - self.startTicks >= self.periodTicks:
                self.start_send(globalTicks)
        elif self.state == "stuck":
            if globalTicks - self.startTicks >= self.delayTicks:
                self.start_send(globalTicks)

class Counter():
    def __init__(self):
        self.countNum = 0 

    def add(self):
        # time.sleep(0.1)
        # print("{:*^30}".format("counter update"))
        self.countNum += 1
    
    def clear(self):
        self.countNum = 0

    @property
    def ticks(self):
        return self.countNum

class LBT_Model():
    def __init__(self, chList):
        self.counter = Counter()
        self.chList = chList

    def run(self, stopTicks=600000):
        while True:
            for c in self.chList:
                for n in c.nodeList:
                    gTicks = self.counter.ticks
                    n.update(gTicks)
            self.counter.add()
            if self.counter.ticks >= stopTicks:
                raise KeyboardInterrupt

class LoRaPacket():
    '''
    All the formulas referred to the sx1276 datasheet
    '''
    def __init__(self, bw="125KHz", sf=7, cr="4/5"):
        if bw == "125KHz":
            self.bw = 125000
        elif bw == "250KHz":
            self.bw = 250000
        elif bw == "500KHz":
            self.bw = 500000
        else:
            raise ValueError("Bandwidth is out of range")

        if sf not in list(range(6, 13)):
            raise ValueError("Value for spread factor is out of range")
        else:
            self.sf = sf
        
        if cr == "4/5":
            self.cr = 1
        elif cr == "4/6":
            self.cr = 2
        elif cr == "4/7":
            self.cr = 3
        elif cr == "4/8":
            self.cr = 4
        else:
            raise ValueError("Value for code rate is out of range")
        self.Tsym = (2**self.sf) / self.bw # Symbol rate 

    def get_time(self, preamble=8, header=0, payload=0, crc=2, ldro=0):
        Tpreamble = (preamble+4.25) * self.Tsym
        temp = math.ceil((8*payload-4*self.sf+28+16*crc-20*header)/(4 * (self.sf-2*ldro)))*(self.cr+4)
        Npl = 8 + max(temp, 0)
        Tpacket = Tpreamble + Npl * self.Tsym
        return Tpacket

def main():
    # packet = LoRaPacket(sf=9)
    # tp = int(packet.get_time(payload=255) * 1000)

    # try:
    #     ch1 = Channel("Channel 1")
    #     for i in range(40):
    #         ch1.add_node(Node(i, 60000, tp, ch1)) # period:60s
    #     chList = [ch1]
    #     model = LBT_Model(chList)
    #     model.run() 
    # except KeyboardInterrupt:
    #     for i, n in enumerate(ch1.nodeList):
    #         print("Node {}: success times {}, fail times {}".format(i, n.successCount, n.failCount))
    #     print(tp)

    packet = LoRaPacket(sf=9)
    tp = int(packet.get_time(payload=255) * 1000)

    try:
        ch1 = Channel("Channel 1")
        ch2 = Channel("Channel 2")
        for i in range(0, 20):
            ch1.add_node(Node(i, 60000, tp, ch1)) # period:60s
        for i in range(20, 40):
            ch2.add_node(Node(i, 60000, tp, ch2))
        chList = [ch1, ch2]
        model = LBT_Model(chList)
        model.run() 
    except KeyboardInterrupt:
        for c in chList:
            for i, n in enumerate(c.nodeList):
                print("Node {}: success times {}, fail times {}".format(i, n.successCount, n.failCount))
        print(tp)

if __name__ == "__main__":
    main()


