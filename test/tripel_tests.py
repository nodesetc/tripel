import os
import getpass
import traceback

import nose
from mock import Mock, create_autospec

import web
from py2neo import neo4j

from tripel.tripel_core import PgUtil, NeoUtil, init_neodb, User, Invitation, MetaspaceInvitation, Nodespace, NodespaceInvitation
from tripel.tripel_core import PasswordChangeAuditEntry, MetaspacePrivilegeAuditEntry
from tripel.tripel_core import MetaspacePrivilegeSet, NodespacePrivilegeSet, PrivilegeChecker, MetaspacePrivilegeChecker, NodespacePrivilegeChecker, MetaspaceSession
from tripel.util import DateTimeUtil
import tripel.config.parameters as params

os.chdir('..')
os.chdir('tripel')

pgdb_password_test = getpass.getpass('please enter the postgres database password: ')

PGDB_TEST = PgUtil.get_db_conn_ssl(params.PG_DBNAME_TEST, params.PG_USERNAME_TEST, pgdb_password_test, params.PG_HOST_ADDR_TEST)
NEODB_TEST = NeoUtil.get_db_conn(params.NEO_DB_URI_TEST)
DB_TUPLE_TEST = (PGDB_TEST, NEODB_TEST)

PGDB_MOCK = create_autospec(web.database)
#TODO: anything that uses NEODB_MOCK (directly or indirectly) needs to make some assertions about how it's called
NEODB_MOCK = create_autospec(neo4j.GraphDatabaseService)
DB_TUPLE_MOCK = (PGDB_MOCK, NEODB_MOCK)

DB_TUPLE_PT_NM = (PGDB_TEST, NEODB_MOCK)


#TODO: have a way to easily track nodes/edges created in neo in a test, and easy way to clean them all up at the end of the test.
class AutoRollbackTransaction(object):
    def __enter__(self):
        self.test_trans = PGDB_TEST.transaction()
        return self.test_trans
    def __exit__(self, type, value, traceback):
        self.test_trans.rollback()

class AssertExceptionThrown(object):
    def __init__(self, expected_exception_type):
        self._expected_exception_type = expected_exception_type
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_value, exc_traceback):
        if not isinstance(exc_value, self._expected_exception_type):
            print 'expected type: %s; actual type: %s' % (self._expected_exception_type, exc_type)
            traceback.print_tb(exc_traceback)
        assert isinstance(exc_value, self._expected_exception_type)
        return True



class TestData(object):
    USER_ADMIN = {'email_addr': 'frink@springface.net',
                'username': 'professor frink',
                'cleartext_password': 'passw0rd',
                'user_statement': '',
                'is_enabled': True,
                'metaspace_privileges': MetaspacePrivilegeSet.create_from_list_of_strings([MetaspacePrivilegeSet.SUPER, MetaspacePrivilegeSet.CREATE_USER, MetaspacePrivilegeSet.CREATE_SPACE]),
                'creator': None}
    
    USER_HANS = {'email_addr': 'hans_moleman@springface.net',
                'new_email_addr': 'hmoleman61@springface.net',
                'username': 'mole_man',
                'new_username': 'rmelish',
                'cleartext_password': 'passw0rd',
                'new_cleartext_password': 'passw0rd1',
                'user_statement': 'was in fact saying boo-urns',
                'new_user_statement': 'was not in fact saying boo-urns',
                'is_enabled': True,
                'new_is_enabled': False,
                'metaspace_privileges': MetaspacePrivilegeSet(),
                'new_metaspace_privileges': MetaspacePrivilegeSet.create_from_list_of_strings([MetaspacePrivilegeSet.CREATE_USER]),
                'modifier': None,
                'modification_date': None}
    
    MS_INV_JASPER = {'metaspace_invitation_code': None,
                'metaspace_invitation_code': None,
                'invitee_email_addr': 'jasper@springface.net',
                'initial_metaspace_privileges': MetaspacePrivilegeSet(),
                'invitation_msg': 'test metaspace inv message',
                'decision_date': None,
                'was_accepted': None,
                'new_user_id': None}
    
    NODESPACE_1 = {'nodespace_name': 'test_space_1',
                    'nodespace_description': 'a test nodespace'}
    
    NS_INV_HORATIO = {'nodespace_invitation_code': None,
                'invitee_email_addr': 'horatio_mccallister@springface.net',
                'invitee_username': 'sea_captain',
                'invitee_password': 'passw0rd',
                'invitee_user_statement': 'aye, the hotpants',
                'initial_nodespace_privileges': NodespacePrivilegeSet.create_from_list_of_strings([NodespacePrivilegeSet.EDITOR, NodespacePrivilegeSet.MODERATOR]),
                'invitation_msg': 'test nodespace inv msg',
                'decision_date': None,
                'was_accepted': None,
                'user_id': None}
    
    NS_ARSFT = {'nodespace_name': 'Ayn Rand School For Tots',
                'nodespace_description': 'develop the bottle within',
                'modifier': None,
                'modification_date': None}


