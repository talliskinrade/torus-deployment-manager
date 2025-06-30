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

DEFAULT_DEPLOY_VERSION = 'elmer.4' # Set here the default version to deploy

PROJECT = 1 # 0 for IRC-SPHERE

DEVICE_OFFSET_ELEPHANT = 1
DEVICE_OFFSET_TRUNK = 128
DEVICE_OFFSET_WEARABLE = 192


MEM_OFFSET_WEARABLE_STATIC_ADDR = "0x0004C85C"               # in the form C0:54:53:52:00:00'NULL' aka 18 bytes long
MEM_OFFSET_WEARABLE_STATIC_ADDR_END = "0x0004C86E"           # 0xC85C + 0x12

MEM_OFFSET_WEARABLE_TARGET_AP_ADDR = "0x20003434"           # in the form ee5453520000 aka 12 bytes long
MEM_OFFSET_WEARABLE_TARGET_AP_ADDR_END = "0x20003440"       # 0x3434 + 0x0C

MEM_OFFSET_WEARABLE_AES_KEY_ADDR = "0x20007A90"                # in the form 01234567012345670123456701234567 aka 4 bytes long
MEM_OFFSET_WEARABLE_AES_KEY_ADDR_END = "0x20007A94"            # 0x7A90 + 0x04


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
        lf.write("\\node[xshift="+"%.3f" % (x+1.5) +"cm,yshift=-"+"%.3f" % (y-0.3) +"cm] at (current page.north west) {" + chr(ord(addr[-1:].upper()) + 17) + "};\n")
    else:
        lf.write("\\node[xshift="+"%.3f" % (x+1.5) +"cm,yshift=-"+"%.3f" % y +"cm] at (current page.north west) {" + device_type + "%s" % (addr[-2:].upper()) + "};\n")
    lf.write("\\end{tikzpicture}\n")


def make_target_addr(network, device, be = True):
    if be == True:
        mac_addr = "EE545253" + "%.2x" % (device) + "%.2x" % (network) # Big-endian
    else:
        mac_addr = "%.4x" % (network) + "%.2x" % (device) + "535254EE" # Little-endian
    return mac_addr


def make_ble_addr(network, device, be = True):
    if be == True:
        BLE_addr = "C0545253" + "%.2x" % (device) + "%.2x" % (network) # Big-endian
    else:
        BLE_addr = "%.4x" % (network) + "%.2x" % (device) + "535254C0" # Little-endian
    return BLE_addr


def make_image(network, keys, mac_addr_le, ble_addr_le, insertions, filename, directory, addr, device_type, count, tc):
    if device_type == "E":
        config = {
            "device": f"{device_type}{tc:02d}_{addr}",
            "key": get_key(network, keys).hex(),
            "target_address": ":".join(mac_addr_le[i:i+2] for i in range(0, len(mac_addr_le), 2)), # wearable
            "ble_address": ":".join(ble_addr_le[i:i+2] for i in range(0, len(ble_addr_le), 2)),
            "firmware": join(directory_firmware, filename)
        }

        config_path = join(directory, f"{device_type}{tc:02d}_{addr}" +  ".json")
        with open(config_path, 'w') as config_file:
            json.dump(config, config_file, indent=4)
    
    else:
        # Create a temporary binary with combined payload
        with open("key.bin", 'wb') as f:
            f.write(binascii.unhexlify(get_key(network,keys)))
            f.write(binascii.unhexlify(mac_addr_le))
            f.write(binascii.unhexlify(ble_addr_le))

        # Use srec_cat to insert each section
        cmd = ["srec_cat"]
        offset_map = {
            "key": binascii.unhexlify(get_key(network, keys)),
            "mac_addr": binascii.unhexlify(mac_addr_le),
            "ble_addr": binascii.unhexlify(ble_addr_le)
        }

        for i, (offset, label) in enumerate(insertions):
            with open(f"{label}.bin", 'wb') as part:
                part.write(offset_map[label])
            cmd += [f"{label}.bin", "-binary", "-offset", offset]

        cmd += [join(directory_firmware, filename), "-intel"]
        for offset, label in insertions:
            cmd += ["-exclude", offset, hex(int(offset, 16) + len(offset_map[label]))]
        cmd += ["-o", join(directory, device_type + "%.2d" % (tc) + "_" + addr + ".hex"), "-intel"]

        call(cmd)
        for _, label in insertions:
            os.remove(f"{label}.bin")
        os.remove("key.bin")


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
if total_elephants < 0 or total_elephants > 62:
    print("Incorrect number of elephants. Use [0-62].")
    sys.exit(1)

