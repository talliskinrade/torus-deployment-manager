# torus-deployment-manager

# README #
## Information ##


## Tallis Notes on sphere-deployment-manager ##

## Intention of the deployment manager ##
- image generation
    creates firmware images for each device 
- label creation
    generate device labels
- deployment tracking
    organizes and records networkIDs (internal id, addresses), houseIDs (4-digit delivery id), deployment and status

## Definitions ##
- firmware image = the software that is embedded in IoT devices

## What devices need firmware ##
- Pis
- NUC
- dongles
- wearable
- barometer arduino
- docking station
- video and cameras

we no longer have the water environmental sensors, so anything updatin gfirmware to those should be deleted.

the sphere gateways had 2 MCUs, 'F' and 'G'. I don't think we have that anymore. i think the Pis only have 1 MCU that does the ble-scan-advertise

## Questions ##
- do the Rasberry Pi's need a scharing schedule? A: I don't think so.


## Log ##
# 24/06/25 #
- Crypo and Crypto.Cipher from pycrypto package are outdated. Updated to pycryptodomex / pycryptodome. 
- ConfigParser package was outdated. Updated to configparser
- Changed the types of strings to binary when being concatonated with bytes. Required as python 3.13 is now stricter on concatonations only being between the same type.
- config.readfp is depriciated and has been removed. Has been replace with the function config.read().
- config.read() expects a string not a object, therefore the open() function was removed.
- The 'torus_network_id.csv' file was not written in binary, so in run.py line 203 the open() function was changed to read, rather than read binary.

# 25/06/25 #
- keeping install.py exactly the same, only changing 'SPHERE' to 'TORUS' 
- Cannot be run on python 3.14, requires package 'Pillow' which as of 25/06/25 can only run on python 3.13.
- When creating the labels, had to replace "pdflatex" with the file directory for pdflatex in miktex module.
- Scrap 'tsch', only using BLE advertising now. I don't think the Pi's require a sharing schedule.
- Scrap 'total_environmental'.  These were used in the SPHERE project, but we're not using them anymore
- Added variable 'total_rpis'. these and the raspberry pi's that forward data to the NUC (gateway).
- `total_gateway`: Total number of gateways including root gateway. Aka the NUC.
- 
