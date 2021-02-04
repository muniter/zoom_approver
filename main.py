#!/usr/bin/python3
# Application that automatically approves ZoomUS client registrations.


import json
import logging
import requests
import util
import gspread
from gspread.exceptions import CellNotFound
from flask import Flask, jsonify, request, abort

# Logging configuration
logging.basicConfig(
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ],
    format='%(asctime)s - %(message)s',
    level=logging.INFO
)

# Getting the config variables
with open('./config/config.json') as config_file:
    config_data = json.load(config_file)

# Zoom Data
API_BASE_URL = 'https://api.zoom.us/v2'
API_KEY = config_data['api_key']
API_SECRET = config_data['api_secret']
EVENTS_URL = config_data['events_url']
MEETINGS_INFORMATION = config_data['meetings_information']
MEETINGS_IDS = [int(m_id) for m_id in MEETINGS_INFORMATION.keys()]

# Google Data
GOOGLE_DATA = config_data["google_data"]
SHEET_KEY = GOOGLE_DATA["sheet_key"]
WORKSHEET_NAME = GOOGLE_DATA["worksheet_name"]
# LOG_WORKSHEET_NAME = GOOGLE_DATA["log_worksheet_name"]
COLUMNS = GOOGLE_DATA["columns"]

# Google Sheet Setup
GC = gspread.service_account('./config/service-account.json')
# Sheet and Worksheet object
SH = GC.open_by_key(SHEET_KEY)
WS = SH.worksheet(WORKSHEET_NAME)
# WS_LOG = SH.worksheet(LOG_WORKSHEET_NAME)

# Replace column letter from config with tupple (number, letter)
for key, val in COLUMNS.items():
    # Find the column name (first row)
    val_cell = WS.find(val, in_row=1)
    COLUMNS[key] = (val, val_cell.col)

app = Flask(__name__)


@app.route(EVENTS_URL, methods=['POST'])
def registration_events():
    """Receives all the event related to registrations, and routes
    it to the proper method

    :arg1: TODO
    :returns: TODO

    """
    if request.is_json:
        logging.info(
            f'Received request at {request.path} with data {request.json}'
        )
    else:
        logging.info(f'Received request at {request.path} with no JSON data')

    data = request.json
    if 'event' not in data:
        logging.info('Recieved request without event type, aborting')

    if data['event'] == "meeting.registration_created":
        logging.info(
            f"Event type is {data['event']}, calling new_registartion method"
        )
        new_registration(data)

    resp = jsonify(success=True)
    return resp


def new_registration(data):
    """Method triggered when there's a new registration
    It will accept the registration or leave it pending,
    and will leave logs behind.

    :request: The http request made by zoom
    :request: The json data incoming in the request
    :returns: Nothing
    """
    meeting_id = data.get('payload').get('object').get('id')
    registrant = data.get('payload').get('object').get('registrant')

    # Filter for correct meeting id
    if meeting_id and meeting_id not in MEETINGS_IDS:
        logging.info(
            f"Meeting ID didn't match, received "
            f"{meeting_id}, looking for one of {MEETINGS_IDS}"
        )
    else:
        logging.info(
            f"Meeting ID matched, received {meeting_id}"
        )
        # Get all the answers to the custom questions and find which are keys
        answers = []
        for question in registrant["custom_questions"]:
            ans = question["value"]
            # Remove trailing and leading whitespace and make lower case
            ans = ans.lstrip()
            ans = ans.rstrip()
            ans = ans.lower()
            if len(ans) == 10:
                answers.append(ans)

        if any(answers):
            if len(answers) == 1:
                key = answers[0]
                logging.info(
                    f'One of the answer matches a valid key, proceeding '
                    f'with approval procedure, key: {key}'
                )
                registration_approver(registrant, data, meeting_id, key)
            elif len(answers) > 1:
                logging.info(
                    'More than one of the answers provided is a valid key '
                    f'answers: {answers}'
                )
        else:
            logging.info(
                'None of the answers provided is a valid key '
                f'answers: {answers}',
            )

        resp = jsonify(success=True)
        return resp