total_trunks = int(config.get("DEFAULT", "total_trunks"))
if total_trunks < 0 or total_trunks > 64:
    print("Incorrect number of trunks. Use [0-64].")
    sys.exit(1)

total_wearables = int(config.get("DEFAULT", "total_wearables"))
if total_wearables < 0 or total_wearables > 64:
    print("Incorrect number of wearables. Use [0-64].")
    sys.exit(1)

# Deploy Version
deploy_version = DEFAULT_DEPLOY_VERSION
directory_firmware = join("firmware", deploy_version)

if not os.path.exists(directory_firmware):
    print("#cannot find firmware directory: " + directory_firmware)
    sys.exit(1)

print("Using system version: " + deploy_version)

Wearable_Firmware_Filename = "zephyr_full.hex"
Trunk_Firmware_Filename = "G2_full.hex"

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

# # ELEPHANTS - in progress
# print("Total Elephants: " + str(total_elephants))
# for elephant_count in range(0,total_elephants):
#     device_count = device_count + 1

#     device = DEVICE_OFFSET_ELEPHANT + elephant_count

#     label_addr = make_ble_addr(network, device)

#     BLE_addr_le = make_ble_addr(network, device, False)
#     MAC_addr_le =  make_mac_addr(network, device, False)

#     make_image(network, keys, MAC_addr_le, BLE_addr_le, "", "", "", directory_img, label_addr, "E", device_count, elephant_count)

#     af.write(label_addr + "\n")

#     make_qrcode(directory_qr, lf, label_addr, "E", device_count, elephant_count)

#     print("[Device: " + "%.3d" % (device) + "] Image created. Elephant: " + label_addr)   

# # TRUNKS
# call(["srec_cat", join(directory_firmware, "G2.hex"), "-intel", join(directory_firmware, "G2Stack.hex"), "-intel", "-o", join(directory_firmware, Trunk_Firmware_Filename), "-intel"])   

# print("Total Trunks: " + str(total_trunks))
# for trunk_count in range(0,total_trunks):
#     device_count = device_count + 1

#     device = DEVICE_OFFSET_TRUNK + trunk_count

#     label_addr = make_ble_addr(network, device)

#     BLE_addr_le = make_ble_addr(network, device, False)
#     MAC_addr_le =  make_mac_addr(network, device, False)

#     make_image(network, keys, MAC_addr_le, BLE_addr_le, MEM_OFFSET_TRUNK, MEM_OFFSET_TRUNK_END, Trunk_Firmware_Filename, directory_img, label_addr, "T", device_count, trunk_count)

#     af.write(label_addr + "\n")

#     make_qrcode(directory_qr, lf, label_addr, "T", device_count, trunk_count)

#     print("[Device: " + "%.3d" % (device) + "] Image created. Trunk: " + label_addr)   

# WEARABLES
shutil.copyfile(
    join(directory_firmware, "zephyr.hex"),
    join(directory_firmware, Wearable_Firmware_Filename)
)

print("Total Wearables: " + str(total_wearables))
for wearable_count in range(0,total_wearables):
    device_count = device_count + 1

    device = DEVICE_OFFSET_WEARABLE + wearable_count

    label_addr = make_ble_addr(network, device)

    BLE_addr_le = make_ble_addr(network, device, False)
    MAC_addr_le =  make_target_addr(network, device, False)

    make_image(network, keys, MAC_addr_le, BLE_addr_le, [
    (MEM_OFFSET_WEARABLE_STATIC_ADDR, "ble_addr"),
    (MEM_OFFSET_WEARABLE_TARGET_AP_ADDR, "mac_addr"),
    (MEM_OFFSET_WEARABLE_AES_KEY_ADDR, "key")
], Wearable_Firmware_Filename, directory_img, label_addr, "W", device_count, wearable_count)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "W", device_count, wearable_count)

    print("[Device: " + "%.3d" % (device) + "] Image created. Wearable: " + label_addr)    


af.close()
lf.write("\\end{document}\n")
lf.close()

print("Creating labels..")
os.chdir(join("out", house_string,"qr"))
with open(os.devnull, "w") as fnull:
    result = call([r"pdflatex", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull) # replace "fire directory" with "pdflatex"
    result = call([r"pdflatex", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull)   
print("Labels written in labels.pdf")
