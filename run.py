#!/usr/bin/env python

import binascii
import enc
import sys
from subprocess import call
import datetime
import os
import hashlib
import configparser
import getpass
import qrcode
import csv
from os.path import join
import shutil
import json
import subprocess
from pathlib import Path

directory_firmware = "firmware" # Set here the default version to deploy

PROJECT = 1 # 0 for IRC-SPHERE

DEVICE_OFFSET_ELEPHANT = 1
DEVICE_OFFSET_TRUNK = 65
DEVICE_OFFSET_WEARABLE = 129
DEVICE_OFFSET_DOCKING_STATION = 131
DEVICE_OFFSET_NUC = 132


MEM_OFFSET_WEARABLE_STATIC_ADDR = "0x0004c85c"               # in the form C0:54:53:52:00:00'NULL' aka 18 bytes long
MEM_OFFSET_WEARABLE_STATIC_ADDR_END = "0x0004c86e"           # 0xc85c + 0x12

MEM_OFFSET_WEARABLE_TARGET_AP_ADDRS = ["0x0004c7b8", "0x0004c7cc", "0x0004c7e0"]           # pointers stored in the array 'target_ap_addrs'
MEM_OFFSET_WEARABLE_TARGET_AP_ADDRS_END = ["0x0004c7c9", "0x0004c7dd", "0x0004c7f1"]       # each address + 0x11

MEM_OFFSET_WEARABLE_AES_KEY_ADDR = "0x0004c758"              # in the form 01234567012345670123456701234567 aka 16 bytes long
MEM_OFFSET_WEARABLE_AES_KEY_ADDR_END = "0x0004c768"          # 0xc758 + 0x10


TEST_NETWORK_ID_MIN = 250
TEST_NETWORK_ID_MAX = 254


LABELS_PAPER_SIZE = 1 # 5x13 (new)
#LABELS_PAPER_SIZE = 2 # 4x10 (old)


def open_keyfile(password):
    with open ("ckeys.hash", "r") as f:
      hash=f.readlines()
    f.close()
    with open("ckeys", 'rb') as in_file:
        keys = enc.decrypt(in_file, password)
        if  hashlib.sha1(keys).hexdigest() != hash[0]:
            return ""
        else:
            return binascii.hexlify(keys)
    in_file.close()


def get_key(networkID,keys_hex):
    if TEST_NETWORK_ID_MIN <= networkID <= TEST_NETWORK_ID_MAX:
        # A non-secure test network; just use repeated network ID as the key
        return "{:02x}".format(networkID) * 16
    # A secure network; use the key from the file
    return keys_hex[(networkID*16)*2:((networkID+1)*16)*2]


def git_clone_or_pull():
    repos = {
        "https://github.com/shuhao-dong/BORUS.git": "firmware/wearable",
        "https://github.com/shuhao-dong/ble-scan-advertise.git": "firmware/elephants",
        "https://github.com/shuhao-dong/wearable_dock.git": "firmware/docking_station"
    }

    print("Updating Firmware:")

    for url, path in repos.items():
        if os.path.isdir(path):
            # Pull from Git
            subprocess.run(["git", "-C", path, "pull"], check=True)
        else:
            # Clone from Git
            subprocess.run(["git", "clone", url, path], check=True)



def make_qrcode(directory_qr, lf, addr, device_type, count, c):
    qr=qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    m = ':'.join(addr[i:i+2] for i in range(0,len(addr),2))
    qr.add_data(m)

    qr.make(fit=True)
    img=qr.make_image() # fill_color="black", back_color="white"
    qr_filename = device_type + "%.2d" % (c) + "_" + addr+".png"
    img.save(join(directory_qr, qr_filename))
    lf.write("\\begin{tikzpicture}[remember picture,overlay]\n")

    if LABELS_PAPER_SIZE == 1:
      col = count // 13
      row = count % 13
      x = 1.5+4.2*col
      y = 1.6+2.25*row

    if LABELS_PAPER_SIZE == 2:
      col = count // 10
      row = count % 10
      x = 2.5+5.1*col
      y = 2.8+2.7*row


    lf.write("\\node[xshift="+"%.3f" % x +"cm,yshift=-"+"%.3f" % y +"cm] at (current page.north west) {\\includegraphics[width=2cm]{" + qr_filename + "}};\n")
    if device_type == "W":
        lf.write("\\node[xshift="+"%.3f" % (x+1.5) +"cm,yshift=-"+"%.3f" % (y+0.3) +"cm] at (current page.north west) {" + device_type + "%s" % (addr[-2:].upper()) + "};\n")
        # lf.write("\\node[xshift="+"%.3f" % (x+1.5) +"cm,yshift=-"+"%.3f" % (y-0.3) +"cm] at (current page.north west) {" + chr(ord(addr[-1:].upper()) + 17) + "};\n")
    else:
        lf.write("\\node[xshift="+"%.3f" % (x+1.5) +"cm,yshift=-"+"%.3f" % y +"cm] at (current page.north west) {" + device_type + "%s" % (addr[-2:].upper()) + "};\n")
    lf.write("\\end{tikzpicture}\n")


