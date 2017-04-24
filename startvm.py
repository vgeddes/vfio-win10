#!/usr/bin/env python2

import os
import errno
import sys
import argparse
import subprocess
import uuid
import glob
import json
import pwd
import errno
import time
import fcntl
import datetime

from functools import partial
from signal import signal, alarm, SIGTERM, SIGINT, SIGUSR1, SIGUSR2, SIGALRM

from qmp.qmp import QEMUMonitorProtocol


def log(msg, *args):
    sys.stdout.write("{}: {}\n".format(datetime.datetime.now().isoformat(), msg.format(*args)))
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', action='store', metavar='PROFILE', help='Start the guest using PROFILE')

    args = parser.parse_args()
    
    rundir = "/run/qemu"
    try:
        os.makedirs(rundir)
    except OSError as ex:
        if ex.errno != errno.EEXIST:
            log("Could not create runtime directory {}: {}", rundir, ex)
            return 1
    else:
        log("Created runtime directory {}", rundir)

    lockf = open(os.path.join(rundir, 'lock'), 'w+')
    try:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as ex:
        if ex.errno == errno.EAGAIN:
            log("Another instance is already running")
            return 1            
        
    with open(os.path.join(rundir, "pid"), "w") as f:
        f.write(str(os.getpid()) + '\n')
        
    if args.profile:
        ret = start(args.profile)
    else:
        parser.print_usage()
        ret = 0
        
    return ret


def start(profile):

    cmd = make_cmd(profile)    
    log("Starting Qemu with command: {}", ' '.join(cmd))
    p = subprocess.Popen(cmd, shell=False, preexec_fn=os.setpgrp)

    log("Qemu has PID {}", p.pid)

    box = [None]
    def handler(box, signal, frame):
        box[0] = signal

    signal(SIGINT, partial(handler, box))
    signal(SIGTERM, partial(handler, box))
    signal(SIGUSR1, partial(handler, box))
    signal(SIGUSR2, partial(handler, box))
    signal(SIGALRM, partial(handler, box))
    
    while True:
        try:
            _, status = os.waitpid(p.pid, 0)
        except OSError as ex:
            if ex.errno == errno.EINTR:
                handle_signal(p.pid, box[0])
        else:
            break

    if os.WIFEXITED(status) or os.WTERMSIG(status) == SIGTERM:
        return 0
    else:
        return 1

    
def make_cmd(profile):
    cmd = ['/usr/bin/qemu-system-x86_64']

    path = None
    for p in glob.glob("/var/lib/vm/windows10/*.profile"):
        if profile in os.path.basename(p):
            path = p

    if not path:
        raise ValueError("Could not find profile")

    with open(path) as f:
        lines = [l.strip() for l in f.readlines() if not l.startswith('#') and l.strip()]
        cmd += [x for y in [l.split() for l in lines] for x in y]

    return cmd


def handle_signal(pid, signal):
    log("Handling signal {}",
        {
            SIGINT: 'SIGINT',
            SIGTERM: 'SIGTERM',
            SIGUSR1: 'SIGUSR1',
            SIGUSR2: 'SIGUSR2',
            SIGALRM: 'SIGALRM'
        }.get(signal, signal))
    
    if signal in (SIGINT, SIGTERM):
        cmd_shutdown()
    if signal == SIGALRM:
        alarm(0)
        os.kill(pid, SIGTERM)
    elif signal == SIGUSR1:
        cmd_attach_usb()    
    elif signal == SIGUSR2:
        cmd_detach_usb()
    else:
        pass
    
        
def cmd_shutdown():
    """
    Try and perform a clean shutdown, failing which the qemu process will be issued a SIGTERM.
    """
    log("Shutting down Qemu")
    try:
        qga_cmd('guest-shutdown', mode='powerdown')
    except Exception as ex:
        try:
            qmp_cmd('system_powerdown')
        except Exception as ex:
            pass
    alarm(60)


def cmd_attach_usb():
    with open('/sys/bus/pci/devices/0000:04:00.0/driver/unbind', 'w') as f:
        f.write('0000:04:00.0')
    with open('/sys/bus/pci/drivers/vfio-pci/new_id', 'w') as f:
        f.write('1b21 1242')
    time.sleep(0.5)
    qmp_cmd('device_add', driver='vfio-pci', id='xhci0', host='04:00.0')


def cmd_detach_usb():
    qmp_cmd('device_del', id='xhci0')
    time.sleep(0.5)
    with open('/sys/bus/pci/devices/0000:04:00.0/driver/unbind', 'w') as f:
        f.write('0000:04:00.0')
    with open('/sys/bus/pci/drivers/xhci_hcd/bind', 'w') as f:
        f.write('0000:04:00.0')

    
    
# def cmd_attach_usb():
#     log("Attaching USB device")
#     try:
#         qmp_cmd('device_add', driver='usb-host', bus='xhci.0', id='usb0', isobsize='4', vendorid='1118', productid='1957')
#     except Exception as ex:
#         print ex


# def cmd_detach_usb():
#     log("Detaching USB device")
#     try:
#         qmp_cmd('device_del', id='usb0')
#         time.sleep(1)
#         status = subprocess.call(['/usr/local/bin/resetmsmice'])
#         log("resetmsmice finished with status {}", status)
#     except Exception as ex:
#         print ex

            
def qmp_cmd(cmd, **args):
    client = QEMUMonitorProtocol("/run/qemu/qmp-sock")
    client.connect(True)
    result = client.command(cmd, **args)
    client.close()


def qga_cmd(cmd, **args):
    client = QEMUMonitorProtocol("/run/qemu/qga-sock")
    client.connect(False)
    return client.command(cmd, **args)


if __name__ == '__main__':
   sys.exit(main())
