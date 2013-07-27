"""
TODO:
* display in UTC by default.  but since timestamp has TZ info, should really make disp TZ a user pref applied to query results.
 * actually, the reason you're seeing PST offsets in the current web UI is likely the way PG is returning date 
  fields.  still, date fields should be init'ed to datetime objs from query results, and those objs should be run through
  formatting before display (i.e. don't dump raw PG output).
"""

import re
import urllib
import json

import web

import tripel_core as tc
import config.parameters as params
import util



RENDER = web.template.render(params.TEMPLATE_DIR)

PGDB = tc.PgUtil.get_db_conn_ssl(params.PG_DBNAME, params.PG_USERNAME, util.get_file_contents(params.PG_PASS_FILENAME))
NEODB = tc.NeoUtil.get_db_conn()
DB_TUPLE = (PGDB, NEODB)

MS_PRVLG_CHKR = tc.MetaspacePrivilegeChecker
NS_PRVLG_CHKR = tc.NodespacePrivilegeChecker

util.init_web_config_mail_params()


def build_url_path(subpath):
    return util.build_url_path(params.APP_DEPLOYMENT_PATH, subpath)

def build_url(path):
    return util.build_url(params.SERVER_HOSTNAME, path)


def privilege_select_elts(field_name, grantable_privileges, selected_privileges=tc.PrivilegeSet()):
    priv_entries = []
    for priv in grantable_privileges:
        priv_title = util.msg_lookup('%s_priv_title' % priv)
        priv_desc = util.msg_lookup('%s_priv_desc' % priv)
        priv_checkbox = web.form.Checkbox(field_name, value=priv, description='%s: %s' % (priv_title, priv_desc), checked=(selected_privileges.has_privilege(priv)))
        priv_entries.append(priv_checkbox)
    
    return priv_entries

def metaspace_privilege_select_elts(field_name='metaspace_privileges', grantable_privileges=None, selected_privileges=tc.MetaspacePrivilegeSet()):
    cmp = tc.MetaspacePrivilegeSet.comparator
    return privilege_select_elts(field_name, sorted(grantable_privileges, cmp), selected_privileges)

def nodespace_privilege_select_elts(field_name='nodespace_privileges', grantable_privileges=None, selected_privileges=tc.NodespacePrivilegeSet()):
    cmp = tc.NodespacePrivilegeSet.comparator
    return privilege_select_elts(field_name, sorted(grantable_privileges, cmp), selected_privileges)


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


#TODO: you should either start referring to things like ms_session as instance vars (via self.) instead of passing 
# them around, or you should make everything into classmethods.  either way, things that don't actually avail themselves
# of the instantiated-ness of instance methods should be turned into classmethods.
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
        return util.msg_lookup('%s_page_name' % cls.__name__)
    
    @classmethod
    def get_page_title(cls):
        return '%s: %s' % (util.msg_lookup('instance_name'), cls.get_page_name())
    
    @classmethod
    def _get_header_links(cls, user):
        if user is None:
            return None
        return [{'url': user_info_edit_form.build_page_url(query_params={'edited_user_id': user.user_id}), 'display_text': util.msg_lookup('edit_usr_link_disp_txt')},
                {'url': user_change_pass_form.build_page_url(query_params={'edited_user_id': user.user_id}), 'display_text': util.msg_lookup('passwd_link_disp_txt')},
                {'url': logout.build_page_url(), 'display_text': util.msg_lookup('logout_link_disp_txt')}]
    
    @classmethod
    def _get_nav_links(cls, user):
        if user is None:
            return None
        
        ret_val = []
        if metaspace_command_list.is_allowed_to_use(None, user, False):
            ret_val.append({'url': metaspace_command_list.build_page_url(), 'display_text': metaspace_command_list.get_page_name()})
        ret_val.append({'url': nodespace_list_accessible.build_page_url(), 'display_text': util.msg_lookup('accessible_nodespaces_link_disp_txt', {'username': user.username})})
        
        return ret_val
    
    @classmethod
    def _get_command_links(cls, user):
        return None
    
    @classmethod
    def _get_content_summary(cls, user):
        return util.msg_lookup('%s_smry' % cls.__name__)
    
    def wrap_content(self, content, ms_session=None, user=None):
        if user is None and ms_session is not None and ms_session.is_session_valid():
            user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        
        hdr_links = self._get_header_links(user)
        nav_links = self._get_nav_links(user)
        cmd_links = self._get_command_links(user)
        content_summary = self._get_content_summary(user)
        return RENDER.outer_wrapper(self.get_page_title(), content_summary, content, util.msg_lookup, hdr_links, nav_links, cmd_links)
    
    def render_angular_app(self, ms_session=None, user=None):
        if user is None and ms_session is not None and ms_session.is_session_valid():
            user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        
        hdr_links = self._get_header_links(user)
        return RENDER.nga(self.get_page_title(), util.msg_lookup, hdr_links)
    
    def render_input_forwarding_form(self, forwarding_form_action=None, forwarding_target=None):
        forwarded_fields = [web.form.Hidden(name=k, value=v) for k, v in web.input().items() if k not in ['login_username', 'login_password', 'Login']]
        #TODO: null out forwarding_target if it's not pointing to something in the site
        if forwarding_target is not None:
            forwarded_fields.append(web.form.Hidden(name='forwarding_target', value=forwarding_target))
        forwarding_form = web.form.Form(*forwarded_fields)
        if forwarding_form_action is not None:
            return self.wrap_content(RENDER.basic_form_template(forwarding_form.render(), 'forwarding_form', forwarding_form_action, True))
        else:
            return forwarding_form.render()
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        raise NotImplementedError('subclass must implement this')
    
    def GET(self):
        if self.CAN_GET_PAGE:
            return self.check_session_and_render_page()
        else:
            web.nomethod()
    
    def POST(self):
        if self.CAN_POST_PAGE:
            return self.check_session_and_render_page()
        else:
            web.nomethod()

    def check_session_and_render_page(self):
        ms_session = get_session_from_cookie(PGDB)
        if self.REQUIRES_VALID_SESSION and (ms_session is None or not ms_session.is_session_valid()):
            return self.render_input_forwarding_form(login_form.build_page_url(), build_url(web.ctx.path))
        else:
            if ms_session is not None and ms_session.is_session_valid():
                ms_session.touch_session(PGDB)
            
            try:
                return self.render_page(ms_session)
            except tc.PrivilegeChecker.InsufficientPrivilegesException:
                web.forbidden()
            except tc.User.TooManyBadPasswordsException:
                kill_session_and_cookie(PGDB, ms_session)
                web.found(login_form.build_page_url())
    
    def get_page_render_fn(self, page_mode):
        if page_mode == self.FULL_HTML_MODE:
            return self.render_page_full_html
        elif page_mode == self.CHECK_IS_ALLOWED_TO_USE_MODE:
            return self.render_page_is_allowed_to_use
        elif page_mode == self.JSON_MODE:
            return self.render_page_json
        elif page_mode == self.NO_WRAPPER_HTML_MODE:
            return self.render_page_no_wrapper_html
        
        return None
    
    #TODO: eventually, none of the subclasses will implement render_page anymore, they'll 
    # implement the specific rendering functions mapped to page_mode values by get_page_render_fn.
    # subclass may also extend get_page_render_fn if supporting non-standard modes.
    def render_page(self, ms_session):
        page_mode = web.input(modeselektion=self.FULL_HTML_MODE).get('modeselektion')
        page_render_fn = self.get_page_render_fn(page_mode)
        
        # i'm not sure if this is actually an appropriate use of the 412 response code, since the RFC 
        # indicated that it should be used based on what the request headers indicate (and this response is 
        # based on a request parameter).  regardless, clients should ideally not encounter this anyway.
        if page_render_fn is None:
            raise web.preconditionfailed('unsupported page_mode')
        
        return page_render_fn(ms_session)
    
    def render_page_is_allowed_to_use(self, ms_session):
        raise NotImplementedError('must be implemented by subclass')
    
    def render_page_full_html(self, ms_session):
        raise NotImplementedError('must be implemented by subclass')
    
    def render_page_json(self, ms_session):
        raise NotImplementedError('must be implemented by subclass')
    
    def render_page_no_wrapper_html(self, ms_session):
        raise NotImplementedError('must be implemented by subclass')

