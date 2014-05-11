'''
TODO: pages that return json should all:
1) use the same field name for indicating whether an error was encountered
2) stop returning status messages for now
3) eventually return error and warning codes as needed
'''
import re
import urllib
import json

import web

import tripel_core as tc
import config.parameters as params
import config.messages as messages
import util



RENDER = web.template.render(params.TEMPLATE_DIR)

PGDB = tc.PgUtil.get_db_conn_ssl(params.PG_DBNAME, params.PG_USERNAME, util.get_file_contents(params.PG_PASS_FILENAME))
NEODB = tc.NeoUtil.get_db_conn()
DB_TUPLE = (PGDB, NEODB)

MS_PRVLG_CHKR = tc.MetaspacePrivilegeChecker
NS_PRVLG_CHKR = tc.NodespacePrivilegeChecker

MSGS = messages.Messages

util.init_web_config_mail_params()


def build_url_path(subpath):
    return util.build_url_path(params.APP_DEPLOYMENT_PATH, subpath)

def build_url(path):
    return util.build_url(params.SERVER_HOSTNAME, path)

def get_json_string(obj):
    class JSONEncoderTripelDefault(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, util.datetime) or isinstance(obj, tc.PrivilegeSet):
                return str(obj)
            else:
                return super(JSONEncoderTripelDefault, self).default(obj)
    
    return json.dumps(obj, indent=2, cls=JSONEncoderTripelDefault)

def kill_session_and_cookie(pgdb, ms_session):
    if ms_session is not None:
        ms_session.kill_session(pgdb)
    web.setcookie(params.SESSION_ID_COOKIE_NAME, None, expires='-1', domain=None, secure=True)

def get_session_from_cookie(pgdb):
    ms_session_id = web.cookies().get(params.SESSION_ID_COOKIE_NAME)
    if ms_session_id is None:
        return None
    
    ms_session = tc.MetaspaceSession.get_existing_session(pgdb, ms_session_id)
    if ms_session is not None and ms_session.is_session_valid():
        return ms_session
    else:
        kill_session_and_cookie(pgdb, ms_session)
        return None


# note that BasePage and its subclasses are comprised entirely of classmethods.  currently, web.py 
# creates a new instance of the appropriate class for each request it handles, but according to a 
# thread on the web.py google group "this behavior should be considered an internal implementation 
# detail of web.py and might change in the future."  as my use of instance variables was already 
# very limited in this module, i just got rid of that entirely.  eventually the few methods that were
# made kludgey because of this should get removed anyway (since they implement UI code that's getting
# superseded by angular).
#  see also:  https://groups.google.com/d/topic/webpy/n93iZmrTFlU/discussion
class BasePage(object):
    CAN_GET_PAGE = True
    CAN_POST_PAGE = True
    REQUIRES_VALID_SESSION = True
    
    FULL_HTML_MODE, CHECK_IS_ALLOWED_TO_USE_MODE = 'full_html', 'check_is_allowed_to_use'
    JSON_MODE, NO_WRAPPER_HTML_MODE = 'json', 'no_wrapper_html'
    
    
    @classmethod
    def get_page_subpath(cls):
        return '/%s' % cls.__name__
    
    @classmethod
    def build_page_url(cls, query_params=None, should_include_hostname=True):
        ret_val = build_url_path(cls.get_page_subpath())
        if should_include_hostname: ret_val = build_url(ret_val)
        if query_params is not None: ret_val = '%s?%s' % (ret_val, urllib.urlencode(query_params))
        return ret_val
    
    @classmethod
    def get_page_name(cls):
        return MSGS.lookup('%s_page_name' % cls.__name__)
    
    @classmethod
    def get_page_title(cls):
        return '%s: %s' % (MSGS.lookup('instance_name'), cls.get_page_name())
    
    @classmethod
    def _get_header_links(cls, user, extra_display_info):
        if user is None:
            return None
        return [{'url': user_info_edit_form.build_page_url(query_params={'edited_user_id': user.user_id}), 'display_text': MSGS.lookup('edit_usr_link_disp_txt')},
                {'url': user_change_pass_form.build_page_url(query_params={'edited_user_id': user.user_id}), 'display_text': MSGS.lookup('passwd_link_disp_txt')},
                {'url': logout.build_page_url(), 'display_text': MSGS.lookup('logout_link_disp_txt')}]
    
    @classmethod
    def _get_nav_links(cls, user, extra_display_info):
        if user is None:
            return None
        
        ret_val = []
        if metaspace_command_list.is_allowed_to_use(None, user, False):
            ret_val.append({'url': metaspace_command_list.build_page_url(), 'display_text': metaspace_command_list.get_page_name()})
        ret_val.append({'url': nodespace_list_accessible.build_page_url(), 'display_text': MSGS.lookup('accessible_nodespaces_link_disp_txt', {'username': user.username})})
        
        return ret_val
    
    @classmethod
    def _get_command_links(cls, user, extra_display_info):
        return None
    
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        return MSGS.lookup('%s_smry' % cls.__name__)
    
    @classmethod
    def wrap_content(cls, content, ms_session=None, user=None, extra_display_info={}):
        if user is None and ms_session is not None and ms_session.is_session_valid():
            user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        
        hdr_links = cls._get_header_links(user, extra_display_info)
        nav_links = cls._get_nav_links(user, extra_display_info)
        cmd_links = cls._get_command_links(user, extra_display_info)
        content_summary = cls._get_content_summary(user, extra_display_info)
        return RENDER.outer_wrapper(cls.get_page_title(), content_summary, content, MSGS.lookup, hdr_links, nav_links, cmd_links)
    
    @classmethod
    def render_angular_app(cls, ms_session=None, user=None, extra_display_info={}):
        if user is None and ms_session is not None and ms_session.is_session_valid():
            user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        
        hdr_links = cls._get_header_links(user, extra_display_info)
        return RENDER.nga(cls.get_page_title(), MSGS.lookup, hdr_links)
    
    @classmethod
    def render_input_forwarding_form(cls, forwarding_form_action=None, forwarding_target=None):
        forwarded_fields = [web.form.Hidden(name=k, value=v) for k, v in web.input().items() if k not in ['login_username', 'login_password', 'Login']]
        #TODO: null out forwarding_target if it's not pointing to something in the site
        if forwarding_target is not None:
            forwarded_fields.append(web.form.Hidden(name='forwarding_target', value=forwarding_target))
        forwarding_form = web.form.Form(*forwarded_fields)
        if forwarding_form_action is not None:
            return cls.wrap_content(RENDER.basic_form_template(forwarding_form.render(), 'forwarding_form', forwarding_form_action, True))
        else:
            return forwarding_form.render()
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        raise NotImplementedError('subclass must implement this')
    
    @classmethod
    def GET(cls):
        if cls.CAN_GET_PAGE:
            return cls.check_session_and_render_page()
        else:
            web.nomethod()
    
    @classmethod
    def POST(cls):
        if cls.CAN_POST_PAGE:
            return cls.check_session_and_render_page()
        else:
            web.nomethod()
    
    @classmethod
    def check_session_and_render_page(cls):
        ms_session = get_session_from_cookie(PGDB)
        if cls.REQUIRES_VALID_SESSION and (ms_session is None or not ms_session.is_session_valid()):
            return cls.render_input_forwarding_form(login_form.build_page_url(), build_url(web.ctx.path))
        else:
            if ms_session is not None and ms_session.is_session_valid():
                ms_session.touch_session(PGDB)
            
            try:
                return cls.render_page(ms_session)
            except tc.PrivilegeChecker.InsufficientPrivilegesException:
                web.forbidden()
            except tc.User.TooManyBadPasswordsException:
                kill_session_and_cookie(PGDB, ms_session)
                web.found(login_form.build_page_url())
    
    @classmethod
    def get_page_render_fn(cls, page_mode):
        if page_mode == cls.FULL_HTML_MODE:
            return cls.render_page_full_html
        elif page_mode == cls.CHECK_IS_ALLOWED_TO_USE_MODE:
            return cls.render_page_is_allowed_to_use
        elif page_mode == cls.JSON_MODE:
            #TODO: would be good to set the headers to say json's being returned, right?
            return cls.render_page_json
        elif page_mode == cls.NO_WRAPPER_HTML_MODE:
            return cls.render_page_no_wrapper_html
        
        return None
    
    #TODO: eventually, none of the subclasses will implement render_page anymore, they'll 
    # implement the specific rendering functions mapped to page_mode values by get_page_render_fn.
    # subclass may also extend get_page_render_fn if supporting non-standard modes.
    @classmethod
    def render_page(cls, ms_session):
        page_mode = web.input(modeselektion=cls.FULL_HTML_MODE).get('modeselektion')
        page_render_fn = cls.get_page_render_fn(page_mode)
        
        # i'm not sure if this is actually an appropriate use of the 412 response code, since the RFC 
        # indicated that it should be used based on what the request headers indicate (and this response is 
        # based on a request parameter).  regardless, clients should ideally not encounter this anyway.
        if page_render_fn is None:
            raise web.preconditionfailed('unsupported page_mode')
        
        return page_render_fn(ms_session)
    
    @classmethod
    def render_page_is_allowed_to_use(cls, ms_session):
        raise NotImplementedError('must be implemented by subclass')
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        raise NotImplementedError('must be implemented by subclass')
    
    @classmethod
    def render_page_json(cls, ms_session):
        raise NotImplementedError('must be implemented by subclass')
    
    @classmethod
    def render_page_no_wrapper_html(cls, ms_session):
        raise NotImplementedError('must be implemented by subclass')

