#!/usr/bin/python3
from settings import *
import email
import re
import json
from urllib import parse

def clean_html(html):
    # First we remove inline JavaScript/CSS:
    cleaned = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", html.strip())
    # Then we remove html comments. This has to be done before removing regular
    # tags since comments can contain '>' characters.
    cleaned = re.sub(r"(?s)<!--(.*?)-->[\n]?", "", cleaned)
    # Next we can remove the remaining tags:
    cleaned = re.sub(r"(?s)<.*?>", " ", cleaned)
    # Finally, we deal with whitespace
    cleaned = re.sub(r"&nbsp;", " ", cleaned)
    cleaned = re.sub(r"  ", " ", cleaned)
    cleaned = re.sub(r"  ", " ", cleaned)
    return cleaned.strip()

while True:
    imap = IMAP4_SSL(host=url, ssl_context=context)
    print("Logging into mailbox...")
    retcode, d = imap.login(user, password)
    assert retcode == 'OK', 'login failed'
    print(f"Select folder: {folder}.")
    imap.select(folder)
    while True:
        try:
            retcode, messages = imap.search(None, '(UNSEEN)')
            assert retcode == 'OK', 'search messages failed'
            uids = messages[0].split()
            print(f"Found new mail(s) in folder: {uids}")
            for i in uids:
                typ, data = imap.fetch(i, '(RFC822)')
                encodes = ['utf-8', 'GB2312', 'US-ASCII']
                for encode in encodes:
                    try:
                        message = email.message_from_string(data[0][1].decode(encode))
                    except:
                        print(f"Cannot decode with {encode}")
                    else:
                        messageEncoding = encode
                        break
                if not messageEncoding:
                    raise Exception('No encoding can decode the message')
                subject = message['Subject']
                date = email.utils.parsedate_to_datetime(message['Date']) if message['Date'] else None
                sender = email.utils.parseaddr(message['From'])[1]
                receivers = email.utils.parseaddr(message['To'])[1]
                header, encoding = email.header.decode_header(subject)[0]
                if encoding:
                    subject = header.decode(encoding)
                if message['CC']:
                    carboncopy = [email.utils.parseaddr(i)[1] for i in message['CC'].split(',')]
                else:
                    carboncopy = None

                print("A mail received:")
                print(f"Subject:   {subject}")
                print(f"Date:      {date}")
                print(f"Sender:    {sender}")
                print(f"Receivers: {receivers}")
                print(f"CC:        {carboncopy}")    

                for part in message.walk():
                    if part.is_multipart():
                        filename = part.get_filename()  # attachment file name
                        if filename:
                            filename, encoding = email.header.decode_header(filename)[0]
                            if encoding:
                                filename = filename.decode(encoding)
                            # sample code if downloading attachment
                            # data = part.get_payload(decode=True)
                            # f = open(filename, 'wb')
                            # f.write(data)
                            # f.close()
                    else:
                        if part.get_content_subtype() == 'plain':
                            content = part.get_payload(decode=True).decode(part.get_content_charset())
                        elif part.get_content_subtype() == 'html':
                            content = clean_html(part.get_payload(decode=True).decode(part.get_content_charset()))
                        else:
                            content = "unknown content type"

                # push message to push provider
                title = "{0}{1}".format(msgprefix,subject)
                if (pushprovider.lower() == 'gotify'):
                    headers = {'X-Gotify-Key': gotifytoken}
                    resp = requests.post(
                        gotifyurl,
                        headers=headers,
                        data={
                            'title': title,
                            'message': {content},
                            'priority': 5})
                    if (resp.status_code != 200):
                        print(f"Gotify message was not successfully sent: {resp}")
                    else:
                        print("Gotify message is sent for the mail successfully.")
                elif (pushprovider.lower() == 'serverchan'):
                    resp = requests.post(serverchanurl + '?title=' + parse.quote(title) + '&desp=' + parse.quote(content))
                    if (resp.status_code != 200):
                        print(f"ServerChan message was not successfully sent: {resp}")
                    else:
                        print("ServerChan message is sent for the mail successfully.")
                elif (pushprovider.lower() == 'bark'):
                    headers = {'Content-Type': 'application/json; charset=utf-8'}
                    data = {
                        "title": title,
                        "body": content,
                        "device_key": barktoken
                    }
                    resp = requests.post(
                        barkurl,
                        headers=headers,
                        data=json.dumps(data))
                    if (resp.status_code != 200):
                        print(f"Bark message was not successfully sent: {resp}")
                    else:
                        print("Bark message is sent for the mail successfully.")
                else:
                    print("Unknown push service provider.")
                # mark mail as Read so it won't be pushed to Gotify again
                imap.store(i, '+FLAGS', '\Seen')
        except Exception as e:
            print(f"Got exception: {e}.")
            if infiniteloop:
                print("Wait and trying to re-establish connection...")
                time.sleep(60)
            break
        else:
            if (not infiniteloop): 
                break
            else:
                print("Sleep 60 seconds...")
                time.sleep(60)
    if (not infiniteloop): 
        break
print("Logging out mailbox...")
imap.close()
imap.logout()
