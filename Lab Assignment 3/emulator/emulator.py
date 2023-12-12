import sys, getopt
import socket
import struct
from datetime import datetime
import ipaddress
import select

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

def buildForwardTable(start_vertex, topology):

    confirmed = {start_vertex: {"Cost": 0, "NextHop": None}}
    tentative = {}

    next = start_vertex

    while True:
        # Traversing each neighbor
        for neighbor in topology[next]:
            # Calculating the current cost to neighbor
            cost = confirmed[next]["Cost"] + 1
            if neighbor not in confirmed.keys() and neighbor not in tentative.keys():
                tentative[neighbor] = {"Cost": cost, "NextHop": neighbor if confirmed[next]["NextHop"] is None else confirmed[next]["NextHop"]}
            elif neighbor in tentative.keys():
                if cost < tentative[neighbor]["Cost"]:
                    tentative[neighbor] = {"Cost": cost, "NextHop": neighbor if confirmed[next]["NextHop"] is None else confirmed[next]["NextHop"]}
                    
        if not tentative:
            break
        
        # Picking the lowest cost node from the tentative list
        next = min(tentative, key=lambda k: tentative[k]["Cost"])
        # Transferring the lowest cost node from tentative to confirmed
        confirmed[next] = tentative.pop(next)

    # Returning the forwarding table as a dictionary
    return {destination: confirmed[destination]["NextHop"] for destination in confirmed}

def printUpdates(topology, forwarding_table):
    # Printing information
    print("Topology:")
    print()
    print(topology)
    print()
    print("Forwarding Table:")
    print()
    print(forwarding_table)
    print()
    return

# Get the command line arguments
opts, _ = getopt.getopt(sys.argv[1:],"p:f:")
opts = dict(opts)

port, file_name = int(opts['-p']), opts['-f']

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

# Static Forwarding Table (Destination, Next Hop)
forwarding_table = buildForwardTable((socket.gethostbyname(socket.gethostname()), port), topology)

# Latest timestamps from neighbors
neighbors = {neighbor: 0 for neighbor in topology[(socket.gethostbyname(socket.gethostname()), port)]}

# Largest sequence numbers from each nodes
largest_seq_no = {}

seq_no = 1      # Initializing sequence number
TTL = 30        # Initializing TTL
LSP_INTERVAL = 1000     # Initializing defined interval for linkStateMessage
HM_INTERVAL = 10        # Initializing interval for helloMessage
last_LSM = 0            # Latest timestamp for linkStateMessage
last_HM = 0             # Latest timestamp for helloMessage

