import email
import poplib
import sys
import os

import conf

def decode_header(header, msgno=''):
    b, enc = email.header.decode_header(header)[0]
    if enc is not None:
        try:
            return b.decode(enc)
        except:
            sys.stderr.write("[%s] cannot decode subject with encoding: %s\n" % (msgno, enc))
            return ""
    if isinstance(b, bytes):
        return b.decode()
    return b

def is_interested_in(msg, msgno=''):
    for i in msg.get_all('Subject'):
        subject = decode_header(i, msgno)
        if conf.keyword in subject:
            return True
    return False   
    
def save_to(uid, filename, payload):
    if not filename:
        filename = 'test.zip'
    path = '-'.join([uid, filename])
    with open(os.path.join(conf.save_dir, path), 'wb') as f:
        f.write(payload)

class Pop3:
    def __init__(self, config, uids):
        self.config = config
        self.uids = uids

    def __enter__(self):
        self.pop3 = self._connect(self.config)
        user, pass_ = self.config.user.split(':')
        self.pop3.user(user)
        self.pop3.pass_(pass_)
        self.pop3.set_debuglevel(self.config.debug_level)
        return self
    
    def __exit__(self, type_, value, traceback):
        self._disconnect()
        return False

    def _connect(self, config):
        if ':' in config.pop3:
            host, port = config.pop3.split(':')
        else:
            host = config.pop3
            if config.enable_ssl:
                port = poplib.POP3_SSL_PORT
            else:
                port = poplib.POP3_PORT

        if conf.enable_ssl:
            pop3 = poplib.POP3_SSL(host, port)
        else:
            pop3 = poplib.POP3(host, port)
        return pop3

    def _disconnect(self):
        self.pop3.quit()

    def fetch(self, msgno):
        resp, raw_msg, octs = self.pop3.retr(msgno)
        msg = email.message_from_bytes(b'\n'.join(raw_msg))
        return msg

    def top(self):
        resp, uids, octets = self.pop3.uidl()
        for uid in uids[::-1]:
            msgno, uid = uid.split()
            
            msgno = msgno.decode()
            uid = uid.decode()

            if uid in self.uids:
                continue
            resp, raw_msg, octs = self.pop3.top(msgno, 0)
            msg = email.message_from_bytes(b'\n'.join(raw_msg))
            yield msgno, uid, msg

def main():
    known_uids = []
    try:
        with open(conf.message_id) as f:
            known_uids = [l.strip() for l in f.readlines()]
    except:
        pass

    pop3 = Pop3(conf, known_uids)
    with pop3:
        with open(conf.message_id, 'a') as msgIdLog:
            for msgno, uid, msg in pop3.top():
                # record uid
                msgIdLog.write(uid+'\n') 

                if not is_interested_in(msg, msgno):
                    continue


                msg = pop3.fetch(msgno)
                for part in msg.walk():
                    filename = part.get_filename()
                    if filename is not None and 'crash-report' in filename:
                        save_to( uid,
                                 part.get_filename(),
                                 part.get_payload(decode=1))
                        print(uid)

if __name__ == '__main__':
    main()

