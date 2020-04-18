from helium import *
from time import sleep
from datetime import datetime
import json
import requests
import pickle
import time
import os
import sys

# -- data -- #
credentials = json.load(open("credentials.json"))
INSTACART_EMAIL = credentials["INSTACART_EMAIL"]
INSTACART_PASSWORD = credentials["INSTACART_PASSWORD"]
MAILGUN_DOMAIN = credentials["MAILGUN_DOMAIN"]
MAILGUN_API_KEY = credentials["MAILGUN_API_KEY"]
STORE_LIST = credentials["STORE_LIST"]
INSTACART_BASE_URL = credentials["INSTACART_BASE_URL"]
INSTACART_DELIVERY_URL = credentials["INSTACART_DELIVERY_URL"]
NOTIFICATION_EMAIL = credentials["NOTIFICATION_EMAIL"]

# -- login logic -- #
def login():
    print("Logging into Instacart...")
    try:
        f = open("cookies.pkl", "rb")
        cookies = pickle.load(f)
        print("Cookies found! Using cookies to log in.")
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)
        go_to(INSTACART_BASE_URL)
    except IOError:
        print("Cookies not found, logging in!")
        click(Button("Log In"))
        write(INSTACART_EMAIL, into="Email address")
        write(INSTACART_PASSWORD, into="Password")
        click(Button("Log In"))
        wait_until(Link("Your Items").exists)
        pickle.dump( driver.get_cookies() , open("cookies.pkl","wb"))

driver = start_chrome(INSTACART_BASE_URL, headless=True)
login()


# -- check store logic -- #
def check_delivery_times_for_store(store_name, retries=0):
    if retries > 2:
        print("Already retried 2 times, giving up...")
        return False, "Errored after 2 retries"

    sleep(2)
    go_to(INSTACART_DELIVERY_URL.format(store_name))
    sleep(2)

    if (Text("Saturday").exists() or Text("Sunday").exists() or Text("Monday").exists() or Text("Tuesday").exists() or Text("Wednesday").exists() or Text("Thursday").exists() or Text("Friday").exists()):
        return True, "Delivery times found for {}!".format(store_name)
    elif Text("Fast & Flexible").exists():
        return True, "Delivery times found for {}!".format(store_name)
    elif Link("More times").exists():
        return True, "Delivery times found for {}!".format(store_name)
    elif (Text("Today").exists() or Text("Tomorrow").exists()):
        return True, "Delivery times found for {}!".format(store_name)
    elif Text("There was a problem loading this page").exists():
        return False, "There was a problem loading {}".format(store_name)
    elif Text("No delivery times available").exists():
        return False, "No Delivery times available for {}".format(store_name)
    else:
        #unexpected response, generate screenshot, return generic error
        print("Retrying {} time #{}".format(store_name, retries + 1))
        driver.save_screenshot("screenshot_retry_{}.png".format(retries))
        login()
        return check_delivery_times_for_store(store_name, retries + 1)


# -- send email -- #
def send_simple_message(message):

    if (MAILGUN_API_KEY=="") or (MAILGUN_API_KEY=="xxx") or (MAILGUN_DOMAIN=="") or (MAILGUN_DOMAIN=="xxx.mailgun.org") or (NOTIFICATION_EMAIL=="") or (NOTIFICATION_EMAIL=="xxx@gmail.com"):
        print ("ERROR: Can't sent email notification. Invalid Mailgun API Key, URL or Notification Email")
        return null

    return requests.post(
        "https://api.mailgun.net/v3/{}/messages".format(MAILGUN_DOMAIN),
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": "Instacart Delivery Notifier <instacart_notify@{}>".format(
                MAILGUN_DOMAIN
            ),
            "to": NOTIFICATION_EMAIL,
            "subject": "Instacart Delivery Time Available!!",
            "text": message,
        },
    )


# -- check all stores in list and notify -- #
def main():
    deliveryAvailability = False
    
    voiceNotification = False
    emailNotification = True

    while deliveryAvailability == False:
        print("--------------- "+str(datetime.now().strftime("%b %d, %Y %H:%M:%S"))+" ------------")

        for store in STORE_LIST:
            availability, message = check_delivery_times_for_store(store)
            if availability == True:
                if voiceNotification:
                    os.system('say -v Samantha "Delivery is available at {}!"'.format(store))
                if emailNotification:
                    send_simple_message(message)
                deliveryAvailability = True

            print (message)

        print("\nNext update in 15 minutes...\n")
        time.sleep(900)


if __name__ == "__main__":
    main()