class ListTablePage(object):
    @classmethod
    def _get_col_keys(cls, table_data):
        return table_data[0].__dict__.keys()
    
    @classmethod
    def _get_table_headers(cls, table_data):
        return map(lambda x: MSGS.lookup('%s_col_hdr' % x), cls._get_col_keys(table_data))
    
    @classmethod
    def _get_display_row(cls, table_data_row):
        return util.get_websafe_dict_copy(table_data_row.__dict__)
    
    @classmethod
    def _table_data_to_basic_table_template_input(cls, table_data):
        if table_data is None or len(table_data) == 0:
            return [None, None, None]
        table_rows = map(cls._get_display_row, table_data)
        return [cls._get_col_keys(table_data), cls._get_table_headers(table_data), table_rows]
    
    @classmethod
    def basic_table_content(cls, table_data):
        return RENDER.basic_table_template(*cls._table_data_to_basic_table_template_input(table_data))

class login_form(BasePage):
    REQUIRES_VALID_SESSION = False
    
    LOGIN_FORM = web.form.Form(
                    web.form.Textbox(name='login_username', description=MSGS.lookup('username_label')),
                    web.form.Password(name='login_password', description=MSGS.lookup('login_password_label')),
                    web.form.Button(name=MSGS.lookup('login_submit_btn')))
    
    @classmethod
    def render_page(cls, ms_session):
        login_form_html = cls.LOGIN_FORM(web.input()).render()
        if web.input().get('forwarding_target') is not None:
            login_form_html = '%s%s' % (login_form_html, cls.render_input_forwarding_form())
        return cls.wrap_content(RENDER.basic_form_template(login_form_html, 'login_form', login_verify.build_page_url()))

class login_verify(BasePage):
    CAN_GET_PAGE = False
    REQUIRES_VALID_SESSION = False
    
    @classmethod
    def create_session_and_set_cookie(cls, pgdb, user_id):
        ms_session = tc.MetaspaceSession.force_create_new_session(pgdb, user_id)
        web.setcookie(params.SESSION_ID_COOKIE_NAME, ms_session.metaspace_session_id, expires='', domain=None, secure=True)
        return ms_session
    
    @classmethod
    def render_page(cls, ms_session):
        username = web.input().get('login_username')
        cleartext_password = web.input().get('login_password')
        
        has_valid_session = False
        if username is not None and cleartext_password is not None:
            user = tc.User.get_existing_user_by_username(PGDB, username)
            if user is not None and user.check_password_audited(PGDB, cleartext_password, False):
                ms_session = cls.create_session_and_set_cookie(PGDB, user.user_id)
                has_valid_session = True

        if web.input().get('forwarding_target') is not None:
            forwarding_form_action = web.input().get('forwarding_target') if has_valid_session else login_form.build_page_url()
            return cls.render_input_forwarding_form(forwarding_form_action)
        else:
            web.found(nodespace_list_accessible.build_page_url())

class logout(BasePage):
    REQUIRES_VALID_SESSION = False
    
    @classmethod
    def render_page(cls, ms_session):
        ms_session = get_session_from_cookie(PGDB)
        kill_session_and_cookie(PGDB, ms_session)
        web.found(login_form.build_page_url())

class auth_status(BasePage, ListTablePage):
    REQUIRES_VALID_SESSION = False
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        has_valid_session = (ms_session is not None) and ms_session.is_session_valid()
        output_html = MSGS.lookup('auth_status_text', {'has_valid_session': has_valid_session})
        if ms_session is not None:
            output_html = '<p>%s</p><p>%s</p>' % (output_html, cls.basic_table_content([ms_session]))
        return cls.wrap_content(output_html, ms_session=ms_session)
    
    @classmethod
    def render_page_json(cls, ms_session):
        has_valid_session = (ms_session is not None) and ms_session.is_session_valid()
        session_dict = {'has_valid_session': has_valid_session}
        
        if has_valid_session:
            for col_key in cls._get_col_keys([ms_session]):
                session_dict[col_key] = getattr(ms_session, col_key)
        
        return get_json_string(session_dict)

class NodespaceForm(object):
    @classmethod
    def get_nodespace_form(cls, btn_content_key):
        return web.form.Form(web.form.Textbox('nodespace_name', 
                                                web.form.Validator(MSGS.lookup('invalid_ns_name'), lambda x: tc.Nodespace.is_valid_nodespace_name(x)),
                                                description=MSGS.lookup('create_ns_form_nsname')),
                                web.form.Textarea('nodespace_description', description=MSGS.lookup('create_ns_form_ns_desc'), cols='40', rows='3'),
                                web.form.Button(name=MSGS.lookup(btn_content_key)))

class nodespace_create_form(BasePage, NodespaceForm):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_create.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        cls.is_allowed_to_use(None, user)
        
        nodespace_create_form_html = cls.get_nodespace_form('create_ns_submit_btn')(web.input()).render()
        return cls.wrap_content(RENDER.basic_form_template(nodespace_create_form_html, 'nodespace_create_form', nodespace_create.build_page_url()), user=user)