def setup_test_pgdb():
    # create the first user if they don't already exist
    admin_user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
    if admin_user is None:
        admin_data = TestData.USER_ADMIN
        admin_user = User.create_new_user(PGDB_TEST, admin_data['email_addr'], admin_data['username'], admin_data['cleartext_password'], admin_data['user_statement'],
                                            admin_data['is_enabled'], admin_data['metaspace_privileges'], admin_data['creator'])
        ns_data = TestData.NODESPACE_1
        Nodespace.create_new_nodespace(PGDB_TEST, ns_data['nodespace_name'], ns_data['nodespace_description'], admin_user.user_id)

"""
#TODO: does not currently work since my test neodb instance won't cache scripts
def setup_test_neodb():
    NEODB_TEST.clear()
    NeoUtil.init_gremlin_env(NEODB_TEST)
    init_neodb(DB_TUPLE_TEST)
"""

def User_create_and_retrieve_test():
    hans_data = TestData.USER_HANS
    admin_user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
    hans_data['creator'] = admin_user.user_id

    with AutoRollbackTransaction() as test_trans:
        creation_date_lb = DateTimeUtil.datetime_now_utc_aware()
        hans = User.create_new_user(DB_TUPLE_PT_NM, hans_data['email_addr'], hans_data['username'], hans_data['cleartext_password'], hans_data['user_statement'],
                                    hans_data['is_enabled'], hans_data['metaspace_privileges'], hans_data['creator'])
        creation_date_ub = DateTimeUtil.datetime_now_utc_aware()
        
        hans_data['user_id'] = hans.user_id
        hans_data['encrypted_password'] = hans.encrypted_password
        
        assert creation_date_lb <= hans.creation_date <= creation_date_ub
        for field_name in User.FIELD_NAMES:
            if field_name not in ['creation_date']:
                assert hans_data[field_name] == vars(hans)[field_name]
        assert hans.check_password(hans_data['cleartext_password']) == True
        assert hans.check_password(hans_data['new_cleartext_password']) == False
        
        hans_data['old_encrypted_password'] = hans_data['encrypted_password']
        hans_data['modifier'] = hans_data['creator']
        hans.set_and_save_user_info(PGDB_TEST, hans_data['new_username'], hans_data['new_email_addr'], hans_data['new_user_statement'], hans_data['modifier'])
        modification_date_lb = DateTimeUtil.datetime_now_utc_aware()
        hans.set_and_save_metaspace_access(PGDB_TEST, hans_data['new_is_enabled'], hans_data['new_metaspace_privileges'], hans_data['modifier'])
        hans.set_and_save_encrypted_password(PGDB_TEST, hans_data['new_cleartext_password'], hans_data['modifier'])
        modification_date_ub = DateTimeUtil.datetime_now_utc_aware()
        
        hans = User.get_existing_user_by_email(PGDB_TEST, hans_data['new_email_addr'])
        hans_data['encrypted_password'] = hans.encrypted_password
        
        hans_by_id = User.get_existing_user_by_id(PGDB_TEST, hans.user_id)
        for field_name in User.FIELD_NAMES:
            assert getattr(hans, field_name) == getattr(hans_by_id, field_name)
        
        assert modification_date_lb <= hans.modification_date <= modification_date_ub
        assert hans.username == hans_data['new_username']
        assert hans.email_addr == hans_data['new_email_addr']
        assert hans.user_statement == hans_data['new_user_statement']
        assert hans.metaspace_privileges == hans_data['new_metaspace_privileges']
        assert hans.modifier == hans_data['modifier']
        assert hans.check_password(hans_data['new_cleartext_password']) == True
        assert hans.check_password(hans_data['cleartext_password']) == False
        assert hans_data['encrypted_password'] != hans_data['old_encrypted_password']
        
        latest_pw_chg_audit_entry = PasswordChangeAuditEntry.get_audit_log_entries_for_user(PGDB_TEST, hans.user_id)[0]
        latest_ms_priv_audit_entry = MetaspacePrivilegeAuditEntry.get_audit_log_entries_for_user(PGDB_TEST, hans.user_id)[0]
        
        assert latest_pw_chg_audit_entry.updated_user == hans.user_id
        assert latest_pw_chg_audit_entry.updating_user == hans.modifier
        assert modification_date_lb <= latest_pw_chg_audit_entry.passwd_chg_date <= modification_date_ub
        assert latest_ms_priv_audit_entry.updated_user == hans.user_id
        assert latest_ms_priv_audit_entry.updating_user == hans.modifier
        assert latest_ms_priv_audit_entry.new_privileges == hans.metaspace_privileges
        assert modification_date_lb <= latest_ms_priv_audit_entry.ms_priv_chg_date <= modification_date_ub

    # the following lines are more testing AutoRollbackTransaction
    hans = User.get_existing_user_by_email(PGDB_TEST, hans_data['email_addr'])
    assert hans == None
    hans = User.get_existing_user_by_email(PGDB_TEST, hans_data['new_email_addr'])
    assert hans == None

