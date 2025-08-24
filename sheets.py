from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = 'credentials_sheets.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SPREADSHEET_ID = '1XPTtr9T2g5MxhYqu61A5lOi9JdWjYW4-ItvJIhfLTYI'
RANGE_NAME = 'Sheet1!A1'

def test_api():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=RANGE_NAME).execute()
        print("API is enabled and accessible! Data:", result.get('values'))
    except Exception as e:
        print("API call failed. Maybe the API is not enabled or credentials are wrong.")
        print(e)

if __name__ == '__main__':
    test_api()


import pygsheets

# Authorize using the JSON file
gc = pygsheets.authorize(service_file='credentials_sheets.json')

# Open a Google Sheet by title
sh = gc.open_by_key('1XPTtr9T2g5MxhYqu61A5lOi9JdWjYW4-ItvJIhfLTYI')

# Select the first sheet
wks = sh[0]

# Update a cell
wks.update_value('A1', 'Hello from pygsheets!')

# Read the value back from cell A1
value = wks.get_value('A1')

# Print the value

print('Value in A1:', value)
