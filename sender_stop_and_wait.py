import sys
import time
import socket
import struct

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

ACKS = {}

# read data
with open("file.mp3", "rb") as f:
    data = f.read()

# create a udp socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    # bind the socket to a OS port
    udp_socket.bind(("localhost", 5000))
    udp_socket.settimeout(1)

    start_time = time.time()
    packet_start_times = {}
    packet_end_times = {}
    # start sending data from 0th sequence
    seq_id = 0
    while seq_id < len(data):
        # create message
        acks = {}
        seq_id_tmp = seq_id

        # construct message
        message_data = data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
        message = bytearray(struct.pack(">I", seq_id_tmp))
        if len(message_data) != 0:
            message.extend(message_data)

        # create ack
        acks[seq_id_tmp] = False
        # move seq_id tmp pointer ahead
        seq_id_tmp += len(message_data)
        if len(message_data) == 0:
            break

        # send message out
        for k in acks.keys():
            packet_start_times[k] = time.time()
        udp_socket.sendto(message, ("localhost", 5001))

        # wait for acknowledgement
        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                ack_id = struct.unpack(">I", ack[:SEQ_ID_SIZE])[0]
                ack_message = ack[SEQ_ID_SIZE:]

                if ack_message == b"fin":
                    break

                for _id in acks:
                    if _id < ack_id:
                        acks[_id] = True
                        if _id not in packet_end_times:
                            packet_end_times[_id] = time.time()
                            # print("ack", _id, "received")

                ACKS[ack_id] = ACKS.get(ack_id, 0) + 1

                if all(acks.values()):
                    break
            except socket.timeout:
                udp_socket.sendto(message, ("localhost", 5001))

        seq_id = seq_id_tmp

    finack = bytearray(struct.pack(">I", seq_id))
    finack.extend(b"==FINACK==")
    try:
        udp_socket.sendto(finack, ("localhost", 5001))
        ack, _ = udp_socket.recvfrom(PACKET_SIZE)
    except socket.timeout:
        pass

    end_time = time.time()
    time_elapsed = end_time - start_time

    avg_delay = 0
    for k in packet_end_times.keys():
        packet_delay = packet_end_times[k] - packet_start_times[k]
        avg_delay += packet_delay

    avg_delay /= len(packet_end_times.keys())
    metric = sys.getsizeof(data) / (avg_delay * time_elapsed)
    print(
        "{:.2f},{:.2f},{:.2f}".format(
            sys.getsizeof(data) / time_elapsed, avg_delay, metric
        )
    )
    # minutes, seconds = divmod(time_elapsed, 60)
    # print("Time elapsed: {:.0f} minutes {:.2f} seconds".format(minutes, seconds))