def Invitation_test():
    with AssertExceptionThrown(Exception):
        Invitation.validate_invitation_code_format(Invitation.generate_random_invitation_code(Invitation.MIN_INVITE_CODE_LEN-2))

class MetaspaceInvitation_tests(object):
    ms_inv_data = TestData.MS_INV_JASPER
    
    def accept_test(self):
        ms_inv_data = self.ms_inv_data
        admin_user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
        ms_inv_data['creator'] = admin_user.user_id
        
        with AutoRollbackTransaction() as test_trans:
            creation_date_lb = DateTimeUtil.datetime_now_utc_aware()
            ms_invite = MetaspaceInvitation.create_new_invitation(PGDB_TEST, ms_inv_data['metaspace_invitation_code'], ms_inv_data['invitee_email_addr'], 
                            ms_inv_data['initial_metaspace_privileges'], ms_inv_data['invitation_msg'], ms_inv_data['creator'])
            creation_date_ub = DateTimeUtil.datetime_now_utc_aware()
            ms_inv_data['metaspace_invitation_id'] = ms_invite.metaspace_invitation_id
            ms_inv_data['metaspace_invitation_code'] = ms_invite.metaspace_invitation_code
            
            assert creation_date_lb <= ms_invite.creation_date <= creation_date_ub
            assert ms_inv_data['metaspace_invitation_code'] is not None
            for field_name in MetaspaceInvitation.FIELD_NAMES:
                if field_name not in ['creation_date']:
                    assert ms_inv_data[field_name] == vars(ms_invite)[field_name]

            ms_invite = MetaspaceInvitation.get_existing_invitation(PGDB_TEST, ms_inv_data['metaspace_invitation_code'])
            
            for field_name in MetaspaceInvitation.FIELD_NAMES:
                if field_name not in ['creation_date']:
                    assert ms_inv_data[field_name] == vars(ms_invite)[field_name]

            decision_date_lb = DateTimeUtil.datetime_now_utc_aware()
            ms_invite.create_user_and_accept_invitation(DB_TUPLE_PT_NM, 'jasper', 'passw0rd', 'no comment')
            assert ms_invite.was_accepted
            assert decision_date_lb <= ms_invite.decision_date <= DateTimeUtil.datetime_now_utc_aware()
    
    def decline_test(self):
        ms_inv_data = self.ms_inv_data
        admin_user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
        ms_inv_data['creator'] = admin_user.user_id

        with AutoRollbackTransaction() as test_trans:
            ms_invite = MetaspaceInvitation.create_new_invitation(PGDB_TEST, ms_inv_data['metaspace_invitation_code'], ms_inv_data['invitee_email_addr'], 
                            ms_inv_data['initial_metaspace_privileges'], ms_inv_data['invitation_msg'], ms_inv_data['creator'])
            
            decision_date_lb = DateTimeUtil.datetime_now_utc_aware()
            ms_invite.decline_invitation(PGDB_TEST)
            assert not ms_invite.was_accepted
            assert decision_date_lb <= ms_invite.decision_date <= DateTimeUtil.datetime_now_utc_aware()
            
            ms_invite = MetaspaceInvitation.get_existing_invitation(PGDB_TEST, ms_inv_data['metaspace_invitation_code'])
            assert not ms_invite.was_accepted

