import email
import poplib
import sys

import conf


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

    def fetch(self):
        resp, uids, octets = self.pop3.uidl()
        for uid in uids:
            msgno, uid = uid.split()
            if uid in self.uids:
                continue
            print('msgno = ', msgno)
            print('uid = ', uid)
            resp, raw_msg, octs = self.pop3.retr(msgno.decode())
            msg = email.message_from_bytes(b'\n'.join(raw_msg))
            yield uid, msg


def main():
    known_uids = None
    with open(sys.argv[1]) as f:
        known_uids = f.readlines()

    pop3 = Pop3(conf, known_uids)
    with pop3:
        for uid, msg in pop3.fetch():
            if not conf.is_interested_in(msg):
                continue
            for part in msg.walk():
                # if part.get('Content-Disposition') is None:
                #     continue
                conf.save_to(uid,
                             part.get_filename(),
                             part.get_payload(decode=1))

            print(uid)


if __name__ == '__main__':
    main()

