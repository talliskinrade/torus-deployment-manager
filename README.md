<<<<<<< HEAD

# README

## Information

The TORUS Deployment Manager is a tool for preparing firmware images and configuration files ('.hex' and '.json') for deployment to TORUS wearable sensors and forwarding gateways (Raspberry Pi and nRF52840 dongles). It is based on the SPHERE Deployment Manager [1] ([preprint](https://seis.bristol.ac.uk/~xf14883/files/conf/2018_adhocnow_deployment.pdf)).

Created by @talliskinrade and based on the work of:

```
@inproceedings{Fafoutis2018SDM,
  author={Fafoutis, X. and Elsts, A. and Oikonomou, G. and Piechocki, R.},
  title={{SPHERE Deployment Manager: A Tool for Deploying IoT Sensor Networks at Large Scale}},
  booktitle={Proc. 17th International Conference on Ad Hoc Networks and Wireless (AdHoc-NOW)},
  year={2018}
}
```

[1] X. Fafoutis, A. Elsts, G. Oikonomou, and R. Piechocki. SPHERE Deployment Manager: A Tool for Deploying IoT Sensor Networks at Large Scale. In Proceedings of the 17th International Conference on Ad Hoc Networks and Wireless (AdHoc-NOW), Saint Malo, France, September 2018.

## Installation

Run `install.py` to setup an encrypted key file with a password.

### Dependencies

Install all necessary python packages, `srecord` for `srec_cat`, and `texlive` for `pdflatex`.

Must be run in Python version that supports Pillow, which is required for QR code image generation.

## Configuration File

- `house_id`: House ID (HID)
- `version`: System version to use as in `/firmware/` (optional).
- `total_elephants`: Total number of Raspberry Pi forwarding gateways, including root gateway and docking stations.
- `total_trunks`: Total number of nRF52840 USB-dongles ("trunks").
- `total_wearables`: Total number of wearable sensors.

### Example

```
>>type config\0000.cfg
[DEFAULT]
house_id = 0000
total_elephants = 4
total_trunks = 4
total_wearables = 4
```

## Record of Deployments

Each house should be allocated a unique House ID (HID) and entered at the `torus_network_id.csv`:

- 1st column: Network ID (NID)
- 2nd column: House ID (HID)
- 3rd column: 1 if HID allocated to participant
- 4th column: 1 if deployment is active

## Execution Example

```
>>python run.py 0000
Using system version: elmer.4
Password:
TORUS Deployment Manager - Report
--------------------------------------------
House ID: 0000
Network ID: 0
Date: 2025-07-01
Total Elephants: 4
[Device: 001] Image created. Elephant: C05452530100
[Device: 002] Image created. Elephant: C05452530200
[Device: 003] Image created. Elephant: C05452530300
[Device: 004] Image created. Elephant: C05452530400
Total Wearables: 4
[Device: 192] Image created. Wearable: EE545253c000
[Device: 193] Image created. Wearable: EE545253c100
[Device: 194] Image created. Wearable: EE545253c200
[Device: 195] Image created. Wearable: EE545253c300
Creating labels..
Labels written in labels.pdf
```

## Output

The output can be found in `/out/<HID>/`:

- `/out/<HID>/img/`: Contains the images and JSON files to be installed to the devices
- `/out/<HID>/label.pdf`: Label file for printing

## Flashing the Devices

Flash the generated `.hex` files to the devices using your preferred tool.

- Wearables: use the `.hex` files in `/out/<HID>/img/`.
- # Elephants: use the `.json` files in `/out/<HID>/img/` for configuration.

# torus-deployment-manager

# README

## Information

## Tallis Notes on sphere-deployment-manager

## Intention of the deployment manager

- image generation
  creates firmware images for each device
- label creation
  generate device labels
- deployment tracking
  organizes and records networkIDs (internal id, addresses), houseIDs (4-digit delivery id), deployment and status

## Definitions

- firmware image = the software that is embedded in IoT devices

## What devices need firmware

- Pis
- NUC
- dongles
- wearable
- barometer arduino
- docking station
- video and cameras

we no longer have the water environmental sensors, so anything updatin gfirmware to those should be deleted.

the sphere gateways had 2 MCUs, 'F' and 'G'. I don't think we have that anymore. i think the Pis only have 1 MCU that does the ble-scan-advertise

## Questions

- do the mac addresses need to be colon seperated?

## Log

# 24/06/25

- Crypo and Crypto.Cipher from pycrypto package are outdated. Updated to pycryptodomex / pycryptodome.
- ConfigParser package was outdated. Updated to configparser
- Changed the types of strings to binary when being concatonated with bytes. Required as python 3.13 is now stricter on concatonations only being between the same type.
- config.readfp is depriciated and has been removed. Has been replace with the function config.read().
- config.read() expects a string not a object, therefore the open() function was removed.
- The 'torus_network_id.csv' file was not written in binary, so in run.py line 203 the open() function was changed to read, rather than read binary.

# 25/06/25

- keeping install.py exactly the same, only changing 'SPHERE' to 'TORUS'
- Cannot be run on python 3.14, requires package 'Pillow' which as of 25/06/25 can only run on python 3.13.
- When creating the labels, had to replace "pdflatex" with the file directory for pdflatex in miktex module.
- Scrap 'tsch', only using BLE advertising now. I don't think the Pi's require a sharing schedule.
- Scrap 'total_environmental'. These were used in the SPHERE project, but we're not using them anymore
- `total_gateway`: Total number of gateways including root gateway. Aka the NUC. renamed to rpi.
- for wearable
  - random mac addr: EE:54:52:53:00:00
  - ble addr: C0:54:52:53:00:00
- dont need ieee addr
- rpi done. getting the random mac address in the address file. last 4 digits are the house id. need to ask if he wants then calon seperated or not.
- install.py creates a password for the key file. there are 256 keys in the ckeys file, and each one is applied to a wearable.

# 26/06/25

- the wearable and the dongle need ble addresses, the pi and the nuc need mac addresses?
- wrote up breakdown of sphere-deployment-manager
- the forwarding pis are dubbed elephants (for now)
- the ble dongles are dubbed trunks (for now)
- other potential names: rhino and horn, platapus and beak, unicorn and horn, narwhal and horn, bird and beak

# 27/06/25

- MEM*OFFSET*\* -- inclusive start address
- MEM*OFFSET*\*\_END -- exclusive end address
- sreccat: -exclude <start> <end> -- excludes all addresses from start (inclusive) up to but not including end (exclusive)
- need 32 bytes to insert the block. 16 bytes for key, 8 bytes static address, 8 bytes ble
- for elephant, create a json file instead
- Output:
  (venv) PS C:\Users\wo22854\OneDrive - University of Bristol\Documents\TORUS\torus-deployment-manager> python -m run.py 0000
  Using system version: elmer.4
  Password:
  TORUS Deployment Manager - Report
  ***
  House ID: 0000
  Network ID: 0
  Date: 2025-06-27
  Total Elephants: 4
  [Device: 001] Image created. Elephant: 015452530000
  [Device: 002] Image created. Elephant: 025452530000
  [Device: 003] Image created. Elephant: 035452530000
  [Device: 004] Image created. Elephant: 045452530000
  Total Trunks: 4
  [Device: 128] Image created. Trunk: 805452530000
  [Device: 129] Image created. Trunk: 815452530000
  [Device: 130] Image created. Trunk: 825452530000
  [Device: 131] Image created. Trunk: 835452530000
  Total Wearables: 4
  [Device: 192] Image created. Wearable: c05452530000
  [Device: 193] Image created. Wearable: c15452530000
  [Device: 194] Image created. Wearable: c25452530000
  [Device: 195] Image created. Wearable: c35452530000
  Creating labels..
  Labels written in labels.pdf
- from BORUS
  static const char \*target_ap_addrs[] = {
  "2C:CF:67:89:E0:5D", // Public address of the built-in RPi controller
  "C0:54:52:53:00:00", // Random static address of the nrf53840dk
  };
- mac and ble addresses are the same which needs to be fixed
- need to get BORUS to build on personal computer

# 30/06/25

- flash address size variable name
  0004c85c l O rodata 00000012 wearable_static_addr
  20003434 l O datas 0000000c target_ap_addrs
  20007a90 l O bss 00000004 g_aes_key_id
- for wearable_static_addr its stored in rom which may cause an issue.
- added a section to install.py to ensure all the keys are unique. changed key size to 4 bytes.
- discovered that C0 denotes a random static address, so changed ble address to "C0545253" + "%.2x" % (device) + "%.2x" % (network) # Big-endian instead
- so for the static address, raspberry pis must have prefix c0, wearables must have prefix ee
- half way through changing make image to have inclusions in many addresses, not a block of addresses

# 01/07/25

- 20007a90 l O bss 00000004 g_aes_key_id
- 0004c85c l O rodata 00000012 wearable_static_addr
- 20003434 l O datas 0000000c target_ap_addrs

- can probably get rid of the offset, because the addresses are different for elephants and wearables
- seems to be creating the new hex absolutely fine. should be able to test it on the torus53 device.

# 02/07/25

- The dongle is flashed with the HCI controller firmware at: https://github.com/shuhao-dong/BORUS
- need to add a seperate docking station
- i'm strugglig to get the hex file for the dongle/trunk
- make mqtt topic for elephant: <HID>\<WID>\<EID>

from meeting with duke, to do:

- get rid of zephyr_full.hex **<- i'll do this after i know its changing the correct addresses, so at the end or at least once its been tested successfully on the wearable**
- check that aes key and target ap addr are correct
  20007a90 l O bss 00000004 g_aes_key_id
  0004c758 l O rodata 00000010 aes_key.0
  **done**
- target ap addr is a pointer, so make sure your replacing the values its pointing to (on wearable)
  0x20003434 <target_ap_addrs>: 0x0004c7b8 0x0004c7cc 0x0004c7e0
  add 17 addresses to the end of each (covers all the characters)
  **<- i need the targer ap addr array to have the max number of arrays it can, and just set the ones we're not using to 'NULL' so that the total number of elephants can change per house and it not cause huge issues**
- if multiple wearables in house, the addresses of all the wearables have to be stored in the config files (on elephant)
  **done**
- docking station code is out, so add that firmware and deployment section
  **done**
- the elephant needs the mqtt topic it needs to pub to
  <HID>\<EID>
  The JSON packet should include what wearable it came from i think
  not sure how we're going to distinguish if theres multiple wearables in the house how we can tell which data comes from which wearable, and how we pass that onto the nuc.
  **done**
- the elephant needs the broker address (not sure how to do this yet)
  **done**
- confirm whether the wearable requires the addresses to be inputted as big or little endian
  done as big endian and thats whats in the addresses currently
  (gdb) x/s 0x0004c7b8
  0x4c7b8: "C0:54:52:53:00:00"
  (gdb) x/17bx 0x0004c7b8
  0x4c7b8: 0x43 0x30 0x3a 0x35 0x34 0x3a 0x35 0x32
  0x4c7c0: 0x3a 0x35 0x33 0x3a 0x30 0x30 0x3a 0x30
  0x4c7c8: 0x30
  **done**

# 03/07/25

- need to add a section for NUC
- ip addresses: 0.0.0.0 to 255.255.255.255
- max number of houses = 254
- not sure if the NUC needs the wearable addresses

  > > > > > > > 12438dc86a2007be4ce26837d4384f458eb6d021