def Nodespace_test():
    ns_data = TestData.NS_ARSFT
    admin_user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
    ns_data['creator'] = admin_user.user_id
    
    with AutoRollbackTransaction() as test_trans:
        ns = Nodespace.create_new_nodespace(DB_TUPLE_PT_NM, ns_data['nodespace_name'], ns_data['nodespace_description'], ns_data['creator'])
        ns_data['nodespace_id'] = ns.nodespace_id
        
        for field_name in Nodespace.FIELD_NAMES:
            if field_name not in ['creation_date']:
                assert ns_data[field_name] == vars(ns)[field_name]
        
        ns = Nodespace.get_existing_nodespace(PGDB_TEST, ns_data['nodespace_name'])
        
        for field_name in Nodespace.FIELD_NAMES:
            if field_name not in ['creation_date']:
                assert ns_data[field_name] == vars(ns)[field_name]
        
        assert Nodespace.is_valid_nodespace_name('_named_like-a-private-pyth0n-var')
        assert not Nodespace.is_valid_nodespace_name('')

class NodespaceInvitation_tests(object):
    ns_inv_data = TestData.NS_INV_HORATIO
    
    def accept_test(self):
        ns_inv_data = self.ns_inv_data
        test_ns = Nodespace.get_existing_nodespace(PGDB_TEST, TestData.NODESPACE_1['nodespace_name'])
        admin_user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
        ns_inv_data['nodespace_id'] = test_ns.nodespace_id
        ns_inv_data['creator'] = admin_user.user_id
        
        with AutoRollbackTransaction() as test_trans:
            ns_invite = NodespaceInvitation.create_new_invitation(PGDB_TEST, ns_inv_data['nodespace_invitation_code'], ns_inv_data['invitee_email_addr'], ns_inv_data['nodespace_id'], 
                            ns_inv_data['initial_nodespace_privileges'], ns_inv_data['invitation_msg'], ns_inv_data['creator'])
            ns_inv_data['nodespace_invitation_id'] = ns_invite.nodespace_invitation_id
            ns_inv_data['nodespace_invitation_code'] = ns_invite.nodespace_invitation_code
            
            assert ns_inv_data['nodespace_invitation_code'] is not None
            for field_name in NodespaceInvitation.FIELD_NAMES:
                if field_name not in ['creation_date']:
                    assert ns_inv_data[field_name] == vars(ns_invite)[field_name]
            
            ns_invite = NodespaceInvitation.get_existing_invitation(PGDB_TEST, ns_inv_data['nodespace_invitation_code'])
            
            for field_name in NodespaceInvitation.FIELD_NAMES:
                if field_name not in ['creation_date']:
                    assert ns_inv_data[field_name] == vars(ns_invite)[field_name]
            
            decision_date_lb = DateTimeUtil.datetime_now_utc_aware()
            ns_invite.create_user_and_accept_invitation(DB_TUPLE_PT_NM, ns_inv_data['invitee_username'], ns_inv_data['invitee_password'], 
                                                        ns_inv_data['invitee_user_statement'])
            assert ns_invite.was_accepted == True
            assert decision_date_lb <= ns_invite.decision_date <= DateTimeUtil.datetime_now_utc_aware()
            
            new_user = User.get_existing_user_by_email(PGDB_TEST, ns_inv_data['invitee_email_addr'])
            assert new_user.user_id == ns_invite.user_id
            assert new_user.check_password(ns_inv_data['invitee_password']) == True
    
    def decline_test(self):
        ns_inv_data = self.ns_inv_data
        test_ns = Nodespace.get_existing_nodespace(PGDB_TEST, TestData.NODESPACE_1['nodespace_name'])
        admin_user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
        ns_inv_data['nodespace_id'] = test_ns.nodespace_id
        ns_inv_data['creator'] = admin_user.user_id

        with AutoRollbackTransaction() as test_trans:
            ns_invite = NodespaceInvitation.create_new_invitation(PGDB_TEST, ns_inv_data['nodespace_invitation_code'], ns_inv_data['invitee_email_addr'], ns_inv_data['nodespace_id'], 
                            ns_inv_data['initial_nodespace_privileges'], ns_inv_data['invitation_msg'], ns_inv_data['creator'])
            
            decision_date_lb = DateTimeUtil.datetime_now_utc_aware()
            ns_invite.decline_invitation(PGDB_TEST)
            ns_invite = NodespaceInvitation.get_existing_invitation(PGDB_TEST, ns_inv_data['nodespace_invitation_code'])
            assert ns_invite.was_accepted == False
            assert decision_date_lb <= ns_invite.decision_date <= DateTimeUtil.datetime_now_utc_aware()



