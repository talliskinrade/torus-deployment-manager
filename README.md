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