def registration_approver(registrant, data, meeting_id, key):
    """Approves the registration if criteria is matches

    Criteria is:
    1. key must be valid when checking on the database
    2. The participant must not be already registered, meaning
    the key hasn't been used before for registering.

    :registrant: Received data on the webhook about the registrant
    :meeting_id: Meeting ID the registration is against
    :data: All the data received on the webhook
    :returns: True if registration is approved, False if it's denied.
    """
    # __import__('pdb').set_trace()
    # First let's find the key in the column
    try:
        find_key = WS.find(key, in_column=COLUMNS["registrant_key"][1])
        registrant_row = find_key.row
        ws_registrant_data = WS.row_values(registrant_row)
    except CellNotFound as e:
        logging.info(
            f'Did not found key {key} in the database ABORTING',
        )
        return

    # Here the key has been found
    # Let's check the owner hasn't registered

    # Information
    name = ws_registrant_data[0]
    registrant_status = ws_registrant_data[COLUMNS["registrant_status"][1] - 1]
    registrant_data = ws_registrant_data[COLUMNS["registrant_data"][1] - 1]
    registrant_id = ws_registrant_data[COLUMNS["registrant_id"][1] - 1]
    registrant_time_id = ws_registrant_data[COLUMNS["time_id"][1] - 1]

    if registrant_status == 'REGISTERED':
        logging.info(
            f'The registrant "{name}" is already registered '
            f'current data is {registrant_data} ABORTING'
        )
    elif registrant_data == 'PENDING':
        logging.info(
            f'The registrant "{name}" has a pending registration '
            f'current data is {registrant_data} ABORTING'
        )
    elif registrant_data == '':
        logging.info(
            f'The registrant "{name}" has not registered will '
            'continue proccess.'
        )

        # Check if registerint to the correct meeting
        print("Registrant time ID in sheets", registrant_time_id)
        correct_time_id = MEETINGS_INFORMATION[str(meeting_id)]["time_id"]
        if int(registrant_time_id) == int(correct_time_id):
            logging.info(
                f'The registrant "{name}" is in the correct meeting '
                f'will now apporve the registration.'
            )

            approve = approve_registrant_zoom(
                registrant["id"],
                registrant["email"],
                meeting_id,
                registrant
            )

            if approve:
                STATUS = 'REGISTERED'
                # Update the values in the sheet/database
                WS.update_cell(
                    registrant_row,
                    COLUMNS["registrant_id"][1],
                    registrant["id"]
                )
                WS.update_cell(
                    registrant_row,
                    COLUMNS["registrant_data"][1],
                    json.dumps(obj=registrant, ensure_ascii=False)
                )
                WS.update_cell(
                    registrant_row,
                    COLUMNS["registrant_status"][1],
                    STATUS
                )
            else:
                STATUS = 'PENDING'
                WS.update_cell(
                    registrant_row,
                    COLUMNS["registrant_id"][1],
                    registrant["id"]
                )
                WS.update_cell(
                    registrant_row,
                    COLUMNS["registrant_data"][1],
                    json.dumps(obj=registrant, ensure_ascii=False)
                )
                WS.update_cell(
                    registrant_row,
                    COLUMNS["registrant_status"][1],
                    STATUS
                )

            logging.info(
                f'Succesfully updated data row: {registrant_row} '
                f'status is now {STATUS}'
            )

        else:
            logging.info(
                f'The registrant "{name}" is NOT in the correct meeting '
                f'will now ABORT'
            )

    return


def approve_registrant_zoom(id, email, meeting_id, registrant):
    """Approve the registrant against zoom api.

    :id: The registrant id (recived in the webhook)
    :mail: The registrant email (recived in the webhook)
    :returns: True if succesful False if not
    """
    token = util.generate_jwt(API_KEY, API_SECRET)

    headers = {
        'authorization': f"Bearer {token}",
        'content-type': "application/json",
    }

    data = {
        "action": "approve",
        "registrants": [
            {
                "id": id,
                "email": email
            }
        ]
    }

    url = API_BASE_URL + '/meetings/' + str(meeting_id) + '/registrants/status'

    response = requests.put(url=url, json=data, headers=headers)
    logging.info(
        f'Response from Zoom API request Status Code: {response.status_code} '
        f'Response content: {response.text}'
    )
    if response.status_code == 204:
        logging.info(
            f'Succesfully approved registrant with id: {id} '
            f'name: {registrant["first_name"] + " " + registrant["last_name"]} '
            f'email: {email}'
        )
        return True

    return False


if __name__ == "__main__":
    # Run the flask app
    app.run(host='0.0.0.0', port=5000)
