"""
Reads students' names from an attendance sheet (Google Sheets) and writes their
grades to the class register. Can also write the acronym of the TA to the class
register. This option is only to be used once per subgroup. The ID of the class
register is specified in the credentials.json file.

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


def _get_args():
    """
    Parses and returns the command-line arguments.
    """
    parser = argparse.ArgumentParser("Reads students' names from an " + \
        "attendance sheet (Google Sheets) and writes their grades to the " +\
        "class register")
    parser.add_argument('-l', '--lab', dest='lab_no', type=int, required=True,
        help='Lab number')
    parser.add_argument('-t', '--ta', dest='ta', type=str, required=False,
        help="TA acronym")
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


def _get_attendees(service, attendance_id, lab_no):
    """
    Returns a list of tuples made up of lab attendees' Moodle IDs and their
    grades.
    """
    attendance_range = f'Prezenta lab {lab_no}!D2:E'
    students_lab = service.spreadsheets().values().get(
        spreadsheetId=attendance_id, range=attendance_range).execute()['values']

    return list(filter(lambda s: s[0] != '#N/A', students_lab))


def _get_register_range(service, register, sheet, lab_no):
    """
    Returns the following dictionary:
        - keys = students' Moodle IDs
        - values = tuple(index in the grades list, grade)
    """
    ranges = [
        f'{sheet}!{register["moodle_ids"]}',
        f'{sheet}!{register["lab_cols"][lab_no]}'
    ]
    grades = service.spreadsheets().values().batchGet(
        spreadsheetId=register['ID'], ranges=ranges).execute()

    stud_names = grades['valueRanges'][0]['values']
    stud_grades = grades['valueRanges'][1].get('values', [])
    stud_grades += [[]] * (len(stud_names) - len(stud_grades))
    both = zip(stud_names, stud_grades)

    return { k[0]: (v, i) for i, (k, v) in enumerate(both) }


def _make_value_range(sheet, col, idx, value):
    """
    Returns one ValueRange object that writes the given value at lab_col[idx].
    """
    # lab_col = register['lab_cols'][lab_no]
    pos = col.find(':')
    # TODO: [Bug] This assumes actual grades start from a row < 10.
    # This holds true for most registers, though.
    col_start = int(col[pos - 1 : pos])
    col = col[pos + 1 :]

    return {
        'range': f'{sheet}!{col}{col_start + idx}',
        'majorDimension': 'ROWS',
        'values': [[value]]
    }


def main(course, attendance_id, lab_no, ta):
    """
    Retrieves the attendance list and grades all studens who haven't been
    already graded. Also assigns the TA to the subgroup if the ta parameter is
    specified.
    """
    service = _login()
    register = load(open('course_registers.json'))[course]

    # Read students who participated in the lab.
    students_lab = _get_attendees(service, attendance_id, lab_no)

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
                body['data'].append(_make_value_range(sheet,
                    register['lab_cols'][lab_no], reg_range[stud][1], grade))
                if ta:
                    body['data'].append(_make_value_range(sheet,
                        register['ta_col'], reg_range[stud][1], ta))
            elif stud in reg_range:
                print(f'Error: student "{stud}" has already been graded for lab {lab_no}.')

    # Send the update request.
    request = service.spreadsheets().values().batchUpdate(
        spreadsheetId=register['ID'], body=body)
    response = request.execute()

    print(f'Class register: https://docs.google.com/spreadsheets/d/{register["ID"]}')

    # Print the results.
    updated_cells = response.get('totalUpdatedCells', 0)
    if (not ta and updated_cells == len(students_lab)) \
            or (ta and updated_cells == 2 * len(students_lab)):
        print(f'All students are graded!')
    elif updated_cells != 0:
            print(f'Modified {updated_cells} cells:')
            for resp in response['responses']:
                print(resp['updatedRange'])
    else:
        print('Fucked up completely: cells modified!')


if __name__ == '__main__':
    args = _get_args()
    main(args.course, args.attendance, args.lab_no, args.ta)
