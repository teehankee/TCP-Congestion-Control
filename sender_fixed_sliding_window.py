import sys
import time
import socket

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
# total packets to send
WINDOW_SIZE = 100
ACKS = {}

# read data
with open("file.mp3", "rb") as f:
    data = f.read()  # [:500000]

# create a udp socket with slinding window
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    # bind the socket to a OS port
    udp_socket.bind(("localhost", 5000))
    udp_socket.settimeout(1)

    start_time = time.time()
    packet_start_times = {}
    start_times = {}
    packet_end_times = {}

    # create messages
    window_resource = WINDOW_SIZE
    messages = []
    acks = {}
    seq_id_tmp = 0
    lock = False

    while True:
        for i in range(window_resource):
            # construct messages
            message_data = data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]

            if lock:
                break

            if seq_id_tmp > len(data):
                print("sending final")
                message = int.to_bytes(
                    len(data), SEQ_ID_SIZE, byteorder="big", signed=True
                )
                lock = True
            else:
                message = (
                    int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder="big", signed=True)
                    + message_data
                )

            acks[seq_id_tmp] = False

            if seq_id_tmp not in packet_start_times:
                packet_start_times[seq_id_tmp] = time.time()
                start_times[seq_id_tmp] = time.time()

            udp_socket.sendto(message, ("localhost", 5001))
            window_resource -= 1
            seq_id_tmp += len(message_data)

        try:
            ack, _ = udp_socket.recvfrom(PACKET_SIZE)
            ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big")
            ack_message = ack[SEQ_ID_SIZE:]

            if ack_message == b"fin":
                break
            for _id in acks:
                if _id < ack_id:
                    acks[_id] = True
                    if _id not in packet_end_times:
                        packet_end_times[_id] = time.time()
                        window_resource += 1

            # manual timeout
            if not all(acks.values()):
                first_zero_instance = min(i for i, x in acks.items() if x == 0)
                internal_timeout = time.time() - start_times[first_zero_instance]
                if internal_timeout > 1:
                    print("timeout " + str(internal_timeout) + "\n")
                    message_resend = (
                        int.to_bytes(
                            first_zero_instance,
                            SEQ_ID_SIZE,
                            byteorder="big",
                            signed=True,
                        )
                        + data[first_zero_instance : first_zero_instance + MESSAGE_SIZE]
                    )
                    udp_socket.sendto(message_resend, ("localhost", 5001))
                    start_times[first_zero_instance] = time.time()

            print(ack_id, ack_message)

        except socket.timeout:
            pass
        # if not acks.get(seq_id_tmp, False):
        #     udp_socket.sendto(message, ('localhost', 5001))

    finack = (
        int.to_bytes(len(data), SEQ_ID_SIZE, byteorder="big", signed=True)
        + b"==FINACK=="
    )
    udp_socket.sendto(finack, ("localhost", 5001))

    print("here")
    end_time = time.time()
    time_elapsed = end_time - start_time

    avg_delay = 0
    for k in packet_end_times.keys():
        packet_delay = packet_end_times[k] - packet_start_times[k]
        avg_delay += packet_delay

    avg_delay /= len(packet_end_times.keys())
    metric = sys.getsizeof(data) / (avg_delay * time_elapsed)
    print("throughput ")
    print(sys.getsizeof(data) / time_elapsed)
    print("avg delay")
    print(avg_delay)
    print("metric")
    print(metric)
    print("elapsed time")
    print(str(time_elapsed // 60) + " min " + str(time_elapsed % 60) + " sec")
# throughput
# 49431.29506797432
# avg delay
# 0.36021099216733243
# metric
# 137228.72467204308
# elapsed time
# 1 min and 47.618584394454956 sec
