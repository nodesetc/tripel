class Messages(object):
    DEFAULT_LOCALE = 'en-US'
    
    TRANSLATION_LOCALES = {
        'en-US': {
            'translation': {
                'instance_name': 'de brouwerij',
                
                'logout_label': 'logout',
                
                'login_form_page_name': 'login',
                'auth_status_page_name': 'auth status for current user',
                'nodespace_create_form_page_name': 'create new nodespace',
                'nodespace_view_page_name': 'nodespace info',
                'nodespace_edit_form_page_name': 'edit nodespace info',
                'user_invite_create_form_page_name': 'invite new user',
                'user_invite_decide_form_page_name': 'accept/decline invitation',
                'nodespace_invite_create_form_page_name': 'invite user to nodespace',
                'nodespace_invite_decide_form_page_name': 'accept/decline nodespace invitation',
                'nodespace_access_view_page_name': 'user access for nodespace',
                'user_view_page_name': 'user info',
                'user_info_edit_form_page_name': 'edit user info',
                'user_change_pass_form_page_name': 'change password',
                'nodespace_list_accessible_page_name': 'accessible nodespaces for user',
                'nodespace_list_all_page_name': 'all nodespaces',
                'user_list_nodespace_page_name': 'list nodespace users',
                'user_list_all_page_name': 'list all users',
                'metaspace_access_edit_form_page_name': 'edit metaspace access',
                'nodespace_access_edit_form_page_name': 'edit nodespace access',
                'metaspace_command_list_page_name': 'metaspace commands',
                
                'username_col_hdr': 'username',
                'nodespace_privileges_col_hdr': 'nodespace privileges',
                'is_enabled_for_ns_col_hdr': 'enabled in nodespace?',
                'is_enabled_for_ms_col_hdr': 'enabled in metaspace?',
                'email_addr_col_hdr': 'email address',
                'user_statement_col_hdr': 'user statement',
                'metaspace_privileges_col_hdr': 'metaspace privileges',
                'is_enabled_col_hdr': 'enabled?',
                'creator_col_hdr': 'created by',
                'creation_date_col_hdr': 'created on',
                'modifier_col_hdr': 'last modified by',
                'modification_date_col_hdr': 'last modified on',
                'cmd_link_col_hdr': 'command',
                'nodespace_name_link_col_hdr': 'nodespace',
                'nodespace_description_col_hdr': 'description',
                'nodespace_name_col_hdr': 'nodespace',
                
                'login_form_smry': '',
                'login_verify_smry': '',
                'logout_smry': '',
                'nodespace_create_smry': '',
                'nodespace_edit_smry': '',
                'user_invite_decide_smry': '',
                'nodespace_invite_decide_smry': '',
                'nodespace_access_view_smry': '',
                'user_info_edit_smry': '',
                'user_change_pass_smry': '',
                'metaspace_access_edit_smry': '',
                'nodespace_access_edit_smry': '',
                'nodespace_view_smry': 'nodespace info for: %(nodespace_name)s',
                'user_invite_create_form_smry': 'invite new user to metaspace',
                'auth_status_smry': 'current login status',
                'nodespace_create_form_smry': 'create a new nodespace',
                'nodespace_edit_form_smry': 'edit nodespace info for: %(nodespace_name)s',
                'user_invite_create_form_smry': 'invite a new user',
                'user_invite_create_smry': 'invitation created',
                'user_invite_decide_form_smry': 'accept or decline invitation',
                'nodespace_invite_create_form_smry': 'create nodespace invitation',
                'nodespace_invite_create_smry': 'invitation created',
                'nodespace_invite_decide_form_smry': 'accept or decline nodespace invitation',
                'user_view_smry': 'user info for: %(username)s',
                'my_user_info_edit_form_smry': 'edit my user info',
                'other_user_info_edit_form_smry': 'edit user info for: %(username)s',
                'my_user_change_pass_form_smry': 'change my password',
                'other_user_change_pass_form_smry': 'change password for: %(username)s',
                'nodespace_list_accessible_smry': 'accessible nodespaces',
                'nodespace_list_all_smry': 'all nodespaces',
                'user_list_nodespace_smry': 'users in nodespace: %(nodespace_name)s',
                'user_list_all_smry': 'all users',
                'metaspace_access_edit_form_smry': 'edit metaspace access for: %(username)s',
                'nodespace_access_edit_form_smry': 'edit nodespace access to %(nodespace_name)s for %(username)s',
                'metaspace_command_list_smry': 'metaspace commands',
                
                'email_addr_label': 'email address',
                'username_label': 'username',
                'password_label': 'password',
                'new_password_label': 'new password',
                'reenter_password_label': 're-enter password',
                'password_mismatch_error': 'passwords don\'t match',
                
                'login_submit_btn': 'login',
                
                'create_ns_form_nsname': 'nodespace name',
                'create_ns_form_ns_desc': 'nodespace description',
                'invalid_ns_name': 'nodespace name must be non-empty and unique',
                'create_ns_submit_btn': 'create nodespace',
                'edit_ns_submit_btn': 'update nodespace info',
                
                'auth_status_text': 'has session: %(has_valid_session)s',
                
                'create_inv_code': 'invitation code (>=%(min_length)i characters; alphanumeric, hyphen, or underscore.)',
                'create_inv_email_addr': 'invitee email address',
                'create_user_priv_title': 'Create User',
                'create_user_priv_desc': 'the ability to create new users',
                'super_priv_title': 'Super User',
                'super_priv_desc': 'can do anything, so hand this out judiciously',
                'create_space_priv_title': 'Create Space',
                'create_space_priv_desc': 'can create new nodespaces',
                'create_inv_submit_btn': 'create invitation',
                'create_ms_inv_msg': 'an optional message for the user you\'re creating',
                'create_ns_inv_msg': 'an optional message for the user you\'re inviting to this nodespace',
                
                'inv_create_success': 'to accept/decline, visit: %(inv_url)s',
                'inv_create_failure': 'failed to create invitation',
                
                'inv_not_found': 'invitation code not found or no longer valid',
                'inv_accept_submit_btn': 'accept invitation',
                'inv_decline_submit_btn': 'decline invitation',
                
                'user_statement_blurb': 'user statement',
                
                'ms_inv_decide_header': 'Please decide on invitatation %(inv_code)s (sent to %(invitee_email_addr)s)',
                'ms_inv_user_create_failure': 'failed to create new user',
                'ms_inv_declined_ack': 'declined invitation %(inv_code)s',
                
                'ns_inv_decide_ext_user_header': 'Please decide on invitatation %(inv_code)s to nodespace %(nodespace_name)s for existing user %(invitee_email_addr)s',
                'ns_inv_decide_new_user_header': 'Please decide on invitatation %(inv_code)s to nodespace %(nodespace_name)s for new user %(invitee_email_addr)s',
                
                'contributor_priv_title': 'Contributor',
                'contributor_priv_desc': 'can create new content',
                'editor_priv_title': 'Editor',
                'editor_priv_desc': 'can alter content created by others',
                'moderator_priv_title': 'Moderator',
                'moderator_priv_desc': 'can approve content and modify taxonomy',
                'admin_priv_title': 'Admin',
                'admin_priv_desc': 'can set settings, alter user access, and generally administrate',
                
                'ns_inv_declined_ack': 'declined invitation %(inv_code)s to nodespace %(nodespace_name)s',
                'ns_inv_accept_failure': 'error accepting invitation',
                
                'ns_access_header': 'access to nodespace %(nodespace_name)s',
                'ns_no_access_header': 'no access to nodespace',
                
                'user_info_edit_submit_btn': 'update user info',
                
                'user_change_password_submit_btn': 'change password',
                
                'password_check_failed': 'incorrect password',
                
                'ms_inv_email_subject': 'tripel account creation invitation',
                'ms_inv_email_message': 'You have been invited to create a tripel user account.  To accept or decline the invitation, visit:\n%(inv_url)s\n\n%(inv_msg)s',
                
                'ns_inv_email_subject': 'tripel nodespace invitation: %(nodespace_name)s',
                'ns_inv_email_message': 'You have been invited to access %(nodespace_name)s.  To accept or decline the invitation, visit:\n%(inv_url)s\n\n%(inv_msg)s',
                
                'edit_usr_link_disp_txt': 'edit user info',
                'passwd_link_disp_txt': 'change password',
                'logout_link_disp_txt': 'logout',
                
                'accessible_nodespaces_link_disp_txt': 'nodespaces for %(username)s',
                
                'edit_other_usr_link_disp_txt': 'edit user info for %(username)s',
                'edit_other_usr_privs_link_disp_txt': 'alter metaspace privileges for %(username)s',
                
                'chg_pass_other_user_disp_txt': 'change password for %(username)s',
                
                'edit_nodespace_link_disp_txt': 'edit nodespace info for %(nodespace_name)s',
                'nodespace_inv_link_disp_txt': 'invite user to %(nodespace_name)s',
                'nodespace_user_list_link_disp_txt': 'list users in %(nodespace_name)s',
                
                'update_ms_privs_submit_btn': 'update metaspace privileges',
                
                'user_is_enabled': 'enable/disable user access',
                'ms_enabled_desc': 'enabled (user can login)',
                'ms_disabled_desc': 'disabled (user can\'t login)',
                
                'ns_enabled_desc': 'enabled (user can access nodespace)',
                'ns_disabled_desc': 'disabled (user can\'t access nodespace)',
                
                'update_ns_privs_submit_btn': 'update nodespace privileges'
            }
        }
    }
    
    @classmethod
    def lookup(cls, key, content_dict={}, locale=DEFAULT_LOCALE):
        locale = locale if locale in cls.TRANSLATION_LOCALES else cls.DEFAULT_LOCALE
        translation = cls.TRANSLATION_LOCALES[locale]['translation']
        return translation[key] % content_dict if key in translation else key