class ListTablePage(object):
    @classmethod
    def _get_col_keys(cls, table_data):
        return table_data[0].__dict__.keys()
    
    @classmethod
    def _get_table_headers(cls, table_data):
        return map(lambda x: util.msg_lookup('%s_col_hdr' % x), cls._get_col_keys(table_data))
    
    @classmethod
    def _get_display_row(cls, table_data_row):
        return util.get_websafe_dict_copy(table_data_row.__dict__)
    
    def _table_data_to_basic_table_template_input(self, table_data):
        if table_data is None or len(table_data) == 0:
            return [None, None, None]
        table_rows = map(self._get_display_row, table_data)
        return [self._get_col_keys(table_data), self._get_table_headers(table_data), table_rows]
    
    def basic_table_content(self, table_data):
        return RENDER.basic_table_template(*self._table_data_to_basic_table_template_input(table_data))

class login_form(BasePage):
    REQUIRES_VALID_SESSION = False
    
    LOGIN_FORM = web.form.Form(
                    web.form.Textbox(name='login_username', description=util.msg_lookup('username_label')),
                    web.form.Password(name='login_password', description=util.msg_lookup('password_label')),
                    web.form.Button(name=util.msg_lookup('login_submit_btn')))
    
    def render_page(self, ms_session):
        login_form_html = self.LOGIN_FORM(web.input()).render()
        if web.input().get('forwarding_target') is not None:
            login_form_html = '%s%s' % (login_form_html, self.render_input_forwarding_form())
        return self.wrap_content(RENDER.basic_form_template(login_form_html, 'login_form', login_verify.build_page_url()))

class login_verify(BasePage):
    CAN_GET_PAGE = False
    REQUIRES_VALID_SESSION = False
    
    @classmethod
    def create_session_and_set_cookie(cls, pgdb, user_id):
        ms_session = tc.MetaspaceSession.force_create_new_session(pgdb, user_id)
        web.setcookie(params.SESSION_ID_COOKIE_NAME, ms_session.metaspace_session_id, expires='', domain=None, secure=True)
        return ms_session
    
    def render_page(self, ms_session):
        username = web.input().get('login_username')
        cleartext_password = web.input().get('login_password')
        
        has_valid_session = False
        if username is not None and cleartext_password is not None:
            user = tc.User.get_existing_user_by_username(PGDB, username)
            if user is not None and user.check_password_audited(PGDB, cleartext_password, False):
                ms_session = self.create_session_and_set_cookie(PGDB, user.user_id)
                has_valid_session = True

        if web.input().get('forwarding_target') is not None:
            forwarding_form_action = web.input().get('forwarding_target') if has_valid_session else login_form.build_page_url()
            return self.render_input_forwarding_form(forwarding_form_action)
        else:
            web.found(nodespace_list_accessible.build_page_url())

class logout(BasePage):
    REQUIRES_VALID_SESSION = False
    
    def render_page(self, ms_session):
        ms_session = get_session_from_cookie(PGDB)
        kill_session_and_cookie(PGDB, ms_session)
        web.found(login_form.build_page_url())

class auth_status(BasePage, ListTablePage):
    REQUIRES_VALID_SESSION = False
    
    def render_page(self, ms_session):
        has_valid_session = (ms_session is not None) and ms_session.is_session_valid()
        output_html = util.msg_lookup('auth_status_text', {'has_valid_session': has_valid_session})
        if ms_session is not None:
            output_html = '<p>%s</p><p>%s</p>' % (output_html, self.basic_table_content([ms_session]))
        return self.wrap_content(output_html, ms_session=ms_session)

