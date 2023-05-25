import argparse
import os
import pytz
import csv
import base64
import requests
from datetime import datetime, time, date, timedelta
from dotenv import load_dotenv
import json
from pathlib import Path


load_dotenv()
dotenv_path = Path('pagerduty-importer.env')
load_dotenv(dotenv_path=dotenv_path)

def send_email_sparkpost(csv_file, recipient_email, working_hours=False, on_call_non_working_hours=False, all_hours=False):
    sparkpost_api_key = os.getenv('SPARKPOST_API_KEY')
    base_url = 'https://api.eu.sparkpost.com/api/v1'
    sender = '<EMAIL_TO_SEND>'

    if working_hours:
        subject = "Weekly Pagerduty Working Hours Report"
        body = "Report in CSV format"
        recipients = [recipient_email]
    elif on_call_non_working_hours:
        subject = "Weekly Pagerduty Non Working Hours Report"
        body = "Report in CSV format"
        recipients = [recipient_email]
    elif all_hours:
        subject = "Weekly Pagerduty With ALL incidents Report"
        body = "Report in CSV format"
        recipients = [recipient_email]
    else:
        print('This script requires working_hours, n_call_non_working_hours or all_hours parameter')

    with open(csv_file, 'rb') as file:
        attachment_data = file.read()

    attachment = {
        'name': csv_file,
        'type': 'text/csv',
        'data': base64.b64encode(attachment_data).decode()
    }

    headers = {
        'Authorization': f'Bearer {sparkpost_api_key}',
        'Content-Type': 'application/json'
    }

    data = {
        'options': {
            'sandbox': False
        },
        'content': {
            'from': sender,
            'subject': subject,
            'text': body,
            'attachments': [attachment]
        },
        'recipients': [{'address': recipient} for recipient in recipients]
    }

    response = requests.post(f'{base_url}/transmissions', headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print("Correo electrónico enviado correctamente")
    else:
        print(f"Error al enviar el correo electrónico: {response.text}")

def is_within_time_range(incident_time, working_hours=False, on_call_non_working_hours=False):
    incident_datetime = None
    try:
        incident_datetime = datetime.strptime(incident_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        incident_datetime = datetime.strptime(incident_time, "%Y-%m-%dT%H:%M:%SZ")

    madrid_tz = pytz.timezone("Europe/Madrid")
    utc_tz = pytz.timezone("UTC")

    incident_datetime = utc_tz.localize(incident_datetime)
    incident_datetime = incident_datetime.astimezone(madrid_tz)

    incident_weekday = incident_datetime.weekday()
    incident_time = incident_datetime.time()

    if working_hours:
        if 0 <= incident_weekday <= 4 and time(8, 0) <= incident_time <= time(17, 0):
            return True
    elif on_call_non_working_hours:
        if 0 <= incident_weekday <= 4 and (time(17, 0) <= incident_time or incident_time <= time(8, 0)):
            return True
        elif incident_weekday >= 5:
            return True
    else:
        return True

def get_incidents(api_key, start_date, end_date, working_hours=False, on_call_non_working_hours=False, all_hours=False):
    start = f"{start_date}T00:00:00-00:00"
    end = f"{end_date}T23:59:59-00:00"

    headers = {
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Authorization": f"Token token={api_key}"
    }

    all_incidents = []
    offset = 0
    limit = 25

    while True:
        url = f"https://api.pagerduty.com/incidents?&since={start}&until={end}&offset={offset}&limit={limit}"
        response = requests.get(url, headers=headers)

        if response.ok:
            incidents = response.json()["incidents"]
            if not incidents:
                break

            all_incidents.extend(incidents)
            offset += limit
        else:
            response.raise_for_status()
            break

    filtered_incidents = [incident for incident in all_incidents if is_within_time_range(incident["created_at"], working_hours, on_call_non_working_hours)]
    return filtered_incidents

def export_to_csv(incidents, filename):

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Title", "Date", "Hour", "Status"])

        madrid_tz = pytz.timezone("Europe/Madrid")
        utc_tz = pytz.timezone("UTC")
        
        for incident in incidents:
            incident_title = incident["title"]
            incident_time = incident["created_at"].split("T")
            incident_date = incident_time[0]
            incident_hour = incident_time[1].split("-")[0].replace("Z", "")
            incident_status = incident["status"]

            incident_datetime = datetime.strptime(f"{incident_date} {incident_hour}", "%Y-%m-%d %H:%M:%S")
            incident_datetime = utc_tz.localize(incident_datetime)
            incident_datetime = incident_datetime.astimezone(madrid_tz)

            incident_date = incident_datetime.strftime("%Y-%m-%d")
            incident_hour = incident_datetime.strftime("%H:%M:%S")

            writer.writerow([incident_title, incident_date, incident_hour, incident_status])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", required=True, type=str, help="Start date in the format YYYY-MM-DD")
    parser.add_argument("--end_date", required=True, type=str, help="End date in the format YYYY-MM-DD")
    parser.add_argument("--on_call_non_working_hours", action="store_true", help="Obtain incidents from Monday to Friday from 5 p.m. to 8 a.m. and all day on weekends")
    parser.add_argument("--working_hours", action="store_true", help="Obtain incidents from Monday to Friday from 8h to 17h")
    parser.add_argument("--all_hours", action="store_true", help="Obtain all incidents")
    parser.add_argument("--filename", default=None, help="The name of the output CSV file")
    parser.add_argument("--email", required=True, type=str, help="Recipient email address")
    args = parser.parse_args()

    if args.filename is None:
        args.filename = f"incidents_{args.end_date}.csv"

    pagerduty_api_key = os.getenv('PAGERDUTY_TOKEN')
    incidents = get_incidents(pagerduty_api_key, args.start_date, args.end_date, args.working_hours, args.on_call_non_working_hours)
    export_to_csv(incidents, args.filename)

    send_email_sparkpost(args.filename, args.email, args.working_hours, args.on_call_non_working_hours, args.all_hours)

if __name__ == "__main__":
    main()
