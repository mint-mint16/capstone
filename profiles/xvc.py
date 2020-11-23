from __future__ import print_function

from django.shortcuts import render
from googleapiclient import discovery
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from httplib2 import Http
from oauth2client import file, client, tools

# Login to Google Drive and create drive object

# Importing os and glob to find all PDFs inside subfolder
import os, random


SCOPES = 'https://www.googleapis.com/auth/drive'
store = file.Storage('token2.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('../client_secrets.json', SCOPES)
    creds = tools.run_flow(flow, store)
DRIVE = discovery.build('drive', 'v3', http=creds.authorize(Http()))
DRIVES = discovery.build('drive', 'v2', http=creds.authorize(Http()))

size = 100
list_file = DRIVE.files().list(
    pageSize=size, fields="nextPageToken, files(id, name, mimeType)").execute()

print(list_file)
