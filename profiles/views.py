import hashlib
import random
import os
# from builtins import list
# from pydoc import doc
from zipfile import ZipFile
import time
from django.contrib.auth import update_session_auth_hash
from cryptography.fernet import Fernet
from django.db.models import Q, Count
from pyotp import HOTP, random_base32
from django.http import JsonResponse
from django.views.generic import FormView
from django.conf import settings
# from pyotp import HOTP
# from base64 import b32encode
from datetime import datetime
from random import choice
from string import digits
# from django import forms
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LogoutView
# from django.core.mail import send_mail
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login
from django.views.generic import TemplateView
from googleapiclient.http import MediaFileUpload
from django.core.mail import EmailMultiAlternatives
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from django.contrib.auth.models import User
from .forms import RegistrationForm, PermisssionForm
from django.contrib.auth.forms import PasswordChangeForm
from .models import Drive, File, ShareFile, OTP, downloadFile
from oauth2client import file, client, tools
from googleapiclient import discovery
from httplib2 import Http
from .download_share_procedure import *
from .SMSgateway import recevieSmsMessage, sendSmsMessage
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import FileResponse, Http404
from dateutil.parser import parse

gauth = GoogleAuth()
drive = GoogleDrive(gauth)
SCOPES = 'https://www.googleapis.com/auth/drive'
store = file.Storage('profiles/token2.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('client_secrets.json', SCOPES)
    creds = tools.run_flow(flow, store)
DRIVE = discovery.build('drive', 'v3', http=creds.authorize(Http()))
DRIVES = discovery.build('drive', 'v2', http=creds.authorize(Http()))


def login_request(request):
    if request.method == 'POST':
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"Welcome back, {username}")
                return redirect('/profile/viewfile/')
        else:
            messages.error(request,
                           mark_safe(
                               "Invalid username or password! Please check again or  <a href='/register'>click here</a> to register"))
            return redirect('/')
    form = AuthenticationForm()
    return render(request=request,
                  template_name="baseIndex.html",
                  context={"form": form})


def userProfile(request):
    phone_number = request.user.first_name
    new_phone = phone_number.replace(phone_number[0:3], '0')
    context = {'user': request.user, 'new_phone': new_phone}
    return render(request, 'userProfile.html', context)


# def update_phone_number(request):
#     try:
#         phone_get = request.POST['phone_update']
#         if phone_get is not digits:
#             messages.error(request, "Invalid input. Please check again")
#             return redirect('/profile/usr/')
#         elif phone_get is
#     except:
#         pass

def register(request):
    form = RegistrationForm()
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            new_user = authenticate(username=form.cleaned_data['username'],
                                    password=form.cleaned_data['password1'],
                                    )
            login(request, new_user)
            return HttpResponseRedirect("/createfolder")
    return render(request, 'register.html', {'form': form})


def createFolder(request):
    if request.method == 'POST':
        current_user = request.user
        username = current_user.username
        folder = drive.CreateFile({'title': username, 'mimeType': 'application/vnd.google-apps.folder'})
        folder.Upload()
        messages.info(request, f"Welcome {username}. Please read our document carefully before enjoy!")
        Drive.objects.update_or_create(driveID=folder['id'], driveName=folder['title'], driveOwner_id=current_user.id)
        return HttpResponseRedirect("/profile")
    return render(request, 'createfolder.html')


def viewfilebyusername(request):
    current_user = request.user
    if current_user.is_superuser == True:
        size = 100
        list_file = DRIVE.files().list(
            pageSize=size, fields="nextPageToken, files(id, name, mimeType)").execute()
    else:
        a = Drive.objects.get(driveOwner_id=current_user.id)
        folderid = a.driveID
        query = f"parents = '{folderid}'"
        list_file = DRIVE.files().list(q=query).execute()

    return render(request, 'profile.html', list_file)


def viewDetail(request):
    if request.method == "POST":
        current_id = request.POST['filedetail']
        filede = DRIVE.files().get(fileId=current_id, fields='size, createdTime').execute()
        dt = filede['createdTime']
        mod = parse(dt)
        context = {'size': filede['size'], 'createdTime': mod}
    return render(request, 'filedetail.html', context)


def detail(request):
    if request.method == "POST":
        current_id = request.POST['filedetail']
        filede = DRIVE.files().get(fileId=current_id, fields='size, createdTime').execute()
        dt = filede['createdTime']
        mod = parse(dt)
        context = {'size': filede['size'], 'createdTime': mod}
    return render(request, 'detail.html', context)


