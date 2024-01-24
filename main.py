import pandas as pd
import requests
import time
from datetime import datetime
import os 
import paho.mqtt.client as mqtt
import json

def get_total_power(page):

    start_tag = b"<td align=center>Current Power</td><td align=center>"
    end_tag = b" W</td></tr></center><center><tr><td align=center>Generation Of Current Day</td>"

    start = page.find(start_tag) + len(start_tag)
    end = page.find(end_tag)

    return page[start:end]

def get_days_generation(page):

    start_tag = b"<td align=center>Generation Of Current Day</td><td align=center>"
    end_tag = b" kWh</td></tr></center><center><tr><td align=center>Last connection to website</td>"

    start = page.find(start_tag) + len(start_tag)
    end = page.find(end_tag)

    return page[start:end]

def get_lifetime_generation(page):

    start_tag = b"</tr></center><center><tr><td align=center>Lifetime generation</td><td align=center>"
    end_tag = b" kWh</td></tr></center><center><tr><td align=center>Current Power</td>"

    start = page.find(start_tag) + len(start_tag)
    end = page.find(end_tag)

    return page[start:end]

def get_current_time():
    now = datetime.now()
    return now.strftime("%d/%m/%Y %H:%M:%S")

def read_config(path="data-puller.conf"):
    conf = {}

    f = open("data-puller.conf", "r")

    for line in f:
        field,data = line.split("=")
        conf[field] = data.strip("\n")


    return conf

def check_connection_up(hostname):
   
    while True:

        response = os.system("ping -c 1 " + hostname + "> /dev/null")

        if response == 0:
            print(f"{hostname} is up!")
            return 0
        else:
            print(f"{hostname} is down, waiting 5 minutes")
            time.sleep(300)


conf = read_config()
columns = ["total_power","day_generation", "lifetime_generation", "datetime", "time_since_epoch"]
ip = conf["ip"]
homepageurl = "http://{}/cgi-bin/home".format(ip)

print("waiting for connection")
check_connection_up(ip)
print("connected")


# check if we should publish to mqtt
# this is dumb
run_mqtt=False
if (conf["mqtt"] == "True"):
    run_mqtt = True
    mqtt_host = conf["mqtt_host"]
    mqtt_port = int(conf["mqtt_port"])
    mqtt_topic = conf["mqtt_topic"]

if(run_mqtt):
    # setup mqtt
    client=mqtt.Client("APS-ECU-3 Solar Panel")
    client.connect(mqtt_host,mqtt_port)

prevData = []
while True:

    try:
        # get data from homepage
        page = requests.get(homepageurl).content
        data = []


        # collate data as list
        data.append(float(get_total_power(page)))
        data.append(float(get_days_generation(page)))
        data.append(float(get_lifetime_generation(page)))
        data.append(str(get_current_time()))
        data.append(time.time())

        # we only publish if there is a new packet
        if ( data[0:2] == prevData[0:2]):
            time.sleep(int(conf["sleep_time"]))
            continue

        # write to csv
        df = pd.DataFrame(columns=columns)
        df.loc[0] = data
        df.to_csv(conf["csv_filename"],mode='a',header=False)
        print("wrote to csv at {}".format(get_current_time()))
        


        # write to mqtt
        if(run_mqtt):
            # create json
            JSON = {}
            for i,column in enumerate(columns):
                JSON[column] = data[i]
            
            # publish
            client.publish(mqtt_topic,json.dumps(JSON))

        prevData = data
        # sleep until next reading
        time.sleep(int(conf["sleep_time"]))
   
    except KeyboardInterrupt:
        exit()
    except:
        print("error'ed out, host is probably down")
        check_connection_up(ip)

