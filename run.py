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
import re
from intelhex import IntelHex


PROJECT = 1 # 0 for IRC-SPHERE

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
        "https://github.com/shuhao-dong/ble-scan-advertise.git": "firmware/receivers",
        "https://github.com/JoelDunnett/JORUS.git": "firmware/docking_station"
    }

    special_branch = {
        "https://github.com/shuhao-dong/ble-scan-advertise.git": "integration/mqtt-publisher"
    }

    print("Updating Firmware:")

    for url, path in repos.items():
        if os.path.isdir(path):
            print(f"Pulling updates for {path}...")
            subprocess.run(["git", "-C", path, "fetch"], check=True)

            if url in special_branch:
                branch = special_branch[url]
                print(f"Switching to branch {branch} in {path}...")
                subprocess.run(["git", "-C", path, "checkout", branch], check=True)
                subprocess.run(["git", "-C", path, "pull", "origin", branch], check=True)
            else:
                subprocess.run(["git", "-C", path, "pull"], check=True)

        else:
            if url in special_branch:
                branch = special_branch[url]
                print(f"Cloning {url} into {path} (branch: {branch})...")
                subprocess.run(["git", "clone", "--branch", branch, url, path], check=True)
            else:
                print(f"Cloning {url} into {path} (default branch)...")
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


def make_addr(prefix, network, device, be = True):
    if be == True:
        BLE_addr = prefix + ":54:52:53:" + "%.2x" % (network) + ":" + "%.2x" % (device) # Big-endian
    else:
        BLE_addr = "%.2x" % (device) + ":" + "%.2x" % (network) + ":53:52:54:" +  prefix # Little-endian
    return BLE_addr


def make_ip_addr(network, device):
    # "192.168" means its a private ip address
    ip_addr = "192.168."+ "%.2x" % (network) + "." + "%.2x" % (device)
    return ip_addr


def make_image(network, keys, houseID, wearable_addr_be, ble_addr_be, nuc_addr, directory, addr, device_type, tc):
    if device_type == "R": # RASPBERRY PI FORWARDING GATEWAYS

        # Regex pattern to find the target_mac definition
        input_path = os.path.join("firmware", "receivers", "scan_adv.c")
        output_path = os.path.join(directory, addr+"_scan_adv.c")

        with open(input_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        patterns_to_replace = {
            r'(^[ \t]*#define\s+BROKER_ADDR\s+)".*?"(\s*$)': f'\\1"{nuc_addr}"\\2',
            r'(^[ \t]*#define\s+MQTT_TOPIC\s+)".*?"(\s*$)': f'\\1"{houseID}/{addr}"\\2',
            r'(static\s+const\s+char\s+random_ble_addr\[\]\s*=\s*)".*?"(\s*;?\s*$)': f'\\1"{ble_addr_be}"\\2',
        }

        for pattern, replacement in patterns_to_replace.items():
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # AES Key
        key = get_key(network, keys).decode("utf-8")    # returns 32-character hex string
        key_bytes = bytes.fromhex(key)                  # convert to 16 bytes
        aes_key_c_array = ',\n    '.join(f'0x{b:02X}' for b in key_bytes)

        aes_key_replacement = f'''static const unsigned char aes_key[16] = {{
            {aes_key_c_array}
        }};'''

        content = re.sub(
            r'static\s+const\s+unsigned\s+char\s+aes_key\[16\]\s*=\s*\{[^}]*?\};',
            aes_key_replacement,
            content,
            flags=re.DOTALL
        )

        # Wearable Address
        content = re.sub(
            r'static\s+const\s+char\s+target_mac\[\]\s*=\s*"[^"]+";\s*(/\*.*\*/)?',
            '',
            content
        )
        content = re.sub(
            r'const\s+char\*\s+target_mac\[\]\s*=\s*\{[^}]*?\};',
            '',
            content,
            flags=re.DOTALL
        )

        if len(wearable_addr_be) == 1:
            target_mac_decl = f'static const char target_mac[] = "{wearable_addr_be[0]}"; /* BORUS wearable */'
        else:
            target_mac_array = ',\n    '.join(f'"{mac}"' for mac in wearable_addr_be)
            target_mac_decl = f'const char* target_mac[] = {{\n    {target_mac_array}\n}}; /* BORUS wearable */'
        
        insertion_match = re.search(r'static\s+const\s+char\s+random_ble_addr\[\]\s*=\s*".*?";', content)
        insert_idx = insertion_match.start()

        content = content[:insert_idx] + target_mac_decl + '\n' + content[insert_idx:]
            
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(content)

        
    # elif device_type == "N": # NUC
    #     config = {
    #         "device": f"{device_type}{tc:02d}_{addr}",
    #         "wearable_addresses": wearable_addr_be,
    #         "ble_addresses": ble_addr_be,
    #         "mqtt_topics": [f"{houseID}/{ble_addr.replace(":", "")}" for ble_addr in ble_addr_be],
    #         "broker_ip_addr": nuc_addr,
    #         "static_ip": True,
    #         "broker_port": 1883
    #     }

    #     config_path = join(directory, f"{device_type}{tc:02d}_{addr}" +  ".json")
    #     with open(config_path, 'w') as config_file:
    #         json.dump(config, config_file, indent=4)


    elif device_type == "D": # DOCKING STATION
        input_path = os.path.join("firmware", "docking_station", "dock.c")
        output_path = os.path.join(directory, f"{addr}_dock.c")

        with open(input_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()

        # Remove existing #define values
        patterns_to_replace = {
            r'(^[ \t]*#define\s+BROKER_ADDR\s+)".*?"(\s*$)': f'\\1"{nuc_addr}"\\2',
            r'(^[ \t]*#define\s+MQTT_TOPIC\s+)".*?"(\s*$)': f'\\1"{houseID}/{addr}"\\2',
            r'(^[ \t]*#define\s+WEARABLE_ID\s+)".*?"(\s*$)': f'\\1"{ble_addr_be[0]}"\\2',
            r'(^[ \t]*#define\s+GATEWAY_ID\s+)".*?"(\s*$)': f'\\1"{wearable_addr_be[0]}"\\2',
        }

        for pattern, replacement in patterns_to_replace.items():
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(content)


    else: # WEARABLE
        # Paths
        root = Path(__file__).parent
        script_path = root / "firmware" / "wearable" / "tools" / "factory_data_generator" / "mk_factory_page.py"
        output_file = root / (str(addr)+"_factory_data.hex")
        destination_dir = root / Path(directory)
        destination_file = destination_dir / (str(addr)+"_factory_data.hex")

        # print("Wearable:")
        # print(wearable_addr_be, ", ", type(wearable_addr_be))
        # print("Targets:")
        # print(ble_addr_be, ", ", type(ble_addr_be))
        # print(ble_addr_be[0], ", ", type(ble_addr_be[0]))
        # print("Key:")
        # print(get_key(network, keys), ", ", type(get_key(network, keys)))
        # print("Output File:")
        # print(str(output_file), ", ", type(str(output_file)))
        # print("Input File:")
        # print(str(script_path), ", ", type(str(script_path)))

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

total_receivers = int(config.get("DEFAULT", "total_receivers"))
if total_receivers < 0 or total_receivers > 64:
    print("Incorrect number of elephants. Use [0-64].")
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

directory_wearable = join(directory_img, "wearable")
if not os.path.exists(directory_wearable):
    os.makedirs(directory_wearable)

directory_receiver = join(directory_img, "receiver")
if not os.path.exists(directory_receiver):
    os.makedirs(directory_receiver)

directory_dock = join(directory_img, "dock")
if not os.path.exists(directory_dock):
    os.makedirs(directory_dock)

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

# RECEIVERS
print("Total Receivers: " + str(total_receivers))
BLE_addr_be = []
receiver_label_addr = []
for receiver_count in range(0,total_receivers):
    device_count = device_count + 1

    device = receiver_count

    addr = make_addr("C0", network, device)
    BLE_addr_be.append(addr)

    label_addr = addr.replace(":", "")
    receiver_label_addr.append(label_addr)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "R", device_count, receiver_count)


# WEARABLES
print("Total Wearables: " + str(total_wearables))
wearable_addr_be = []
wearable_label_addr = []
for wearable_count in range(0,total_wearables):
    device_count = device_count + 1

    device = wearable_count

    addr = make_addr("EE", network, device)
    wearable_addr_be.append(addr)

    label_addr = addr.replace(":", "")
    wearable_label_addr.append(label_addr)

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "W", device_count, wearable_count)