def write_file(file_path, data):
    with open(file_path, "wb") as file:
        file.write(data)


def encrypt_file_stored_on_Cloud(filename):
    key = Fernet.generate_key()
    f = Fernet(key)
    plaintext_data = read_file(filename)
    # encrypt data
    encrypted_data = f.encrypt(plaintext_data)
    # write the encrypted file
    write_file(filename, encrypted_data)
    return key


def decrypt_file_stored_on_Cloud(file_id, filename):
    item = ShareFile.objects.get(shareFileID=file_id)
    key = File.objects.get(fileID=item.file_id_id).secretKey.encode('utf-8')
    f = Fernet(key)
    encrypted_data = read_file(filename)
    # decrypt data
    decrypted_data = f.decrypt(encrypted_data)
    # write the original file
    write_file(filename, decrypted_data)


def upinf(request):
    basedir = r"C:\\"
    if request.method == "POST":
        current_user = request.user
        a = Drive.objects.get(driveOwner_id=current_user.id)
        fol_id = a.driveID
        filename = request.POST["fileupload"]
        key = encrypt_file_stored_on_Cloud(filename)
        try:
            file_metadata = {'name': filename, 'parents': [fol_id]}
            media = MediaFileUpload(filename, mimetype='application/pdf', resumable=True)
            DRIVE.files().create(body=file_metadata,
                                 media_body=media,
                                 fields='id').execute()
            query = f"parents = '{fol_id}'"
            list_file = DRIVE.files().list(q=query).execute()
            for file in list_file.get('files', []):
                File.objects.update_or_create(driveID_id=fol_id, secretKey=key.decode("utf-8"), fileID=file['id'],
                                              fileName=filename)
        except Exception as e:
            print(e)
        messages.success(request, 'Upload File Success')
        return HttpResponseRedirect('/profile/viewfile/')
    return render(request, 'profile.html', {})


def create(request):
    form = PermisssionForm()
    if request.method == "POST":
        fileid = request.POST['fileid']
        a = File.objects.get(fileID=fileid)
        create = a.fileID
        item = DRIVE.files().get(fileId=create).execute()
        con = {'id': item['id'], 'name': item['name'], 'form': form}
    return render(request, 'create.html', con)


def back(request):
    return render(request, 'profile.html', {})


def createLink(request):
    if request.method == "POST":
        current_user = request.user
        try:
            filid = request.POST['filid']
            filname = request.POST['filname']
            email = request.POST['shareEmails']
            editable = request.POST['editable']
            printable = request.POST['printable']
            downloadable = request.POST['downloadable']
            expDate = request.POST['expDate']
            f = drive.CreateFile({'id': filid, 'title': filname})
            f.GetContentFile(filname, 'application/pdf')
            file_meta = {'name': filname, 'parents': ['1JuyWaMD46VcLXtGJyKMR8jQWHl1X_OSq']}
            media = MediaFileUpload(filname, mimetype='application/pdf', resumable=True)
            DRIVE.files().create(body=file_meta,
                                 media_body=media,
                                 fields='id').execute()
            query = f"parents = '{'1JuyWaMD46VcLXtGJyKMR8jQWHl1X_OSq'}'"
            filess = DRIVE.files().list(q=query).execute()
            for item in filess.get('files', []):
                linkshare = "localhost:8000/linkshare/" + item['id']
                ShareFile.objects.update_or_create(shareFileID=item['id'], file_id_id=filid, share_file_name=filname,
                                                   shareEmails=email, owner_name=request.user.username,
                                                   owner_id=current_user.id, link=linkshare, editable=editable,
                                                   printable=printable,
                                                   downloadable=downloadable, expDate=expDate)
            # return HttpResponseRedirect("/linkshare")
        except Exception as e:
            print(e)
    return render(request, 'back&sendMail.html', {})


def sendMail(request):
    if request.method == "POST":
        a = ShareFile.objects.latest('date_create')
        print(a.shareEmails)
        subject, sender, to = 'LinkViewFile', settings.EMAIL_HOST_USER, a.shareEmails
        text_content = 'Welcome to join with Cloud9. Please click the link below to join.'
        html_content = 'Welcome to join with Cloud9. Please click the link below to join.' \
                       '<a href="http://localhost:8000/check/' + a.shareFileID + '"> LINK </a>'
        msg = EmailMultiAlternatives(subject, text_content, sender, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    return HttpResponseRedirect('/profile/viewfile/')


def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            redirect('usrprofile')
        else:
            messages.error(request, 'Something wrong.Please check again')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_pwd.html', {
        'form': form
    })


