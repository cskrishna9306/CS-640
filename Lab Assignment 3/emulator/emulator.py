import sys, getopt
import socket
import struct
from datetime import datetime
import ipaddress
import select
import logging

def readTopology(file_name):
    topology = {}
    with open(file_name) as f:
        for line in f:
            links = line.strip().split(" ")
            topology[(links[0].split(",")[0], int(links[0].split(",")[1]))] = [(ip_addr, int(port)) for ip_addr, port in (link.split(",") for link in links[1:])]
    
    return topology

def createRoutes():
    pass

def forwardPacket():
    pass

def buildForwardTable():
    pass


# Get the command line arguments
opts, _ = getopt.getopt(sys.argv[1:],"p:f:")
opts = dict(opts)

port, file_name = int(opts['-p']), opts['-f'],

if not 2049 < port < 65536:
    print("Error: Port number not between the range 2049 and 65536")
    exit(1)

# Binding the socket at the specified port number
socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_object.bind((socket.gethostbyname(socket.gethostname()), port))

# Set the socket to non-blocking mode
socket_object.setblocking(0)

# Reading the topology within the specified file
topology = readTopology(file_name)
print(topology)
# Static Forwarding Table
forwarding_table = {}

# Constructing the forwarding table
with open(file_name) as f:
    for line in f:
       file = line.strip().split(" ")
       if (socket.gethostbyname(file[0]), int(file[1])) == (socket.gethostbyname(socket.gethostname()), port):
           forwarding_table[(socket.gethostbyname(file[2]), int(file[3]))] = {"next_hop": (file[4], int(file[5]))}

# Receving and Forwarding packets
while True:
    ready_to_read, _, _ = select.select([socket_object], [], [], 0)
    
    if ready_to_read:
        full_packet, _ = socket_object.recvfrom(1024)
        # Unpacking the contents of the packet header
        packet_header = struct.unpack("!BIHIHIcII", full_packet[:26])
    
        priority = packet_header[0]
        
        src_ip_address = str(ipaddress.ip_address(int(packet_header[1])))
        src_port = packet_header[2]
        
        dest_ip_address = str(ipaddress.ip_address(int(packet_header[3])))
        dest_port = packet_header[4]
        
        payload_size = packet_header[5] - 9
        packet_type = packet_header[6].decode()

        # TODO: Receiving helloMessage and LinkStateMessage
        
        # Logging packet loss: No match in forwarding table
        if (dest_ip_address, dest_port) not in forwarding_table:
            logging.error(f"{datetime.now().strftime('%m/%d/%Y %H:%M:%S.%f')[:-3]} - ERROR - Destination address not found in forwarding table \n\tSource: {socket.gethostbyaddr(src_ip_address)[0]}:{src_port} \n\tDestination: {socket.gethostbyaddr(dest_ip_address)[0]}:{dest_port} \n\tPriority: {priority} \n\tPayload Size: {payload_size} \n")
            continue

        # Sending the packet to its next hop
        socket_object.sendto(full_packet, forwarding_table[(dest_ip_address, dest_port)]["next_hop"])

    # TODO: Sending helloMessage to neighbors after certain interval
    
    # TODO: Check for helloMessages from neighbors
    # TODO: If no receipt of helloMessage remove from topology
    