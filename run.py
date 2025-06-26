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

DEFAULT_DEPLOY_VERSION = 'elmer.4' # Set here the default version to deploy

PROJECT = 1 # 0 for IRC-SPHERE

DEVICE_OFFSET_GATEWAY_F = 1
DEVICE_OFFSET_RPIS = 128
DEVICE_OFFSET_WEARABLE = 192

MEM_OFFSET_WEARABLE = "0xDFE0"
MEM_OFFSET_WEARABLE_END = "0xDFFE"

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


def make_mac_addr(network, device, be = True):
    if be == True:
        rand_mac_addr = "ee545253" + "%.2x" % (network) + "%.2x" % (device) # Big-endian
    else:
        rand_mac_addr = "%.2x" % (device) + "%.2x" % (network) + "535254ee" # Little-endian
    return rand_mac_addr

def make_ble_addr(network, device, be = True):
    if be == True:
        BLE_addr = "%.2x" % (device) + "545253" + "%.4x" % (network) # Big-endian
    else:
        BLE_addr = "%.4x" % (network) + "535254" + "%.2x" % (device) # Little-endian
    return BLE_addr

def make_image(network, keys, mac_addr_le, ble_addr_le, offset, offsetend, filename, directory, addr, device_type, count, tc):
    with open("key.bin", 'wb') as f:
        f.write(binascii.unhexlify(get_key(network,keys)))
        f.write(binascii.unhexlify(mac_addr_le))
        f.write(binascii.unhexlify(ble_addr_le))
    f.close()
    call(["srec_cat", "key.bin", "-binary", "-offset", offset, join(directory_firmware, filename), "-intel", "-exclude", offset, offsetend, "-o", join(directory, device_type + "%.2d" % (tc) + "_" + addr+".hex"), "-intel"])
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

total_gateways = int(config.get("DEFAULT", "total_gateways"))
if total_gateways < 0 or total_gateways > 62:
    print("Incorrect number of gateways. Use [0-62].")
    sys.exit(1)

total_rpis = int(config.get("DEFAULT", "total_rpis"))
if total_rpis < 0 or total_rpis > 64:
    print("Incorrect number of rpi sensors. Use [0-64].")
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

Wearable_Firmware_Filename = "SPW2_full.hex"

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

# WEARABLES
call(["srec_cat", join(directory_firmware, "SPW2.hex"), "-intel", join(directory_firmware, "SPW2Stack.hex"), "-intel", "-o", join(directory_firmware, Wearable_Firmware_Filename), "-intel"])   

print("Total Wearables: " + str(total_wearables))
for wearable_count in range(0,total_wearables):
    device_count = device_count + 1

    device = DEVICE_OFFSET_WEARABLE + wearable_count

    label_addr = make_ble_addr(network, device)

    BLE_addr_le = make_ble_addr(network, device, False)
    MAC_addr_le =  make_mac_addr(network, device, False)

    make_image(network, keys, MAC_addr_le, BLE_addr_le, MEM_OFFSET_WEARABLE, MEM_OFFSET_WEARABLE_END, Wearable_Firmware_Filename, directory_img, label_addr, "W", device_count, wearable_count)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "W", device_count, wearable_count)

    print("[Device: " + "%.3d" % (device) + "] Image created. Wearable: " + label_addr)    


af.close()
lf.write("\\end{document}\n")
lf.close()

print("Creating labels..")
os.chdir(join("out", house_string,"qr"))
with open(os.devnull, "w") as fnull:
    result = call([r"C:\Users\wo22854\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull) # replace "fire directory" with "pdflatex"
    result = call([r"C:\Users\wo22854\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull)   
print("Labels written in labels.pdf")
