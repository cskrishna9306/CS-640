import sys, getopt
import queue
import socket
import struct
from datetime import datetime
import time


def forwardPacket():
    pass



# Get the command line arguments
opts, _ = getopt.getopt(sys.argv[1:],"p:q:f:l:")
opts = dict(opts)

port, queue_size, file_name, log = int(opts['-p']), int(opts['-q']), opts['-f'], opts['-l']

# Setting up priority queues
high_priority = queue.Queue()
medium_priority = queue.Queue()
low_priority = queue.Queue()

# priority_queues = {1: queue.Queue(), 2: queue.Queue(), 3: queue.Queue()}
# priority_queue = {priority: queue.Queue(maxsize = queue_size) for priority in ["high", "medium", "low"]}
priority_queues = [queue.Queue(maxsize = queue_size) for i in range(3)]

# Binding the socket at the specified port number
socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_object.bind((socket.gethostbyname(socket.gethostname()), port))

# Static Forwarding Table
forwarding_table = dict()
# Filter the file for the current emulator
with open(file_name) as f:
    for line in f:
       file = line.strip().split(" ")
    #    print(socket.gethostbyname(socket.gethostname()))
       if (socket.gethostbyname(file[0]), int(file[1])) == (socket.gethostbyname(socket.gethostname()), port):
           # Not sure if there may exist multiple entries for the same destination, but different next hop
           # can turn the value field into a dict
           forwarding_table[(socket.gethostbyname(file[2]), int(file[3]))] = {"next_hop": (file[4], int(file[5])), "delay": int(file[6]), "loss_prob": int(file[7])}
        #   mumble-03 and mumble-04 mapped to the same ip address
        #    print(socket.gethostbyaddr(socket.gethostbyname("follis")))

print(forwarding_table)

# Receving packets
while True:
    full_packet, sender_address = socket_object.recvfrom(1024)
    recv_time = datetime.now()

    if not full_packet:
        packet_header = full_packet[:17]
    
        # TODO: Unpack the contents of the packet header
        packet_header = struct.unpack("!bII", packet_header)
    
        priority = packet_header[0].decode()
        dest_ip_address = packet_header[3].decode()
        dest_port = packet_header[4].decode()
      
        payload = full_packet[17:].decode()

        if (dest_ip_address, dest_port) not in forwarding_table:
            # TODO: Log the packet loss
            continue

        # Placing the packets in their respective priority queues
        if not priority_queues[priority - 1].maxsize():
            priority_queues[priority - 1].put((full_packet, recv_time))
        else:
            # TODO: Log the packet loss
            pass


    # When talking about delay, do i keep checking if the delay time has elapsed for the packet without putting it to sleep
    # Because wouldn't using time.sleep function delay recvfro function, or is that ok


    # Note: Should forwarding take place asynchronously
    # Forwarding packets
    # Choose the packet from the queues
    forwarding_packet = None
    # if priority_queues[0].not_empty():
    #     forwarding_packet = priority_queues[0].get()
    # elif priority_queues[1].not_empty():
    #     forwarding_packet = priority_queues.get()
    # elif priority_queues[2].not_empty():
    #     forwarding_packet = priority_queues.get()

    # forwarding_packet = priority_queues[i].get() if priority_queues[i].not_empty() for i in range(3)
    # TODO: Maintain check for delayed packets and only pull packets when nothing is being delayed
    for i in range(3):
        if priority_queues[i].not_empty():
            forwarding_packet, recv_time = priority_queues[i].get()
            # TODO: recv_time should be the time from when i pull the packet from the queue
            break

    forwarding_packet_header = forwarding_packet[:17]
    
    # TODO: Unpack the contents of the packet header
    forwarding_packet_header = struct.unpack("!bII", forwarding_packet_header)
    
    dest_ip_address = forwarding_packet_header[3].decode()
    dest_port = forwarding_packet_header[4].decode()
    
    delay = forwarding_table[(dest_ip_address, dest_port)]["delay"]
    loss_prob = forwarding_table[(dest_ip_address, dest_port)]["loss_prob"]
    
    if datetime.now() - recv_time < delay:
        time.sleep((delay - (datetime.now() - recv_time)) / 1000)
    # TODO: DO NOT SLEEP and just wait for the delay time to eventually pass

    # TODO: Perform the loss_prob and choose whether to send it or not
    # can i choose a random number  between 1 to 100 and if it is below the loss_prob i drop it

    # TODO: Log the packet loss if loss_prob is true
    # TODO: Skip the loss_prob if the packet is an END packet
    # Sending the packet
    socket_object.sendto(forwarding_packet, forwarding_table[(dest_ip_address, dest_port)]["next_hop"])


    
    



    


    