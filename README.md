<<<<<<< HEAD

# README

## Information

The SPHERE Deployment Manager is a tool for preparing deployment images for the SPHERE IoT platforms. Detailed information is available in [1] ([preprint](https://seis.bristol.ac.uk/~xf14883/files/conf/2018_adhocnow_deployment.pdf)). If you use the SPHERE Deployment Manager you are kindly asked to cite [1].

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

Run `install.py` to setup a password.

### Dependencies

Install all necessary python packages, `srecord` for `srec_cat`, and `texlive` for `pdflatex`.

## Configuration File

- `house_id`: House ID (HID)
- `version`: System version to use as in `/firmware/` (optional).
- `tsch`: TSCH Schedule to use. Gateways should match schedule: e.g. for 4 total gateways use `3_and_1_shared_schedule`.
- `total_gateway`: Total number of gateways including root gateway.
- `total_environmental`: Total number of environmental sensors.
- `total_wearables`: Total number of wearable sensors.

### Example

```
>>type config\0000.cfg
[DEFAULT]
house_id = 0000
tsch = 3_and_1_shared_schedule
total_gateways = 4
total_environmental = 4
total_wearables = 4
```

## Record of Deployments

Each house should be allocated a unique House ID (HID) and entered at the `sphere_network_id.csv`:

- 1st column: Network ID (NID)
- 2nd column: House ID (HID)
- 3rd column: 1 if HID allocated to participant
- 4th column: 1 if deployment is active

## Execution Example

```
>>python run.py 0000
No explicit system version specified. Using default system version: elmer.4
Password:
SPHERE Deployment Manager - Report
--------------------------------------------
House ID: 0000
Network ID: 121
Date: 2017-10-25
Total Gateways: 4
[Device: 001] Image created. Root Gateway (F): 00124b0000007901
[Device: 064] Image created. Root Gateway (G): 00124b0000007940
[Device: 002] Image created. Gateway (F): 00124b0000007902
[Device: 065] Image created. Gateway (G): 00124b0000007941
[Device: 003] Image created. Gateway (F): 00124b0000007903
[Device: 066] Image created. Gateway (G): 00124b0000007942
[Device: 004] Image created. Gateway (F): 00124b0000007904
[Device: 067] Image created. Gateway (G): 00124b0000007943
Total Environmental: 4
[Device: 128] Image created. Environmental: 00124b0000007980
[Device: 128] Image created. Water sensor: 00124b0000007980
[Device: 129] Image created. Environmental: 00124b0000007981
[Device: 129] Image created. Water sensor: 00124b0000007981
[Device: 130] Image created. Environmental: 00124b0000007982
[Device: 130] Image created. Water sensor: 00124b0000007982
[Device: 131] Image created. Environmental: 00124b0000007983
[Device: 131] Image created. Water sensor: 00124b0000007983
Total Wearables: 4
[Device: 192] Image created. Wearable: a0e6f80079c0
[Device: 193] Image created. Wearable: a0e6f80079c1
[Device: 194] Image created. Wearable: a0e6f80079c2
[Device: 195] Image created. Wearable: a0e6f80079c3
Creating labels..
Labels written in labels.pdf
```

## Output

The output can be found in `/out/<HID>/`:

- `/out/<HID>/img/`: Contains the images to be installed to the devices
- `/out/<HID>/label.pdf`: Label file for printing

## Flashing the Devices

### SPHERE Gateways

The two MCUs are named `F` and `G` as marked on the silkscreen of the PCB.

For the root gateway programme only the `F` side.

### SPHERE Environmental Sensors

Use the image marked as 'water sensor' for the environmental sensors that have the water flow sensor board plugged.

=======

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
- half way through changing make image to have inclusions in many adresses, not a block of addresses

> > > > > > > 12438dc86a2007be4ce26837d4384f458eb6d021