def make_wearable_addr(network, device, be = True):
    if be == True:
        mac_addr = "EE:54:52:53:" + "%.2x" % (network) + ":" + "%.2x" % (device) # Big-endian
    else:
        mac_addr = "%.2x" % (device) + ":" + "%.4x" % (network) + ":53:52:54:EE" # Little-endian
    return mac_addr


def make_ble_addr(network, device, be = True):
    if be == True:
        BLE_addr = "C0:54:52:53:" + "%.2x" % (network) + ":" + "%.2x" % (device) # Big-endian
    else:
        BLE_addr = "%.2x" % (device) + ":" + "%.2x" % (network) + ":53:52:54:C0" # Little-endian
    return BLE_addr


def make_ip_addr(network, device):
    # "192.168" means its a private ip address
    ip_addr = "192.168."+ "%.2x" % (network) + "." + "%.2x" % (device)
    return ip_addr


def make_image(network, keys, houseID, wearable_addr_be, ble_addr_be, nuc_addr, filename, directory, addr, device_type, tc):
    if device_type == "E": # RASPBERRY PI FORWARDING GATEWAYS
        config = {
            "device": f"{device_type}{tc:02d}_{addr}",
            "key": str(get_key(network, keys)),
            "wearable_addresses": wearable_addr_be,
            "ble_address": ble_addr_be,
            "mqtt_topic": f"{houseID}/{addr}",
            "broker_ip_addr": nuc_addr,
            "broker_port": 1883
        }

        config_path = join(directory, f"{device_type}{tc:02d}_{addr}" +  ".json")
        with open(config_path, 'w') as config_file:
            json.dump(config, config_file, indent=4)
    
    elif device_type == "T": # DONGLES
        input_file = join(directory_firmware, filename)
        output_file = join(directory, f"{device_type}{tc:02d}_{addr}.hex")
        shutil.copyfile(input_file, output_file)
        
    elif device_type == "N": # NUC
        config = {
            "device": f"{device_type}{tc:02d}_{addr}",
            "wearable_addresses": wearable_addr_be,
            "ble_addresses": ble_addr_be,
            "mqtt_topics": [f"{houseID}/{ble_addr.replace(":", "")}" for ble_addr in ble_addr_be],
            "broker_ip_addr": nuc_addr,
            "static_ip": True,
            "broker_port": 1883
        }

        config_path = join(directory, f"{device_type}{tc:02d}_{addr}" +  ".json")
        with open(config_path, 'w') as config_file:
            json.dump(config, config_file, indent=4)

    elif device_type == "D": # DOCKING STATION
        config = {
            "device": f"{device_type}{tc:02d}_{addr}",
            "wearable_addresses": wearable_addr_be,
            "mqtt_topic": f"{houseID}/{addr}",
            "broker_ip_addr": nuc_addr,
            "broker_port": 1883
        }

        config_path = join(directory, f"{device_type}{tc:02d}_{addr}" +  ".json")
        with open(config_path, 'w') as config_file:
            json.dump(config, config_file, indent=4)
    
    else: # WEARABLE
        # Paths
        root = Path(__file__).parent
        script_path = root / "firmware" / "wearable" / "tools" / "factory_data_generator" / "mk_factory_page.py"
        output_file = root / (str(addr)+"_factory_data.hex")
        destination_dir = root / "out" / "0000" / "img"
        destination_file = destination_dir / (str(addr)+"_factory_data.hex")

        subprocess.run([
            "python",
            str(script_path),
            "--ble", wearable_addr_be,
            "--ap", *ble_addr_be,
            "--key", get_key(network, keys),
            "--out", str(output_file)
        ], check=True, stdout=subprocess.DEVNULL)

        destination_dir.mkdir(parents=True, exist_ok=True)

        shutil.move(str(output_file), str(destination_file))