# Receving and Forwarding packets
while True:
    ready_to_read, _, _ = select.select([socket_object], [], [], 0)
    
    if ready_to_read:
        full_packet, _ = socket_object.recvfrom(1024)
        
        # Unpacking the contents of the packet header
        packet_header = struct.unpack("!BIHIHIcII", full_packet[:26])
        
        packet_TTL = packet_header[0]
        
        src_ip_address = str(ipaddress.ip_address(int(packet_header[1])))
        src_port = packet_header[2]
        
        dest_ip_address = str(ipaddress.ip_address(int(packet_header[3])))
        dest_port = packet_header[4]
        
        packet_type = packet_header[6].decode()
        packet_seq_no = packet_header[7]

        match packet_type:
            case "H":   # Handle Hello Message
                if (src_ip_address, src_port) not in neighbors:
                    # Updating topology to reflect the addition of a new neighbor
                    topology[(socket.gethostbyname(socket.gethostname()), port)].append((src_ip_address, src_port))
                    # Updating the forwarding table
                    forwarding_table = buildForwardTable((socket.gethostbyname(socket.gethostname()), port), topology)
                    # Printing information
                    printUpdates(topology, forwarding_table)
                    # Incrementing sequence number
                    seq_no += 1
            
                # Updating the latest timestamp for the neighbor
                neighbors[(src_ip_address, src_port)] = datetime.now().timestamp()
            
            case "L" if packet_TTL > 0:     # Handle Link State Message
                if (src_ip_address, src_port) in largest_seq_no:
                    # Check for an update
                    if largest_seq_no[(src_ip_address, src_port)] < packet_seq_no:
                        # Updating route topology
                        topology[(src_ip_address, src_port)] = eval(full_packet[26:].decode())
                        # Updating the forwarding table
                        forwarding_table = buildForwardTable(((socket.gethostbyname(socket.gethostname()), port)), topology)
                        # Printing information
                        printUpdates(topology, forwarding_table)
                        
                        # Forwarding packets via reliable flooding
                        # forwardPacket(socket_object, full_packet, neighbors.keys().remove((src_ip_address, src_port)))
                
                        for neighbor in neighbors:
                            if neighbor is not (src_ip_address, src_port):
                                newPacket = struct.pack("!BIHIHIcII", packet_TTL - 1, int(ipaddress.ip_address(src_ip_address)), src_port, int(ipaddress.ip_address(dest_ip_address)), dest_port, 0, bytes("L", "utf-8"), packet_seq_no, 0) + full_packet[26:]
                                socket_object.sendto(newPacket, neighbor)
                else:
                    # Updating route topology
                    topology[(src_ip_address, src_port)] = eval(full_packet[26:].decode())
                    # Updating the forwarding table
                    forwarding_table = buildForwardTable(((socket.gethostbyname(socket.gethostname()), port)), topology)
                    # Printing information
                    printUpdates(topology, forwarding_table)
                    
                    # Forwarding packets via reliable flooding
                    # forwardPacket(socket_object, full_packet, neighbors.keys().remove((src_ip_address, src_port)))
                
                    for neighbor in neighbors:
                        if neighbor is not (src_ip_address, src_port):
                            newPacket = struct.pack("!BIHIHIcII", packet_TTL - 1, int(ipaddress.ip_address(src_ip_address)), src_port, int(ipaddress.ip_address(dest_ip_address)), dest_port, 0, bytes("L", "utf-8"), packet_seq_no, 0) + full_packet[26:]
                            socket_object.sendto(newPacket, neighbor)
            
                # Updating the largest sequence number from this source node
                largest_seq_no[(src_ip_address, src_port)] = packet_seq_no
                
            case ("D" | "E" | "R" | "A") if packet_TTL > 0:     # Handle Data, End, Request, and ACK packets
                # Sending the packet to its next hop
                full_packet = struct.pack("!BIHIHIcII", packet_TTL - 1, int(ipaddress.ip_address(socket.gethostbyname(src_ip_address))), src_port, int(ipaddress.ip_address(dest_ip_address)), dest_port, packet_header[5], bytes(packet_type, "utf-8"), packet_seq_no, packet_header[8]) + full_packet[26:]
                socket_object.sendto(full_packet, forwarding_table[(dest_ip_address, dest_port)])
            
            case "T":   # Handle Route Trace packets
                if packet_TTL == 0:
                    routeTrace = struct.pack("!BIHIHIcII", packet_TTL, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(dest_ip_address)), dest_port, 9, bytes("T", "utf-8"), 0, 0)
                    socket_object.sendto(routeTrace, (src_ip_address, src_port))
                else:
                    routeTrace = struct.pack("!BIHIHIcII", packet_TTL - 1, int(ipaddress.ip_address(socket.gethostbyname(src_ip_address))), src_port, int(ipaddress.ip_address(dest_ip_address)), dest_port, 9, bytes("T", "utf-8"), 0, 0)
                    socket_object.sendto(routeTrace, forwarding_table[(dest_ip_address, dest_port)])

    # Sending helloMessage to neighbors after certain interval
    if (datetime.now().timestamp() - last_HM) * 1000 > HM_INTERVAL:
        for neighbor in neighbors:
            # Sending hello message to every neighbor
            helloMessage = struct.pack("!BIHIHIcII", TTL, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(neighbor[0])), neighbor[1], 9, bytes("H", "utf-8"), 0, 0)
            socket_object.sendto(helloMessage, neighbor)
            
        # Updating the timestamp for the latest helloMessage
        last_HM = datetime.now().timestamp()

    # Check for helloMessages from neighbors
    neighbors_rm = []
    for neighbor in neighbors:
        # Check the latest timestamp
        if (datetime.now().timestamp() - neighbors[neighbor]) * 1000 > HM_INTERVAL + 100:
            # Remove from topology
            if neighbor in topology[(socket.gethostbyname(socket.gethostname()), port)]:
                # Updating route topology
                topology[(socket.gethostbyname(socket.gethostname()), port)].remove(neighbor)
                # Updating forwarding table
                forwarding_table = buildForwardTable((socket.gethostbyname(socket.gethostname()), port), topology)
                # Printing information
                printUpdates(topology, forwarding_table)
            
            # Removing neighbors from the largest sequence number dictionary
            if neighbor in largest_seq_no:
                largest_seq_no.pop(neighbor)    
            
            neighbors_rm.append(neighbor)
            seq_no += 1     # Indicates an update in LSP
    
    # Removing neighbors
    for neighbor in neighbors_rm:
        del neighbors[neighbor]
        
    # Sending new LinkStateMessage to all neighbors after certain interval
    if (datetime.now().timestamp() - last_LSM) * 1000 > LSP_INTERVAL:
        LSM_body = str(list(neighbors.keys()))
        for neighbor in neighbors:
            linkStateMessage = struct.pack("!BIHIHIcII", TTL, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(neighbor[0])), neighbor[1], 9 + len(LSM_body), bytes("L", "utf-8"), seq_no, len(LSM_body)) + LSM_body.encode()
            socket_object.sendto(linkStateMessage, neighbor)
            
        # Updating the latest timestamp for the linkStateMessage
        last_LSM = datetime.now().timestamp()