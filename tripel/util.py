import os
import re
import base64
from datetime import datetime
import pytz

import web

import config.parameters as params
import config.messages as messages

MSGS = messages.Messages


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
    subject = MSGS.lookup('ms_inv_email_subject')
    message = MSGS.lookup('ms_inv_email_message',  {'inv_url': ms_inv_link, 'inv_msg': ms_inv.invitation_msg})
    sendmail(from_addr, to_addr, subject, message)

def send_nodespace_invitation_email(nodespace_name, ns_inv, ns_inv_link):
    from_addr = params.DEFAULT_FROM_ADDRESS
    to_addr = ns_inv.invitee_email_addr
    subject = MSGS.lookup('ns_inv_email_subject', {'nodespace_name': nodespace_name})
    message = MSGS.lookup('ns_inv_email_message', {'nodespace_name': nodespace_name, 'inv_url': ns_inv_link, 'inv_msg': ns_inv.invitation_msg})
    sendmail(from_addr, to_addr, subject, message)

def a_elt(link_text=None, href_att_val=None, class_att_val=None, id_att_val=None):
    href_att_txt = '' if href_att_val is None else ' href="%s"' % href_att_val
    class_att_txt = '' if class_att_val is None else ' class="%s"' % class_att_val
    id_att_txt = '' if id_att_val is None else ' id="%s"' % id_att_val
    return '<a %s>%s</a>' % (' '.join([href_att_txt, class_att_txt, id_att_txt]), link_text)

#the idea here is to be able to easily create dictionaries representing arbitrary nodes/edges/graphs,
#where the nodes and edges don't necessarily conform to the constraints (e.g. required fields, field names) of
#the tripel node and edge classes.  these dictionaries can be consumed by things like the cytoscape graph
#rendering library (in that case, after being turned into json).  this allows for the use of ad-hoc neo4j query results
#that don't necessarily get full tripel objects (which for postgres results, would just be a list of dictionaries).
def build_adhoc_node_dict(node_id, node_type, node_data):
    return {'node_id': node_id, 'node_type': node_type, 'node_properties': node_data}

def build_adhoc_edge_dict(edge_id, edge_type, source, target, edge_data):
    return {'edge_id': edge_id, 'edge_type': edge_type, 'source': source, 'target': target, 'edge_properties': edge_data}

def build_adhoc_graph_dict(query_results, get_node_and_edge_dicts_fn):
    graph_dict = {'nodes': {}, 'edges': {}}
    for row in query_results:
        nodes, edges = get_node_and_edge_dicts_fn(row)
        
        for node in nodes:
            node_id = node['node_id']
            if node_id not in graph_dict['nodes']:
                graph_dict['nodes'][node_id] = node
        
        for edge in edges:
            edge_id = edge['edge_id']
            if edge_id not in graph_dict['edges']:
                graph_dict['edges'][edge_id] = edge
    
    return graph_dict