# DOCKING STATION
print("Total Docking Stations: " + str(total_docks))
for dock_count in range(0,total_docks):
    device_count = device_count + 1

    device = dock_count

    addr = make_addr("C1", network, device)
    dock_label_addr = addr.replace(":", "")

    af.write(dock_label_addr + "\n")

    make_qrcode(directory_qr, lf, dock_label_addr, "D", device_count, dock_count)

# NUC
print("Total NUCs: " + str(total_nucs))
for nuc_count in range(0,total_nucs):
    device_count = device_count + 1

    device = nuc_count

    # NUC_addr = make_ip_addr(network, device)
    NUC_addr = "192.168.88.251"

    label_addr = NUC_addr.replace(".", "")
    nuc_label_addr = label_addr

    af.write(label_addr + "\n")

    make_qrcode(directory_qr, lf, label_addr, "N", device_count, nuc_count)


# MAKE IMAGES
# RECEIVERS
for rec in range(len(BLE_addr_be)):
    make_image(network, keys, house_string, wearable_addr_be, BLE_addr_be[rec], NUC_addr, directory_receiver, receiver_label_addr[rec], "R", rec)
    print("[Device: " + "%.3d" % (device) + "] Image created. Receivers: " + receiver_label_addr[rec].replace(":", ""))   

# WEARABLES
for wear in range(len(wearable_addr_be)):
    make_image(network, keys, house_string, wearable_addr_be[wear], BLE_addr_be, "", directory_wearable, wearable_label_addr[wear], "W", wear)
    print("[Device: " + "%.3d" % (device) + "] Image created. Wearable: " + wearable_label_addr[wear].replace(":", ""))   

# DOCKING STATIONS
make_image(network, keys, house_string, wearable_addr_be, BLE_addr_be, NUC_addr, directory_dock, dock_label_addr, "D", dock_count)
print("[Device: " + "%.3d" % (device) + "] Image created. Docking Station: " + dock_label_addr.replace(":", ""))

# # NUCS
# make_image(network, keys, house_string, wearable_addr_be, BLE_addr_be, NUC_addr, "", directory_img, nuc_label_addr, "N", nuc_count)
# print("[Device: " + "%.3d" % (device) + "] Image created. NUC: " + nuc_label_addr.replace(":", "")) 

af.close()
lf.write("\\end{document}\n")
lf.close()

print("Creating labels..")
os.chdir(join("out", house_string,"qr"))
with open(os.devnull, "w") as fnull:
    result = call([r"pdflatex", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull) 
    result = call([r"pdflatex", "-output-directory=..", "labels.tex"], stdout = fnull, stderr = fnull)   
print("Labels written in labels.pdf")
