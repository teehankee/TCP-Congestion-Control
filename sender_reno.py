import sys
import time
import socket
import matplotlib.pyplot as plt

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
# total packets to send
ack_counts = {}
caught_triple_dup_acks = []
ssthresh = 64
received_acks = []
window_sizes = []
times = []
start_time = time.time()
triple_dup_count = 0
timeout_count = 0
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
    start_times = {}
    packet_end_times = {}
    # start sending data from 0th sequence
    seq_id = 0
    dup_ack_reset = False
    timeout_reset = False
    dup_ack = 0
    dup_ack_cwnd = []
    triple_dup_ack_ids = []
    # window size
    first_packet_send_time = None
    first_packet_receive_time = None
    cwnd = 1
    timeout = 0.5
    compare_data = []
    phases = []
    while seq_id < len(data):
        # create messages
        messages = []
        acks = {}
        seq_id_tmp = seq_id
        for i in range(cwnd):
            # construct messages
            # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
            message_data = data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
            # check if not last message
            if len(message_data) == 0:
                message = int.to_bytes(
                    seq_id_tmp, SEQ_ID_SIZE, byteorder="big", signed=True
                )
            else:
                message = (
                    int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder="big", signed=True)
                    + message_data
                )
            messages.append((seq_id_tmp, message))
            # create ack
            acks[seq_id_tmp] = False
            # move seq_id tmp pointer ahead
            seq_id_tmp += len(message_data)
            if len(message_data) == 0:
                break

        # send messages
        for sid, message in messages:
            for k in acks.keys():
                packet_start_times[k] = time.time()
                start_times[k] = time.time()
            udp_socket.sendto(message, ("localhost", 5001))

        prev_ack_id = -1
        # wait for acknowledgement
        while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)

                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big")
                ack_message = ack[SEQ_ID_SIZE:]
                ack_counts[ack_id] = ack_counts.get(ack_id, 0) + 1
                if ack_message == "fin":
                    break

                # update acks below cumulative ack
                for _id in acks:
                    if _id < ack_id:
                        acks[_id] = True
                        if _id not in packet_end_times:
                            packet_end_times[_id] = time.time()
                            timeout = 0.5
                if not all(acks.values()):
                    first_zero_instance = min(i for i, x in acks.items() if x == 0)
                    internal_timeout = time.time() - start_times[first_zero_instance]
                    if ack_counts[ack_id] == 4:
                        ssthresh = max(cwnd // 2, 1)
                        cwnd = ssthresh
                        triple_dup_count += 1
                        dup_ack_reset = True
                        seq_id = first_zero_instance
                        break
                    if internal_timeout > timeout:
                        for sid, message in messages:
                            if sid == first_zero_instance:
                                message_to_send = message
                        ssthresh = max(cwnd // 2, 1)
                        cwnd = 1
                        timeout_count += 1
                        timeout += timeout
                        timeout_reset = True
                        seq_id = first_zero_instance
                        break
                else:
                    # slow start
                    if cwnd < ssthresh:
                        cwnd += cwnd
                    else:
                        cwnd += 1
                    break
            except socket.timeout:
                pass
        if timeout_reset or dup_ack_reset:
            dup_ack_reset = False
            timeout_reset = False
        else:
            seq_id = seq_id_tmp
    # send final closing message

    finack = (
        int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder="big", signed=True) + b"==FINACK=="
    )
    try:
        udp_socket.sendto(finack, ("localhost", 5001))
        ack, _ = udp_socket.recvfrom(PACKET_SIZE)
    except:
        pass

    end_time = time.time()
    time_elapsed = end_time - start_time

    avg_delay = 0
    for k in packet_end_times.keys():
        packet_delay = packet_end_times[k] - packet_start_times[k]
        avg_delay += packet_delay

    avg_delay /= len(packet_end_times.keys())
    metric = sys.getsizeof(data) / (avg_delay * time_elapsed)

    print(str(round(sys.getsizeof(data) / time_elapsed, 2)) + ",")
    print(str(round(avg_delay, 2)) + ",")
    print(str(round(metric, 2)))