###########################################################################################


if not os.path.isfile('ckeys'):
    print("Not installed. Run install.py first.")
    sys.exit(1)

# Input parameters
if len(sys.argv) < 2:
    print("Incorrect input parameters. Set HID.")
    sys.exit(1)

config_file = sys.argv[1] + ".cfg"

if os.path.isfile(join("config", config_file)) == False:
    print("Configuration file does not exist.")
    sys.exit(1)

config = configparser.ConfigParser()
config.read(join("config", config_file))

total_elephants = int(config.get("DEFAULT", "total_elephants"))
if total_elephants < 0 or total_elephants > 64:
    print("Incorrect number of elephants. Use [0-64].")
    sys.exit(1)

total_trunks = int(config.get("DEFAULT", "total_trunks"))
if total_trunks < 0 or total_trunks > 64:
    print("Incorrect number of trunks. Use [0-64].")
    sys.exit(1)

total_wearables = int(config.get("DEFAULT", "total_wearables"))
if total_wearables < 0 or total_wearables > 2:
    print("Incorrect number of wearables. Use [0-2].")
    sys.exit(1)

total_nucs = int(config.get("DEFAULT", "total_nucs"))
if total_nucs < 0 or total_nucs > 1:
    print("Incorrect number of NUCs. Use [0-1].")
    sys.exit(1)

total_docks = int(config.get("DEFAULT", "total_docking_stations"))
if total_docks < 0 or total_docks > 1:
    print("Incorrect number of Docking Stations. Use [0-1].")
    sys.exit(1)


# Deploy Version
directory_firmware = "firmware" # Set here the default version to deploy

# Update or clone necessary firmware repositories
git_clone_or_pull()

if not os.path.exists(directory_firmware):
    print("Cannot find firmware directory: " + directory_firmware)
    sys.exit(1)

# print("Using system version: " + deploy_version)

Wearable_Firmware_Filename = "zephyr.hex"
Trunk_Firmware_Filename = "TRS_T.hex"

# convert house ID to network ID
network = -1
house = int(config.get("DEFAULT", "house_id"))
house_string = "%.4d" % (house)
with open('torus_network_id.csv', 'r') as fc:
    reader = csv.reader(fc, delimiter=',')
    for row in reader:
         if row[1] == house_string:
             if row[2] == "0":
                 print ("House ID not allocated.")
                 sys.exit(1)
             if row[3] == "0":
                 print ("House ID not active.")
                 sys.exit(1)
             network = int(row[0])

if network == -1:
    print("House ID not registered in 'torus_network_id.csv'.")
    sys.exit(-1)

if TEST_NETWORK_ID_MIN <= network <= TEST_NETWORK_ID_MAX:
    keys = ""
else:
    # Unlock key file
    password = getpass.getpass()
    keys = open_keyfile(password)
    if keys == "":
        print("Wrong password.")
        sys.exit(1)

# Make the directory structure
if not os.path.exists("out"):
    os.makedirs("out")
if not os.path.exists("firmware"):
    os.makedirs("firmware")

directory = join("out", house_string)
try:
  if os.path.exists(directory):
    shutil.rmtree(directory)
finally:
  os.makedirs(directory)

af = open(join(directory, "addresses.txt"), "w")

directory_img = join(directory, "img")
if not os.path.exists(directory_img):
    os.makedirs(directory_img)
directory_qr = join(directory, "qr")
if not os.path.exists(directory_qr):
    os.makedirs(directory_qr)

lf = open(join(directory_qr, "labels.tex"), "w")
lf.write("\\documentclass[12pt, a4paper]{article}\n")
lf.write("\\usepackage{tikz}\n")
lf.write("\\begin{document}\n")
lf.write("\\pagenumbering{gobble}")

print("TORUS Deployment Manager - Report")
print("--------------------------------------------")
print("House ID: " + house_string)
print("Network ID: " + "%d" % (network))
print("Date: " + datetime.date.today().strftime('%Y-%m-%d'))

device_count = 0

