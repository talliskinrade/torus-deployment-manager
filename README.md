
# README #

## Information ##

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

## Installation ##

Run `install.py` to setup a password.

### Dependencies ###

Install all necessary python packages, `srecord` for `srec_cat`, and `texlive` for `pdflatex`.

## Configuration File ##

- `house_id`: House ID (HID)
- `version`: System version to use as in `/firmware/` (optional).
- `tsch`: TSCH Schedule to use. Gateways should match schedule: e.g. for 4 total gateways use `3_and_1_shared_schedule`. 
- `total_gateway`: Total number of gateways including root gateway.
- `total_environmental`: Total number of environmental sensors.
- `total_wearables`: Total number of wearable sensors.

### Example ###

~~~~
>>type config\0000.cfg
[DEFAULT]
house_id = 0000
tsch = 3_and_1_shared_schedule
total_gateways = 4
total_environmental = 4
total_wearables = 4
~~~~

## Record of Deployments ##

Each house should be allocated a unique House ID (HID) and entered at the `sphere_network_id.csv`:

- 1st column: Network ID (NID)
- 2nd column: House ID (HID)
- 3rd column: 1 if HID allocated to participant
- 4th column: 1 if deployment is active

## Execution Example ##

~~~~
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
~~~~

## Output ##

The output can be found in `/out/<HID>/`:

- `/out/<HID>/img/`: Contains the images to be installed to the devices
- `/out/<HID>/label.pdf`: Label file for printing

## Flashing the Devices ##

### SPHERE Gateways ###

The two MCUs are named `F` and `G` as marked on the silkscreen of the PCB. 

For the root gateway programme only the `F` side.

### SPHERE Environmental Sensors ###

Use the image marked as 'water sensor' for the environmental sensors that have the water flow sensor board plugged.