def linkshare(request, file_id):
    a = ShareFile.objects.latest('date_create')
    a.shareFileID = file_id
    con = {'id': a.shareFileID, 'date_create': a.date_create}
    return render(request, 'link.html', con)


def viewsharefile(request):
    if request.method == "POST":
        if request.method == "POST":
            share = request.POST['shareid']
            flag = ShareFile.objects.get(shareFileID=share)
            a = ShareFile.objects.latest('date_create')
            a.shareFileID = share
            itemlist = DRIVE.files().get(fileId=a.shareFileID).execute()
            context = {'id': itemlist['id'], 'name': itemlist['name'], 'flag': flag}
    return render(request, 'share/profileSharing.html', context)


def view_revoke(request):
    file_id = request.POST['file_id']
    fname = request.POST['name']
    user_id = request.user.id
    a = ShareFile.objects.filter(file_id_id=file_id, owner_id=user_id).values_list('shareFileID', flat=True)
    list_shareFileID = list(a)
    b = downloadFile.objects.filter(sharefile_id__in=[item for item in list_shareFileID]).values_list('licenseID',
                                                                                                      flat=True)
    list_licensed = list(b)
    for item in list_licensed:
        c = downloadFile.objects.filter(licenseID=item).values_list('downloader', flat=True)
        list_name = list(c)
    list_shareFileID.clear()
    return render(request, 'view_revoke.html', {'data': list_licensed, 'name': fname, 'downloader': list_name})


def revokeFile(request):
    if request.method == "POST":
        current_id = request.POST['filedel']
        fileid = downloadFile.objects.get(licenseID=current_id)
        fileid.delete()
        messages.success(request, "Revoke Successfully")
    return render(request, 'view_revoke.html')


def login_check(request, file_id):
    if request.method == 'POST':
        x = request.path.lstrip('/check/')
        y = x.rstrip('/')
        file_id = y
        a = ShareFile.objects.get(shareFileID=file_id)
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if username == a.shareEmails:
                login(request, user)
                return HttpResponseRedirect('/linkshare/' + a.shareFileID)
            else:
                login(request, user)
                messages.error(request, 'Deny permission to access file, we will redirect to your dashboard')
                return redirect('/profile/viewfile/')
    form = AuthenticationForm()
    return render(request=request,
                  template_name="logincheck.html",
                  context={"form": form})

# profilesharing
def sendMailOTP(request):
    if request.method == "POST":
        a = ShareFile.objects.latest('date_create')
        OTP_value = OTP_generator(request)
        id = request.POST['fileid']
        subject, sender, to = 'OTP Code', settings.EMAIL_HOST_USER, request.user.username
        text_content = 'OTP Value: ' + OTP_value
        # OTP.objects.update_or_create(otp_id = OTP_value, owner_id = b.id, email=a.shareEmails, file_id_id=fileid)
        msg = EmailMultiAlternatives(subject, text_content, sender, [to])
        msg.send()
        # con = {'file_id_id': fileid}
    return render(request, 'verifyOTP.html',{'id': id})

# resendOTP
def sendmailOTP(request):
    if request.method == "POST":
        a = ShareFile.objects.latest('date_create')
        OTP_value = OTP_generator(request)
        subject, sender, to = 'OTP Code', settings.EMAIL_HOST_USER, request.user.username
        text_content = 'OTP Value: ' + OTP_value
        # OTP.objects.update_or_create(otp_id = OTP_value, owner_id = b.id, email=a.shareEmails, file_id_id=fileid)
        msg = EmailMultiAlternatives(subject, text_content, sender, [to])
        msg.send()
        # con = {'file_id_id': fileid}
    return render(request, 'verifyOTP.html',{})


def viewOnline(request):
    if request.method == "POST":
        otp_check = request.POST['otps']
        check = OTP_verification(request, otp_check)
        if check == 1:

            return render(request, 'renderToViewOnline.html',)
        elif check == 0:
            messages.error(request, "Your OTP is wrong")
            return render(request, 'verifyOTP.html', {})
        else:
            messages.error(request, "Your OTP is expire please click send OTP again to receive another")
            return render(request, 'verifyOTP.html', {})


