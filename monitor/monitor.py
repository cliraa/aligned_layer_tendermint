import os
import requests
import time
import sys
from slack_sdk import WebhookClient

SLACK_URL = os.environ["SLACK_URL"]
CHAIN_ID = os.environ.get("CHAIN_ID", "alignedlayer")

FAUCET_URL = "http://faucet.alignedlayer.com/"

FAUCET_MIN_FUNDS = 1100050

urls = ["http://91.107.239.79:26657/",
        "http://116.203.81.174:26657/",
        "http://88.99.174.203:26657/",
        "http://128.140.3.188:26657/"]  

NUMBER_OF_NODES = len(urls)

def get_block_of(url):
    for _ in range(5):
        try: 
            height = requests.get(url+"abci_info?", timeout=5).json()["result"]["response"]["last_block_height"]
            timestamp =  requests.get(url+"block?", params={"height": height}, timeout=5).json()["result"]["block"]["header"]["time"]
            return (height,timestamp)
        except:
            print("Waiting to check again...")
            time.sleep(5)
            continue
    return ("ERROR","ERROR")
        
def get_faucet_funds():
    for _ in range(5):
        try:
            funds = requests.get(FAUCET_URL+"balance/"+CHAIN_ID, timeout=5).json()["amount"]
            return funds
        except:
            print("Wainting to check faucet again...")
            time.sleep(5)
            continue
    return "ERROR"

def send_faucet_alert(msg):
    webhook = WebhookClient(SLACK_URL)
    webhook.send(text=msg)

def send_alert(node_url, height, timestamp):
    webhook = WebhookClient(SLACK_URL)
    webhook.send(text="Node with ip: " + node_url + " is not advancing its state. The last block height is "+ height + " at "+ timestamp)

def send_blockchain_halted_alert():
    webhook = WebhookClient(SLACK_URL)
    webhook.send(text="The chain is halted. There aren't enough nodes validating blocks for consensus")

def send_back_up_alert(node_url, height, timestamp):
    webhook = WebhookClient(SLACK_URL)
    webhook.send(text="Node with ip: " + node_url + " is back up. The last block height is "+ height + " at "+ timestamp)

def send_unreachable_alert(node_url, height):
    webhook = WebhookClient(SLACK_URL)
    webhook.send(text="Not able to reach node with ip: " + node_url + ". The last block height is "+ height)

def send_blockchain_back_up():
    webhook = WebhookClient(SLACK_URL)
    webhook.send(text="The blockchain is back up.")

if __name__ == "__main__":
    last_height = [0] * NUMBER_OF_NODES
    current_height = [0] * NUMBER_OF_NODES
    alive = [True for i in range(NUMBER_OF_NODES)]
    faucet_ok = True
    faucet_full = True

    for i in range(NUMBER_OF_NODES):
        print("Starting node " + str(i))
        sys.stdout.flush()
        last_height[i], timestamp = get_block_of(urls[i])
        
    while True:
        time.sleep(60)
        
        funds = get_faucet_funds()
        print(funds)
        if faucet_ok and funds=="ERROR":
            send_faucet_alert("The faucet is unreachable.")
            faucet_ok = False
        elif faucet_ok and faucet_full and funds!="ERROR" and int(funds) < FAUCET_MIN_FUNDS:
            send_faucet_alert("The faucet has run out of funds. Please refill.")
            faucet_full = False
        elif not faucet_ok and funds!="ERROR":
            faucet_ok = True
            send_faucet_alert("The faucet is back online.")
        elif faucet_ok and not faucet_full and int(funds)>=FAUCET_MIN_FUNDS:
            faucet_full = True
            send_faucet_alert("The faucet has been successfully refilled.")

        for i in range(NUMBER_OF_NODES):
            current_height[i], timestamp = get_block_of(urls[i])

            if timestamp=="ERROR": 
                if alive[i]:
                    send_unreachable_alert(urls[i],last_height[i])
                    alive[i] = False
                    
            elif current_height[i]==last_height[i] and alive[i]:
                send_alert(urls[i],current_height[i],timestamp)
                alive[i] = False
            
            elif current_height[i]!=last_height[i] and not alive[i]:
                send_back_up_alert(urls[i],current_height[i],timestamp)
                alive[i] = True

            print("Node number "+ str(i)+ " is at height " + current_height[i]+ " at time "+ timestamp)
            sys.stdout.flush()
            last_height[i] = current_height[i]

