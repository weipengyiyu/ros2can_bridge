import asyncio
import can 
import rclpy
import os
import time
import threading
import logging
from rclpy.node import Node
from interface.msg import CanData
from rclpy.executors import MultiThreadedExecutor


#使用了异步需要配置异步
logging.getLogger('asyncio').setLevel(logging.WARNING)

class BridgeVal():
    bus0 = None
    bus1 = None
    recv0pub = None
    recv1pub = None
    

class CanBridge(Node):
    def __init__(self, dev, bitrate):
        super().__init__('can_bridge'+'_'+str(dev))
        self._dev = dev
        self._bitrate = bitrate

        self._can_pub = self.create_publisher(
            CanData,
            self._dev+"/recv",
            10
        )
            
        self._can_sub = self.create_subscription(
            CanData,
            self._dev+"/send",
            self.send_callback,
            10
        )

        self.can_init_dev()

        self._can_bus = can.interface.Bus(channel=self._dev, bustype="socketcan") 
            
    def send_callback(self, msg):
        sendmsg = can.Message(arbitration_id=msg.arbitration_id, \
            data=list(msg.data), is_extended_id=msg.extended)
        self._can_bus.send(sendmsg)

    def can_init_dev(self):
        ret = os.system('sudo ip link set '+self._dev+' type can bitrate '+self._bitrate)
        if ret != 0:
            os.system('sudo ifconfig '+self._dev+' down')
        os.system('sudo ip link set '+self._dev+' type can bitrate '+self._bitrate)
        os.system('sudo ifconfig '+self._dev+' up')
        os.system('sudo ifconfig '+self._dev+' txqueuelen 65536')
        time.sleep(2)


class AsynRecv():
    def __init__(self, bus, pub):
        self._bus = bus
        self._pub = pub

    def recv_handle(self, msg):
        recvmsg = CanData()
        recvmsg.extended = msg.is_extended_id
        recvmsg.arbitration_id= msg.arbitration_id
        recvmsg.data = msg.data

        if msg is None:
            pass

        self._pub.publish(recvmsg)

    async def can_recv(self):
        reader = can.AsyncBufferedReader()

        notifier = can.Notifier(self._bus, [self.recv_handle, reader])

        await reader.get_message()

        notifier.stop()


def run(bus, pub):
    asynrecv = AsynRecv(bus, pub)

    asyncio.run(asynrecv.can_recv())

def main():
    rclpy.init()
    try:
        can0node = CanBridge("can0", "500000")
        BridgeVal.bus0 = can0node._can_bus
        BridgeVal.recv0pub = can0node._can_pub
        can1node = CanBridge("can1", "500000")
        BridgeVal.bus1 = can1node._can_bus
        BridgeVal.recv1pub = can1node._can_pub

        try:
            can0asyn = threading.Thread(target=run, args=(BridgeVal.bus0,BridgeVal.recv0pub,))
            can1asyn = threading.Thread(target=run, args=(BridgeVal.bus1,BridgeVal.recv1pub,))

            can0asyn.start()
            can1asyn.start()
        except:
            logging.error("asyn thread create fail.")
        
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(can0node)
        executor.add_node(can1node)
        try:
            executor.spin()
        finally:
            executor.shutdown()
            can0node.destroy_node()
            can1node.destroy_node()
    except:
        logging.error("bridge node create fail.")
    finally:
        can0asyn.join()
        can1asyn.join()
        rclpy.shutdown()