def deleteFile(request):
    if request.method == "POST":
        current_id = request.POST['filedel']
        fileid = File.objects.get(fileID=current_id)
        filedel = fileid.fileID
        f = drive.CreateFile({'id': filedel})
        f.Delete()
        messages.success(request, "File Deleted")
        return HttpResponseRedirect('/profile/viewfile/')
    return render(request, 'profile.html', {})


def downloadfileInProfile(request):
    if request.method == "POST":
        # path = r"D:\\"
        current_user = request.POST['filedown']
        name = request.POST['name']
        # i = os.path.join(path, name)
        f = drive.CreateFile({'id': current_user, 'title': name})
        f.GetContentFile(name, 'application/pdf')

        messages.success(request, "Download Success")
        return HttpResponseRedirect('/profile/viewfile/')
    return render(request, 'profile.html', {})


def downloadfileInSharing(request):
    if request.method == "POST":
        # Download file ve de xu ly
        current_id = request.POST['filedown']
        name = request.POST['name']
        f = drive.CreateFile({'id': current_id, 'title': name})
        f.GetContentFile(name, 'application/pdf')
        decrypt_file_stored_on_Cloud(current_id, name)
        item = ShareFile.objects.latest('date_create')
        # Lay tu database
        # SharedFile table
        # Lay licensseID moi nhat tu database (row cuoi cung)
        licenseid = downloadFile.objects.latest('date_create')
        last_license_id = licenseid.licenseID
        # last_license_id = 'abcdea'
        editable, printable, expDate, owner = item.editable, item.printable, item.expDate, item.owner_name
        # Login table
        username, phone = request.user.username, request.user.first_name
        # DownloadedFile table
        downloader = request.user.username
        # Tao license_id()
        license_id = create_license_id(last_license_id)

        # decrypt_file_stored_on_Cloud() chua lam
        synchronous_key = key_synchronous_generator(license_id, editable, printable, username, phone, owner)

        # download function()
        # download file ve server va lay duong dan cua file
        file_path = name
        # file ma hoa thay the file cu
        synchronous_encryption(file_path, synchronous_key)

        # tao gia tri hash cua file vua ma hoa
        hash_encrypted_file = compute_hash_file(file_path)

        # tao file json chua thong tin file
        json_path = './' + hash_encrypted_file + '.json'
        dict = {
            'license_id': license_id,
            'downloader': downloader,
            'editable': editable,
            'printable': printable,
            'expDate': str(expDate),
            'owner': owner
        }
        generate_json_file(json_path, hash_encrypted_file, dict)

        try:
            # Nen 2 file vao file zip
            filename = name + '.zip'
            with ZipFile(filename, 'w') as zipObj2:
                zipObj2.write(name)
                zipObj2.write(json_path)
            # Upload file len Cloud
            file_meta = {'name': filename, 'parents': ['1O0QxtqjUV0EZu-SZOWOcdBfTogVUpgTT']}
            media = MediaFileUpload(filename, mimetype='application/unknown', resumable=True)
            DRIVE.files().create(body=file_meta,
                                 media_body=media,
                                 fields='id').execute()
            query = f"parents = '{'1O0QxtqjUV0EZu-SZOWOcdBfTogVUpgTT'}'"
            filess = DRIVE.files().list(q=query).execute()
            for item in filess.get('files', []):
                downloadFile.objects.update_or_create(licenseID=license_id, sharefile_id=current_id,
                                                      fileID_zip=item['id'],
                                                      downloader=request.user.username)
        except Exception as e:
            print(e)
        # Download File zip ve user machine
        path = r'D:\\'
        i = os.path.join(path, filename)
        abc = downloadFile.objects.latest('date_create')
        f = drive.CreateFile({'id': abc.fileID_zip, 'title': filename})
        f.GetContentFile(i, 'application/unknown')
        messages.success(request, "Download Success")
        context = {'id': current_id}
    return render(request, 'downloadSuccessInSharing.html', context)


def re(request):
    if request.method == "POST":
        share = request.POST['shareid']
        # date_last = request.POST['date_create']
        a = ShareFile.objects.latest('date_create')
        a.shareFileID = share
        itemlist = DRIVE.files().get(fileId=a.shareFileID).execute()
        context = {'id': itemlist['id'], 'name': itemlist['name']}
    return render(request, 'share/profileSharing.html', context)


# OTP code:
def random_digit():
    random_code = ''.join(choice(digits) for i in range(10))
    return int(random_code)


def read_file(path):
    with open(path, 'rb') as f:
        data = f.read()
    return data


def read_json_file(path):
    with open(path) as f:
        data = load(f)
    return data


