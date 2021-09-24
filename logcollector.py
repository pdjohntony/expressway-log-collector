import sys
import time
import requests
import re
import configparser
requests.packages.urllib3.disable_warnings()

#! Future features
# Multiple config.ini files
# CLI menu instead of passing arguments

def read_ini(file_path):
	config = configparser.ConfigParser()
	config.read(file_path)

	cfg = {
		"creds": (config["GENERAL"]["username"], config["GENERAL"]["password"]),
		"exp_servers": config["SERVERS"]
	}
	return cfg

def log_put(url, exp_creds, headers, req_body):
	url = url + "/api/provisioning/common/diagnosticlogging"
	# req_body = {"Mode": mode}
	# print(f"PUT {url}")
	response = requests.put(url=url, auth=exp_creds, json=req_body, headers=headers, verify=False)
	print(f"    Response Status: {response.status_code} {response.reason}")
	print(f"    Response: {response.json()}")

def get_filename_from_cd(cd):
	if not cd:
		return None
	fname = re.findall('filename=(.+)', cd)
	if len(fname) == 0:
		return None
	return fname[0]

def log_download(url, exp_creds, headers, req_body):
	url = url + "/api/provisioning/common/diagnosticlogging"

	while True:
		# print(f"GET {url}")
		response = requests.get(url=url, auth=exp_creds, headers=headers, verify=False)
		print(f"    Response Status: {response.status_code} {response.reason}")
		print(f"    Response: {response.json()}")
		rj = response.json()
		if rj["DownLoadStatus"] == "Ready to download": break
		time.sleep(2)

	# print(f"PUT {url}")
	response = requests.put(url=url, auth=exp_creds, json=req_body, headers=headers, verify=False)
	print(f"    Response Status: {response.status_code} {response.reason}")
	filename = get_filename_from_cd(response.headers.get('content-disposition'))
	filename = filename.strip('"') # Remove quotes from ends of string
	filename = filename.replace(':','_') # Replace : for _ due to Windows filename limitation
	open(filename, 'wb').write(response.content)
	print(f"Log saved: {filename}")

cfg = read_ini("config.ini")
exp_creds = cfg['creds']

headers = {"content-type": "application/json"}

exp_srv_list = []
for k in cfg['exp_servers']:
	x = cfg['exp_servers'][k].split(':')
	exp_srv_list.append((x[0].strip(), x[1].strip()))

# Prefix https to servers
# print(exp_srv_list)
for i,v in enumerate(exp_srv_list):
	exp_srv_list[i] = ("https://" + v[0], v[1])
# print(exp_srv_list)

try:
	if not re.search("^(start|stop|download)$", sys.argv[1]):
		print(f"{sys.argv[1]} is not a valid argument!")
		sys.exit(1)
except IndexError:
	print("Missing arguments!")
	sys.exit(1)

if sys.argv[1] == "start":
	# Start logging on master servers
	for srv in exp_srv_list:
		if srv[1] == "master":
			print(f"Starting logging on {srv[0]}")
			req_body = {
				"Mode": "start",
				"TCPDump": "on"
			}
			log_put(url=srv[0], exp_creds=exp_creds, headers=headers, req_body=req_body)

elif sys.argv[1] == "stop":
	# Stop logging on master servers
	for srv in exp_srv_list:
		if srv[1] == "master":
			print(f"Stopping logging on {srv[0]}")
			req_body = {
				"Mode": "stop"
			}
			log_put(url=srv[0], exp_creds=exp_creds, headers=headers, req_body=req_body)

elif sys.argv[1] == "download":
	# Initiate log collection on all servers, then download
	for srv in exp_srv_list:
		print(f"Starting log collection on {srv[0]}")
		req_body = {
			"Mode": "collect"
		}
		log_put(url=srv[0], exp_creds=exp_creds, headers=headers, req_body=req_body)
	
	time.sleep(2)

	for srv in exp_srv_list:
		print(f"Starting log download on {srv[0]}")
		req_body = {
			"Mode": "download"
		}
		log_download(url=srv[0], exp_creds=exp_creds, headers=headers, req_body=req_body)