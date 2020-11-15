import sched, time
from rcon import rcon,rconException

def print_state():
    with rcon("127.0.0.1", "pass", port=9889) as r:
        return r.command("/observe")

interval = 1.0/15.0

count = 0
filename = "factai_" + str(time.time())
# Open the file in write mode and store the content in file_object
# with open(filename, 'w') as file_object:
while True:
    time.sleep(interval - time.monotonic() % interval)
    # file_object.write(print_state())
    print(print_state())
    count += 1
    if count > 60*5:
        break