def write_json_file(path, data):
    with open(path, 'w') as f:
        dump(data, f, indent=4)


def generate_json_file(path, object, dict):
    data = {
        object: []
    }
    data[object].append(dict)
    write_json_file(path, data)


def append_json_file(path, object, dict, session_id):
    data = read_json_file(path)
    list_dict = data[object]
    for i in reversed(range(len(list_dict))):
        temp = list_dict[i]
        check = 0
        if session_id in temp:
            check = 1
            temp[session_id] = dict[session_id]
            temp['base32secret'] = dict['base32secret']
            temp['time_create'] = dict['time_create']
            break
    if check == 0:
        list_dict.append(dict)
    write_json_file(path, data)


def file_is_not_existed(file_path):
    if not path.isfile(file_path) or read_file(file_path) == b'':
        return True
    else:
        return False


def OTP_generator(request):
    # Lay sessionID cua user
    # a = ShareFile.objects.latest('date_create')
    a = request.session
    session_id = a.session_key
    base32secret = random_base32()
    hotp = HOTP(base32secret)
    counter = random_digit()
    OTP_value = hotp.at(counter)
    time_create = datetime.now().strftime('%Y%m%d%H%M%S%f')
    # Tao data cho file json
    dict = {
        session_id: counter,
        'base32secret': base32secret,
        'time_create': time_create
    }
    # Neu file ton tai va khac rong
    if file_is_not_existed('./OTP.json'):
        generate_json_file('./OTP.json', 'OTP', dict)
    else:
        append_json_file('./OTP.json', 'OTP', dict, session_id)

    return OTP_value


def OTP_verification(request, OTP_value):
    # Lay sessionID cua user
    a = request.session
    session_id = a.session_key
    data = None
    counter, OTP_check, time_create = None, None, None
    # Neu file ton tai va khac rong
    if file_is_not_existed('./OTP.json'):
        # print('OTP expires!!!')
        return -1
    else:
        data = read_json_file('./OTP.json')

    for i in reversed(range(len(data["OTP"]))):
        dict = data["OTP"][i]
        if session_id in dict:
            counter = dict[session_id]
            base32secret = dict['base32secret']
            time_create = dict['time_create']
            break

    time_verify = datetime.now().strftime('%Y%m%d%H%M%S%f')
    # 2020 10 28 02 30 08 743182
    # 2020 10 28 02 35 08 743183
    if time_create is not None and int(time_verify) - int(time_create) <= 500000000:
        hotp = HOTP(base32secret)
        if hotp.verify(OTP_value, counter):

            return 1
        else:
            return 0
    else:
        return -1


def sendSMS():
    while True:
        try:
            time.sleep(5)
            sender_phone, messages = recevieSmsMessage()
            temp = messages.split()
            if temp[0] == 'v' or temp[0] == 'V':
                license_id_SMS = temp[1]
                # license_id_SMS = 'abcdeb'
                random_code_SMS = temp[2]
                try:
                    check = downloadFile.objects.get(licenseID=license_id_SMS)
                    downloader = check.downloader
                    username = User.objects.get(username=downloader).username
                    phone = User.objects.get(username=downloader).first_name
                    sharefile_id = check.sharefile_id
                    expDate = ShareFile.objects.get(shareFileID=sharefile_id).expDate
                    time1_string = datetime.now().strftime('%Y%m%d%H%M%S%f')
                    x = expDate.strftime('%Y%m%d%H%M%S%f')
                    # print(time1_string)
                    # print(x)
                    if int(x) - int(time1_string) > 0:
                        if phone == sender_phone:
                            otp_value = OTP_synchronous_generator(license_id_SMS, downloader, username, phone,
                                                                  expDate, random_code_SMS)
                            message = 'OTP value: ' + otp_value
                            sendSmsMessage(sender_phone, message)
                            # temp.clear()
                        else:
                            sendSmsMessage(sender_phone, "You are not have permission to view this file")
                    else:
                        sendSmsMessage(sender_phone, "File is expired")
                except:
                    sendSmsMessage(sender_phone, "Your licensedID is wrong or revoked! Try again!")
            else:
                print(temp[0], temp[1], temp[2])
                sendSmsMessage(sender_phone, "SMS syntax error")

            temp.clear()
        except IndexError:
            continue


def statistic(request):
    return render(request, 'index.html')


class EditProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'


class SiteLogoutView(LogoutView):
    template_name = 'logout.html'