# ELEPHANTS
print("Total Elephants: " + str(total_elephants))
BLE_addr_be = []
elephant_label_addr = []
for elephant_count in range(0,total_elephants):
    device_count = device_count + 1

    device = DEVICE_OFFSET_ELEPHANT + elephant_count

    label_addr = make_ble_addr(network, device).replace(":", "")
    elephant_label_addr.append(label_addr)

    BLE_addr_be.append(make_ble_addr(network, device))

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "E", device_count, elephant_count)

# TRUNKS
print("Total Trunks: " + str(total_trunks))
trunk_label_addr = []
for trunk_count in range(0,total_trunks):
    device_count = device_count + 1

    device = DEVICE_OFFSET_TRUNK + trunk_count

    label_addr = make_ble_addr(network, device).replace(":", "")
    trunk_label_addr.append(label_addr)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "T", device_count, trunk_count)

# WEARABLES
print("Total Wearables: " + str(total_wearables))

wearable_addr_be = []
wearable_label_addr = []
for wearable_count in range(0,total_wearables):
    device_count = device_count + 1

    device = DEVICE_OFFSET_WEARABLE + wearable_count

    label_addr = make_wearable_addr(network, 1).replace(":", "")
    wearable_label_addr.append(label_addr)

    wearable_addr_be.append(make_wearable_addr(network, 1))         # Big Endian

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "W", device_count, wearable_count)

# DOCKING STATION
print("Total Docking Stations: " + str(total_docks))
for dock_count in range(0,total_docks):
    device_count = device_count + 1

    device = DEVICE_OFFSET_DOCKING_STATION + dock_count

    label_addr = make_ble_addr(network, device).replace(":", "")
    dock_label_addr = label_addr

    dock_addr = make_ip_addr(network, device)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "D", device_count, dock_count)

# NUC
print("Total NUCs: " + str(total_nucs))
for nuc_count in range(0,total_nucs):
    device_count = device_count + 1

    device = DEVICE_OFFSET_NUC + nuc_count

    label_addr = make_ip_addr(network, device).replace(".", "")
    nuc_label_addr = label_addr

    NUC_addr = make_ip_addr(network, device)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "N", device_count, nuc_count)



# MAKE IMAGES
# ELEPHANTS
for el in range(len(BLE_addr_be)):
    make_image(network, keys, house_string, wearable_addr_be, BLE_addr_be[el], NUC_addr, "", directory_img, elephant_label_addr[el], "E", el)
    print("[Device: " + "%.3d" % (device) + "] Image created. Elephant: " + elephant_label_addr[el].replace(":", ""))   

# TRUNKS
for tr in range(len(trunk_label_addr)):
    make_image(network, keys, house_string, "", "", "", Trunk_Firmware_Filename, directory_img, trunk_label_addr[tr], "T", tr)
    print("[Device: " + "%.3d" % (device) + "] Image created. Trunk: " + trunk_label_addr[tr].replace(":", ""))   

# WEARABLES
for wear in range(len(wearable_addr_be)):
    make_image(network, keys, house_string, wearable_addr_be[wear], BLE_addr_be, "", Wearable_Firmware_Filename, directory_img, wearable_label_addr[wear], "W", wear)
    print("[Device: " + "%.3d" % (device) + "] Image created. Wearable: " + wearable_label_addr[wear].replace(":", ""))   

# DOCKING STATIONS
make_image(network, "", house_string, wearable_addr_be, BLE_addr_be, NUC_addr, "", directory_img, dock_label_addr, "D", dock_count)
print("[Device: " + "%.3d" % (device) + "] Image created. Docking Station: " + dock_label_addr.replace(":", ""))

# NUCS
make_image(network, keys, house_string, wearable_addr_be, BLE_addr_be, NUC_addr, "", directory_img, nuc_label_addr, "N", nuc_count)
print("[Device: " + "%.3d" % (device) + "] Image created. NUC: " + nuc_label_addr.replace(":", "")) 

af.close()
lf.write("\\end{document}\n")
lf.close()

print("Creating labels..")
os.chdir(join("out", house_string,"qr"))
with open(os.devnull, "w") as fnull:
    result = call([r"pdflatex", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull) # replace "fire directory" with "pdflatex"
    result = call([r"pdflatex", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull)   
print("Labels written in labels.pdf")
