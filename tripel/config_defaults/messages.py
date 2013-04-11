class Messages(object):
    DEFAULT_TRANSLATION='dflt'
    
    
    instance_name = {DEFAULT_TRANSLATION: 'tripel'}
    
    logout_label = {DEFAULT_TRANSLATION: 'logout'}
    
    login_form_page_name = {DEFAULT_TRANSLATION: 'login'}
    auth_status_page_name = {DEFAULT_TRANSLATION: 'auth status for current user'}
    nodespace_create_form_page_name = {DEFAULT_TRANSLATION: 'create new nodespace'}
    nodespace_view_page_name = {DEFAULT_TRANSLATION: 'nodespace info'}
    nodespace_edit_form_page_name = {DEFAULT_TRANSLATION: 'edit nodespace info'}
    user_invite_create_form_page_name = {DEFAULT_TRANSLATION: 'invite new user'}
    user_invite_decide_form_page_name = {DEFAULT_TRANSLATION: 'accept/decline invitation'}
    nodespace_invite_create_form_page_name = {DEFAULT_TRANSLATION: 'invite user to nodespace'}
    nodespace_invite_decide_form_page_name = {DEFAULT_TRANSLATION: 'accept/decline nodespace invitation'}
    nodespace_access_view_page_name = {DEFAULT_TRANSLATION: 'user access for nodespace'}
    user_view_page_name = {DEFAULT_TRANSLATION: 'user info'}
    user_info_edit_form_page_name = {DEFAULT_TRANSLATION: 'edit user info'}
    user_change_pass_form_page_name = {DEFAULT_TRANSLATION: 'change password'}
    nodespace_list_accessible_page_name = {DEFAULT_TRANSLATION: 'accessible nodespaces for user'}
    nodespace_list_all_page_name = {DEFAULT_TRANSLATION: 'all nodespaces'}
    user_list_nodespace_page_name = {DEFAULT_TRANSLATION: 'list nodespace users'}
    user_list_all_page_name = {DEFAULT_TRANSLATION: 'list all users'}
    metaspace_access_edit_form_page_name = {DEFAULT_TRANSLATION: 'edit metaspace access'}
    nodespace_access_edit_form_page_name = {DEFAULT_TRANSLATION: 'edit nodespace access'}
    metaspace_command_list_page_name = {DEFAULT_TRANSLATION: 'metaspace commands'}
    
    username_col_hdr = {DEFAULT_TRANSLATION: 'username'}
    nodespace_privileges_col_hdr = {DEFAULT_TRANSLATION: 'nodespace privileges'}
    is_enabled_for_ns_col_hdr = {DEFAULT_TRANSLATION: 'enabled in nodespace?'}
    is_enabled_for_ms_col_hdr = {DEFAULT_TRANSLATION: 'enabled in metaspace?'}
    email_addr_col_hdr = {DEFAULT_TRANSLATION: 'email address'}
    user_statement_col_hdr = {DEFAULT_TRANSLATION: 'user statement'}
    metaspace_privileges_col_hdr = {DEFAULT_TRANSLATION: 'metaspace privileges'}
    is_enabled_col_hdr = {DEFAULT_TRANSLATION: 'enabled?'}
    creator_col_hdr = {DEFAULT_TRANSLATION: 'created by'}
    creation_date_col_hdr = {DEFAULT_TRANSLATION: 'created on'}
    modifier_col_hdr = {DEFAULT_TRANSLATION: 'last modified by'}
    modification_date_col_hdr = {DEFAULT_TRANSLATION: 'last modified on'}
    cmd_link_col_hdr = {DEFAULT_TRANSLATION: 'command'}
    nodespace_name_link_col_hdr = {DEFAULT_TRANSLATION: 'nodespace'}
    nodespace_description_col_hdr = {DEFAULT_TRANSLATION: 'description'}
    nodespace_name_col_hdr = {DEFAULT_TRANSLATION: 'nodespace'}
    
    login_form_smry = {DEFAULT_TRANSLATION: ''}
    login_verify_smry = {DEFAULT_TRANSLATION: ''}
    logout_smry = {DEFAULT_TRANSLATION: ''}
    nodespace_create_smry = {DEFAULT_TRANSLATION: ''}
    nodespace_edit_smry = {DEFAULT_TRANSLATION: ''}
    user_invite_decide_smry = {DEFAULT_TRANSLATION: ''}
    nodespace_invite_decide_smry = {DEFAULT_TRANSLATION: ''}
    nodespace_access_view_smry = {DEFAULT_TRANSLATION: ''}
    user_info_edit_smry = {DEFAULT_TRANSLATION: ''}
    user_change_pass_smry = {DEFAULT_TRANSLATION: ''}
    metaspace_access_edit_smry = {DEFAULT_TRANSLATION: ''}
    nodespace_access_edit_smry = {DEFAULT_TRANSLATION: ''}
    nodespace_view_smry = {DEFAULT_TRANSLATION: 'nodespace info for: %(nodespace_name)s'}
    user_invite_create_form_smry = {DEFAULT_TRANSLATION: 'invite new user to metaspace'}
    auth_status_smry = {DEFAULT_TRANSLATION: 'current login status'}
    nodespace_create_form_smry = {DEFAULT_TRANSLATION: 'create a new nodespace'}
    nodespace_edit_form_smry = {DEFAULT_TRANSLATION: 'edit nodespace info for: %(nodespace_name)s'}
    user_invite_create_form_smry = {DEFAULT_TRANSLATION: 'invite a new user'}
    user_invite_create_smry = {DEFAULT_TRANSLATION: 'invitation created'}
    user_invite_decide_form_smry = {DEFAULT_TRANSLATION: 'accept or decline invitation'}
    nodespace_invite_create_form_smry = {DEFAULT_TRANSLATION: 'create nodespace invitation'}
    nodespace_invite_create_smry = {DEFAULT_TRANSLATION: 'invitation created'}
    nodespace_invite_decide_form_smry = {DEFAULT_TRANSLATION: 'accept or decline nodespace invitation'}
    user_view_smry = {DEFAULT_TRANSLATION: 'user info for: %(username)s'}
    my_user_info_edit_form_smry = {DEFAULT_TRANSLATION: 'edit my user info'}
    other_user_info_edit_form_smry = {DEFAULT_TRANSLATION: 'edit user info for: %(username)s'}
    my_user_change_pass_form_smry = {DEFAULT_TRANSLATION: 'change my password'}
    other_user_change_pass_form_smry = {DEFAULT_TRANSLATION: 'change password for: %(username)s'}
    nodespace_list_accessible_smry = {DEFAULT_TRANSLATION: 'accessible nodespaces'}
    nodespace_list_all_smry = {DEFAULT_TRANSLATION: 'all nodespaces'}
    user_list_nodespace_smry = {DEFAULT_TRANSLATION: 'users in nodespace: %(nodespace_name)s'}
    user_list_all_smry = {DEFAULT_TRANSLATION: 'all users'}
    metaspace_access_edit_form_smry = {DEFAULT_TRANSLATION: 'edit metaspace access for: %(username)s'}
    nodespace_access_edit_form_smry = {DEFAULT_TRANSLATION: 'edit nodespace access to %(nodespace_name)s for %(username)s'}
    metaspace_command_list_smry = {DEFAULT_TRANSLATION: 'metaspace commands'}
    
    email_addr_label = {DEFAULT_TRANSLATION: 'email address'}
    username_label = {DEFAULT_TRANSLATION: 'username'}
    password_label = {DEFAULT_TRANSLATION: 'password'}
    new_password_label = {DEFAULT_TRANSLATION: 'new password'}
    reenter_password_label = {DEFAULT_TRANSLATION: 're-enter password'}
    password_mismatch_error = {DEFAULT_TRANSLATION: 'passwords don\'t match'}
    
    login_submit_btn = {DEFAULT_TRANSLATION: 'login'}
    
    create_ns_form_nsname = {DEFAULT_TRANSLATION: 'nodespace name'}
    create_ns_form_ns_desc = {DEFAULT_TRANSLATION: 'nodespace description'}
    invalid_ns_name = {DEFAULT_TRANSLATION: 'nodespace name must be non-empty and unique'}
    create_ns_submit_btn = {DEFAULT_TRANSLATION: 'create nodespace'}
    edit_ns_submit_btn = {DEFAULT_TRANSLATION: 'update nodespace info'}
    
    auth_status_text = {DEFAULT_TRANSLATION: 'has session: %(has_valid_session)s'}
    
    create_inv_code = {DEFAULT_TRANSLATION: 'invitation code (>=%(min_length)i characters; alphanumeric, hyphen, or underscore.)'}
    create_inv_email_addr = {DEFAULT_TRANSLATION: 'invitee email address'}
    create_user_priv_title = {DEFAULT_TRANSLATION: 'Create User'}
    create_user_priv_desc = {DEFAULT_TRANSLATION: 'the ability to create new users'}
    super_priv_title = {DEFAULT_TRANSLATION: 'Super User'}
    super_priv_desc = {DEFAULT_TRANSLATION: 'can do anything, so hand this out judiciously'}
    create_space_priv_title = {DEFAULT_TRANSLATION: 'Create Space'}
    create_space_priv_desc = {DEFAULT_TRANSLATION: 'can create new nodespaces'}
    create_inv_submit_btn = {DEFAULT_TRANSLATION: 'create invitation'}
    create_ms_inv_msg = {DEFAULT_TRANSLATION: 'an optional message for the user you\'re creating'}
    create_ns_inv_msg = {DEFAULT_TRANSLATION: 'an optional message for the user you\'re inviting to this nodespace'}
    
    inv_create_success = {DEFAULT_TRANSLATION: 'to accept/decline, visit: %(inv_url)s'}
    inv_create_failure = {DEFAULT_TRANSLATION: 'failed to create invitation'}
    
    inv_not_found = {DEFAULT_TRANSLATION: 'invitation code not found or no longer valid'}
    inv_accept_submit_btn = {DEFAULT_TRANSLATION: 'accept invitation'}
    inv_decline_submit_btn = {DEFAULT_TRANSLATION: 'decline invitation'}
    
    user_statement_blurb = {DEFAULT_TRANSLATION: 'user statement'}
    
    ms_inv_decide_header = {DEFAULT_TRANSLATION: 'Please decide on invitatation %(inv_code)s (sent to %(invitee_email_addr)s)'}
    ms_inv_user_create_failure = {DEFAULT_TRANSLATION: 'failed to create new user'}
    ms_inv_declined_ack = {DEFAULT_TRANSLATION: 'declined invitation %(inv_code)s'}
    
    ns_inv_decide_ext_user_header = {DEFAULT_TRANSLATION: 'Please decide on invitatation %(inv_code)s to nodespace %(nodespace_name)s for existing user %(invitee_email_addr)s'}
    ns_inv_decide_new_user_header = {DEFAULT_TRANSLATION: 'Please decide on invitatation %(inv_code)s to nodespace %(nodespace_name)s for new user %(invitee_email_addr)s'}
    
    contributor_priv_title = {DEFAULT_TRANSLATION: 'Contributor'}
    contributor_priv_desc = {DEFAULT_TRANSLATION: 'can create new content'}
    editor_priv_title = {DEFAULT_TRANSLATION: 'Editor'}
    editor_priv_desc = {DEFAULT_TRANSLATION: 'can alter content created by others'}
    moderator_priv_title = {DEFAULT_TRANSLATION: 'Moderator'}
    moderator_priv_desc = {DEFAULT_TRANSLATION: 'can approve content and modify taxonomy'}
    admin_priv_title = {DEFAULT_TRANSLATION: 'Admin'}
    admin_priv_desc = {DEFAULT_TRANSLATION: 'can set settings, alter user access, and generally administrate'}
    
    ns_inv_declined_ack = {DEFAULT_TRANSLATION: 'declined invitation %(inv_code)s to nodespace %(nodespace_name)s'}
    ns_inv_accept_failure = {DEFAULT_TRANSLATION: 'error accepting invitation'}
    
    ns_access_header = {DEFAULT_TRANSLATION: 'access to nodespace %(nodespace_name)s'}
    ns_no_access_header = {DEFAULT_TRANSLATION: 'no access to nodespace'}
    
    user_info_edit_submit_btn = {DEFAULT_TRANSLATION: 'update user info'}
    
    user_change_password_submit_btn = {DEFAULT_TRANSLATION: 'change password'}
    
    password_check_failed = {DEFAULT_TRANSLATION: 'incorrect password'}
    
    ms_inv_email_subject = {DEFAULT_TRANSLATION: 'tripel account creation invitation'}
    ms_inv_email_message = {DEFAULT_TRANSLATION: 'You have been invited to create a tripel user account.  To accept or decline the invitation, visit:\n%(inv_url)s\n\n%(inv_msg)s'}

    ns_inv_email_subject = {DEFAULT_TRANSLATION: 'tripel nodespace invitation: %(nodespace_name)s'}
    ns_inv_email_message = {DEFAULT_TRANSLATION: 'You have been invited to access %(nodespace_name)s.  To accept or decline the invitation, visit:\n%(inv_url)s\n\n%(inv_msg)s'}
    
    edit_usr_link_disp_txt = {DEFAULT_TRANSLATION: 'edit user info'}
    passwd_link_disp_txt = {DEFAULT_TRANSLATION: 'change password'}
    logout_link_disp_txt = {DEFAULT_TRANSLATION: 'logout'}
    
    accessible_nodespaces_link_disp_txt = {DEFAULT_TRANSLATION: 'nodespaces for %(username)s'}
    
    edit_other_usr_link_disp_txt = {DEFAULT_TRANSLATION: 'edit user info for %(username)s'}
    edit_other_usr_privs_link_disp_txt = {DEFAULT_TRANSLATION: 'alter metaspace privileges for %(username)s'}
    
    chg_pass_other_user_disp_txt = {DEFAULT_TRANSLATION: 'change password for %(username)s'}
    
    edit_nodespace_link_disp_txt = {DEFAULT_TRANSLATION: 'edit nodespace info for %(nodespace_name)s'}
    nodespace_inv_link_disp_txt = {DEFAULT_TRANSLATION: 'invite user to %(nodespace_name)s'}
    nodespace_user_list_link_disp_txt = {DEFAULT_TRANSLATION: 'list users in %(nodespace_name)s'}
    
    update_ms_privs_submit_btn = {DEFAULT_TRANSLATION: 'update metaspace privileges'}
    
    user_is_enabled = {DEFAULT_TRANSLATION: 'enable/disable user access'}
    ms_enabled_desc = {DEFAULT_TRANSLATION: 'enabled (user can login)'}
    ms_disabled_desc = {DEFAULT_TRANSLATION: 'disabled (user can\'t login)'}
    
    ns_enabled_desc = {DEFAULT_TRANSLATION: 'enabled (user can access nodespace)'}
    ns_disabled_desc = {DEFAULT_TRANSLATION: 'disabled (user can\'t access nodespace)'}
    
    update_ns_privs_submit_btn = {DEFAULT_TRANSLATION: 'update nodespace privileges'}
