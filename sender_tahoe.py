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
ACKS = {}
ssthresh = 64
window_sizes = []
times = []
phases = []
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
    packet_end_times = {}
    # start sending data from 0th sequence
    seq_id = 0
    dup_ack_reset = False
    timeout_reset = False
    dup_ack = 0
    dup_ack_cwnd = []

    # window size
    cwnd = 1
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
            # print('sending', sid)
            udp_socket.sendto(message, ("localhost", 5001))

        # wait for acknowledgement
        while True:
            try:
                # print(acks)
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)

                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big")
                ack_message = ack[SEQ_ID_SIZE:]

                if ack_message == "fin":
                    break

                # update acks below cumulative ack
                for _id in acks:
                    if _id < ack_id:
                        acks[_id] = True
                        if _id not in packet_end_times:
                            packet_end_times[_id] = time.time()

                    # triple duplicate acks
                    else:
                        dup_ack += 1
                        if dup_ack == 3:
                            dup_ack_reset = True
                            print("triple duplicate acks")
                            raise socket.timeout

                ACKS[ack_id] = ACKS.get(ack_id, 0) + 1

                print("received", ack_id)

                # all acks received, increase window size
                if all(acks.values()):
                    # slow start
                    if cwnd < ssthresh:
                        cwnd += cwnd
                        phases.append("slow start")
                        window_sizes.append(cwnd)
                    # congestion avoidance
                    else:
                        cwnd += 1
                        phases.append("congestion avoidance")
                        window_sizes.append(cwnd)
                    break
                else:
                    first_zero_instance = min(i for i, x in acks.items() if x == 0)
                    internal_timeout = (
                        time.time() - packet_start_times[first_zero_instance]
                    )
                    if internal_timeout > 1:
                        print("timeout " + str(internal_timeout) + "\n")
                        timeout_reset = True
                        raise socket.timeout
            except socket.timeout:
                if dup_ack_reset or timeout_reset:
                    print("fast retransmit and recovery")
                    for sid, message in messages:
                        # if not acks[sid]:
                        if not acks.get(sid, False):
                            print("sending %r", sid)
                            udp_socket.sendto(message, ("localhost", 5001))
                            packet_start_times[sid] = time.time()

                    ssthresh = cwnd // 2
                    cwnd = 1
                    if dup_ack_reset:
                        triple_dup_count += 1
                        dup_ack_reset = False
                        phases.append("dup_ack_reset")
                        window_sizes.append(cwnd)
                    else:
                        timeout_count += 1
                        timeout_reset = False
                        phases.append("timeout_reset")
                        window_sizes.append(cwnd)
                pass

        # move sequence id forward
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
    print("time elapsed")
    print(time_elapsed)
    print("triple dup count")
    print(triple_dup_count)
    print("timeout count")
    print(timeout_count)
    print("elapsed time")
    print(str(time_elapsed // 60) + " min " + str(time_elapsed % 60) + " sec")
print(window_sizes)
print(dup_ack_cwnd)
plt.plot(window_sizes)

plt.xlabel("Time")
plt.ylabel("Window Size")
plt.title("Window Size Over Time")

slow_start_indices = [i for i, p in enumerate(phases) if p == "slow start"]
slow_start_sizes = [window_sizes[i] for i in slow_start_indices]
plt.scatter(slow_start_indices, slow_start_sizes, color="g", label="Slow Start")

congestion_avoidance_indices = [
    i for i, p in enumerate(phases) if p == "congestion avoidance"
]
congestion_avoidance_sizes = [window_sizes[i] for i in congestion_avoidance_indices]
plt.scatter(
    congestion_avoidance_indices,
    congestion_avoidance_sizes,
    color="r",
    label="Congestion Avoidance",
)

dup_ack_reset_indices = [i for i, p in enumerate(phases) if p == "dup_ack_reset"]
dup_ack_reset_sizes = [window_sizes[i] for i in dup_ack_reset_indices]
plt.scatter(
    dup_ack_reset_indices, dup_ack_reset_sizes, color="y", label="Dup Ack Reset"
)

timeout_reset_indices = [i for i, p in enumerate(phases) if p == "timeout_reset"]
timeout_reset_sizes = [window_sizes[i] for i in timeout_reset_indices]
plt.scatter(
    timeout_reset_indices, timeout_reset_sizes, color="m", label="Timeout Reset"
)

plt.legend()
plt.show()
plt.savefig("window_size.png")
