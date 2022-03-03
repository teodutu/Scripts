"""
Reads students' names from an attendance sheet (Google Sheets) and writes their
grades to the class register. The ID of this register is specified in the
credentials.json file

Requires the following pip3 modules:
pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import argparse
from os.path import exists
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from json import load

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Hard-coded to fit my own attendance list format. Deal with it!
ATTENDANCE_RANGE = 'Lista de prezenta!D2:E'


def _get_args():
    """
    Parses and returns the command-line arguments.
    """
    parser = argparse.ArgumentParser("Reads students' names from an " + \
        "attendance sheet (Google Sheets) and writes their grades to the " +\
        "class register")
    parser.add_argument('-l', '--lab', dest='lab_no', type=int, required=True,
        help='Lab number')
    parser.add_argument('-a', '--attendance', dest='attendance', type=str,
        required=True, help="The ID of the attendance list")
    parser.add_argument('-c', '--course', dest='course', type=str, required=True,
        help="The acronym of the course in whose register to write the grades.")

    return parser.parse_args()


def _login():
    """
    Performs TA login using the tokens.json file, if present.
    Otherwise, it uses credentials.json.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('sheets', 'v4', credentials=creds)


def _get_attendees(service, attendance_id):
    """
    Returns a list of tuples made up of lab attendees' Moodle IDs and their
    grades.
    """
    students_lab = service.spreadsheets().values().get(
        spreadsheetId=attendance_id, range=ATTENDANCE_RANGE).execute()['values']
    return list(filter(lambda s: s[0] != '#N/A', students_lab))


def _get_register_range(service, register, sheet, lab_no):
    """
    Returns the following dictionary:
        - keys = students' Moodle IDs
        - values = tuple(index in the grades list, grade)
    """
    ranges = [
        f'{sheet}!{register["moodle_ids"]}',
        f'{sheet}!{register["labs"][lab_no]}'
    ]
    grades = service.spreadsheets().values().batchGet(
        spreadsheetId=register['ID'], ranges=ranges).execute()

    both = zip(grades['valueRanges'][0]['values'],
            grades['valueRanges'][1]
            .get('values', [[]] * len(grades['valueRanges'][0]['values'])))

    return { k[0]: (v, i) for i, (k, v) in enumerate(both) }


def _make_value_range(register, sheet, lab_no, idx, grade):
    """
    Returns one ValueRange object that corresponds to the grade of one student.
    """
    lab_col = register['labs'][lab_no]
    pos = lab_col.find(':')

    # TODO: [Bug] This assumes actual grades start from a row < 10.
    # This holds true for most registers, though.
    lab_col_start = int(lab_col[pos-1:pos])
    lab_col = lab_col[pos+1:]

    return {
        'range': f'{sheet}!{lab_col}{lab_col_start + idx}',
        'majorDimension': 'ROWS',
        'values': [[grade]]
    }


def main(course, attendance_id, lab_no):
    """
    Retrieves the attendance list and grades all studens who haven't been
    already graded.
    """
    service = _login()
    register = load(open('course_registers.json'))[course]

    # Read students who participated in the lab.
    students_lab = _get_attendees(service, attendance_id)

    # The skeleton of the request body.
    body = {
        'valueInputOption': 'USER_ENTERED',
        'data': [ ],
        'includeValuesInResponse': False
    }

    # Look for the students in all sheets.
    for sheet in register['sheets']:
        reg_range = _get_register_range(service, register, sheet, lab_no)

        for stud, grade in students_lab:
            if stud in reg_range and len(reg_range[stud][0]) == 0:
                body['data'].append(_make_value_range(register, sheet, lab_no,
                    reg_range[stud][1], grade))
            elif stud in reg_range:
                print(f'Error: student "{stud}" has already been graded for lab {lab_no}.')

    # Send the update request.
    request = service.spreadsheets().values().batchUpdate(
        spreadsheetId=register['ID'], body=body)
    response = request.execute()

    print(f'Class register: https://docs.google.com/spreadsheets/d/{register["ID"]}')

    # Print the results.
    updated_cells = response.get('totalUpdatedCells', 0)
    if updated_cells == len(students_lab):
        print(f'All students are graded!')
    elif updated_cells != 0:
            print(f'Graded {updated_cells} students at cells:')
            for resp in response['responses']:
                print(resp['updatedRange'])
    else:
        print('Fucked up completely: no students graded!')


if __name__ == '__main__':
    args = _get_args()
    main(args.course, args.attendance, args.lab_no)