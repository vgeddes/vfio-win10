-machine q35,accel=kvm,usb=off

-enable-kvm
-parallel none
-no-hpet

# Memory
-m 8096
-mem-prealloc
-balloon none

# CPU
-cpu host,hv_relaxed,hv_synic,hv_reset,hv_stimer,hv_vpindex,hv_runtime,hv_spinlocks=0x1fff,hv_vapic,hv_time
-smp cores=4,threads=1,sockets=1

# Time
-rtc base=localtime

-vga none
-display none

-object input-linux,id=kbd0,grab_all=off,repeat=off,evdev=/dev/input/by-id/usb-Microsoft_Microsoft®_2.4GHz_Transceiver_v9.0-event-kbd

-device ioh3420,bus=pcie.0,addr=1c.0,multifunction=on,port=1,chassis=1,id=root.1
-device vfio-pci,host=01:00.0,bus=root.1,addr=00.0,multifunction=on,romfile=/var/lib/vm/windows10/AMD.R9Nano.4096.160212.rom
-device vfio-pci,host=01:00.1,bus=root.1,addr=00.1
-device vfio-pci,host=04:00.0,id=xhci0

-object iothread,id=thread0
-device virtio-blk-pci,scsi=off,config-wce=off,drive=hd0,iothread=thread0
-drive file=/dev/nvme0n1p4,format=raw,id=hd0,if=none,cache=directsync,aio=native

# OVMF
-drive if=pflash,format=raw,readonly,file=/usr/share/edk2.git/ovmf-x64/OVMF_CODE-pure-efi.fd
-drive if=pflash,format=raw,file=/var/lib/vm/windows10/vars.fd

# Network
-netdev tap,helper=/usr/lib/qemu/qemu-bridge-helper,id=net5,vhost=on
-device virtio-net-pci,netdev=net5,mac=00:00:00:02:01:04

# Qemu Monitor Protocol
-qmp unix:/run/qemu/qmp-sock,server,nowait -monitor none

# Guest Agent
-chardev socket,path=/run/qemu/qga-sock,server,nowait,id=qga0
-device virtio-serial
-device virtserialport,chardev=qga0,name=org.qemu.guest_agent.0


