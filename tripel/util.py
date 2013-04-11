import os
import re
import base64
from datetime import datetime
import pytz

import web

import config.parameters as params
import config.messages as msg


class DateTimeUtil(object):
    @staticmethod
    def datetime_now_utc_aware():
        return datetime.now(pytz.utc)


def generate_random_url_safe_string(string_len):
    # ripped off from http://stackoverflow.com/questions/785058/random-strings-in-python-2-6-is-this-ok
    return base64.urlsafe_b64encode(os.urandom(string_len))[0:string_len]

def is_hyphenated_alphanumeric_string(str):
    return (str is not None) and (re.match('[A-Za-z0-9_\-]+', str).group(0) == str)

def build_url_path(app_deployment_path, subpath):
    return '%s%s' % (app_deployment_path, subpath)

def build_url(server_hostname, path):
    return '%s%s' % (server_hostname, path)

def get_file_contents(filename):
    f = open(filename, 'r')
    contents = f.read().strip()
    f.close()
    return contents

def get_websafe_dict_copy(original_dict):
    ret_val = original_dict.copy()
    for key in ret_val.keys():
        ret_val[key] = web.websafe(ret_val[key])
    return ret_val

def msg_lookup(key, content_dict={}, translation=msg.Messages.DEFAULT_TRANSLATION, should_escape_content=True):
    if should_escape_content:
        content_dict = get_websafe_dict_copy(content_dict)
    
    if hasattr(msg.Messages, key):
        content = getattr(msg.Messages, key)
        if translation not in content.keys():
            translation = msg.Messages.DEFAULT_TRANSLATION
        return content[translation] % content_dict
    else:
        return key

def init_web_config_mail_params():
    web.config.smtp_server = params.SMTP_SERVER
    web.config.smtp_port = params.SMTP_PORT
    web.config.smtp_username = params.SMTP_USERNAME
    web.config.smtp_password = get_file_contents(params.SMTP_PASS_FILENAME)

def sendmail(from_addr, to_addr, subject, message, headers=None, **kw):
    #TODO: this should happen asynchronously so the calling thread doesn't have to wait on the send
    # http://docs.python.org/2/library/threading.html#thread-objects
    web.utils.sendmail(from_addr, to_addr, subject, message, headers=headers, **kw)

def send_metaspace_invitation_email(ms_inv, ms_inv_link):
    from_addr = params.DEFAULT_FROM_ADDRESS
    to_addr = ms_inv.invitee_email_addr
    subject = msg_lookup('ms_inv_email_subject')
    message = msg_lookup('ms_inv_email_message',  {'inv_url': ms_inv_link, 'inv_msg': ms_inv.invitation_msg})
    sendmail(from_addr, to_addr, subject, message)

def send_nodespace_invitation_email(nodespace_name, ns_inv, ns_inv_link):
    from_addr = params.DEFAULT_FROM_ADDRESS
    to_addr = ns_inv.invitee_email_addr
    subject = msg_lookup('ns_inv_email_subject', {'nodespace_name': nodespace_name})
    message = msg_lookup('ns_inv_email_message', {'nodespace_name': nodespace_name, 'inv_url': ns_inv_link, 'inv_msg': ns_inv.invitation_msg})
    sendmail(from_addr, to_addr, subject, message)

def a_elt(link_text=None, href_att_val=None, class_att_val=None, id_att_val=None):
    href_att_txt = '' if href_att_val is None else ' href="%s"' % href_att_val
    class_att_txt = '' if class_att_val is None else ' class="%s"' % class_att_val
    id_att_txt = '' if id_att_val is None else ' id="%s"' % id_att_val
    return '<a %s>%s</a>' % (' '.join([href_att_txt, class_att_txt, id_att_txt]), link_text)