class NodespaceForm(object):
    @classmethod
    def get_nodespace_form(cls, btn_content_key):
        return web.form.Form(web.form.Textbox('nodespace_name', 
                                                web.form.Validator(util.msg_lookup('invalid_ns_name'), lambda x: tc.Nodespace.is_valid_nodespace_name(x)),
                                                description=util.msg_lookup('create_ns_form_nsname')),
                                web.form.Textarea('nodespace_description', description=util.msg_lookup('create_ns_form_ns_desc'), cols='40', rows='3'),
                                web.form.Button(name=util.msg_lookup(btn_content_key)))

class nodespace_create_form(BasePage, NodespaceForm):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_create.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.is_allowed_to_use(None, user)
        
        nodespace_create_form_html = self.get_nodespace_form('create_ns_submit_btn')(web.input()).render()
        return self.wrap_content(RENDER.basic_form_template(nodespace_create_form_html, 'nodespace_create_form', nodespace_create.build_page_url()), user=user)

class nodespace_create(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.CREATE_SPACE_ACTION, None, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.is_allowed_to_use(None, user)
        
        nodespace_name = web.input().get('nodespace_name')
        nodespace_description = web.input().get('nodespace_description')
        new_nodespace = None
        if tc.Nodespace.is_valid_nodespace_name(nodespace_name) and tc.Nodespace.get_existing_nodespace(PGDB, nodespace_name) is None:
            new_nodespace = tc.Nodespace.create_new_nodespace(DB_TUPLE, nodespace_name, nodespace_description, user.user_id)
        
        if new_nodespace is not None:
            web.found(nodespace_view.build_page_url(query_params={'nodespace_id': new_nodespace.nodespace_id}))
        else:
            web.found(nodespace_create_form.build_page_url(web.input()))

class nodespace_edit_form(BasePage, NodespaceForm):
    def _get_content_summary(self, user):
        if user is None:
            return None
        return util.msg_lookup('nodespace_edit_form_smry', {'nodespace_name': self.nodespace.nodespace_name})
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        self.is_allowed_to_use(self.nodespace, user)
        
        nodespace_id_hidden_html = web.form.Hidden(name='nodespace_id', value=self.nodespace.nodespace_id).render()
        nodespace_edit_form_html = '%s\n%s' % (nodespace_id_hidden_html, self.get_nodespace_form('edit_ns_submit_btn')(self.nodespace.__dict__).render())
        return self.wrap_content(RENDER.basic_form_template(nodespace_edit_form_html, 'nodespace_edit_form', nodespace_edit.build_page_url()), user=user)

class nodespace_edit(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.ALTER_NODESPACE_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        
        self.is_allowed_to_use(nodespace, user)
        
        nodespace_name = web.input().get('nodespace_name')
        nodespace_description = web.input().get('nodespace_description')
        nodespace.set_and_save_nodespace_settings(PGDB, nodespace_name, nodespace_description, user.user_id)
        
        web.found(nodespace_view.build_page_url(query_params={'nodespace_id':nodespace.nodespace_id}))

class nodespace_view(BasePage, ListTablePage):
    def _get_content_summary(self, user):
        if user is None:
            return None
        return util.msg_lookup('nodespace_view_smry', {'nodespace_name': self.nodespace.nodespace_name})
    
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['nodespace_name', 'nodespace_description', 'creator', 'creation_date', 'modifier', 'modification_date']
    
    def _get_command_links(self, user):
        if user is None:
            return None
        
        ret_val = []
        
        if nodespace_edit_form.is_allowed_to_use(self.nodespace, user, False):
            ns_edit_url = nodespace_edit_form.build_page_url(query_params={'nodespace_id': self.nodespace.nodespace_id})
            ns_edit_disp_txt = util.msg_lookup('edit_nodespace_link_disp_txt', {'nodespace_name': self.nodespace.nodespace_name})
            ret_val.append({'url': ns_edit_url, 'display_text': ns_edit_disp_txt})
        
        if user_list_nodespace.is_allowed_to_use(self.nodespace, user, False):
            user_list_ns_url = user_list_nodespace.build_page_url(query_params={'nodespace_id': self.nodespace.nodespace_id})
            user_list_ns_disp_txt = util.msg_lookup('nodespace_user_list_link_disp_txt', {'nodespace_name': self.nodespace.nodespace_name})
            ret_val.append({'url': user_list_ns_url, 'display_text': user_list_ns_disp_txt})
        
        if nodespace_invite_create_form.is_allowed_to_use(self.nodespace, user, False):
            ns_inv_url = nodespace_invite_create_form.build_page_url(query_params={'nodespace_id': self.nodespace.nodespace_id})
            ns_inv_disp_txt = util.msg_lookup('nodespace_inv_link_disp_txt', {'nodespace_name': self.nodespace.nodespace_name})
            ret_val.append({'url': ns_inv_url, 'display_text': ns_inv_disp_txt})
        
        return ret_val
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace_id = web.input().get('nodespace_id')
        self.nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, nodespace_id)
        return self.wrap_content(self.basic_table_content([self.nodespace]), user=user)

class user_invite_create_form(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return user_invite_create.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def get_ms_inv_create_form(cls, user):
        return web.form.Form(
                            *([web.form.Textbox('invitee_email_addr', description=util.msg_lookup('create_inv_email_addr'))] +
                            metaspace_privilege_select_elts(grantable_privileges=user.metaspace_privileges.get_grantable_privileges()) +
                            [web.form.Textarea('invitation_msg', description=util.msg_lookup('create_ms_inv_msg'), cols='40', rows='3'),
                            web.form.Button(name=util.msg_lookup('create_inv_submit_btn'))]))
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.is_allowed_to_use(None, user)
        
        ms_inv_create_form_html = self.get_ms_inv_create_form(user)().render()
        return self.wrap_content(RENDER.basic_form_template(ms_inv_create_form_html, 'ms_inv_create_form', user_invite_create.build_page_url()), user=user)
        
class user_invite_create(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.CREATE_USER_ACTION, None, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.is_allowed_to_use(None, user)
        
        invitee_email_addr = web.input().get('invitee_email_addr')
        metaspace_privileges = tc.MetaspacePrivilegeSet.create_from_list_of_strings(web.input(metaspace_privileges=[]).get('metaspace_privileges'))
        invitation_msg = web.input().get('invitation_msg')
        ms_inv = tc.MetaspaceInvitation.create_new_invitation(PGDB, None, invitee_email_addr, metaspace_privileges, invitation_msg, user.user_id)
        
        if ms_inv is not None and ms_inv.metaspace_invitation_id is not None:
            ms_inv_link = user_invite_decide_form.build_page_url(query_params={'metaspace_invitation_code': ms_inv.metaspace_invitation_code})
            util.send_metaspace_invitation_email(ms_inv, ms_inv_link)
            status_message = util.msg_lookup('inv_create_success', {'inv_url': ms_inv_link})
        else:
            status_message = util.msg_lookup('inv_create_failure')
            
        return self.wrap_content(status_message, user=user)

class InviteDecideForm(object):
    INV_ACCEPT_FORM = web.form.Form(
                                web.form.Textbox('username', description=util.msg_lookup('username_label')),
                                web.form.Password(name='cleartext_password_1', description=util.msg_lookup('new_password_label')),
                                web.form.Password(name='cleartext_password_2', description=util.msg_lookup('reenter_password_label')),
                                web.form.Textarea('user_statement', description=util.msg_lookup('user_statement_blurb'), cols='40', rows='3'),
                                web.form.Button(name=util.msg_lookup('inv_accept_submit_btn')))
    
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
        return cls.build_single_button_form(form_name, form_target, [ms_inv_code_hidden, ms_inv_decline_hidden], util.msg_lookup('inv_decline_submit_btn'))

class user_invite_decide_form(BasePage, InviteDecideForm):
    REQUIRES_VALID_SESSION = False
        
    def render_page(self, ms_session):
        ms_inv_code = web.input().get('metaspace_invitation_code')
        ms_inv = tc.MetaspaceInvitation.get_existing_invitation(PGDB, ms_inv_code)
        if ms_inv is None or ms_inv.decision_date is not None:
            return self.wrap_content(util.msg_lookup('inv_not_found'))
        
        form_target = user_invite_decide.build_page_url()
        ms_inv_accept_form_html = self.build_accept_form('ms_inv_accept_form', form_target, 'metaspace_invitation_code', ms_inv_code)
        ms_inv_decline_form_html = self.build_decline_form('ms_inv_decline_form', form_target, 'metaspace_invitation_code', ms_inv_code)
        
        ms_inv_decide_header = util.msg_lookup('ms_inv_decide_header', {'inv_code': ms_inv_code, 'invitee_email_addr': ms_inv.invitee_email_addr})
        return self.wrap_content('<p>%s</p>\n <p>%s</p>\n <p>%s</p>\n <p>%s</p> ' % (ms_inv_decide_header, ms_inv.invitation_msg, ms_inv_accept_form_html, ms_inv_decline_form_html))
        
class user_invite_decide(BasePage):
    REQUIRES_VALID_SESSION = False
    
    def render_page(self, ms_session):
        ms_inv_code = web.input().get('metaspace_invitation_code')
        ms_inv = tc.MetaspaceInvitation.get_existing_invitation(PGDB, ms_inv_code)
        if ms_inv is None or ms_inv.decision_date is not None:
            return self.wrap_content(util.msg_lookup('inv_not_found'))

        was_accepted = web.input().get('was_accepted')
        if was_accepted == user_invite_decide_form.DECLINED:
            ms_inv.decline_invitation(PGDB)
            return self.wrap_content(util.msg_lookup('ms_inv_declined_ack', {'inv_code': ms_inv_code}))
        
        username = web.input().get('username')
        user_statement = web.input().get('user_statement')
        cleartext_password_1 = web.input().get('cleartext_password_1')
        cleartext_password_2 = web.input().get('cleartext_password_2')
        if cleartext_password_1 != cleartext_password_2:
            return self.wrap_content(util.msg_lookup('password_mismatch_error'))
        
        new_user = ms_inv.create_user_and_accept_invitation(DB_TUPLE, username, cleartext_password_1, user_statement)
        if new_user is not None and new_user.user_id is not None:
            ms_session = login_verify.create_session_and_set_cookie(PGDB, new_user.user_id)
            web.found(auth_status.build_page_url())
        else:
            return self.wrap_content(util.msg_lookup('ms_inv_user_create_failure'))

#TODO: the invite create(/decide?) workflows have largely the same logic and content, can probably centralize and have wrappers pass in differentiated form/field names
class nodespace_invite_create_form(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_invite_create.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    def get_ns_inv_create_form(cls, nodespace, user):
        ns_access_for_user = nodespace.get_nodespace_access_for_user(PGDB, user.user_id)
        grantable_privileges = ns_access_for_user.nodespace_privileges if ns_access_for_user is not None else tc.NodespacePrivilegeSet()
        return web.form.Form(
                            *([web.form.Textbox('invitee_email_addr', description=util.msg_lookup('create_inv_email_addr'))] +
                            nodespace_privilege_select_elts(grantable_privileges=grantable_privileges) +
                            [web.form.Textarea('invitation_msg', description=util.msg_lookup('create_ns_inv_msg'), cols='40', rows='3'),
                            web.form.Button(name=util.msg_lookup('create_inv_submit_btn'))]))
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        self.is_allowed_to_use(nodespace, user)
        
        nodespace_id_hidden = web.form.Hidden(name='nodespace_id', value=web.input().get('nodespace_id'))
        ns_inv_create_form_html = '%s %s' % (nodespace_id_hidden.render(), self.get_ns_inv_create_form(nodespace, user).render())
        return self.wrap_content(RENDER.basic_form_template(ns_inv_create_form_html, 'ns_inv_create_form', nodespace_invite_create.build_page_url()), user=user)

class nodespace_invite_create(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.ALTER_NODESPACE_ACCESS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        
        self.is_allowed_to_use(nodespace, user)
        
        invitee_email_addr = web.input().get('invitee_email_addr')
        nodespace_privileges = tc.NodespacePrivilegeSet.create_from_list_of_strings(web.input(nodespace_privileges=[]).get('nodespace_privileges'))
        invitee_user = tc.User.get_existing_user_by_email(PGDB, invitee_email_addr)
        if invitee_user is None:
            tc.MetaspacePrivilegeChecker.is_allowed_to_do(DB_TUPLE, tc.MetaspacePrivilegeChecker.CREATE_USER_ACTION, None, user)
        
        invitation_msg = web.input().get('invitation_msg')
        ns_inv = tc.NodespaceInvitation.create_new_invitation(PGDB, None, invitee_email_addr, nodespace.nodespace_id, nodespace_privileges, invitation_msg, user.user_id)
        
        if ns_inv is not None and ns_inv.nodespace_invitation_id is not None:
            ns_inv_link = nodespace_invite_decide_form.build_page_url(query_params={'nodespace_invitation_code': ns_inv.nodespace_invitation_code})
            util.send_nodespace_invitation_email(nodespace.nodespace_name, ns_inv, ns_inv_link)
            status_message = util.msg_lookup('inv_create_success', {'inv_url': ns_inv_link})
        else:
            status_message = util.msg_lookup('inv_create_failure')
            
        return self.wrap_content(status_message, user=user)

class nodespace_invite_decide_form(BasePage, InviteDecideForm):
    REQUIRES_VALID_SESSION = False
    
    def render_page(self, ms_session):
        inv_code_field_name = 'nodespace_invitation_code'
        ns_inv_code = web.input().get(inv_code_field_name)
        ns_inv = tc.NodespaceInvitation.get_existing_invitation(PGDB, ns_inv_code)
        if ns_inv is None or ns_inv.decision_date is not None:
            return self.wrap_content(util.msg_lookup('inv_not_found'))
        
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, ns_inv.nodespace_id)
        invitee_user = tc.User.get_existing_user_by_email(PGDB, ns_inv.invitee_email_addr)
        
        form_target = nodespace_invite_decide.build_page_url()
        form_name = 'ns_inv_accept_form'
        header_content_dict = {'inv_code': ns_inv_code, 'nodespace_name': nodespace.nodespace_name, 'invitee_email_addr': ns_inv.invitee_email_addr}
        if invitee_user is not None:
            ns_inv_code_hidden = web.form.Hidden(name=inv_code_field_name, value=ns_inv_code).render()
            ns_inv_accept_hidden = web.form.Hidden(name='was_accepted', value=self.ACCEPTED).render()
            ns_inv_accept_form_html = self.build_single_button_form(form_name, form_target, [ns_inv_code_hidden, ns_inv_accept_hidden], util.msg_lookup('inv_accept_submit_btn'))
            ns_inv_decide_header = util.msg_lookup('ns_inv_decide_ext_user_header', header_content_dict)
        else:
            ns_inv_accept_form_html = self.build_accept_form(form_name, form_target, inv_code_field_name, ns_inv_code)
            ns_inv_decide_header = util.msg_lookup('ns_inv_decide_new_user_header', header_content_dict)
        
        ns_inv_decline_form_html = self.build_decline_form('ns_inv_decline_form', form_target, inv_code_field_name, ns_inv_code)
        
        return self.wrap_content('<p>%s</p>\n <p>%s</p>\n <p>%s</p>\n <p>%s</p> ' % (ns_inv_decide_header, ns_inv.invitation_msg, ns_inv_accept_form_html, ns_inv_decline_form_html))

class nodespace_invite_decide(BasePage):
    REQUIRES_VALID_SESSION = False
    
    def render_page(self, ms_session):
        ns_inv_code = web.input().get('nodespace_invitation_code')
        ns_inv = tc.NodespaceInvitation.get_existing_invitation(PGDB, ns_inv_code)
        if ns_inv is None or ns_inv.decision_date is not None:
            return self.wrap_content(util.msg_lookup('inv_not_found'))
        
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, ns_inv.nodespace_id)
        
        was_accepted = web.input().get('was_accepted')
        if was_accepted == nodespace_invite_decide_form.DECLINED:
            ns_inv.decline_invitation(PGDB)
            return self.wrap_content(util.msg_lookup('ns_inv_declined_ack', {'inv_code': ns_inv_code, 'nodespace_name': nodespace.nodespace_name}))
        
        cleartext_password_1 = web.input().get('cleartext_password_1')
        cleartext_password_2 = web.input().get('cleartext_password_2')
        if cleartext_password_1 != cleartext_password_2:
            return self.wrap_content(util.msg_lookup('password_mismatch_error'))
        
        invitee_user = tc.User.get_existing_user_by_email(PGDB, ns_inv.invitee_email_addr)
        if invitee_user is not None:
            ns_inv.accept_invitation(PGDB, invitee_user.user_id)
        else:
            invitee_user = ns_inv.create_user_and_accept_invitation(DB_TUPLE, web.input().get('username'), cleartext_password_1, web.input().get('user_statement'))
        
        nodespace_access_entry = nodespace.get_nodespace_access_for_user(PGDB, invitee_user.user_id)
        
        if invitee_user is not None and nodespace_access_entry is not None:
            #TODO: this actually presents a security hole:  anyone who has an invitation link for an existing user can
            # get a session as that user.  should just redirect to login page.  maybe do the same for ms user creation,
            # if only for consistency's sake.
            ms_session = login_verify.create_session_and_set_cookie(PGDB, invitee_user.user_id)
            web.found(nodespace_access_view.build_page_url(query_params={'nodespace_id': nodespace.nodespace_id}))
        else:
            return self.wrap_content(util.msg_lookup('ns_inv_accept_failure'))

class nodespace_access_view(BasePage, ListTablePage):
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        nodespace_access_entry = nodespace.get_nodespace_access_for_user(PGDB, user.user_id)
        
        if nodespace_access_entry is not None:
            status_text = util.msg_lookup('ns_access_header', {'nodespace_name': nodespace.nodespace_name})
            access_html = self.basic_table_content([nodespace_access_entry])
        else:
            status_text = util.msg_lookup('ns_no_access_header')
            access_html = None
        session_html = self.basic_table_content([ms_session])
        output_html = '<p>%s</p><p>%s</p><p>%s</p>' % (status_text, access_html, session_html)
        return self.wrap_content(output_html, user=user)
        
class user_view(BasePage, ListTablePage):
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['username', 'email_addr', 'user_statement', 'metaspace_privileges', 'is_enabled', 'creator', 'creation_date', 'modifier', 'modification_date']
    
    def _get_content_summary(self, user):
        if user is None:
            return None
        return util.msg_lookup('user_view_smry', {'username': self.viewed_user.username})
    
    def _get_command_links(self, user):
        if user is None:
            return None
        
        ret_val = []
        
        if user_info_edit_form.is_allowed_to_use(None, user, False):
            user_edit_url = user_info_edit_form.build_page_url(query_params={'edited_user_id': self.viewed_user.user_id})
            user_edit_disp_txt = util.msg_lookup('edit_other_usr_link_disp_txt', {'username': self.viewed_user.username})
            ret_val.append({'url': user_edit_url, 'display_text': user_edit_disp_txt})
        
        if user_change_pass_form.is_allowed_to_use(None, user, False):
            user_chg_pass_url = user_change_pass_form.build_page_url(query_params={'edited_user_id': self.viewed_user.user_id})
            user_chg_pass_disp_txt = util.msg_lookup('chg_pass_other_user_disp_txt', {'username': self.viewed_user.username})
            ret_val.append({'url': user_chg_pass_url, 'display_text': user_chg_pass_disp_txt})
        
        if metaspace_access_edit_form.is_allowed_to_use(None, user, False):
            ms_priv_edit_url = metaspace_access_edit_form.build_page_url(query_params={'edited_user_id': self.viewed_user.user_id})
            ms_priv_edit_disp_txt = util.msg_lookup('edit_other_usr_privs_link_disp_txt', {'username': self.viewed_user.username})
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
    
    def render_page(self, ms_session):
        viewing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.viewed_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('viewed_user_id'))
        
        self.is_allowed_to_use(self.viewed_user, viewing_user)
        
        return self.wrap_content(self.basic_table_content([self.viewed_user]), user=viewing_user)

class user_info_edit_form(BasePage):
    USER_INFO_EDIT_FORM = web.form.Form(
                            web.form.Textbox('email_addr', description=util.msg_lookup('email_addr_label')),
                            web.form.Textbox('username', description=util.msg_lookup('username_label')),
                            web.form.Textarea('user_statement', description=util.msg_lookup('user_statement_blurb'), cols='40', rows='3'),
                            web.form.Button(name=util.msg_lookup('user_info_edit_submit_btn')))
    
    def _get_content_summary(self, user):
        if user is None:
            return None
        if user.user_id == self.edited_user.user_id:
            return util.msg_lookup('my_user_info_edit_form_smry')
        else:
            return util.msg_lookup('other_user_info_edit_form_smry', {'username': self.edited_user.username})
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return user_info_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.edited_user = tc.User.get_existing_user_by_id(PGDB, int(web.input().get('edited_user_id')))
        self.is_allowed_to_use(self.edited_user, editing_user)
        
        default_input = {'email_addr': self.edited_user.email_addr, 'username': self.edited_user.username, 'user_statement': self.edited_user.user_statement}
        edited_user_id_hidden_html = web.form.Hidden(name='edited_user_id', value=self.edited_user.user_id).render()
        user_edit_form_html = '%s\n%s' % (edited_user_id_hidden_html, self.USER_INFO_EDIT_FORM(web.input('edited_user_id', **default_input)).render())
        return self.wrap_content(RENDER.basic_form_template(user_edit_form_html, 'user_info_edit_form', user_info_edit.build_page_url()), user=editing_user)

class user_info_edit(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.ALTER_USER_INFO_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, int(web.input().get('edited_user_id')))
        self.is_allowed_to_use(edited_user, editing_user)
        
        edited_user.set_and_save_user_info(PGDB, web.input().get('username'), web.input().get('email_addr'), web.input().get('user_statement'), editing_user.user_id)
        
        web.found(user_view.build_page_url(query_params={'viewed_user_id': edited_user.user_id}))

class user_change_pass_form(BasePage):
    USER_CHANGE_PASS_FORM = web.form.Form(
                            web.form.Password('editing_user_cleartext_password', description=util.msg_lookup('password_label')),
                            web.form.Password('cleartext_password_1', description=util.msg_lookup('new_password_label')),
                            web.form.Password('cleartext_password_2', description=util.msg_lookup('reenter_password_label')),
                            web.form.Button(name=util.msg_lookup('user_change_password_submit_btn')))
    
    def _get_content_summary(self, user):
        if user is None:
            return None
        if user.user_id == self.edited_user.user_id:
            return util.msg_lookup('my_user_change_pass_form_smry')
        else:
            return util.msg_lookup('other_user_change_pass_form_smry', {'username': self.edited_user.username})
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return user_change_pass.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.edited_user = tc.User.get_existing_user_by_id(PGDB, int(web.input().get('edited_user_id')))
        
        self.is_allowed_to_use(self.edited_user, editing_user)
        
        edited_user_id_hidden_html = web.form.Hidden(name='edited_user_id', value=self.edited_user.user_id).render()
        user_change_pass_form_html = '%s\n%s' % (edited_user_id_hidden_html, self.USER_CHANGE_PASS_FORM(web.input('edited_user_id')).render())
        return self.wrap_content(RENDER.basic_form_template(user_change_pass_form_html, 'user_change_pass_form', user_change_pass.build_page_url()), user=editing_user)

class user_change_pass(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.ALTER_USER_INFO_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, int(web.input().get('edited_user_id')))
        
        self.is_allowed_to_use(edited_user, editing_user)
        
        if not editing_user.check_password_audited(PGDB, web.input().get('editing_user_cleartext_password')):
            return self.wrap_content(util.msg_lookup('password_check_failed'), user=editing_user)
        
        cleartext_password_1 = web.input().get('cleartext_password_1')
        cleartext_password_2 = web.input().get('cleartext_password_2')
        if cleartext_password_1 != cleartext_password_2:
            return self.wrap_content(util.msg_lookup('password_mismatch_error'), user=editing_user)
        
        edited_user.set_and_save_encrypted_password(PGDB, cleartext_password_1, editing_user.user_id)
        
        web.found(user_view.build_page_url(query_params={'viewed_user_id': edited_user.user_id}))

class NodespaceList(BasePage, ListTablePage):
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['nodespace_name_link', 'nodespace_description']
    
    @classmethod
    def _get_display_row(cls, query_row):
        nodespace_name_link = util.a_elt(web.websafe(query_row.nodespace_name), nodespace_view.build_page_url(query_params={'nodespace_id':query_row.nodespace_id}))
        return {'nodespace_name_link': nodespace_name_link, 'nodespace_description': web.websafe(query_row.nodespace_description)}
    
    def render_page_full_html(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.is_allowed_to_use(None, user)
        
        nodespaces = self.get_nodespaces(PGDB, user)
        page_content = self.basic_table_content(nodespaces) if len(nodespaces) > 0 else ''
        return self.wrap_content(page_content, user=user)
    
    def render_page_json(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.is_allowed_to_use(None, user)
        
        nodespaces = self.get_nodespaces(PGDB, user)
        nodespaces_dict_list = [{'nodespace_name': ns.nodespace_name, 
                                            'nodespace_description': ns.nodespace_description,
                                            'nodespace_id': ns.nodespace_id} for ns in nodespaces]
        return json.dumps(nodespaces_dict_list, indent=2)

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
    def _get_content_summary(self, user):
        if user is None:
            return None
        return util.msg_lookup('user_list_nodespace_smry', {'nodespace_name': self.nodespace.nodespace_name})
    
    @classmethod
    def _get_col_keys(cls, table_data):
        return ['username', 'nodespace_privileges', 'is_enabled_for_ns', 'is_enabled_for_ms']
    
    def _get_display_row(self, query_row):
        display_row = query_row.copy()
        user_view_url = user_view.build_page_url(query_params={'viewed_user_id': display_row['user_id']})
        display_row['username'] = util.a_elt(web.websafe(display_row['username']), user_view_url)
        if self.is_allowed_to_edit_ns_access:
            ns_access_edit_url = nodespace_access_edit_form.build_page_url(query_params={'edited_user_id': display_row['user_id'],
                                                                                         'nodespace_id': display_row['nodespace_id']})
            display_row['nodespace_privileges'] = util.a_elt(display_row['nodespace_privileges'], ns_access_edit_url)
        return display_row
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.ALTER_NODESPACE_ACCESS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        nodespace_id = web.input().get('nodespace_id')
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, nodespace_id) if nodespace_id is not None else None
        self.is_allowed_to_use(self.nodespace, user)
        
        self.is_allowed_to_edit_ns_access = nodespace_access_edit_form.is_allowed_to_use(self.nodespace, user, False)
        user_list = tc.User.get_user_and_access_info_by_nodespace_id(PGDB, nodespace_id)
        
        return self.wrap_content(self.basic_table_content(user_list), user=user)

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
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.is_allowed_to_use(None, user)
        
        user_list = tc.User.get_all_users(PGDB)
        
        return self.wrap_content(self.basic_table_content(user_list), user=user)

class metaspace_access_edit_form(BasePage):
    def _get_content_summary(self, user):
        if user is None:
            return None
        return util.msg_lookup('metaspace_access_edit_form_smry', {'username': self.edited_user.username})
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return metaspace_access_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def get_ms_priv_edit_form(cls, edited_user, editing_user):
        grantable_privileges = editing_user.metaspace_privileges.get_grantable_privileges()
        selected_privs = edited_user.metaspace_privileges
        is_enabled_radio_opts = [(True, util.msg_lookup('ms_enabled_desc')), (False, util.msg_lookup('ms_disabled_desc'))]
        return web.form.Form(*(metaspace_privilege_select_elts(grantable_privileges=grantable_privileges, selected_privileges=selected_privs) +
                            [web.form.Radio('is_enabled', is_enabled_radio_opts, value=edited_user.is_enabled, description=util.msg_lookup('user_is_enabled')),
                             web.form.Button(name=util.msg_lookup('update_ms_privs_submit_btn'))]))
    
    def render_page(self, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        self.is_allowed_to_use(self.edited_user, editing_user)
        
        edited_user_id_hidden_html = web.form.Hidden(name='edited_user_id', value=self.edited_user.user_id).render()
        ms_priv_edit_form_html = '%s\n%s' % (edited_user_id_hidden_html, self.get_ms_priv_edit_form(self.edited_user, editing_user)().render())
        return self.wrap_content(RENDER.basic_form_template(ms_priv_edit_form_html, 'ms_priv_edit_form', metaspace_access_edit.build_page_url()), user=editing_user)

class metaspace_access_edit(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return MS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, MS_PRVLG_CHKR.ALTER_USER_ACCESS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        self.is_allowed_to_use(edited_user, editing_user)
        
        new_metaspace_privileges = tc.MetaspacePrivilegeSet.create_from_list_of_strings(web.input(metaspace_privileges=[]).get('metaspace_privileges'))
        edited_user.set_and_save_metaspace_access(PGDB, web.input().get('is_enabled'), new_metaspace_privileges, editing_user.user_id)
        
        web.found(user_view.build_page_url(query_params={'viewed_user_id': edited_user.user_id}))

class nodespace_access_edit_form(BasePage):
    def _get_content_summary(self, user):
        if user is None:
            return None
        return util.msg_lookup('nodespace_access_edit_form_smry', {'nodespace_name': self.nodespace.nodespace_name, 'username': self.edited_user.username})
    
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return nodespace_access_edit.is_allowed_to_use(target, actor, should_raise_insufficient_priv_ex)
    
    @classmethod
    def get_ns_priv_edit_form(cls, edited_user, editing_user, nodespace_id):
        grantable_privileges = tc.NodespaceAccessEntry.get_existing_access_entry(PGDB, nodespace_id, editing_user.user_id).nodespace_privileges.get_grantable_privileges()
        cur_access = tc.NodespaceAccessEntry.get_existing_access_entry(PGDB, nodespace_id, edited_user.user_id)
        selected_privs = cur_access.nodespace_privileges
        is_enabled_radio_opts = [(True, util.msg_lookup('ns_enabled_desc')), (False, util.msg_lookup('ns_disabled_desc'))]
        return web.form.Form(*(nodespace_privilege_select_elts(grantable_privileges=grantable_privileges, selected_privileges=selected_privs) +
                            [web.form.Radio('is_enabled', is_enabled_radio_opts, value=cur_access.is_enabled, description=util.msg_lookup('user_is_enabled')),
                             web.form.Button(name=util.msg_lookup('update_ns_privs_submit_btn'))]))
    
    def render_page(self, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        nodespace_id = web.input().get('nodespace_id')
        self.nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, nodespace_id)
        self.is_allowed_to_use(self.edited_user, editing_user)
        
        edited_user_id_hidden_html = web.form.Hidden(name='edited_user_id', value=self.edited_user.user_id).render()
        nodespace_id_hidden_html = web.form.Hidden(name='nodespace_id', value=nodespace_id).render()
        ns_priv_edit_form_html = '%s\n%s\n%s' % (nodespace_id_hidden_html, edited_user_id_hidden_html, self.get_ns_priv_edit_form(self.edited_user, editing_user, nodespace_id)().render())
        return self.wrap_content(RENDER.basic_form_template(ns_priv_edit_form_html, 'ns_priv_edit_form', nodespace_access_edit.build_page_url()), user=editing_user)

class nodespace_access_edit(BasePage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.ALTER_NODESPACE_ACCESS_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        editing_user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        edited_user = tc.User.get_existing_user_by_id(PGDB, web.input().get('edited_user_id'))
        nodespace_id = web.input().get('nodespace_id')
        self.is_allowed_to_use(edited_user, editing_user)
        
        new_nodespace_privileges = tc.NodespacePrivilegeSet.create_from_list_of_strings(web.input(nodespace_privileges=[]).get('nodespace_privileges'))
        is_enabled = web.input().get('is_enabled')
        
        cur_nodespace_access = tc.NodespaceAccessEntry.get_existing_access_entry(PGDB, nodespace_id, edited_user.user_id)
        cur_nodespace_access.set_and_save_access_entry(PGDB, new_nodespace_privileges, is_enabled, editing_user.user_id)
        
        web.found(user_list_nodespace.build_page_url(query_params={'nodespace_id': nodespace_id}))

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
    
    def render_page_is_allowed_to_use(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        ret_val = {'is_allowed_to_use': self.is_allowed_to_use(None, user)}
        return json.dumps(ret_val)
    
    def render_page_full_html(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        self.is_allowed_to_use(None, user)
        
        cmd_list = []
        for page_class in [nodespace_create_form, user_invite_create_form, nodespace_list_all, user_list_all]:
            page_name = page_class.get_page_name()
            page_url = page_class.build_page_url()
            cmd_list.append({'cmd_link': util.a_elt(link_text=page_name, href_att_val=page_url)})
        
        return self.wrap_content(self.basic_table_content(cmd_list), user=user)

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
        
        return json.dumps(node_list + edge_list, indent=2)

class category_list(BasePage, GraphViewPage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.VIEW_NODESPACE_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        self.is_allowed_to_use(nodespace, user)
        
        cat_tree_info = tc.AdhocNeoQueries.get_nodespace_categories(NEODB, nodespace.nodespace_id)
        cat_tree_json = self.build_cat_tree_json(cat_tree_info)
        return self.wrap_content(RENDER.view_graph_template(cat_tree_json), user=user)

class nodespace_overview(BasePage, GraphViewPage):
    @classmethod
    def is_allowed_to_use(cls, target, actor, should_raise_insufficient_priv_ex=True):
        return NS_PRVLG_CHKR.is_allowed_to_do(DB_TUPLE, NS_PRVLG_CHKR.VIEW_NODESPACE_ACTION, target, actor, should_raise_insufficient_priv_ex)
    
    def render_page_json(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        nodespace = tc.Nodespace.get_existing_nodespace_by_id(PGDB, web.input().get('nodespace_id'))
        self.is_allowed_to_use(nodespace, user)
        
        overview_graph_info = tc.AdhocNeoQueries.get_nodespace_categories_and_writeups(NEODB, nodespace.nodespace_id)
        overview_graph_json = self.build_cat_tree_json(overview_graph_info)
        return overview_graph_json
    
    def render_page_full_html(self, ms_session):
        overview_graph_json = self.render_page_json(ms_session)
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        return self.wrap_content(RENDER.view_graph_template(overview_graph_json), user=user)

class nga(BasePage):
    def render_page(self, ms_session):
        user = tc.User.get_existing_user_by_id(PGDB, ms_session.user_id)
        return self.render_angular_app(user=user)



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
    
    def render_page(self, ms_session):
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
                user_invite_create_form, user_invite_create, user_invite_decide_form, user_invite_decide, 
                nodespace_invite_create_form, nodespace_invite_create, nodespace_invite_decide_form, nodespace_invite_decide, 
                nodespace_access_view, user_view, user_info_edit_form, user_info_edit, user_change_pass_form, user_change_pass,
                nodespace_list_accessible, nodespace_list_all, user_list_nodespace, user_list_all, 
                metaspace_access_edit_form, metaspace_access_edit, 
                nodespace_access_edit_form, nodespace_access_edit, metaspace_command_list,
                category_list, nodespace_overview, writeup_list, comment_thread_list,
                comment_create_form, comment_reply_form, comment_edit_form, writeup_create_form, writeup_edit_form,
                nga]

urls_list = []
for cls in page_classes:
    urls_list.append(cls.build_page_url(None, False))
    urls_list.append(cls)

urls = tuple(urls_list)

app = web.application(urls, globals())
application = app.wsgifunc()
