from threading import Thread
import os
import sched, time
import signal
import subprocess
import sys
import time

from pyfactorio.api.rcon import rcon,rconException

to_quit = []
ready = False
should_quite = False

def observe(args):
    with rcon("127.0.0.1", "pass", 9889) as r:
        interval = 1.0/15.0

        count = 0
        while True:
            if should_quite is True:
                print("exiting observer")
                return
            time.sleep(interval - time.monotonic() % interval)
            # file_object.write(print_state())
            print(r.command("/observe"))
            count += 1
            if count > 60*5:
                break

def start():
    thread = Thread(target = run_headless_server, args = (0, ))
    thread.start()

    while ready is False:
        time.sleep(0.1)

    print("rcon ready")

    def flip():
        global should_quite
        should_quite = True
    signal.signal(signal.SIGINT, flip)
    observe(0)

def run_headless_server(args):
    args = [
        "E:/SteamLibrary/steamapps/common/Factorio/bin/x64/Factorio.exe",
        "--rcon-bind=127.0.0.1:9889",
        "--rcon-password=pass",
        "--start-server=sb.zip",
        "--config=E:/programming/factorio/factai/run/config.ini"
    ]
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd="run")
    global to_quit
    to_quit = process

    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            break
        if output:
            out = output.decode()
            started = "Starting RCON interface"
            if out.find(started) >= 0:
                global ready
                ready = True

            print(out, end="")