class nodespace_create(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.CREATE_SPACE_ACTION, None, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page_is_allowed_to_use(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        ret_val = {'is_allowed_to_use': cls.is_allowed_to_use(None, user, should_raise_insufficient_priv_ex=False)}
        return get_json_string(ret_val)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        cls.is_allowed_to_use(None, user)
        
        nodespace_name = web.input().get('nodespace_name')
        nodespace_description = web.input().get('nodespace_description')
        new_nodespace = None
        #TODO: wrap in transaction?
        if tc.Nodespace.is_valid_nodespace_name(nodespace_name) and tc.Nodespace.get_existing_nodespace(PGDB, nodespace_name) is None:
            new_nodespace = tc.Nodespace.create_new_nodespace(DB_TUPLE, nodespace_name, nodespace_description, user.user_id)
        
        return new_nodespace
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        new_nodespace = cls._render_page_helper(ms_session)
        
        if new_nodespace is not None:
            web.found(nodespace_view.build_page_url(query_params={'nodespace_id': new_nodespace.nodespace_id}))
        else:
            web.found(nodespace_create_form.build_page_url(web.input()))
    
    @classmethod
    def render_page_json(cls, ms_session):
        new_nodespace = cls._render_page_helper(ms_session)
        
        if new_nodespace is not None:
            return get_json_string({'encountered_create_error': False, 'nodespace_id': new_nodespace.nodespace_id})
        else:
            return get_json_string({'encountered_create_error': True})

class nodespace_edit_form(BasePage, NodespaceForm):
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        if user is None:
            return None
        return MSGS.lookup('nodespace_edit_form_smry', {'nodespace_name': extra_display_info['nodespace'].nodespace_name})
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        cls.is_allowed_to_use(nodespace, user)
        
        nodespace_id_hidden_html = web.form.Hidden(name='nodespace_id', value=nodespace.nodespace_id).render()
        nodespace_edit_form_html = '%s\n%s' % (nodespace_id_hidden_html, cls.get_nodespace_form('edit_ns_submit_btn')(nodespace.__dict__).render())
        return cls.wrap_content(RENDER.basic_form_template(nodespace_edit_form_html, 'nodespace_edit_form', nodespace_edit.build_page_url()), user=user, extra_display_info={'nodespace': nodespace})

class nodespace_edit(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.ALTER_NODESPACE_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        
        cls.is_allowed_to_use(nodespace, user)
        
        try:
            nodespace_name = web.input().get('nodespace_name')
            nodespace_description = web.input().get('nodespace_description')
            nodespace.set_and_save_nodespace_settings(PGDB, nodespace_name, nodespace_description, user.user_id)
        except:
            nodespace = None
        
        return nodespace
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        nodespace = cls._render_page_helper(ms_session)
        web.found(nodespace_view.build_page_url(query_params={'nodespace_id':nodespace.nodespace_id}))
    
    @classmethod
    def render_page_json(cls, ms_session):
        nodespace = cls._render_page_helper(ms_session)
        encountered_update_error = False if nodespace is not None else True
        return get_json_string({'encountered_update_error': encountered_update_error})

class nodespace_view(BasePage, ListTablePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.VIEW_NODESPACE_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        if user is None:
            return None
        return MSGS.lookup('nodespace_view_smry', {'nodespace_name': extra_display_info['nodespace'].nodespace_name})
    
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['nodespace_name', 'nodespace_description', 'creator', 'creation_date', 'modifier', 'modification_date']
    
    @classmethod
    def _get_command_perms(cls, user, nodespace):
        perm_dict = {'is_allowed_to_edit_nodespace': False, 
                    'is_allowed_to_list_nodespace_users': False, 
                    'is_allowed_to_invite_nodespace_users': False}
        
        if user is None:
            return perm_dict
        
        perm_dict['is_allowed_to_edit_nodespace'] = nodespace_edit_form.is_allowed_to_use(nodespace, user, False)
        perm_dict['is_allowed_to_list_nodespace_users'] = user_list_nodespace.is_allowed_to_use(nodespace, user, False)
        perm_dict['is_allowed_to_invite_nodespace_users'] = nodespace_invitation_create_form.is_allowed_to_use(nodespace, user, False)
        
        return perm_dict
    
    @classmethod
    def _get_command_links(cls, user, extra_display_info):
        ret_val = []
        nodespace = extra_display_info['nodespace']
        command_perms = cls._get_command_perms(user, nodespace)
        
        if command_perms['is_allowed_to_edit_nodespace']:
            ns_edit_url = nodespace_edit_form.build_page_url(query_params={'nodespace_id': nodespace.nodespace_id})
            ns_edit_disp_txt = MSGS.lookup('edit_nodespace_link_disp_txt', {'nodespace_name': nodespace.nodespace_name})
            ret_val.append({'url': ns_edit_url, 'display_text': ns_edit_disp_txt})
        
        if command_perms['is_allowed_to_list_nodespace_users']:
            user_list_ns_url = user_list_nodespace.build_page_url(query_params={'nodespace_id': nodespace.nodespace_id})
            user_list_ns_disp_txt = MSGS.lookup('nodespace_user_list_link_disp_txt', {'nodespace_name': nodespace.nodespace_name})
            ret_val.append({'url': user_list_ns_url, 'display_text': user_list_ns_disp_txt})
        
        if command_perms['is_allowed_to_invite_nodespace_users']:
            ns_inv_url = nodespace_invitation_create_form.build_page_url(query_params={'nodespace_id': nodespace.nodespace_id})
            ns_inv_disp_txt = MSGS.lookup('nodespace_inv_link_disp_txt', {'nodespace_name': nodespace.nodespace_name})
            ret_val.append({'url': ns_inv_url, 'display_text': ns_inv_disp_txt})
        
        return ret_val
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace_id = web.input().get('nodespace_id')
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, nodespace_id)
        cls.is_allowed_to_use(nodespace, user)
        return cls.wrap_content(cls.basic_table_content([nodespace]), user=user, extra_display_info={'nodespace': nodespace})
    
    @classmethod
    def render_page_json(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace_id = web.input().get('nodespace_id')
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, nodespace_id)
        cls.is_allowed_to_use(nodespace, user)
        
        perms_for_user = cls._get_command_perms(user, nodespace)
        nodespace_info = {}
        for field_name in ['nodespace_name', 'nodespace_description', 'creator', 'creation_date', 'modifier', 'modification_date']:
            nodespace_info[field_name] = getattr(nodespace, field_name)
        ret_val = {'perms_for_user': perms_for_user, 'nodespace_info': nodespace_info}
        
        return get_json_string(ret_val)

class PrivilegesEditForm(object):
    @classmethod
    def privilege_select_elts(cls, field_name, grantable_privileges_list, selected_privileges=tc.PrivilegeSet()):
        priv_entries = []
        for priv in grantable_privileges_list:
            priv_title = MSGS.lookup('%s_priv_title' % priv)
            priv_desc = MSGS.lookup('%s_priv_desc' % priv)
            priv_checkbox = web.form.Checkbox(field_name, value=priv, description='%s: %s' % (priv_title, priv_desc), checked=(selected_privileges.has_privilege(priv)))
            priv_entries.append(priv_checkbox)
        
        return priv_entries
    
    @classmethod
    def metaspace_privilege_select_elts(cls, field_name='metaspace_privileges', grantable_privileges=None, selected_privileges=tc.MetaspacePrivilegeSet()):
        return cls.privilege_select_elts(field_name, sorted(grantable_privileges, tc.MetaspacePrivilegeSet.comparator), selected_privileges)
    
    @classmethod
    def nodespace_privilege_select_elts(cls, field_name='nodespace_privileges', grantable_privileges=None, selected_privileges=tc.NodespacePrivilegeSet()):
        return cls.privilege_select_elts(field_name, sorted(grantable_privileges, tc.NodespacePrivilegeSet.comparator), selected_privileges)

class user_invitation_create_form(BasePage, PrivilegesEditForm):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return user_invitation_create.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def get_ms_inv_create_form(cls, user):
        return web.form.Form(
                            *([web.form.Textbox('invitee_email_addr', description=MSGS.lookup('create_inv_email_addr'))] +
                            cls.metaspace_privilege_select_elts(grantable_privileges=user.metaspace_privileges.get_grantable_privileges()) +
                            [web.form.Textarea('invitation_msg', description=MSGS.lookup('create_ms_inv_msg'), cols='40', rows='3'),
                            web.form.Button(name=MSGS.lookup('create_inv_submit_btn'))]))
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        cls.is_allowed_to_use(None, user)
        
        ms_inv_create_form_html = cls.get_ms_inv_create_form(user)().render()
        return cls.wrap_content(RENDER.basic_form_template(ms_inv_create_form_html, 'ms_inv_create_form', user_invitation_create.build_page_url()), user=user)
    
    @classmethod
    def render_page_json(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        cls.is_allowed_to_use(None, user)
        grantable_privileges = sorted(user.metaspace_privileges.get_grantable_privileges(), tc.MetaspacePrivilegeSet.comparator)
        return get_json_string({'grantable_privileges': grantable_privileges})

class user_invitation_create(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.CREATE_USER_ACTION, None, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page_is_allowed_to_use(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        ret_val = {'is_allowed_to_use': cls.is_allowed_to_use(None, user, should_raise_insufficient_priv_ex=False)}
        return get_json_string(ret_val)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        cls.is_allowed_to_use(None, user)
        
        invitee_email_addr = util.empty_str_to_none(web.input().get('invitee_email_addr'))
        metaspace_privileges = tc.MetaspacePrivilegeSet.create_from_list_of_strings(web.input(metaspace_privileges=[]).get('metaspace_privileges'))
        invitation_msg = web.input().get('invitation_msg')
        try:
            ms_inv = tc.MetaspaceInvitation.create_new_invitation(PGDB, None, invitee_email_addr, metaspace_privileges, invitation_msg, user.user_id)
        except:
            ms_inv = None
        
        if ms_inv is not None and ms_inv.metaspace_invitation_id is not None:
            ms_inv_link = user_invitation_decide_form.build_page_url(query_params={'metaspace_invitation_code': ms_inv.metaspace_invitation_code})
            util.send_metaspace_invitation_email(ms_inv, ms_inv_link)
            status_message = MSGS.lookup('inv_create_success', {'inv_url': ms_inv_link})
        else:
            status_message = MSGS.lookup('inv_create_failure')
        
        return (user, ms_inv, status_message)
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        user, ms_inv, status_message = cls._render_page_helper(ms_session)
        return cls.wrap_content(status_message, user=user)
    
    @classmethod
    def render_page_json(cls, ms_session):
        ms_inv, status_message = cls._render_page_helper(ms_session)
        if ms_inv is not None and ms_inv.metaspace_invitation_id is not None:
            encountered_create_error = False
        else:
            encountered_create_error = True
        return get_json_string({'encountered_create_error': encountered_create_error, 'status_message': status_message})

class InvitationDecideForm(object):
    INV_ACCEPT_FORM = web.form.Form(
                                web.form.Textbox('username', description=MSGS.lookup('username_label')),
                                web.form.Password(name='cleartext_password_1', description=MSGS.lookup('new_password_label')),
                                web.form.Password(name='cleartext_password_2', description=MSGS.lookup('reenter_password_label')),
                                web.form.Textarea('user_statement', description=MSGS.lookup('user_statement_blurb'), cols='40', rows='3'),
                                web.form.Button(name=MSGS.lookup('inv_accept_submit_btn')))
    
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    
    @classmethod
    def build_accept_form(cls, form_name, form_target, inv_code_field_name, inv_code):
        ms_inv_code_hidden = web.form.Hidden(name=inv_code_field_name, value=inv_code).render()
        ms_inv_accept_hidden = web.form.Hidden(name='was_accepted', value=cls.ACCEPTED).render()
        ms_inv_accept_form_html = '%s\n %s\n %s' % (ms_inv_code_hidden, ms_inv_accept_hidden, cls.INV_ACCEPT_FORM().render())
        ms_inv_accept_form_html = RENDER.basic_form_template(ms_inv_accept_form_html, form_name, form_target)
        return ms_inv_accept_form_html
    
    @classmethod
    def build_single_button_form(cls, form_name, form_target, rendered_hidden_field_elts, button_name):
        hidden_field_html = '\n'.join(rendered_hidden_field_elts)
        btn_html = web.form.Button(name=button_name).render()
        single_button_form_html = '%s\n %s' % (hidden_field_html, btn_html)
        single_button_form_html = RENDER.basic_form_template(single_button_form_html, form_name, form_target)
        return single_button_form_html
    
    @classmethod
    def build_decline_form(cls, form_name, form_target, inv_code_field_name, inv_code):
        ms_inv_code_hidden = web.form.Hidden(name=inv_code_field_name, value=inv_code).render()
        ms_inv_decline_hidden = web.form.Hidden(name='was_accepted', value=cls.DECLINED).render()
        return cls.build_single_button_form(form_name, form_target, [ms_inv_code_hidden, ms_inv_decline_hidden], MSGS.lookup('inv_decline_submit_btn'))

class user_invitation_decide_form(BasePage, InvitationDecideForm):
    REQUIRES_VALID_SESSION = False
    
    @classmethod
    def render_page(cls, ms_session):
        ms_inv_code = web.input().get('metaspace_invitation_code')
        ms_inv = tc.MetaspaceInvitation.get_existing_invitation(PGDB, ms_inv_code)
        if ms_inv is None or ms_inv.decision_date is not None:
            return cls.wrap_content(MSGS.lookup('inv_not_found'))
        
        form_target = user_invitation_decide.build_page_url()
        ms_inv_accept_form_html = cls.build_accept_form('ms_inv_accept_form', form_target, 'metaspace_invitation_code', ms_inv_code)
        ms_inv_decline_form_html = cls.build_decline_form('ms_inv_decline_form', form_target, 'metaspace_invitation_code', ms_inv_code)
        
        ms_inv_decide_header = MSGS.lookup('ms_inv_decide_header', {'inv_code': ms_inv_code, 'invitee_email_addr': ms_inv.invitee_email_addr})
        return cls.wrap_content('<p>%s</p>\n <p>%s</p>\n <p>%s</p>\n <p>%s</p> ' % (ms_inv_decide_header, ms_inv.invitation_msg, ms_inv_accept_form_html, ms_inv_decline_form_html))

class user_invitation_decide(BasePage):
    REQUIRES_VALID_SESSION = False
    
    @classmethod
    def render_page(cls, ms_session):
        ms_inv_code = web.input().get('metaspace_invitation_code')
        ms_inv = tc.MetaspaceInvitation.get_existing_invitation(PGDB, ms_inv_code)
        if ms_inv is None or ms_inv.decision_date is not None:
            return cls.wrap_content(MSGS.lookup('inv_not_found'))

        was_accepted = web.input().get('was_accepted')
        if was_accepted == user_invitation_decide_form.DECLINED:
            ms_inv.decline_invitation(PGDB)
            return cls.wrap_content(MSGS.lookup('ms_inv_declined_ack', {'inv_code': ms_inv_code}))
        
        username = util.empty_str_to_none(web.input().get('username'))
        user_statement = web.input().get('user_statement')
        cleartext_password_1 = web.input().get('cleartext_password_1')
        cleartext_password_2 = web.input().get('cleartext_password_2')
        if cleartext_password_1 != cleartext_password_2:
            return cls.wrap_content(MSGS.lookup('password_mismatch_error'))
        
        new_user = ms_inv.create_user_and_accept_invitation(DB_TUPLE, username, cleartext_password_1, user_statement)
        if new_user is not None and new_user.user_id is not None:
            ms_session = login_verify.create_session_and_set_cookie(PGDB, new_user.user_id)
            web.found(auth_status.build_page_url())
        else:
            return cls.wrap_content(MSGS.lookup('ms_inv_user_create_failure'))

#TODO: the invitation create(/decide?) workflows have largely the same logic and content, can probably centralize and have wrappers pass in differentiated form/field names
class nodespace_invitation_create_form(BasePage, PrivilegesEditForm):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_invitation_create.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _get_grantable_privileges(cls, nodespace, user):
        ns_access_for_user = nodespace.get_nodespace_access_for_user(PGDB, user.user_id)
        grantable_privileges = (ns_access_for_user.nodespace_privileges if ns_access_for_user is not None else tc.NodespacePrivilegeSet()).get_grantable_privileges()
        return grantable_privileges
    
    @classmethod
    def get_ns_inv_create_form(cls, nodespace, user):
        grantable_privileges = cls._get_grantable_privileges(nodespace, user)
        return web.form.Form(
                            *([web.form.Textbox('invitee_email_addr', description=MSGS.lookup('create_inv_email_addr'))] +
                            cls.nodespace_privilege_select_elts(grantable_privileges=grantable_privileges) +
                            [web.form.Textarea('invitation_msg', description=MSGS.lookup('create_ns_inv_msg'), cols='40', rows='3'),
                            web.form.Button(name=MSGS.lookup('create_inv_submit_btn'))]))
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        cls.is_allowed_to_use(nodespace, user)
        return (user, nodespace)
        
    @classmethod
    def render_page_full_html(cls, ms_session):
        user, nodespace = cls._render_page_helper(ms_session)
        nodespace_id_hidden = web.form.Hidden(name='nodespace_id', value=web.input().get('nodespace_id'))
        ns_inv_create_form_html = '%s %s' % (nodespace_id_hidden.render(), cls.get_ns_inv_create_form(nodespace, user).render())
        return cls.wrap_content(RENDER.basic_form_template(ns_inv_create_form_html, 'ns_inv_create_form', nodespace_invitation_create.build_page_url()), user=user)
    
    @classmethod
    def render_page_json(cls, ms_session):
        user, nodespace = cls._render_page_helper(ms_session)
        grantable_privileges = cls._get_grantable_privileges(nodespace, user)
        grantable_privileges = sorted(grantable_privileges, tc.NodespacePrivilegeSet.comparator)
        return get_json_string({'grantable_privileges': grantable_privileges})

class nodespace_invitation_create(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.ALTER_NODESPACE_ACCESS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        
        cls.is_allowed_to_use(nodespace, user)
        
        invitee_email_addr = util.empty_str_to_none(web.input().get('invitee_email_addr'))
        nodespace_privileges = tc.NodespacePrivilegeSet.create_from_list_of_strings(web.input(nodespace_privileges=[]).get('nodespace_privileges'))
        invitee_user = tc.User.get_existing_user_by_email(PGDB, invitee_email_addr)
        if invitee_user is None:
            tc.MetaspacePrivilegeChecker.is_allowed_to_do(DB_TUPLE, tc.MetaspacePrivilegeChecker.CREATE_USER_ACTION, None, user)
        
        invitation_msg = web.input().get('invitation_msg')
        ns_inv = tc.NodespaceInvitation.create_new_invitation(PGDB, None, invitee_email_addr, nodespace.nodespace_id, nodespace_privileges, invitation_msg, user.user_id)
        
        if ns_inv is not None and ns_inv.nodespace_invitation_id is not None:
            ns_inv_link = nodespace_invitation_decide_form.build_page_url(query_params={'nodespace_invitation_code': ns_inv.nodespace_invitation_code})
            util.send_nodespace_invitation_email(nodespace.nodespace_name, ns_inv, ns_inv_link)
            status_message = MSGS.lookup('inv_create_success', {'inv_url': ns_inv_link})
        else:
            status_message = MSGS.lookup('inv_create_failure')
        
        return (user, ns_inv, status_message)
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        user, ns_inv, status_message = cls._render_page_helper(ms_session)
        return cls.wrap_content(status_message, user=user)
    
    @classmethod
    def render_page_json(cls, ms_session):
        user, ns_inv, status_message = cls._render_page_helper(ms_session)
        if ns_inv is not None and ns_inv.nodespace_invitation_id is not None:
            encountered_create_error = False
        else:
            encountered_create_error = True
        return get_json_string({'encountered_create_error': encountered_create_error, 'status_message': status_message})

class nodespace_invitation_decide_form(BasePage, InvitationDecideForm):
    REQUIRES_VALID_SESSION = False
    
    @classmethod
    def render_page(cls, ms_session):
        inv_code_field_name = 'nodespace_invitation_code'
        ns_inv_code = web.input().get(inv_code_field_name)
        ns_inv = tc.NodespaceInvitation.get_existing_invitation(PGDB, ns_inv_code)
        if ns_inv is None or ns_inv.decision_date is not None:
            return cls.wrap_content(MSGS.lookup('inv_not_found'))
        
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, ns_inv.nodespace_id)
        invitee_user = tc.User.get_existing_user_by_email(PGDB, ns_inv.invitee_email_addr)
        
        form_target = nodespace_invitation_decide.build_page_url()
        form_name = 'ns_inv_accept_form'
        header_content_dict = {'inv_code': ns_inv_code, 'nodespace_name': nodespace.nodespace_name, 'invitee_email_addr': ns_inv.invitee_email_addr}
        if invitee_user is not None:
            ns_inv_code_hidden = web.form.Hidden(name=inv_code_field_name, value=ns_inv_code).render()
            ns_inv_accept_hidden = web.form.Hidden(name='was_accepted', value=cls.ACCEPTED).render()
            ns_inv_accept_form_html = cls.build_single_button_form(form_name, form_target, [ns_inv_code_hidden, ns_inv_accept_hidden], MSGS.lookup('inv_accept_submit_btn'))
            ns_inv_decide_header = MSGS.lookup('ns_inv_decide_ext_user_header', header_content_dict)
        else:
            ns_inv_accept_form_html = cls.build_accept_form(form_name, form_target, inv_code_field_name, ns_inv_code)
            ns_inv_decide_header = MSGS.lookup('ns_inv_decide_new_user_header', header_content_dict)
        
        ns_inv_decline_form_html = cls.build_decline_form('ns_inv_decline_form', form_target, inv_code_field_name, ns_inv_code)
        
        return cls.wrap_content('<p>%s</p>\n <p>%s</p>\n <p>%s</p>\n <p>%s</p> ' % (ns_inv_decide_header, ns_inv.invitation_msg, ns_inv_accept_form_html, ns_inv_decline_form_html))

class nodespace_invitation_decide(BasePage):
    REQUIRES_VALID_SESSION = False
    
    @classmethod
    def render_page(cls, ms_session):
        ns_inv_code = web.input().get('nodespace_invitation_code')
        ns_inv = tc.NodespaceInvitation.get_existing_invitation(PGDB, ns_inv_code)
        if ns_inv is None or ns_inv.decision_date is not None:
            return cls.wrap_content(MSGS.lookup('inv_not_found'))
        
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, ns_inv.nodespace_id)
        
        was_accepted = web.input().get('was_accepted')
        if was_accepted == nodespace_invitation_decide_form.DECLINED:
            ns_inv.decline_invitation(PGDB)
            return cls.wrap_content(MSGS.lookup('ns_inv_declined_ack', {'inv_code': ns_inv_code, 'nodespace_name': nodespace.nodespace_name}))
        
        cleartext_password_1 = web.input().get('cleartext_password_1')
        cleartext_password_2 = web.input().get('cleartext_password_2')
        if cleartext_password_1 != cleartext_password_2:
            return cls.wrap_content(MSGS.lookup('password_mismatch_error'))
        
        invitee_user = tc.User.get_existing_user_by_email(PGDB, ns_inv.invitee_email_addr)
        if invitee_user is not None:
            ns_inv.accept_invitation(PGDB, invitee_user.user_id)
        else:
            invitee_user = ns_inv.create_user_and_accept_invitation(DB_TUPLE, util.empty_str_to_none(web.input().get('username')), cleartext_password_1, web.input().get('user_statement'))
        
        nodespace_access_entry = nodespace.get_nodespace_access_for_user(PGDB, invitee_user.user_id)
        
        if invitee_user is not None and nodespace_access_entry is not None:
            #TODO: this actually presents a security hole:  anyone who has an invitation link for an existing user can
            # get a session as that user.  should just redirect to login page.  maybe do the same for ms user creation,
            # if only for consistency's sake.
            ms_session = login_verify.create_session_and_set_cookie(PGDB, invitee_user.user_id)
            web.found(nodespace_access_view.build_page_url(query_params={'nodespace_id': nodespace.nodespace_id}))
        else:
            return cls.wrap_content(MSGS.lookup('ns_inv_accept_failure'))

class nodespace_access_view(BasePage, ListTablePage):
    @classmethod
    def render_page(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        nodespace_access_entry = nodespace.get_nodespace_access_for_user(PGDB, user.user_id)
        
        if nodespace_access_entry is not None:
            status_text = MSGS.lookup('ns_access_header', {'nodespace_name': nodespace.nodespace_name})
            access_html = cls.basic_table_content([nodespace_access_entry])
        else:
            status_text = MSGS.lookup('ns_no_access_header')
            access_html = None
        session_html = cls.basic_table_content([ms_session])
        output_html = '<p>%s</p><p>%s</p><p>%s</p>' % (status_text, access_html, session_html)
        return cls.wrap_content(output_html, user=user)

class user_view(BasePage, ListTablePage):
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['user_id', 'username', 'email_addr', 'user_statement', 'metaspace_privileges', 'is_enabled', 'creator', 'creation_date', 'modifier', 'modification_date']
    
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        if user is None:
            return None
        return MSGS.lookup('user_view_smry', {'username': extra_display_info['viewed_user'].username})
    
    @classmethod
    def _get_command_links(cls, user, extra_display_info):
        if user is None:
            return None
        
        ret_val = []
        
        viewed_user = extra_display_info['viewed_user']
        if user_info_edit_form.is_allowed_to_use(None, user, False):
            user_edit_url = user_info_edit_form.build_page_url(query_params={'edited_user_id': viewed_user.user_id})
            user_edit_disp_txt = MSGS.lookup('edit_other_usr_link_disp_txt', {'username': viewed_user.username})
            ret_val.append({'url': user_edit_url, 'display_text': user_edit_disp_txt})
        
        if user_change_pass_form.is_allowed_to_use(None, user, False):
            user_chg_pass_url = user_change_pass_form.build_page_url(query_params={'edited_user_id': viewed_user.user_id})
            user_chg_pass_disp_txt = MSGS.lookup('chg_pass_other_user_disp_txt', {'username': viewed_user.username})
            ret_val.append({'url': user_chg_pass_url, 'display_text': user_chg_pass_disp_txt})
        
        if metaspace_access_edit_form.is_allowed_to_use(None, user, False):
            ms_priv_edit_url = metaspace_access_edit_form.build_page_url(query_params={'edited_user_id': viewed_user.user_id})
            ms_priv_edit_disp_txt = MSGS.lookup('edit_other_usr_privs_link_disp_txt', {'username': viewed_user.username})
            ret_val.append({'url': ms_priv_edit_url, 'display_text': ms_priv_edit_disp_txt})
        
        return ret_val
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.VIEW_USER_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def table_data_to_basic_table_template_input(cls, table_data):
        if table_data is None or len(table_data) == 0:
            return [None, None, None]
        col_keys = table_data[0].keys()
        return [col_keys, col_keys, table_data]
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        viewing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        viewed_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('viewed_user_id'))
        cls.is_allowed_to_use(viewed_user, viewing_user)
        return cls.wrap_content(cls.basic_table_content([viewed_user]), user=viewing_user, extra_display_info={'viewed_user': viewed_user})
    
    @classmethod
    def render_page_json(cls, ms_session):
        viewing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        viewed_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('viewed_user_id'))
        cls.is_allowed_to_use(viewed_user, viewing_user)
        viewed_user_dict = {}
        for col_key in cls._get_col_keys(None):
            viewed_user_dict[col_key] = getattr(viewed_user, col_key)
        return get_json_string(viewed_user_dict)

class user_info_edit_form(BasePage):
    USER_INFO_EDIT_FORM = web.form.Form(
                            web.form.Textbox('email_addr', description=MSGS.lookup('email_addr_label')),
                            web.form.Textbox('username', description=MSGS.lookup('username_label')),
                            web.form.Textarea('user_statement', description=MSGS.lookup('user_statement_blurb'), cols='40', rows='3'),
                            web.form.Button(name=MSGS.lookup('user_info_edit_submit_btn')))
    
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        edited_user = extra_display_info['edited_user']
        if user is None:
            return None
        if user.user_id == edited_user.user_id:
            return MSGS.lookup('my_user_info_edit_form_smry')
        else:
            return MSGS.lookup('other_user_info_edit_form_smry', {'username': edited_user.username})
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return user_info_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, int(web.input().get('edited_user_id')))
        cls.is_allowed_to_use(edited_user, editing_user)
        
        default_input = {'email_addr': edited_user.email_addr, 'username': edited_user.username, 'user_statement': edited_user.user_statement}
        edited_user_id_hidden_html = web.form.Hidden(name='edited_user_id', value=edited_user.user_id).render()
        user_edit_form_html = '%s\n%s' % (edited_user_id_hidden_html, cls.USER_INFO_EDIT_FORM(web.input('edited_user_id', **default_input)).render())
        return cls.wrap_content(RENDER.basic_form_template(user_edit_form_html, 'user_info_edit_form', user_info_edit.build_page_url()), user=editing_user, extra_display_info={'edited_user': edited_user})

class user_info_edit(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.ALTER_USER_INFO_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, int(web.input().get('edited_user_id')))
        cls.is_allowed_to_use(edited_user, editing_user)
        
        encountered_update_error = False
        try:
            edited_user.set_and_save_user_info(PGDB, util.empty_str_to_none(web.input().get('username')), web.input().get('email_addr'), web.input().get('user_statement'), editing_user.user_id)
        except:
            encountered_update_error = True
        
        return (edited_user, encountered_update_error)
        
    @classmethod
    def render_page_full_html(cls, ms_session):
        edited_user, encountered_update_error = cls._render_page_helper(ms_session)
        web.found(user_view.build_page_url(query_params={'viewed_user_id': edited_user.user_id}))
    
    @classmethod
    def render_page_json(cls, ms_session):
        edited_user, encountered_update_error = cls._render_page_helper(ms_session)
        return get_json_string({'encountered_update_error': encountered_update_error})

class user_change_pass_form(BasePage):
    USER_CHANGE_PASS_FORM = web.form.Form(
                            web.form.Password('editing_user_cleartext_password', description=MSGS.lookup('confirm_password_label')),
                            web.form.Password('cleartext_password_1', description=MSGS.lookup('new_password_label')),
                            web.form.Password('cleartext_password_2', description=MSGS.lookup('reenter_password_label')),
                            web.form.Button(name=MSGS.lookup('user_change_password_submit_btn')))
    
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        edited_user = extra_display_info['edited_user']
        if user is None:
            return None
        if user.user_id == edited_user.user_id:
            return MSGS.lookup('my_user_change_pass_form_smry')
        else:
            return MSGS.lookup('other_user_change_pass_form_smry', {'username': edited_user.username})
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return user_change_pass.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, int(web.input().get('edited_user_id')))
        
        cls.is_allowed_to_use(edited_user, editing_user)
        
        edited_user_id_hidden_html = web.form.Hidden(name='edited_user_id', value=edited_user.user_id).render()
        user_change_pass_form_html = '%s\n%s' % (edited_user_id_hidden_html, cls.USER_CHANGE_PASS_FORM(web.input('edited_user_id')).render())
        return cls.wrap_content(RENDER.basic_form_template(user_change_pass_form_html, 'user_change_pass_form', user_change_pass.build_page_url()), user=editing_user, extra_display_info={'edited_user': edited_user})

class user_change_pass(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.ALTER_USER_INFO_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, int(web.input().get('edited_user_id')))
        
        cls.is_allowed_to_use(edited_user, editing_user)
        
        editing_user_current_password = web.input().get('editing_user_cleartext_password')
        cleartext_password_1 = web.input().get('cleartext_password_1')
        cleartext_password_2 = web.input().get('cleartext_password_2')
        
        ret_val = {'encountered_update_error': False}
        
        if not editing_user.check_password_audited(PGDB, editing_user_current_password):
            ret_val['encountered_update_error'] = True
            ret_val['error_msg'] = MSGS.lookup('password_check_failed')
        elif cleartext_password_1 != cleartext_password_2:
            ret_val['encountered_update_error'] = True
            ret_val['error_msg'] = MSGS.lookup('password_mismatch_error')
        else:
            edited_user.set_and_save_encrypted_password(PGDB, cleartext_password_1, editing_user.user_id)
        
        return (ret_val, editing_user, edited_user)
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        change_pass_result, editing_user, edited_user = cls._render_page_helper(ms_session)
        if change_pass_result['encountered_update_error'] == False:
            web.found(user_view.build_page_url(query_params={'viewed_user_id': edited_user.user_id}))
        else:
            return cls.wrap_content(change_pass_result['error_msg'], user=editing_user)
    
    @classmethod
    def render_page_json(cls, ms_session):
        change_pass_result, editing_user, edited_user = cls._render_page_helper(ms_session)
        return get_json_string(change_pass_result)

class NodespaceList(BasePage, ListTablePage):
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['nodespace_name_link', 'nodespace_description']
    
    @classmethod
    def _get_display_row(cls, query_row):
        nodespace_name_link = util.a_elt(web.websafe(query_row.nodespace_name), nodespace_view.build_page_url(query_params={'nodespace_id':query_row.nodespace_id}))
        return {'nodespace_name_link': nodespace_name_link, 'nodespace_description': web.websafe(query_row.nodespace_description)}
    
    @classmethod
    def render_page_is_allowed_to_use(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        ret_val = {'is_allowed_to_use': cls.is_allowed_to_use(None, user, should_raise_insufficient_priv_ex=False)}
        return get_json_string(ret_val)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        cls.is_allowed_to_use(None, user)
        nodespaces = cls.get_nodespaces(PGDB, user)
        return user, nodespaces
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        user, nodespaces = cls._render_page_helper(ms_session)
        page_content = cls.basic_table_content(nodespaces) if len(nodespaces) > 0 else ''
        return cls.wrap_content(page_content, user=user)
    
    @classmethod
    def render_page_json(cls, ms_session):
        user, nodespaces = cls._render_page_helper(ms_session)
        nodespaces_dict_list = [{'nodespace_name': ns.nodespace_name, 
                                            'nodespace_description': ns.nodespace_description,
                                            'nodespace_id': ns.nodespace_id} for ns in nodespaces]
        return get_json_string(nodespaces_dict_list)

class nodespace_list_accessible(NodespaceList):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return True
    
    @classmethod
    def get_nodespaces(cls, PGDB, user):
        return tc.Nodespace.get_accessible_nodespaces_by_user_id(PGDB, user.user_id)

class nodespace_list_all(NodespaceList):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.LIST_ALL_SPACES_ACTION, None, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def get_nodespaces(cls, PGDB, user):
        return tc.Nodespace.get_all_nodespaces(PGDB)

class user_list_nodespace(BasePage, ListTablePage):
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        if user is None:
            return None
        return MSGS.lookup('user_list_nodespace_smry', {'nodespace_name': extra_display_info['nodespace'].nodespace_name})
    
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['username', 'nodespace_privileges', 'is_enabled_for_ns', 'is_enabled_for_ms']
    
    @classmethod
    def _get_display_row(cls, query_row):
        display_row = query_row.copy()
        user_view_url = user_view.build_page_url(query_params={'viewed_user_id': display_row['user_id']})
        display_row['username'] = util.a_elt(web.websafe(display_row['username']), user_view_url)
        if display_row['should_have_ns_access_edit_link']:
            ns_access_edit_url = nodespace_access_edit_form.build_page_url(query_params={'edited_user_id': display_row['user_id'],
                                                                                         'nodespace_id': display_row['nodespace_id']})
            display_row['nodespace_privileges'] = util.a_elt(display_row['nodespace_privileges'], ns_access_edit_url)
        return display_row
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.ALTER_NODESPACE_ACCESS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        nodespace_id = web.input().get('nodespace_id')
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, nodespace_id) if nodespace_id is not None else None
        cls.is_allowed_to_use(nodespace, user)
        
        user_list = tc.User.get_user_and_access_info_by_nodespace_id(PGDB, nodespace_id)
        return (user, nodespace, user_list)
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        user, nodespace, user_list = cls._render_page_helper(ms_session)
        
        extra_display_info = {'nodespace': nodespace}
        should_have_ns_access_edit_links = nodespace_access_edit_form.is_allowed_to_use(nodespace, user, False)
        for user_row in user_list:
            user_row['should_have_ns_access_edit_link'] = should_have_ns_access_edit_links
        
        return cls.wrap_content(cls.basic_table_content(user_list), user=user, extra_display_info=extra_display_info)
    
    @classmethod
    def render_page_json(cls, ms_session):
        user, nodespace, user_list = cls._render_page_helper(ms_session)
        return get_json_string(user_list)

class user_list_nodespace_absent(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.LIST_ALL_USERS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page_json(cls, ms_session):
        nodespace_id = web.input().get('nodespace_id')
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        cls.is_allowed_to_use(None, user)
        
        user_list = tc.User.get_users_absent_from_nodespace(PGDB, nodespace_id)
        return get_json_string([{'user_id': user.user_id, 'username': user.username, 'email_addr': user.email_addr,  
                                'user_statement': user.user_statement, 'is_enabled': user.is_enabled} for user in user_list])

class user_list_all(BasePage, ListTablePage):
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['username', 'email_addr', 'user_statement', 'metaspace_privileges', 'is_enabled', 'creator', 'creation_date', 'modifier', 'modification_date']
    
    @classmethod
    def _get_display_row(cls, table_data_row):
        ret_val = table_data_row.__dict__.copy()
        for key in ['email_addr', 'user_statement']:
            ret_val[key] = web.websafe(ret_val[key])
        ret_val['username'] = util.a_elt(web.websafe(ret_val['username']), user_view.build_page_url(query_params={'viewed_user_id': ret_val['user_id']}))
        return ret_val
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.LIST_ALL_USERS_ACTION, None, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _get_user_list(cls, viewing_user):
        cls.is_allowed_to_use(None, viewing_user)
        return tc.User.get_all_users(PGDB)
    
    @classmethod
    def render_page_is_allowed_to_use(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        ret_val = {'is_allowed_to_use': cls.is_allowed_to_use(None, user, should_raise_insufficient_priv_ex=False)}
        return get_json_string(ret_val)
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        viewing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        user_list = cls._get_user_list(viewing_user)
        return cls.wrap_content(cls.basic_table_content(user_list), user=viewing_user)
    
    @classmethod
    def render_page_json(cls, ms_session):
        viewing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        users = cls._get_user_list(viewing_user)
        user_dict_list = [{'user_id': user.user_id, 'username': user.username, 'email_addr': user.email_addr, 
                            'user_statement': user.user_statement, 'metaspace_privileges': user.metaspace_privileges,
                            'is_enabled': user.is_enabled, 'creator': user.creator, 'creation_date': user.creation_date,
                            'modifier': user.modifier, 'modification_date': user.modification_date} for user in users]
        return get_json_string(user_dict_list)

class metaspace_access_edit_form(BasePage, PrivilegesEditForm):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return metaspace_access_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        if user is None:
            return None
        return MSGS.lookup('metaspace_access_edit_form_smry', {'username': extra_display_info['edited_user'].username})
    
    @classmethod
    def _get_grantable_privileges(cls, editing_user):
        return editing_user.metaspace_privileges.get_grantable_privileges()
    
    @classmethod
    def get_ms_priv_edit_form(cls, edited_user, editing_user):
        grantable_privileges = cls._get_grantable_privileges(editing_user)
        selected_privileges = edited_user.metaspace_privileges
        is_enabled_radio_opts = [(True, MSGS.lookup('ms_enabled_desc')), (False, MSGS.lookup('ms_disabled_desc'))]
        return web.form.Form(*(cls.metaspace_privilege_select_elts(grantable_privileges=grantable_privileges, selected_privileges=selected_privileges) +
                            [web.form.Radio('is_enabled', is_enabled_radio_opts, value=edited_user.is_enabled, description=MSGS.lookup('user_is_enabled')),
                             web.form.Button(name=MSGS.lookup('update_ms_privs_submit_btn'))]))
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        cls.is_allowed_to_use(edited_user, editing_user)
        return editing_user, edited_user
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        editing_user, edited_user = cls._render_page_helper(ms_session)
        edited_user_id_hidden_html = web.form.Hidden(name='edited_user_id', value=edited_user.user_id).render()
        ms_priv_edit_form_html = '%s\n%s' % (edited_user_id_hidden_html, cls.get_ms_priv_edit_form(edited_user, editing_user)().render())
        return cls.wrap_content(RENDER.basic_form_template(ms_priv_edit_form_html, 'ms_priv_edit_form', metaspace_access_edit.build_page_url()), user=editing_user, extra_display_info={'edited_user': edited_user})
    
    @classmethod
    def render_page_json(cls, ms_session):
        editing_user, edited_user = cls._render_page_helper(ms_session)
        grantable_privileges = sorted(cls._get_grantable_privileges(editing_user), tc.MetaspacePrivilegeSet.comparator)
        current_privileges = list(edited_user.metaspace_privileges)
        is_enabled = edited_user.is_enabled
        return get_json_string({'grantable_privileges': grantable_privileges, 'current_privileges': current_privileges, 'is_enabled': is_enabled})

class metaspace_access_edit(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.ALTER_USER_ACCESS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        cls.is_allowed_to_use(edited_user, editing_user)
        
        new_metaspace_privileges = tc.MetaspacePrivilegeSet.create_from_list_of_strings(web.input(metaspace_privileges=[]).get('metaspace_privileges'))
        edited_user.set_and_save_metaspace_access(PGDB, web.input().get('is_enabled'), new_metaspace_privileges, editing_user.user_id)
        
        return edited_user
        
    @classmethod
    def render_page_full_html(cls, ms_session):
        edited_user = cls._render_page_helper(ms_session)
        web.found(user_view.build_page_url(query_params={'viewed_user_id': edited_user.user_id}))
    
    @classmethod
    def render_page_json(cls, ms_session):
        edited_user = cls._render_page_helper(ms_session)
        return get_json_string({'encountered_update_error': False, 'status_message': ''})

class nodespace_access_edit_form(BasePage, PrivilegesEditForm):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_access_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _get_grantable_privileges(cls, nodespace, user):
        ns_access_for_user = nodespace.get_nodespace_access_for_user(PGDB, user.user_id)
        grantable_privileges = (ns_access_for_user.nodespace_privileges if ns_access_for_user is not None else tc.NodespacePrivilegeSet()).get_grantable_privileges()
        return grantable_privileges
    
    @classmethod
    def _get_content_summary(cls, user, extra_display_info):
        if user is None:
            return None
        
        nodespace = extra_display_info['nodespace']
        edited_user = extra_display_info['edited_user']
        return MSGS.lookup('nodespace_access_edit_form_smry', {'nodespace_name': nodespace.nodespace_name, 'username': edited_user.username})
    
    @classmethod
    def get_ns_priv_edit_form(cls, edited_user, editing_user, nodespace):
        grantable_privileges = cls._get_grantable_privileges(nodespace, editing_user)
        cur_access = tc.NodespaceAccessEntry.get_existing_access_entry(PGDB, nodespace.nodespace_id, edited_user.user_id)
        selected_privs = cur_access.nodespace_privileges
        is_enabled_radio_opts = [(True, MSGS.lookup('ns_enabled_desc')), (False, MSGS.lookup('ns_disabled_desc'))]
        return web.form.Form(*(cls.nodespace_privilege_select_elts(grantable_privileges=grantable_privileges, selected_privileges=selected_privs) +
                            [web.form.Radio('is_enabled', is_enabled_radio_opts, value=cur_access.is_enabled, description=MSGS.lookup('user_is_enabled')),
                             web.form.Button(name=MSGS.lookup('update_ns_privs_submit_btn'))]))
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        nodespace_id = web.input().get('nodespace_id')
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, nodespace_id)
        cls.is_allowed_to_use(edited_user, editing_user)
        
        return (editing_user, edited_user, nodespace)
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        editing_user, edited_user, nodespace = cls._render_page_helper(ms_session)
        
        edited_user_id_hidden_html = web.form.Hidden(name='edited_user_id', value=edited_user.user_id).render()
        nodespace_id_hidden_html = web.form.Hidden(name='nodespace_id', value=nodespace.nodespace_id).render()
        ns_priv_edit_form_html = '%s\n%s\n%s' % (nodespace_id_hidden_html, edited_user_id_hidden_html, cls.get_ns_priv_edit_form(edited_user, editing_user, nodespace)().render())
        extra_display_info = {'nodespace': nodespace, 'edited_user': edited_user}
        
        return cls.wrap_content(RENDER.basic_form_template(ns_priv_edit_form_html, 'ns_priv_edit_form', nodespace_access_edit.build_page_url()), user=editing_user, extra_display_info=extra_display_info)
    
    @classmethod
    def render_page_json(cls, ms_session):
        editing_user, edited_user, nodespace = cls._render_page_helper(ms_session)
        
        grantable_privileges = cls._get_grantable_privileges(nodespace, editing_user)
        grantable_privileges = sorted(grantable_privileges, tc.NodespacePrivilegeSet.comparator)
        cur_access = tc.NodespaceAccessEntry.get_existing_access_entry(PGDB, nodespace.nodespace_id, edited_user.user_id)
        current_privileges = list(cur_access.nodespace_privileges)
        is_enabled = cur_access.is_enabled
        
        return get_json_string({'grantable_privileges': grantable_privileges, 'current_privileges': current_privileges, 'is_enabled': is_enabled})

class nodespace_access_edit(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.ALTER_NODESPACE_ACCESS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _render_page_helper(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        nodespace_id = web.input().get('nodespace_id')
        cls.is_allowed_to_use(edited_user, editing_user)
        
        new_nodespace_privileges = tc.NodespacePrivilegeSet.create_from_list_of_strings(web.input(nodespace_privileges=[]).get('nodespace_privileges'))
        is_enabled = web.input().get('is_enabled')
        
        cur_nodespace_access = tc.NodespaceAccessEntry.get_existing_access_entry(PGDB, nodespace_id, edited_user.user_id)
        cur_nodespace_access.set_and_save_access_entry(PGDB, new_nodespace_privileges, is_enabled, editing_user.user_id)
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        cls._render_page_helper(ms_session)
        nodespace_id = web.input().get('nodespace_id')
        web.found(user_list_nodespace.build_page_url(query_params={'nodespace_id': nodespace_id}))
    
    @classmethod
    def render_page_json(cls, ms_session):
        try:
            cls._render_page_helper(ms_session)
            encountered_update_error = False
            status_message = MSGS.lookup('nodespace_access_update_success_blurb')
        except:
            encountered_update_error = True
            status_message = MSGS.lookup('nodespace_access_update_failure_blurb')
        return get_json_string({'encountered_update_error': encountered_update_error, 'status_message': status_message})

#TODO: centralize the repeated stuff between access edit and access revoke
class nodespace_access_revoke(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_access_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page_json(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        nodespace_id = web.input().get('nodespace_id')
        cls.is_allowed_to_use(edited_user, editing_user)
        
        cur_nodespace_access = tc.NodespaceAccessEntry.get_existing_access_entry(PGDB, nodespace_id, edited_user.user_id)
        cur_nodespace_access.revoke_access_entry(PGDB)
        status_message = MSGS.lookup('nodespace_access_revoke_success_blurb')
        
        return get_json_string({'encountered_update_error': False, 'status_message': status_message})

class nodespace_access_grant(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.GRANT_NODESPACE_ACCESS_SANS_INV_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page_json(cls, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        nodespace_id = web.input().get('nodespace_id')
        cls.is_allowed_to_use(edited_user, editing_user)
        
        nodespace_privileges = tc.NodespacePrivilegeSet.create_from_list_of_strings(web.input(nodespace_privileges=[]).get('nodespace_privileges'))
        tc.NodespaceAccessEntry.create_new_access_entry(PGDB, nodespace_id, nodespace_privileges, edited_user.user_id, editing_user.user_id, None)
        status_message = MSGS.lookup('nodespace_access_grant_success_blurb')
        
        return get_json_string({'encountered_update_error': False, 'status_message': status_message})

class metaspace_command_list(BasePage, ListTablePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.VIEW_METASPACE_COMMANDS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def _get_col_keys(cls, table_data):
        return table_data[0].keys()
    
    @classmethod
    def _get_display_row(cls, table_data_row):
        return table_data_row
    
    @classmethod
    def render_page_is_allowed_to_use(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        ret_val = {'is_allowed_to_use': cls.is_allowed_to_use(None, user, should_raise_insufficient_priv_ex=False)}
        return get_json_string(ret_val)
    
    @classmethod
    def render_page_full_html(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        cls.is_allowed_to_use(None, user)
        
        cmd_list = []
        for page_class in [nodespace_create_form, user_invitation_create_form, nodespace_list_all, user_list_all]:
            if page_class.is_allowed_to_use(None, user, should_raise_insufficient_priv_ex=False):
                page_name = page_class.get_page_name()
                page_url = page_class.build_page_url()
                cmd_list.append({'cmd_link': util.a_elt(link_text=page_name, href_att_val=page_url)})
        
        return cls.wrap_content(cls.basic_table_content(cmd_list), user=user)

class GraphViewPage(object):
    #TODO: have central method for converting a given node/edge type dict into json for inclusion in larger json object for display.  build_cat_tree_json
    # can call that conversion method for each node/edge.  for now, stylesheet can probably apply to all graph types if each node/edge type is styled the same
    # in all graphs.
    @classmethod
    def _get_cytoscape_node_dict(cls, adhoc_node_dict):
        cs_node_dict = {'group': 'nodes', 
                        'data': {'id': 'n%s'%adhoc_node_dict['node_id'], 
                                 'node_type': adhoc_node_dict['node_type']}}

        if adhoc_node_dict['node_type'] == tc.CategoryNode.NODE_TYPE:
            cs_node_dict['data']['disp_text'] = web.websafe(adhoc_node_dict['node_properties'][tc.CategoryNode.CAT_NAME_FIELD_NAME])
        elif adhoc_node_dict['node_type'] == tc.WriteupNode.NODE_TYPE:
            cs_node_dict['data']['disp_text'] = web.websafe(adhoc_node_dict['node_properties'][tc.WriteupNode.WRITEUP_TITLE_FIELD_NAME])
        
        return cs_node_dict
    
    @classmethod
    def _get_cytoscape_edge_dict(cls, adhoc_edge_dict):
        cs_edge_dict = {'group': 'edges', 
                        'data': {'id': 'e%s'%adhoc_edge_dict['edge_id'], 
                                        'source': 'n%s'%adhoc_edge_dict['source'], 
                                        'target': 'n%s'%adhoc_edge_dict['target']}}
        return cs_edge_dict
    
    @classmethod
    def build_cat_tree_json(cls, cat_tree_dict):
        node_list, edge_list = [], []
        for node_id in cat_tree_dict['nodes']:
            node = cat_tree_dict['nodes'][node_id]
            node_list.append(cls._get_cytoscape_node_dict(node))
        for edge_id in cat_tree_dict['edges']:
            edge = cat_tree_dict['edges'][edge_id]
            edge_list.append(cls._get_cytoscape_edge_dict(edge))
        
        return get_json_string(node_list + edge_list)

class category_list(BasePage, GraphViewPage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.VIEW_NODESPACE_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        cls.is_allowed_to_use(nodespace, user)
        
        cat_tree_info = tc.AdhocNeoQueries.get_nodespace_categories(NEODB, nodespace.nodespace_id)
        cat_tree_json = cls.build_cat_tree_json(cat_tree_info)
        return cls.wrap_content(RENDER.view_graph_template(cat_tree_json), user=user)

class nodespace_overview(BasePage, GraphViewPage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.VIEW_NODESPACE_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page_json(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        cls.is_allowed_to_use(nodespace, user)
        
        overview_graph_info = tc.AdhocNeoQueries.get_nodespace_categories_and_writeups(NEODB, nodespace.nodespace_id)
        overview_graph_json = cls.build_cat_tree_json(overview_graph_info)
        return overview_graph_json

    @classmethod
    def render_page_full_html(cls, ms_session):
        overview_graph_json = cls.render_page_json(ms_session)
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        return cls.wrap_content(RENDER.view_graph_template(overview_graph_json), user=user)

class nga(BasePage):
    @classmethod
    def _get_header_links(cls, user, extra_display_info):
        if user is None:
            return None
        return [{'url': logout.build_page_url(), 'display_text': MSGS.lookup('logout_link_disp_txt')}]
    
    @classmethod
    def render_page(cls, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        return cls.render_angular_app(user=user)

class get_locale_messages(BasePage):
    JSON_ASSIGNED_MODE = 'json_assigned'
    
    @classmethod
    def get_page_render_fn(cls, page_mode):
        if page_mode == cls.JSON_ASSIGNED_MODE:
            return cls.render_page_json_assigned
        
        return super(cls, cls).get_page_render_fn(page_mode)
        
    @classmethod
    def render_page_json(cls, ms_session):
        msgs_dict = MSGS.TRANSLATION_LOCALES
        return get_json_string(msgs_dict)
    
    @classmethod
    def render_page_json_assigned(cls, ms_session):
        js_var_name = web.input().get('js_var_name');
        return "%s = %s;" % (js_var_name, cls.render_page_json(ms_session))



'''
TODO:
nodespace overview.  can show:
    categories
    categories and writeups
    categories and writeups and comment thread heads
    saved search (watched nodes, etc)
click on a node and see:
    node contents
    commands for operating on node (availability based on perms):
        category: edit, delete, add child cat, add writeup, recategorize (new parent)
        writeup: edit, delete, comment on, recategorize
        comment: edit, delete, reply
'''

class writeup_list(BasePage):
    pass

class comment_thread_list(BasePage):
    pass

class comment_thread_view(BasePage):
    pass

class category_view(BasePage):
    pass

class comment_view(BasePage):
    pass

class writeup_view(BasePage):
    pass

class comment_create_form(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.CREATE_COMMENT_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def render_page(cls, ms_session):
        pass

class comment_reply_form(BasePage):
    pass

class comment_edit_form(BasePage):
    pass

class writeup_create_form(BasePage):
    pass

class writeup_edit_form(BasePage):
    pass
    


"""
web.py (via the call to web.application) wants a urls tuple of the form:
urls = (
    login_form.build_page_url(None, False),     login_form,
    login_verify.build_page_url(None, False),   login_verify,
    '/tripel/page_class',                       page_class
)

so build it from a list of page classes since the pages can each generate their own URL anyway.
"""
page_classes = [login_form, login_verify, logout, auth_status, 
                nodespace_create_form, nodespace_create, nodespace_view, nodespace_edit_form, nodespace_edit,
                user_invitation_create_form, user_invitation_create, user_invitation_decide_form, user_invitation_decide, 
                nodespace_invitation_create_form, nodespace_invitation_create, nodespace_invitation_decide_form, nodespace_invitation_decide, 
                nodespace_access_view, user_view, user_info_edit_form, user_info_edit, user_change_pass_form, user_change_pass,
                nodespace_list_accessible, nodespace_list_all, user_list_nodespace, user_list_nodespace_absent, user_list_all, 
                metaspace_access_edit_form, metaspace_access_edit, 
                nodespace_access_edit_form, nodespace_access_edit, nodespace_access_revoke, nodespace_access_grant, metaspace_command_list,
                category_list, nodespace_overview, writeup_list, comment_thread_list,
                comment_create_form, comment_reply_form, comment_edit_form, writeup_create_form, writeup_edit_form,
                nga, get_locale_messages]

urls_list = []
for cls in page_classes:
    urls_list.append(cls.build_page_url(None, False))
    urls_list.append(cls)

urls = tuple(urls_list)

web.config.debug = params.WEB_PY_DEBUG

app = web.application(urls, globals())
application = app.wsgifunc()