def Privileges_tests():
    ns_privs1 = NodespacePrivilegeSet.create_from_list_of_strings([NodespacePrivilegeSet.EDITOR, NodespacePrivilegeSet.MODERATOR])
    ns_privs2 = NodespacePrivilegeSet.create_from_list_of_strings([NodespacePrivilegeSet.MODERATOR, NodespacePrivilegeSet.EDITOR])
    assert ns_privs1 == ns_privs2
    assert ns_privs1.has_all_privileges([NodespacePrivilegeSet.EDITOR, NodespacePrivilegeSet.MODERATOR])
    
    ns_privs1.add_privilege(NodespacePrivilegeSet.ADMIN)
    assert ns_privs1 != ns_privs2
    ns_privs1.remove_privilege(NodespacePrivilegeSet.ADMIN)
    assert ns_privs1 == ns_privs2
    assert not ns_privs1.has_privilege(NodespacePrivilegeSet.ADMIN)
    
    ns_privs3 = NodespacePrivilegeSet()
    ms_privs1 = MetaspacePrivilegeSet()
    
    with AssertExceptionThrown(TypeError):
        ns_privs3 == ms_privs1

def PrivilegeChecker_tests():
    with AssertExceptionThrown(PrivilegeChecker.UnrecognizedActionException):
        MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, 'MOVE_IMMOVABLE_OBJ', None, User())
    with AssertExceptionThrown(PrivilegeChecker.UnrecognizedActionException):
        NodespacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, 'MOVE_IMMOVABLE_OBJ', None, User())

def MetaspacePrivilegeChecker_tests():
    super_user = User()
    super_user.user_id = -1
    super_user.metaspace_privileges = MetaspacePrivilegeSet.create_from_list_of_strings([MetaspacePrivilegeSet.SUPER])
    user_creator_user = User()
    user_creator_user.user_id = -2
    user_creator_user.metaspace_privileges = MetaspacePrivilegeSet.create_from_list_of_strings([MetaspacePrivilegeSet.CREATE_USER])
    space_creator_user = User()
    space_creator_user.user_id = -3
    space_creator_user.metaspace_privileges = MetaspacePrivilegeSet.create_from_list_of_strings([MetaspacePrivilegeSet.CREATE_SPACE])
    target_user = User()
    target_user.user_id = -4
    target_user.metaspace_privileges = MetaspacePrivilegeSet()
    
    for temp_user in [super_user, user_creator_user, space_creator_user, target_user]:
        setattr(temp_user, 'email_addr', 'dummy_email_%i@test.com' % temp_user.user_id)
    
    assert MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.CREATE_USER_ACTION, None, super_user)
    assert MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.CREATE_USER_ACTION, None, user_creator_user)
    assert MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.ALTER_USER_INFO_ACTION, target_user, super_user)
    assert MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.ALTER_USER_INFO_ACTION, target_user, target_user)
    assert not MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.ALTER_USER_INFO_ACTION, target_user, user_creator_user, False)
    assert not MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.ALTER_USER_ACCESS_ACTION, target_user, user_creator_user, False)
    assert not MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.CREATE_USER_ACTION, None, space_creator_user, False)
    with AssertExceptionThrown(PrivilegeChecker.InsufficientPrivilegesException):
        MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.CREATE_USER_ACTION, None, space_creator_user)
    assert MetaspacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, MetaspacePrivilegeChecker.CREATE_SPACE_ACTION, None, space_creator_user)

