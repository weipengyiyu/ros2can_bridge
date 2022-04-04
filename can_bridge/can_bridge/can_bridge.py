import asyncio
import can 
import rclpy
import threading
import logging
from rclpy.node import Node
from interface.msg import CanData
from rclpy.executors import MultiThreadedExecutor

#使用了异步需要配置异步
logging.getLogger('asyncio').setLevel(logging.WARNING)

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

        self._can_bus = can.Bus(bustype="socketcan", channel=self._dev)
            
    def send_callback(self, msg):
        sendmsg = can.Message(arbitration_id=msg.arbitration_id, \
            data=list(msg.data), is_extended_id=msg.extended)
        self._can_bus.send(sendmsg)


class AsynRecv():
    def __init__(self, bus, pub):
        self._bus = bus
        self._pub = pub

    def recv_handle(self, msg):
        if msg.dlc != 8:
            return
        recvmsg = CanData()
        recvmsg.extended = msg.is_extended_id
        recvmsg.arbitration_id= msg.arbitration_id
        recvmsg.data = msg.data

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
        cannode = CanBridge("vcan0", "500000")
        try:
            canasyn = threading.Thread(target=run, args=(cannode._can_bus,cannode._can_pub,))
            canasyn.start()
        except:
            logging.error("asyn thread create fail.")
        
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(cannode)

        try:
            executor.spin()
        finally:
            executor.shutdown()
            cannode.destroy_node()
    except:
        logging.error("bridge node create fail.")
    finally:
        canasyn.join()

        rclpy.shutdown()