def NodespacePrivilegeChecker_tests():
    ns_inv_data = TestData.NS_INV_HORATIO
    test_ns = Nodespace.get_existing_nodespace(PGDB_TEST, TestData.NODESPACE_1['nodespace_name'])
    admin_user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
    
    ns_inv_data['nodespace_id'] = test_ns.nodespace_id
    ns_inv_data['creator'] = admin_user.user_id
    
    with AutoRollbackTransaction() as test_trans:
        ns_invite = NodespaceInvitation.create_new_invitation(PGDB_TEST, ns_inv_data['nodespace_invitation_code'], ns_inv_data['invitee_email_addr'], ns_inv_data['nodespace_id'], 
                                                            ns_inv_data['initial_nodespace_privileges'], ns_inv_data['invitation_msg'], ns_inv_data['creator'])
        new_user = ns_invite.create_user_and_accept_invitation(DB_TUPLE_PT_NM, ns_inv_data['invitee_username'], ns_inv_data['invitee_password'], ns_inv_data['invitee_user_statement'])
        assert not NodespacePrivilegeChecker.is_allowed_to_do(PGDB_TEST, NodespacePrivilegeChecker.ALTER_NODESPACE_ACCESS_ACTION, test_ns, new_user, False)

def MetaspaceSession_tests():
    user = User.get_existing_user_by_email(PGDB_TEST, TestData.USER_ADMIN['email_addr'])
    
    with AutoRollbackTransaction() as test_trans:
        creation_date_lb = DateTimeUtil.datetime_now_utc_aware()
        ms_session = MetaspaceSession.create_new_session(PGDB_TEST, user.user_id)
        creation_date_ub = DateTimeUtil.datetime_now_utc_aware()
        assert user.user_id == ms_session.user_id
        assert ms_session.is_session_valid()
        assert creation_date_lb <= ms_session.creation_date <= creation_date_ub
        
        last_visit_lb = DateTimeUtil.datetime_now_utc_aware()
        ms_session.touch_session(PGDB_TEST)
        last_visit_ub = DateTimeUtil.datetime_now_utc_aware()
        assert last_visit_lb <= ms_session.last_visit <= last_visit_ub
        
        ms_session = MetaspaceSession.get_existing_session(PGDB_TEST, ms_session.metaspace_session_id)
        assert user.user_id == ms_session.user_id
        assert ms_session.is_session_valid()
        assert creation_date_lb <= ms_session.creation_date <= creation_date_ub
        assert last_visit_lb <= ms_session.last_visit <= last_visit_ub
        
        # fake session expiry for idle time being exceeded
        old_ms_session_id = ms_session.metaspace_session_id
        upd_params = {'last_visit': web.SQLLiteral("last_visit - (interval '%i seconds')" % (MetaspaceSession.MAX_SESSION_IDLE_TIME+60))}
        PGDB_TEST.update(MetaspaceSession.TABLE_NAME, where='metaspace_session_id = $metaspace_session_id', 
                    vars={'metaspace_session_id': ms_session.metaspace_session_id}, **upd_params)
        ms_session = MetaspaceSession.get_existing_session(PGDB_TEST, ms_session.metaspace_session_id)
        assert not ms_session.is_session_valid()
        
        # force create a new session and see that it has the correct info
        creation_date_lb = DateTimeUtil.datetime_now_utc_aware()
        ms_session = MetaspaceSession.force_create_new_session(PGDB_TEST, user.user_id)
        creation_date_ub = DateTimeUtil.datetime_now_utc_aware()
        # there is actually a fleeting chance of the same session id, but it's exceedingly unlikely
        assert ms_session.metaspace_session_id != old_ms_session_id
        assert user.user_id == ms_session.user_id
        assert ms_session.is_session_valid()
        assert creation_date_lb <= ms_session.creation_date <= creation_date_ub
        
        # fake session expiry for overall age
        upd_params = {'creation_date': web.SQLLiteral("creation_date - (interval '%i seconds')" % (MetaspaceSession.MAX_SESSION_AGE+60))}
        PGDB_TEST.update(MetaspaceSession.TABLE_NAME, where='metaspace_session_id = $metaspace_session_id', 
                    vars={'metaspace_session_id': ms_session.metaspace_session_id}, **upd_params)
        ms_session = MetaspaceSession.get_existing_session(PGDB_TEST, ms_session.metaspace_session_id)
        assert not ms_session.is_session_valid()
        
        # test killing the expired session, which should blank out the existing object and remove the session from the db
        old_ms_session_id = ms_session.metaspace_session_id
        ms_session.kill_session(PGDB_TEST)
        assert ms_session.metaspace_session_id is None
        assert MetaspaceSession.get_existing_session(PGDB_TEST, old_ms_session_id) is None
        