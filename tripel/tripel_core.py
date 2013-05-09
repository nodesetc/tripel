"""
TODO:
* make it so that the enabled fields are meaningful (e.g. don't create sessions for disabled users).
* write more unit tests
  * test various permutations of priv set stuff (pass in None, pass in empty set, pass in some privs, pass in redundant privs)
  * test transactionality of compound operations
  * get coverage to 100%
* break things out into more specialized modules
* make sure usage of invite/invitation is consistent, so that the former is always used as a verb and the latter as a noun
"""

import logging

import web
import cryptacular.bcrypt
from py2neo import neo4j, cypher, rest

import config.parameters as params
import util
from util import DateTimeUtil

logger = logging.getLogger(__name__)

# the name of the DB schema in which we're working.  applies to the whole module for now.
SCHEMA_NAME = 'tripel'


class PgUtil(object):
    @staticmethod
    def get_db_conn_ssl(dbname, username, password, hostaddr=params.PG_HOST_ADDR):
        return web.database(dbn='postgres', sslmode='require', hostaddr=hostaddr, dbname=dbname, user=username, pw=password)
    
    @staticmethod
    def get_next_seq_val(pgdb, seqname):
        return pgdb.query("select nextval($seqname) next_seq_val;", vars={'seqname': seqname})[0]['next_seq_val']

#TODO: should have default sort orders for queries
class PgPersistent(object):
    """
    subclass this and define the following constants to facilitate simple object/row mapping:
     TABLE_NAME: the name of the table whose rows map to the object.
     PK_COL_NAME: the name of the primary key column in the table 
     SEQ_NAME: name of the sequence from which the PK col is populated.
     FIELD_NAMES: a list of strings representing the names of the columns in the table.
    """

    @classmethod
    def _create_instance_from_query_row(cls, query_row):
        result = cls()
        for field_name in cls.FIELD_NAMES:
            setattr(result, field_name, query_row[field_name])
        result._massage_raw_pg_output_vals()
        return result

    @classmethod
    def _get_single_obj_instance(cls, pgdb, where_clause_vars):
        query_results = pgdb.where(cls.TABLE_NAME, **where_clause_vars)
        if len(query_results) == 1:
            return cls._create_instance_from_query_row(query_results[0])
        else:
            return None

    @classmethod
    def _get_obj_list(cls, pgdb, where_clause_vars, order=None):
        query_results = pgdb.where(cls.TABLE_NAME, order=order, **where_clause_vars)
        return cls._query_results_to_obj_list(query_results)
    
    @classmethod
    def _query_results_to_obj_list(cls, query_results):
        return map(cls._create_instance_from_query_row, query_results)
    
    def _ins_obj_instance_and_set_pk_att(self, pgdb, ins_params=None):
        if ins_params == None:
            ins_params = self.__dict__.copy()
        pk_val = pgdb.insert(self.TABLE_NAME, seqname=self.SEQ_NAME, **ins_params)
        setattr(self, self.PK_COL_NAME, pk_val)
    
    def _massage_raw_pg_output_vals(self):
        """
        subclasses should implement this method if _create_instance_from_query_row 
        will fill any of the object fields with the wrong thing for when the object
        is actually used.  e.g., privilege list fields will come back from the db as string 
        literals, but generally you want the object field to be a PrivilegeSet object.  the 
        subclass can then implement this method to turn the string literal into the desired 
        object.
        """
        pass


class NeoUtil(object):
    class TripelBatch(neo4j.WriteBatch):
        def __enter__(self):
            return self
        def __exit__(self, type, value, traceback):
            if value is None:
                self.submit()
                return True
            return False
    
    @staticmethod
    def get_db_conn(db_uri=params.NEO_DB_URI):
        return neo4j.GraphDatabaseService(db_uri)
    
    @staticmethod
    def _execute_parameterized_gremlin_script(neodb, script, params):
        '''
        ripped off and repurposed http://pythonhosted.org/py2neo/_modules/py2neo/gremlin.html#execute
        '''
        try:
            uri = neodb._extension_uri('GremlinPlugin', 'execute_script')
        except NotImplementedError:
            raise NotImplementedError("Gremlin functionality not available")
        req = rest.Request(neodb, "POST", uri, {'script': script, 'params': params})
        logger.debug('req.body = %s' % req.body)
        resp = neodb._send(req)
        return resp.body
    
    @classmethod
    def get_gremlin_lib_scripts(cls, script_file_names=params.GREMLIN_LIB_FILES):
        #TODO: should really avoid loading from disk every time
        return map(util.get_file_contents, script_file_names)
    
    @classmethod
    def init_gremlin_env(cls, neodb, gremlin_scripts=None):
        gremlin_scripts = gremlin_scripts if gremlin_scripts is not None else cls.get_gremlin_lib_scripts()
        return map(lambda x: cls._execute_parameterized_gremlin_script(neodb, x, None), gremlin_scripts)
    
    @classmethod
    def _execute_gremlin_script_with_lazy_init(cls, neodb, script, params):
        '''
        mechanism inspired by: http://www.mattluongo.com/post/client-side-gremlin-libraries-in-neo4j
        '''
        try:
            return cls._execute_parameterized_gremlin_script(neodb, script, params)
        except rest.BadRequest as br_ex:
            if br_ex.message.find("javax.script.ScriptException: groovy.lang.MissingPropertyException:") == 0:
                cls.init_gremlin_env(neodb)
                return cls._execute_parameterized_gremlin_script(neodb, script, params)
            else:
                logger.warn(br_ex.message)
                logger.warn('bad gremlin request.  stacktrace: %s' % '\n'.join(br_ex.stacktrace))
                raise br_ex
    
    @classmethod
    def run_gremlin_statements(cls, neodb, stmt_defs, should_run_in_transaction=True, should_lazy_init=False, should_pre_init=True):
        """
        take a database connection and a list of dictionaries describing the gremlin statements to be run,
        build the gremlin code, then run it (in a transaction by default).
        
        more detail...
        
        each entry in stmt_defs has the following fields:
        * method_name: the name of the gremlin method to be called.
        * param_list: a list of the names of the parameters it will be called with (in order).
        * param_cast_list: optional.  if present, a list where each entry is None or a string, corresponding 
          to each element in param_list, specifying what type (if any) each should be cast to in the call.
        * param_values: a dictionary with a value for each parameter that needs a value (so not g for example, 
          since that's provided by the gremlin interpreter).
        * py_result: not used by this method, but the functions that usually provide stmt_defs entries should 
          provide this for the reference of their callers.  the python object (if any) that corresponds to the 
          entry created in the DB (e.g. the domain object that corresponds to the node this statement created).
        
        based on stmt_defs, this method constructs a block of gremlin code from the defined statements in the 
        order provided.  it also constructs a master dictionary of all parameter values, taking care to prevent
        naming conflicts between multiple statements that might use the same param names.  by default, the block
        of code is run in a transaction (by wrapping it in a closure and passing that to execInTransaction).  by
        default it's also run prefixed with the code for the GremlinUtils helper class.
        
        for example, consider a call where stmt_defs is:
        [{'method_name': 'createAndIndexNeoNode', 
         'param_list': ['g', 'nodespace_props', 'fields_to_index'], 
         'param_values': {'nodespace_props':{'name':'...'}...}, 
         'py_result': <NodespaceNode object>}
        {'method_name': 'createAndIndexAndLinkNeoNode', 
         'param_list': ['g', 'root_cat_props', 'fields_to_index', 'edge_info_list'], 
         'param_cast_list': [None, None, None, (Map[])],
         'param_values': {'root_cat_props':...}, 
         'py_result': <RootCategoryNode object>}]
        
        (note that each entry of the dict in the 'param_values' field may itself be a dict.  the values are 
        whatever's expected by the gremlin method being invoked.  python dictionaries should automatically be
        interpreted as maps by groovy/gremlin.)

        said stmt_defs would then generate the following block of gremlin (assuming it gets run as a transaction,
        and omitting the library code loaded at the top):
        
        //GremlinUtils definition stuff up here...
        result = GremlinUtils.execInTransaction(g, { -> 
          result_0 = createAndIndexNeoNode(g, nodespace_props_0, fields_to_index_0);
          result_1 = createAndIndexAndLinkNeoNode(g, root_cat_props_1, fields_to_index_1, (Map[]) edge_info_list_1);
          return [result_0, result_1]
          //you might also note that the assignment of each statement to a predictably named variable lets you 
          //refer to intermediate results among statements, e.g. the second call could've referenced result_0
        })
        
        said stmt_defs would also be used to generate a dictionary with fields such as 'nodespace_props_0' and 
        'root_cat_props_1'.  this master parameter dictionary gets passed in with the generated gremlin script
        for execution.  if all goes well, the script executes successfully, the transaction commits, and a list 
        of results (one per statement) is returned.  if not so well, the transaction rolls back and an error is 
        returned.
        
        while this may seem very convoluted, i hope it will allow cleaner and more maintainable code when many 
        different parts of the codebase need to make transactional multi-statement gremlin calls, which it would
        appear is the only way to get real transactions over a REST connection.
        
        oh, and the init stuff:
        * should_lazy_init=True runs the built up script using a method that will attempt to initialize the gremlin
          environment with the library class(es) if it looks like script execution failed due to the libraries not
          being found.
        * should_pre_init=True just puts the library code in front of the block to be executed, every time it's
          executed, in case the interpreter isn't caching scripts as expected.  bit of a hack.  will cause should_lazy_init
          to be ignored if it's true (if in-lining that stuff doesn't allow it to be recognized, it's unlikely we can rely 
          on the caching).
        """
        master_params = {}
        rendered_stmt_list = []
        result_var_name_list = []
        
        for i in range(len(stmt_defs)):
            stmt_def = stmt_defs[i]
            stmt_method_name = stmt_def['method_name']
            stmt_param_list = stmt_def['param_list']
            stmt_param_cast_list = stmt_def['param_cast_list'] if 'param_cast_list' in stmt_def else None
            assert stmt_param_cast_list is None or len(stmt_param_cast_list) == len(stmt_param_list)
            stmt_param_values = stmt_def['param_values']
            
            stmt_master_param_list = []
            for j in range(len(stmt_param_list)):
                param_name = stmt_param_list[j]
                if param_name in stmt_param_values:
                    master_param_name = '%s_%i' % (param_name, i)
                    master_params[master_param_name] = stmt_param_values[param_name]
                    stmt_master_param_list.append(master_param_name)
                else:
                    stmt_master_param_list.append(param_name)
                
                if stmt_param_cast_list is not None and stmt_param_cast_list[j] is not None:
                    stmt_master_param_list[j] = '%s %s' % (stmt_param_cast_list[j], stmt_master_param_list[j])
            
            stmt_result_var_name = 'result_%i' % i
            result_var_name_list.append(stmt_result_var_name)
            stmt_param_string = ', '.join(stmt_master_param_list)
            rendered_stmt_list.append('  %s = %s(%s)' % (stmt_result_var_name, stmt_method_name, stmt_param_string))
        
        rendered_stmt_list.append('  return [%s]' % ', '.join(result_var_name_list))
        stmt_block = '\n'.join(rendered_stmt_list)
        
        
        if should_run_in_transaction:
            stmt_block = "result = GremlinUtils.execInTransaction(g, { -> \n%s\n})" % stmt_block
        
        if should_pre_init:
            gremlin_lib_scripts = cls.get_gremlin_lib_scripts()
            gremlin_lib_stmt_block = '\n'.join(gremlin_lib_scripts)
            stmt_block = '%s\n\n%s' % (gremlin_lib_stmt_block, stmt_block)
            
            # pre-initializing by putting the library code at the top of the gremlin statement
            # block obviates the need for lazy initialization.  if the gremlin interpreter doesn't 
            # recognize the utility class when it's inline, things are hosed.
            should_lazy_init = False
        
        if should_lazy_init:
            execution_fn = cls._execute_gremlin_script_with_lazy_init
        else:
            execution_fn = cls._execute_parameterized_gremlin_script
        
        
        return execution_fn(neodb, stmt_block, master_params)
    
    @staticmethod
    def get_create_and_index_edge_stmt_def(out_node_lookup_info, in_node_lookup_info, edge_type, edge_props, fields_to_index, py_result):
        return {'method_name': 'GremlinUtils.createAndIndexEdge',
                'param_list': ['g', 'out_node_lookup_info', 'in_node_lookup_info', 'edge_type', 'edge_props', 'fields_to_index'],
                'param_values': {'out_node_lookup_info': out_node_lookup_info, 
                                'in_node_lookup_info': in_node_lookup_info,
                                'edge_type': edge_type,
                                'edge_props': edge_props, 
                                'fields_to_index': fields_to_index},
                'py_result': py_result}
    
    @staticmethod
    def get_create_and_index_node_stmt_def(node_props, fields_to_index, py_result):
        return {'method_name': 'GremlinUtils.createAndIndexNode',
                'param_list': ['g', 'node_props', 'fields_to_index'],
                'param_values': {'node_props': node_props, 
                                    'fields_to_index': fields_to_index},
                'py_result': py_result}


#TODO: each graph element should have a gremlin data integrity check fn, to be run in the transaction and throw an 
# error if expected constraints aren't met (e.g., edge connecting to the wrong node type)
class TripelGraphElement(object):
    FULLTEXT_IDX_CONFIG = {'provider': 'lucene', 'type': 'fulltext', 'to_lower_case': 'true'}
    
    class MissingRequiredFieldError(Exception):
        pass
    
    @classmethod
    def _get_required_fields(cls):
        raise NotImplementedError('subclass must implement this')
    
    def _has_all_required_fields(self):
        for req_field in self._get_required_fields():
            if req_field not in self._properties.keys() or self._properties[req_field] is None:
                return False
        return True
    
    @classmethod
    def _init_from_properties(cls, properties):
        elt = cls()
        elt._properties = properties.copy()
        if not elt._has_all_required_fields():
            raise cls.MissingRequiredFieldError()
        return elt

class TripelEdge(TripelGraphElement):
    UNIQUE_EDGE_ID_PG_SEQ_NAME = '%s.unique_neo_edge_id' % SCHEMA_NAME
    UNIQUE_EDGE_ID_INDEX_NAME = 'UNQ_EDGE_ID_IDX'
    UNIQUE_EDGE_ID_FIELD_NAME = '_TRPL_UNQ_EDGE_ID'
    
    @classmethod
    def _get_fields_to_index(cls):
        '''returns a dictionary where keys are index names and values are the fields to add under that index'''
        return {cls.UNIQUE_EDGE_ID_INDEX_NAME: [cls.UNIQUE_EDGE_ID_FIELD_NAME]}
    
    @classmethod
    def _get_required_fields(cls):
        return [cls.UNIQUE_EDGE_ID_FIELD_NAME]
    
    @classmethod
    def _get_next_unique_edge_id(cls, pgdb):
        return PgUtil.get_next_seq_val(pgdb, cls.UNIQUE_EDGE_ID_PG_SEQ_NAME)
    
    @classmethod
    def get_unique_edge_id_index(cls, neodb):
        return neodb.get_or_create_index(neo4j.Relationship, cls.UNIQUE_EDGE_ID_INDEX_NAME)
    
    @classmethod
    def _init_for_create(cls, pgdb, properties):
        properties = properties.copy()
        properties[cls.UNIQUE_EDGE_ID_FIELD_NAME] = cls._get_next_unique_edge_id(pgdb)
        return cls._init_from_properties(properties)
    
    @classmethod
    def _get_create_edge_stmt_def(cls, pgdb, out_node_lookup_info, in_node_lookup_info, properties, additional_params=None):
        tripel_edge = cls._init_for_create(pgdb, properties)
        stmt_def = NeoUtil.get_create_and_index_edge_stmt_def(out_node_lookup_info, in_node_lookup_info, cls.EDGE_TYPE, 
                                                                tripel_edge._properties, tripel_edge._get_fields_to_index(), tripel_edge)
        return stmt_def
    
    @classmethod
    def _create_new_edge(cls, db_tuple, out_node_lookup_info, in_node_lookup_info, properties, additional_params, should_run_gremlin_immediately):
        pgdb, neodb = db_tuple
        stmt_def = cls._get_create_edge_stmt_def(pgdb, out_node_lookup_info, in_node_lookup_info, properties, additional_params)
        if should_run_gremlin_immediately:
            NeoUtil.run_gremlin_statements(neodb, [stmt_def])
            return stmt_def['py_result']
        else:
            return [stmt_def]
    
    #TODO: for sort of cheap integrity checking, take an optional type for the nodes to be found.  if type is provided 
    # but not matched, throw an exception
    @classmethod
    def link_nodes_by_unique_id(cls, db_tuple, out_node_unq_id, in_node_unq_id, properties, should_run_gremlin_immediately=True):
        out_node_lookup_info = {'lookupIndexName': TripelNode.UNIQUE_NODE_ID_INDEX_NAME, 
                                'lookupKey': TripelNode.UNIQUE_NODE_ID_FIELD_NAME, 
                                'lookupValue': out_node_unq_id}
        in_node_lookup_info = {'lookupIndexName': TripelNode.UNIQUE_NODE_ID_INDEX_NAME, 
                                'lookupKey': TripelNode.UNIQUE_NODE_ID_FIELD_NAME, 
                                'lookupValue': in_node_unq_id}
        return cls._create_new_edge(db_tuple, out_node_lookup_info, in_node_lookup_info, properties, {}, should_run_gremlin_immediately)

class CategoryRootEdge(TripelEdge):
    EDGE_TYPE = 'IS_ROOT_CAT_FOR'
    
    @classmethod
    def link_cat_root_to_nodespace(cls, db_tuple, root_cat_node_unq_id, nodespace_id, properties, should_run_gremlin_immediately=True):
        out_node_lookup_info = {'lookupIndexName': RootCategoryNode.UNIQUE_NODE_ID_INDEX_NAME, 
                                'lookupKey': RootCategoryNode.UNIQUE_NODE_ID_FIELD_NAME, 
                                'lookupValue': root_cat_node_unq_id}
        in_node_lookup_info = {'lookupIndexName': NodespaceNode.NODESPACE_INDEX_NAME, 
                                'lookupKey': NodespaceNode.NODESPACE_ID_FIELD_NAME, 
                                'lookupValue': nodespace_id}
        return cls._create_new_edge(db_tuple, out_node_lookup_info, in_node_lookup_info, properties, {}, should_run_gremlin_immediately)

class CreatedByEdge(TripelEdge):
    EDGE_TYPE = 'CREATED_BY'
    CREATED_BY_INDEX_NAME = 'CREATED_BY_IDX'
    USER_ID_FIELD_NAME = '_TRPL_USER_ID'
    CREATION_DATE_FIELD_NAME = '_TRPL_CREATION_DATE'
    
    @classmethod
    def _get_fields_to_index(cls):
        idx_fields = super(cls, cls)._get_fields_to_index().copy()
        idx_fields.update({cls.CREATED_BY_INDEX_NAME: [cls.USER_ID_FIELD_NAME]})
        return idx_fields
    
    @classmethod
    def _get_required_fields(cls):
        return super(cls, cls)._get_required_fields() + [cls.USER_ID_FIELD_NAME, cls.CREATION_DATE_FIELD_NAME]
    
    @classmethod
    def get_created_by_index(cls, neodb):
        return neodb.get_or_create_index(neo4j.Relationship, cls.CREATED_BY_INDEX_NAME)
    
    @classmethod
    def link_node_to_creator(cls, db_tuple, out_node_unq_id, creator_user_id, should_run_gremlin_immediately=True):
        out_node_lookup_info = {'lookupIndexName': TripelNode.UNIQUE_NODE_ID_INDEX_NAME, 
                                'lookupKey': TripelNode.UNIQUE_NODE_ID_FIELD_NAME, 
                                'lookupValue': out_node_unq_id}
        in_node_lookup_info = {'lookupIndexName': UserNode.USER_INDEX_NAME, 
                                'lookupKey': UserNode.USER_ID_FIELD_NAME, 
                                'lookupValue': creator_user_id}
        edge_props = {}
        edge_props[cls.CREATION_DATE_FIELD_NAME] = str(DateTimeUtil.datetime_now_utc_aware())
        edge_props[cls.USER_ID_FIELD_NAME] = creator_user_id
        return cls._create_new_edge(db_tuple, out_node_lookup_info, in_node_lookup_info, edge_props, {}, should_run_gremlin_immediately)

class SubcategoryEdge(TripelEdge):
    EDGE_TYPE = 'HAS_PARENT_CAT'

class CategorizationEdge(TripelEdge):
    EDGE_TYPE = 'BELONGS_TO_CAT'

class CommentReplyEdge(TripelEdge):
    EDGE_TYPE = 'HAS_PARENT_COMMENT'

class CommentAttachEdge(TripelEdge):
    EDGE_TYPE = 'COMMENTS_ON'

"""
TODO: alerts, recs, messages, etc:  since cypher and gremlin can create links, here's a scheme for alerts:
*each user has a set of saved searches.
*each user has an alerts node.  it links to nodes about which they should be alerted (or maybe link to an intermediate 
node that links to the result and the search(es) that resulted in the hit).
*saved searches are run periodically, alerts are tracked.
*email is sent periodically listing alerted nodes in reverse chronological order of alert (i.e., newest alert first)
"""
class TripelNode(TripelGraphElement):
    NODE_TYPE_FIELD_NAME = '_TRPL_NODE_TYPE'
    UNIQUE_NODE_ID_PG_SEQ_NAME = '%s.unique_neo_node_id' % SCHEMA_NAME
    UNIQUE_NODE_ID_INDEX_NAME = 'UNQ_NODE_ID_IDX'
    UNIQUE_NODE_ID_FIELD_NAME = '_TRPL_UNQ_NODE_ID'
    
    @classmethod
    def _get_fields_to_index(cls):
        '''returns a dictionary where keys are index names and values are the fields to add under that index'''
        return {cls.UNIQUE_NODE_ID_INDEX_NAME: [cls.UNIQUE_NODE_ID_FIELD_NAME]}
    
    @classmethod
    def _get_required_fields(cls):
        return [cls.UNIQUE_NODE_ID_FIELD_NAME, cls.NODE_TYPE_FIELD_NAME]
    
    @classmethod
    def _get_next_unique_node_id(cls, pgdb):
        return PgUtil.get_next_seq_val(pgdb, cls.UNIQUE_NODE_ID_PG_SEQ_NAME)
    
    @classmethod
    def _init_for_create(cls, pgdb, properties):
        properties = properties.copy()
        properties[cls.NODE_TYPE_FIELD_NAME] = cls.NODE_TYPE
        properties[cls.UNIQUE_NODE_ID_FIELD_NAME] = cls._get_next_unique_node_id(pgdb)
        return cls._init_from_properties(properties)
    
    @classmethod
    def _init_from_neo_node(cls, neo_node):
        return cls._init_from_properties(neo_node.get_properties().copy())
    
    @classmethod
    def get_unique_node_id_index(cls, neodb):
        return neodb.get_or_create_index(neo4j.Node, cls.UNIQUE_NODE_ID_INDEX_NAME)
    
    @classmethod
    def _get_create_node_stmt_def(cls, pgdb, properties, additional_params=None):
        tripel_node = cls._init_for_create(pgdb, properties)
        stmt_def = NeoUtil.get_create_and_index_node_stmt_def(tripel_node._properties, tripel_node._get_fields_to_index(), tripel_node)
        return stmt_def
    
    @classmethod
    def _create_new_node(cls, db_tuple, properties, additional_params, should_run_gremlin_immediately):
        pgdb, neodb = db_tuple
        stmt_def = cls._get_create_node_stmt_def(pgdb, properties, additional_params)
        if should_run_gremlin_immediately:
            NeoUtil.run_gremlin_statements(neodb, [stmt_def])
            return stmt_def['py_result']
        else:
            return [stmt_def]
    
    @classmethod
    def get_existing_node_by_unique_id(cls, neodb, unique_node_id):
        return cls._init_from_neo_node(cls.get_unique_node_id_index(neodb).get(cls.UNIQUE_NODE_ID_FIELD_NAME, str(unique_node_id))[0])

class NodespaceNode(TripelNode):
    NODE_TYPE = 'NODESPACE'
    NODESPACE_INDEX_NAME = 'NODESPACE_IDX'
    NODESPACE_ID_FIELD_NAME = '_TRPL_NODESPACE_ID'
    
    @classmethod
    def _get_fields_to_index(cls):
        idx_fields = super(cls, cls)._get_fields_to_index().copy()
        idx_fields.update({cls.NODESPACE_INDEX_NAME: [cls.NODESPACE_ID_FIELD_NAME]})
        return idx_fields
    
    @classmethod
    def _get_required_fields(cls):
        return super(cls, cls)._get_required_fields() + [cls.NODESPACE_ID_FIELD_NAME]
    
    @classmethod
    def get_nodespace_index(cls, neodb):
        return neodb.get_or_create_index(neo4j.Node, cls.NODESPACE_INDEX_NAME)
    
    @classmethod
    def get_existing_nodespace_node(cls, neodb, nodespace_id):
        ns_neo_node = cls.get_nodespace_index(neodb).get(cls.NODESPACE_ID_FIELD_NAME, str(nodespace_id))[0]
        return cls._init_from_neo_node(ns_neo_node) if ns_neo_node is not None else None
    
    @classmethod
    def create_new_nodespace_node(cls, db_tuple, nodespace_id, properties, should_run_gremlin_immediately=True):
        properties = properties.copy()
        properties[cls.NODESPACE_ID_FIELD_NAME] = nodespace_id
        return cls._create_new_node(db_tuple, properties, {}, should_run_gremlin_immediately)

class UserNode(TripelNode):
    NODE_TYPE = 'USER'
    USER_INDEX_NAME = 'USER_IDX'
    USER_ID_FIELD_NAME = '_TRPL_USER_ID'
    
    @classmethod
    def _get_fields_to_index(cls):
        idx_fields = super(cls, cls)._get_fields_to_index().copy()
        idx_fields.update({cls.USER_INDEX_NAME: [cls.USER_ID_FIELD_NAME]})
        return idx_fields
    
    @classmethod
    def _get_required_fields(cls):
        return super(cls, cls)._get_required_fields() + [cls.USER_ID_FIELD_NAME]
    
    @classmethod
    def get_user_index(cls, neodb):
        return neodb.get_or_create_index(neo4j.Node, cls.USER_INDEX_NAME)
    
    @classmethod
    def get_existing_user_node(cls, neodb, user_id):
        ns_neo_node = cls.get_user_index(neodb).get(cls.USER_ID_FIELD_NAME, str(user_id))[0]
        return cls._init_from_neo_node(ns_neo_node) if ns_neo_node is not None else None
    
    @classmethod
    def create_new_user_node(cls, db_tuple, user_id, properties, should_run_gremlin_immediately=True):
        properties = properties.copy()
        properties[cls.USER_ID_FIELD_NAME] = user_id
        return cls._create_new_node(db_tuple, properties, {}, should_run_gremlin_immediately)

class RootCategoryNode(TripelNode):
    NODE_TYPE = 'ROOT_CATEGORY'
    
    @classmethod
    def _get_create_node_stmt_def(cls, pgdb, properties, additional_params=None):
        tripel_node = cls._init_for_create(pgdb, properties)
        stmt_def = NeoUtil.get_create_and_index_node_stmt_def(tripel_node._properties, tripel_node._get_fields_to_index(), tripel_node)
        return stmt_def
    
    @classmethod
    def create_new_root_category_node(cls, db_tuple, nodespace_id, properties, should_run_gremlin_immediately=True):
        pgdb, neodb = db_tuple
        create_node_stmts = cls._create_new_node(db_tuple, properties, {'nodespace_id': nodespace_id}, False)
        root_cat_node_unq_id = create_node_stmts[0]['py_result']._properties[cls.UNIQUE_NODE_ID_FIELD_NAME]
        link_to_ns_stmts = CategoryRootEdge.link_cat_root_to_nodespace(db_tuple, root_cat_node_unq_id, nodespace_id, properties, False)
        stmt_defs = create_node_stmts + link_to_ns_stmts
        
        if should_run_gremlin_immediately:
            NeoUtil.run_gremlin_statements(neodb, stmt_defs)
            return create_node_stmts[0]['py_result']
        else:
            return stmt_defs

class CategoryNode(TripelNode):
    NODE_TYPE = 'CATEGORY'
    CATEGORY_INDEX_NAME = 'CATEGORY_IDX'
    CAT_NAME_FIELD_NAME = '_TRPL_CAT_NAME'
    CAT_DESC_FIELD_NAME = '_TRPL_CAT_DESC'
    
    @classmethod
    def _get_fields_to_index(cls):
        idx_fields = super(cls, cls)._get_fields_to_index().copy()
        idx_fields.update({cls.CATEGORY_INDEX_NAME: [cls.CAT_NAME_FIELD_NAME, cls.CAT_DESC_FIELD_NAME]})
        return idx_fields
    
    @classmethod
    def _get_required_fields(cls):
        return super(cls, cls)._get_required_fields() + [cls.CAT_NAME_FIELD_NAME, cls.CAT_DESC_FIELD_NAME]
    
    @classmethod
    def get_category_index(cls, neodb):
        return neodb.get_or_create_index(neo4j.Node, cls.CATEGORY_INDEX_NAME, config=cls.FULLTEXT_IDX_CONFIG)
    
    @classmethod
    def _get_create_node_stmt_def(cls, pgdb, properties, additional_params=None):
        tripel_node = cls._init_for_create(pgdb, properties)
        stmt_def = NeoUtil.get_create_and_index_node_stmt_def(tripel_node._properties, tripel_node._get_fields_to_index(), tripel_node)
        return stmt_def
    
    @classmethod
    def create_new_category_node(cls, db_tuple, parent_cat_unique_node_id, creator_user_id, cat_name, cat_desc, properties, should_run_gremlin_immediately=True):
        pgdb, neodb = db_tuple
        properties = properties.copy()
        properties[cls.CAT_NAME_FIELD_NAME] = cat_name
        properties[cls.CAT_DESC_FIELD_NAME] = cat_desc
        
        create_node_stmts = cls._create_new_node(db_tuple, properties, {}, False)
        cat_node_unq_id = create_node_stmts[0]['py_result']._properties[cls.UNIQUE_NODE_ID_FIELD_NAME]
        link_to_creator_stmts = CreatedByEdge.link_node_to_creator(db_tuple, cat_node_unq_id, creator_user_id, False)
        link_to_parent_stmts = SubcategoryEdge.link_nodes_by_unique_id(db_tuple, cat_node_unq_id, parent_cat_unique_node_id, {}, False)
        stmt_defs = create_node_stmts + link_to_creator_stmts + link_to_parent_stmts
        
        if should_run_gremlin_immediately:
            NeoUtil.run_gremlin_statements(neodb, stmt_defs)
            return create_node_stmts[0]['py_result']
        else:
            return stmt_defs
    
    #TODO: deletion
    #TODO: lookup
    #TODO: children added/modified after a given date (for notifications)
    
class CommentNode(TripelNode):
    NODE_TYPE = 'COMMENT'
    COMMENT_INDEX_NAME = 'COMMENT_IDX'
    COMMENT_SUBJECT_FIELD_NAME = '_TRPL_COM_SUBJ'
    COMMENT_BODY_FIELD_NAME = '_TRPL_COM_BODY'
    
    @classmethod
    def _get_fields_to_index(cls):
        idx_fields = super(cls, cls)._get_fields_to_index().copy()
        idx_fields.update({cls.COMMENT_INDEX_NAME: [cls.COMMENT_SUBJECT_FIELD_NAME, cls.COMMENT_BODY_FIELD_NAME]})
        return idx_fields
    
    @classmethod
    def _get_required_fields(cls):
        return super(cls, cls)._get_required_fields() + [cls.COMMENT_SUBJECT_FIELD_NAME, cls.COMMENT_BODY_FIELD_NAME]
    
    @classmethod
    def get_comment_index(cls, neodb):
        return neodb.get_or_create_index(neo4j.Node, cls.COMMENT_INDEX_NAME, config=cls.FULLTEXT_IDX_CONFIG)
    
    @classmethod
    def _get_create_node_stmt_def(cls, pgdb, properties, additional_params=None):
        tripel_node = cls._init_for_create(pgdb, properties)
        stmt_def = NeoUtil.get_create_and_index_node_stmt_def(tripel_node._properties, tripel_node._get_fields_to_index(), tripel_node)
        return stmt_def
    
    @classmethod
    def _create_new_comment_node(cls, db_tuple, parent_unique_node_id, edge_type, creator_user_id, comment_subj, comment_body, properties, should_run_gremlin_immediately):
        pgdb, neodb = db_tuple
        properties = properties.copy()
        properties[cls.COMMENT_SUBJECT_FIELD_NAME] = comment_subj
        properties[cls.COMMENT_BODY_FIELD_NAME] = comment_body
        
        create_node_stmts = cls._create_new_node(db_tuple, properties, {}, False)
        com_node_unq_id = create_node_stmts[0]['py_result']._properties[cls.UNIQUE_NODE_ID_FIELD_NAME]
        link_to_creator_stmts = CreatedByEdge.link_node_to_creator(db_tuple, com_node_unq_id, creator_user_id, False)
        link_to_parent_stmts = edge_type.link_nodes_by_unique_id(db_tuple, com_node_unq_id, parent_unique_node_id, {}, False)
        stmt_defs = create_node_stmts + link_to_creator_stmts + link_to_parent_stmts
        
        if should_run_gremlin_immediately:
            NeoUtil.run_gremlin_statements(neodb, stmt_defs)
            return create_node_stmts[0]['py_result']
        else:
            return stmt_defs
    
    @classmethod
    def start_new_comment_thread(cls, db_tuple, parent_cat_or_wrup_unique_node_id, creator_user_id, comment_subj, comment_body, properties, should_run_gremlin_immediately=True):
        return cls._create_new_comment_node(db_tuple, parent_cat_or_wrup_unique_node_id, CommentAttachEdge, creator_user_id, comment_subj, comment_body, properties, should_run_gremlin_immediately)
    
    @classmethod
    def reply_to_comment(cls, db_tuple, parent_cmnt_unique_node_id, creator_user_id, comment_subj, comment_body, properties, should_run_gremlin_immediately=True):
        return cls._create_new_comment_node(db_tuple, parent_cmnt_unique_node_id, CommentReplyEdge, creator_user_id, comment_subj, comment_body, properties, should_run_gremlin_immediately)

class WriteupNode(TripelNode):
    NODE_TYPE = 'WRITEUP'
    WRITEUP_INDEX_NAME = 'WRITEUP_IDX'
    WRITEUP_TITLE_FIELD_NAME = '_TRPL_WRUP_TITLE'
    WRITEUP_BODY_FIELD_NAME = '_TRPL_WRUP_BODY'
    
    @classmethod
    def _get_fields_to_index(cls):
        idx_fields = super(cls, cls)._get_fields_to_index().copy()
        idx_fields.update({cls.WRITEUP_INDEX_NAME: [cls.WRITEUP_TITLE_FIELD_NAME, cls.WRITEUP_BODY_FIELD_NAME]})
        return idx_fields
    
    @classmethod
    def _get_required_fields(cls):
        return super(cls, cls)._get_required_fields() + [cls.WRITEUP_TITLE_FIELD_NAME, cls.WRITEUP_BODY_FIELD_NAME]
    
    @classmethod
    def get_writeup_index(cls, neodb):
        return neodb.get_or_create_index(neo4j.Node, cls.WRITEUP_INDEX_NAME, config=cls.FULLTEXT_IDX_CONFIG)
    
    @classmethod
    def _get_create_node_stmt_def(cls, pgdb, properties, additional_params=None):
        tripel_node = cls._init_for_create(pgdb, properties)
        stmt_def = NeoUtil.get_create_and_index_node_stmt_def(tripel_node._properties, tripel_node._get_fields_to_index(), tripel_node)
        return stmt_def
    
    @classmethod
    def create_new_writeup_node(cls, db_tuple, parent_cat_unique_node_id, creator_user_id, writeup_title, writeup_body, properties, should_run_gremlin_immediately=True):
        pgdb, neodb = db_tuple
        properties = properties.copy()
        properties[cls.WRITEUP_TITLE_FIELD_NAME] = writeup_title
        properties[cls.WRITEUP_BODY_FIELD_NAME] = writeup_body
        
        create_node_stmts = cls._create_new_node(db_tuple, properties, {}, False)
        wrup_node_unq_id = create_node_stmts[0]['py_result']._properties[cls.UNIQUE_NODE_ID_FIELD_NAME]
        link_to_creator_stmts = CreatedByEdge.link_node_to_creator(db_tuple, wrup_node_unq_id, creator_user_id, False)
        link_to_parent_stmts = CategorizationEdge.link_nodes_by_unique_id(db_tuple, wrup_node_unq_id, parent_cat_unique_node_id, {}, False)
        stmt_defs = create_node_stmts + link_to_creator_stmts + link_to_parent_stmts
        
        if should_run_gremlin_immediately:
            NeoUtil.run_gremlin_statements(neodb, stmt_defs)
            return create_node_stmts[0]['py_result']
        else:
            return stmt_defs

class NotificationNode(TripelNode):
    NODE_TYPE = 'NOTIFICATION'
    #TODO: is linked to user, has links to nodes which user should be notified of?  requires custom edge w/ creation date.  would imply one notification hub node.
    #TODO: OR, maybe notification has link to search that spawned notification and link to specific result node, and link to user to be notified.  would imply one node per notification.

class RecommendationNode(NotificationNode):
    NODE_TYPE = 'RECOMMENDATION'
    #TODO: similar structural dilemma as notifications, except these are manual recommendations from user to user (instead of auto-generated recs from saved searches)
    #TODO: a note with the rec?  what about a setup where a rec can point to many nodes?  that'd argue for the one rec node per recommendation scheme (as opposed to a rec hub node for each user)

class AlertNode(NotificationNode):
    NODE_TYPE = 'USR_ALERT'
    #TODO: i think this just links to user or nodespace and is essentially a message or something

def init_neodb(db_tuple):
    pgdb, neodb = db_tuple
    
    TripelEdge.get_unique_edge_id_index(neodb)
    CreatedByEdge.get_created_by_index(neodb)
    TripelNode.get_unique_node_id_index(neodb)
    UserNode.get_user_index(neodb)
    NodespaceNode.get_nodespace_index(neodb)
    CategoryNode.get_category_index(neodb)
    CommentNode.get_comment_index(neodb)
    WriteupNode.get_writeup_index(neodb)

    #create a neo user node for each existing pg user
    users = User.get_all_users(pgdb)
    for user in users:
        UserNode.create_new_user_node(db_tuple, user.user_id, {})
    
    #create a neo nodespace node for each existing pg nodespace,
    #and a root category node for each nodespace node
    nodespaces = Nodespace.get_all_nodespaces(pgdb)
    for nodespace in nodespaces:
        Nodespace._neo_create_nodespace(db_tuple, nodespace.nodespace_id, {})
    

class PasswordChangeAuditEntry(PgPersistent):
    TABLE_NAME = '%s.password_change_audit_log' % SCHEMA_NAME
    PK_COL_NAME = 'passwd_chg_id'
    SEQ_NAME = '%s.password_change_audit_log_passwd_chg_id_seq' % SCHEMA_NAME
    FIELD_NAMES = ['passwd_chg_id', 'updated_user', 'updating_user', 'passwd_chg_date']
    
    @classmethod
    def add_new_audit_log_entry(cls, pgdb, updated_user_id, updating_user_id, password_change_date):
        audit_entry = cls()
        ins_params = {'updated_user': updated_user_id, 'updating_user': updating_user_id, 'passwd_chg_date': password_change_date}
        audit_entry._ins_obj_instance_and_set_pk_att(pgdb, ins_params)
        return audit_entry if audit_entry.passwd_chg_id is not None else None
    
    @classmethod
    def get_audit_log_entries_for_user(cls, pgdb, user_id):
        where_clause_vars = {'updated_user': user_id}
        return cls._get_obj_list(pgdb, where_clause_vars, "passwd_chg_date desc")

class MetaspacePrivilegeAuditEntry(PgPersistent):
    TABLE_NAME = '%s.metaspace_privilege_audit_log' % SCHEMA_NAME
    PK_COL_NAME = 'ms_priv_chg_id'
    SEQ_NAME = '%s.metaspace_privilege_audit_log_ms_priv_chg_id_seq' % SCHEMA_NAME
    FIELD_NAMES = ['ms_priv_chg_id', 'updated_user', 'updating_user', 'is_enabled', 'new_privileges', 'ms_priv_chg_date']
    
    def _massage_raw_pg_output_vals(self):
        self.new_privileges = MetaspacePrivilegeSet.create_from_pg_string_literal(self.new_privileges)
    
    @classmethod
    def add_new_audit_log_entry(cls, pgdb, updated_user_id, updating_user_id, is_enabled, new_privileges, privilege_change_date):
        audit_entry = cls()
        ins_params = {'updated_user': updated_user_id, 'updating_user': updating_user_id, 'is_enabled': is_enabled,
                            'new_privileges': new_privileges.get_pg_string_literal(), 'ms_priv_chg_date': privilege_change_date}
        audit_entry._ins_obj_instance_and_set_pk_att(pgdb, ins_params)
        return audit_entry if audit_entry.ms_priv_chg_id is not None else None
    
    @classmethod
    def get_audit_log_entries_for_user(cls, pgdb, user_id):
        where_clause_vars = {'updated_user': user_id}
        return cls._get_obj_list(pgdb, where_clause_vars, "ms_priv_chg_date desc")

class AuthEvent(PgPersistent):
    SESSION_CREATED, SESSION_KILLED, SESSION_CLEANED = 'session_created', 'session_killed', 'session_cleaned'
    PASSWORD_CHECK_SUCCESS, PASSWORD_CHECK_FAIL = 'password_check_success', 'password_check_fail'
    
    TABLE_NAME = '%s.auth_event_log' % SCHEMA_NAME
    PK_COL_NAME = 'auth_event_id'
    SEQ_NAME = '%s.auth_event_log_auth_event_id_seq' % SCHEMA_NAME
    FIELD_NAMES = ['auth_event_id', 'user_id', 'auth_event', 'auth_event_date']

    @classmethod
    def add_new_auth_event(cls, pgdb, user_id, auth_event, auth_event_date):
        audit_entry = cls()
        ins_params = {'user_id': user_id, 'auth_event': auth_event, 'auth_event_date': auth_event_date}
        audit_entry._ins_obj_instance_and_set_pk_att(pgdb, ins_params)
        return audit_entry if audit_entry.auth_event_id is not None else None
    
    @classmethod
    def get_audit_log_entries_for_user(cls, pgdb, user_id):
        where_clause_vars = {'user_id': user_id}
        return cls._get_obj_list(pgdb, where_clause_vars, "auth_event_date desc")


class User(PgPersistent):
    TABLE_NAME = '%s.users' % SCHEMA_NAME
    PK_COL_NAME = 'user_id'
    SEQ_NAME = '%s.users_user_id_seq' % SCHEMA_NAME
    FIELD_NAMES = ['user_id', 'email_addr', 'username', 'encrypted_password', 'user_statement', 'is_enabled', 'metaspace_privileges', 'creator', 'creation_date', 'modifier', 'modification_date']
    
    def _massage_raw_pg_output_vals(self):
        self.metaspace_privileges = MetaspacePrivilegeSet.create_from_pg_string_literal(self.metaspace_privileges) 
    
    @classmethod
    def create_new_user(cls, db_tuple, email_addr, username, cleartext_password, user_statement, is_enabled, metaspace_privileges, creator):
        pgdb, neodb = db_tuple
        user = cls()
        user.email_addr = email_addr
        user.username = username
        user.user_statement = user_statement
        user.is_enabled = is_enabled
        user.metaspace_privileges = metaspace_privileges if metaspace_privileges is not None else MetaspacePrivilegeSet()
        user.creator = creator
        user.creation_date = DateTimeUtil.datetime_now_utc_aware()
        user.modifier = None
        user.modification_date = None
        user._set_encrypted_password(cleartext_password)
        ins_params = user.__dict__.copy()
        ins_params['metaspace_privileges'] = user.metaspace_privileges.get_pg_string_literal()
        with pgdb.transaction():
            user._ins_obj_instance_and_set_pk_att(pgdb, ins_params)
            MetaspacePrivilegeAuditEntry.add_new_audit_log_entry(pgdb, user.user_id, creator, user.is_enabled, user.metaspace_privileges, user.creation_date)
            UserNode.create_new_user_node(db_tuple, user.user_id, {})
        return user if user.user_id is not None else None
    
    @classmethod
    def _get_existing_user(cls, pgdb, where_clause_vars):
        return cls._get_single_obj_instance(pgdb, where_clause_vars)
    
    @classmethod
    def get_existing_user_by_email(cls, pgdb, email_addr):
        where_clause_vars = {'email_addr': email_addr}
        return cls._get_existing_user(pgdb, where_clause_vars)
    
    @classmethod
    def get_existing_user_by_id(cls, pgdb, user_id):
        where_clause_vars = {'user_id': user_id}
        return cls._get_existing_user(pgdb, where_clause_vars)
    
    @classmethod
    def get_existing_user_by_username(cls, pgdb, username):
        where_clause_vars = {'username': username}
        return cls._get_existing_user(pgdb, where_clause_vars)
    
    def check_password(self, cleartext_password):
        return cryptacular.bcrypt.BCRYPTPasswordManager().check(self.encrypted_password, cleartext_password)
    
    def can_check_password(self, pgdb):
        query_sql = '''select count(ael.auth_event_id) recent_fail_count 
                        from %(auth_event_tbl)s ael 
                        where ael.user_id = $user_id
                        and ael.auth_event = 'password_check_fail' 
                        and ael.auth_event_date >= (timestamp with time zone $cur_time) - (interval '$check_window minutes')
                        ''' % {'auth_event_tbl': AuthEvent.TABLE_NAME}
        where_clause_vars = {'user_id': self.user_id, 'cur_time': DateTimeUtil.datetime_now_utc_aware(), 'check_window': params.PASSWORD_CHECK_WINDOW_IN_MIN}
        query_results = pgdb.query(query_sql, vars=where_clause_vars)
        return query_results[0]['recent_fail_count'] < params.PASSWORD_CHECK_MAX_FAILURES
    
    class TooManyBadPasswordsException(Exception):
        pass
    
    def check_password_audited(self, pgdb, cleartext_password, should_raise_too_many_bad_passwords_ex=True):
        '''
        at the moment, this is purposefully not transactional. mild worries about what would happen 
        with a ton of malicious requests sent exactly simultaneously.  guessing variable network lag 
        would prevent them from all hitting simultaneously.
        '''
        if not self.can_check_password(pgdb):
            if should_raise_too_many_bad_passwords_ex:
                raise self.TooManyBadPasswordsException('user_id %i has entered too many bad passwords' % self.user_id)
            else:
                return False
        
        check_result = self.check_password(cleartext_password)
        auth_event = AuthEvent.PASSWORD_CHECK_SUCCESS if check_result else AuthEvent.PASSWORD_CHECK_FAIL
        AuthEvent.add_new_auth_event(pgdb, self.user_id, auth_event, DateTimeUtil.datetime_now_utc_aware())
        return check_result
    
    def _set_encrypted_password(self, cleartext_password):
        self.encrypted_password = cryptacular.bcrypt.BCRYPTPasswordManager().encode(cleartext_password, params.NUM_BCRYPT_ROUNDS)
    
    def set_and_save_user_info(self, pgdb, new_username, new_email_addr, new_user_statement, modifier):
        self.username = new_username
        self.email_addr = new_email_addr
        self.user_statement = new_user_statement
        self.modifier = modifier
        self.modification_date = DateTimeUtil.datetime_now_utc_aware()
        upd_params = {'username': self.username, 'email_addr': self.email_addr, 'user_statement': self.user_statement,
                        'modifier': self.modifier, 'modification_date': self.modification_date}
        pgdb.update(self.TABLE_NAME, where='user_id = $user_id', vars={'user_id': self.user_id}, **upd_params)
    
    def set_and_save_metaspace_access(self, pgdb, is_enabled, new_metaspace_privileges, modifier):
        self.is_enabled = is_enabled
        self.metaspace_privileges = new_metaspace_privileges
        self.modifier = modifier
        self.modification_date = DateTimeUtil.datetime_now_utc_aware()
        upd_params = {'metaspace_privileges': self.metaspace_privileges.get_pg_string_literal(), 'is_enabled': self.is_enabled,
                        'modifier': self.modifier, 'modification_date': self.modification_date}
        with pgdb.transaction():
            pgdb.update(self.TABLE_NAME, where='user_id = $user_id', vars={'user_id': self.user_id}, **upd_params)
            MetaspacePrivilegeAuditEntry.add_new_audit_log_entry(pgdb, self.user_id, modifier, self.is_enabled, self.metaspace_privileges, self.modification_date)
    
    def set_and_save_encrypted_password(self, pgdb, cleartext_password, modifier):
        self._set_encrypted_password(cleartext_password)
        self.modifier = modifier
        self.modification_date = DateTimeUtil.datetime_now_utc_aware()
        upd_params = {'encrypted_password': self.encrypted_password, 
                        'modifier': self.modifier, 'modification_date': self.modification_date}
        with pgdb.transaction():
            pgdb.update(self.TABLE_NAME, where='user_id = $user_id', vars={'user_id': self.user_id}, **upd_params)
            PasswordChangeAuditEntry.add_new_audit_log_entry(pgdb, self.user_id, modifier, self.modification_date)
    
    @classmethod
    def get_all_users(cls, pgdb):
        return cls._get_obj_list(pgdb, {})
    
    @classmethod
    def get_user_and_access_info_by_nodespace_id(cls, pgdb, nodespace_id):
        query_sql = '''select u.user_id,
                        u.email_addr,
                        u.username,
                        u.is_enabled is_enabled_for_ms,
                        nsam.nodespace_access_id,
                        nsam.nodespace_id,
                        nsam.is_enabled is_enabled_for_ns,
                        nsam.nodespace_privileges
                    from %(user_tbl)s u, 
                        %(ns_tbl)s nsam 
                    where u.user_id = nsam.user_id 
                    and nsam.nodespace_id = $nodespace_id;''' % {'user_tbl': cls.TABLE_NAME, 'ns_tbl': NodespaceAccessEntry.TABLE_NAME}
        where_clause_vars = {'nodespace_id': nodespace_id}
        query_results = pgdb.query(query_sql, vars=where_clause_vars)
        return query_results
    
    #TODO: need a way to list invites from a given user.
    #TODO: need a way to revoke invites from a given user.


class PrivilegeSet(object):
    """
    don't use this directly, use one of the subclasses that defines RECOGNIZED_PRIVILEGES.
    
    apologies for the name, this doesn't actually subclass the 
    python set class, though it does use a set to store its data.
    """
    def __init__(self):
        self._privileges = set()
    
    @classmethod
    def create_from_list_of_strings(cls, priv_list):
        privilege_set = cls()
        privilege_set._privileges = set(filter(cls.is_valid_privilege, priv_list))
        return privilege_set

    @classmethod
    def create_from_pg_string_literal(cls, priv_list_string):
        priv_list = priv_list_string.strip(' {}').replace(' ', '').split(',')
        return cls.create_from_list_of_strings(priv_list)

    @classmethod
    def is_valid_privilege(cls, privilege):
        return privilege in cls.RECOGNIZED_PRIVILEGES
    
    def get_pg_string_literal(self):
        return '{%s}' % ','.join(self._privileges)

    def add_privilege(self, privilege):
        if self.is_valid_privilege(privilege):
            self._privileges.add(privilege)

    def remove_privilege(self, privilege):
        self._privileges.discard(privilege)
    
    def has_privilege(self, privilege):
        return privilege in self._privileges
        
    def has_one_or_more_privileges(self, privileges):
        return len(privileges.intersection(self._privileges)) > 0

    def has_all_privileges(self, privileges):
        return self._privileges.issuperset(privileges)
    
    def get_grantable_privileges(self):
        raise NotImplementedError('subclass must implement this')
    
    @classmethod
    def comparator(cls, priv1, priv2):
        """
        this lets you see whether one privilege is "higher" than
        another, though it's really meant more for display sorting
        than determining ability to do something, since possession of
        a "higher" privilege doesn't necessarily imply the ability to
        do anything a "lower" privilege can.
        """
        priv1_idx = cls._ORDERED_PRIV_LIST.index(priv1)
        priv2_idx = cls._ORDERED_PRIV_LIST.index(priv2)
        if priv1_idx == priv2_idx: return 0
        if priv1_idx < priv2_idx: return -1
        return 1
    
    #TODO: make this follow the __repr__ guideline (i.e., return a string that eval can turn into the object).  might have 
    # to do that in subclass to call right constructor?  or better yet, maybe use introspection on self?
    def __repr__(self):
        return self.get_pg_string_literal()
    
    def __iter__(self):
        return iter(self._privileges)

    def _eq_check_helper(self, other, check_fn):
        if other is None:
            return False
        elif isinstance(self, PrivilegeSet) and isinstance(other, PrivilegeSet) and type(self) == type(other):
            return check_fn(self, other)
        else:
            raise TypeError('can only compare PrivilegeSet objects of the same type. type(self)=%s, type(other)=%s' % (type(self), type(other)))
    
    def __eq__(self, other):
        def check_fn(left, right): return left._privileges == right._privileges
        return self._eq_check_helper(other, check_fn)
    
    def __ne__(self, other):
        def check_fn(left, right): return left._privileges != right._privileges
        return self._eq_check_helper(other, check_fn)

class MetaspacePrivilegeSet(PrivilegeSet):
    CREATE_USER, CREATE_SPACE, SUPER = 'create_user', 'create_space', 'super'
    _ORDERED_PRIV_LIST = [CREATE_USER, CREATE_SPACE, SUPER]
    RECOGNIZED_PRIVILEGES = frozenset(_ORDERED_PRIV_LIST)
    
    def get_grantable_privileges(self):
        if self.has_privilege(self.SUPER):
            return self.create_from_list_of_strings(self.RECOGNIZED_PRIVILEGES)
        else:
            return self.create_from_list_of_strings(self)

class NodespacePrivilegeSet(PrivilegeSet):
    CONTRIBUTOR, EDITOR, MODERATOR, ADMIN = 'contributor', 'editor', 'moderator', 'admin'
    _ORDERED_PRIV_LIST = [CONTRIBUTOR, EDITOR, MODERATOR, ADMIN]
    RECOGNIZED_PRIVILEGES = frozenset(_ORDERED_PRIV_LIST)
    
    def get_grantable_privileges(self):
        if self.has_privilege(self.ADMIN):
            return self.create_from_list_of_strings(self.RECOGNIZED_PRIVILEGES)
        else:
            return NodespacePrivilegeSet()


class PrivilegeChecker(object):
    """
    similar deal to the base PrivilegeSet class and implementing classes: machinery here, config in children, call children.  a bit 
    more machinery in the children on this one, though.
    
    in children: map actions to check functions (by adding a case in get_action_check_fn).  in addition to a db handle, a check 
    function takes a target object ("target", on which checked action is to be performed) and a User object for the user performing 
    the action ("actor").  "target" could be None (if it's not applicable to the check), a Nodespace, a User, whatever.  the db handle 
    may or may not be used, depending on whether the target and actor objects need to be asked for further info to determine the 
    result of the check.
    """
    
    class UnrecognizedActionException(Exception):
        pass
    
    class InsufficientPrivilegesException(Exception):
        pass
    
    @classmethod
    def is_allowed_to_do(cls, db_tuple, action, target, actor, should_raise_insufficent_priv_ex=True):
        """
        this method uses info from the child class to determine whether there's a check function corresponding to the action to be performed.  if not,
        an excpeption is thrown.  if yes, the check is run and the result is returned, or an exception is thrown, depending on the outcome of the check 
        and whether the caller wanted an exception for a failed check (the default behavior).
        """
        action_check_fn = cls.get_action_check_fn(action)
        
        if action_check_fn is None:
            raise cls.UnrecognizedActionException('unrecognized action: %s' % action)
        
        # i do what i want!
        if actor.metaspace_privileges.has_privilege(MetaspacePrivilegeSet.SUPER):
            return True
        
        can_do_action = action_check_fn(db_tuple, target, actor)
        if should_raise_insufficent_priv_ex and not can_do_action:
            raise cls.InsufficientPrivilegesException('%s (user_id=%i) is not allowed to perform %s' % (actor.email_addr, actor.user_id, action))
        else:
            return can_do_action

class MetaspacePrivilegeChecker(PrivilegeChecker):
    VIEW_METASPACE_COMMANDS_ACTION = 'view_metaspace_cmds_act'
    CREATE_USER_ACTION, CREATE_SPACE_ACTION, LIST_ALL_SPACES_ACTION = 'create_user_act', 'create_space_act', 'list_all_spaces_act'
    ALTER_USER_INFO_ACTION, ALTER_USER_ACCESS_ACTION, LIST_ALL_USERS_ACTION = 'alter_user_info_act', 'alter_user_access_act', 'list_all_users_act'
    RECOGNIZED_ACTIONS = frozenset([VIEW_METASPACE_COMMANDS_ACTION, CREATE_USER_ACTION, CREATE_SPACE_ACTION, LIST_ALL_SPACES_ACTION, 
                                    ALTER_USER_INFO_ACTION, ALTER_USER_ACCESS_ACTION, LIST_ALL_USERS_ACTION])
    
    @classmethod
    def get_action_check_fn(cls, action):
        if action == cls.VIEW_METASPACE_COMMANDS_ACTION:
            return cls.can_view_metaspace_commands
        elif action == cls.CREATE_USER_ACTION:
            return cls.can_create_user
        elif action == cls.ALTER_USER_INFO_ACTION:
            return cls.can_update_user
        elif action == cls.CREATE_SPACE_ACTION:
            return cls.can_create_space
        elif action == cls.ALTER_USER_ACCESS_ACTION or action == cls.LIST_ALL_USERS_ACTION or action == cls.LIST_ALL_SPACES_ACTION:
            # reserved for super users.  a super user would've bypassed the 
            # check fn execution, so just return a fn that always returns false.
            return cls.no_can_do
        # no check function found
        return None
    
    @classmethod
    def can_view_metaspace_commands(cls, db_tuple, target, actor):
        return len(actor.metaspace_privileges._privileges) > 0
    
    @classmethod
    def can_create_user(cls, db_tuple, target, actor):
        return actor.metaspace_privileges.has_privilege(MetaspacePrivilegeSet.CREATE_USER)
    
    @classmethod
    def can_update_user(cls, db_tuple, target, actor):
        """only super users can edit other users"""
        return target.user_id == actor.user_id
    
    @classmethod
    def can_create_space(cls, db_tuple, target, actor):
        return actor.metaspace_privileges.has_privilege(MetaspacePrivilegeSet.CREATE_SPACE)
    
    @classmethod
    def no_can_do(cls, db_tuple, target, actor):
        """ if they got this far they aren't a super user """
        return False

class NodespacePrivilegeChecker(PrivilegeChecker):
    CREATE_COMMENT_ACTION, APPROVE_COMMENT_ACTION, EDIT_COMMENT_ACTION, DELETE_COMMENT_ACTION = 'create_comment_act', 'approve_comment_act', 'edit_comment_act', 'delete_comment_act'
    CREATE_WRITEUP_ACTION, APPROVE_WRITEUP_ACTION, EDIT_WRITEUP_ACTION, DELETE_WRITEUP_ACTION = 'create_writeup_act', 'approve_writeup_act', 'edit_writeup_act', 'delete_writeup_act'
    ALTER_NODESPACE_ACTION, ALTER_NODESPACE_ACCESS_ACTION, VIEW_NODESPACE_ACTION, VIEW_USER_ACTION = 'alter_nodespace_act', 'alter_nodespace_access_act', 'view_nodespace_action', 'view_user_action'
    RECOGNIZED_ACTIONS = frozenset([CREATE_COMMENT_ACTION, APPROVE_COMMENT_ACTION, EDIT_COMMENT_ACTION, DELETE_COMMENT_ACTION,
                                    CREATE_WRITEUP_ACTION, APPROVE_WRITEUP_ACTION, EDIT_WRITEUP_ACTION, DELETE_WRITEUP_ACTION,
                                    ALTER_NODESPACE_ACTION, ALTER_NODESPACE_ACCESS_ACTION, VIEW_NODESPACE_ACTION])
    
    @classmethod
    def get_action_check_fn(cls, action):
        if action == cls.ALTER_NODESPACE_ACCESS_ACTION or action == cls.ALTER_NODESPACE_ACTION:
            return cls.has_admin_access
        if action == cls.VIEW_NODESPACE_ACTION:
            return cls.can_view_nodespace
        if action == cls.VIEW_USER_ACTION:
            return cls.can_view_user
        if action == cls.CREATE_COMMENT_ACTION:
            return cls.can_create_comment
        if action == cls.REPLY_TO_COMMENT_ACTION:
            return cls.can_reply_to_comment
        # no check function found
        return None

    @classmethod
    def has_admin_access(cls, db_tuple, target, actor):
        pgdb, neodb = db_tuple
        ns_access = target.get_nodespace_access_for_user(pgdb, actor.user_id)
        ns_privs = ns_access.nodespace_privileges if ns_access is not None else None
        return ns_privs.has_privilege(NodespacePrivilegeSet.ADMIN) if ns_privs is not None else False

    @classmethod
    def can_view_nodespace(cls, db_tuple, target, actor):
        pgdb, neodb = db_tuple
        return target.get_nodespace_access_for_user(pgdb, actor.user_id) is not None
    
    @classmethod
    def can_view_user(cls, db_tuple, target, actor):
        pgdb, neodb = db_tuple
        if target.user_id == actor.user_id: return True
        return Nodespace.do_users_share_nodespace_access(pgdb, target.user_id, actor.user_id)
    
    @classmethod
    def can_create_comment(cls, db_tuple, target, actor):
        pgdb, neodb = db_tuple
        #if user has contributor, moderator, or admin in the nodespace containing the parent object and the parent object is a comment, category, or writeup.
    
    @classmethod
    def can_reply_to_comment(cls, db_tuple, target, actor):
        pgdb, neodb = db_tuple
        
        #TODO: should maybe break this out into a fn under NodespaceNode that returns an instance of that class
        # could also have a util class w/ useful cypher queries that returns the other interesting nodes obtained by this query.
        # could do something similar to that for pg queries that don't return a simple list of objects.
        parent_info_cql = '''START cmnt=node:UNQ_NODE_ID_IDX(_TRPL_UNQ_NODE_ID={cmnt_node_unq_id}) 
                        MATCH p = cmnt-[:HAS_PARENT_COMMENT*0..]->cmnt_thrd_root
                        WITH cmnt_thrd_root ORDER BY length(p) DESC LIMIT 1
                        MATCH cmnt_thrd_root-[:COMMENTS_ON]->cmntd_node-[:HAS_PARENT_CAT*]->root_cat-[:IS_ROOT_CAT_FOR]->nodespace
                        RETURN nodespace;'''
        parent_nodespace = cypher.execute(neodb, parent_info_cql, {"cmnt_node_unq_id": target._properties[target.UNIQUE_NODE_ID_FIELD_NAME]})[0][0][0]
        parent_nodespace_id = parent_nodespace.get_properties()[NodespaceNode.NODESPACE_ID_FIELD_NAME]
        
        ns_access = NodespaceAccessEntry.get_existing_access_entry(pgdb, parent_nodespace_id, actor.user_id)
        ns_privs = ns_access.nodespace_privileges if ns_access is not None else None
        sufficient_privs = frozenset([NodespacePrivilegeSet.CONTRIBUTOR, NodespacePrivilegeSet.MODERATOR, NodespacePrivilegeSet.ADMIN])
        return ns_privs.has_one_or_more_privileges(sufficient_privs) if ns_privs is not None else False
    
    @classmethod
    def can_edit_comment(cls, db_tuple, target, actor):
        pgdb, neodb = db_tuple
        #if user has moderator or admin in the nodespace containing the comment to edit, or if the user created the comment, and comment has no replies yet
    
    @classmethod
    def can_create_writeup(cls, db_tuple, target, actor):
        pgdb, neodb = db_tuple
        #if user user has contributor, editor, or admin in the nodespace containing the parent category
    
    @classmethod
    def can_edit_writeup(cls, db_tuple, target, actor):
        pgdb, neodb = db_tuple
        #if user has editor or admin in the nodespace containing the writeup to edit, or the user created the writeup


class Invitation(object):
    MIN_INVITE_CODE_LEN = 20
    DEFAULT_INVITE_CODE_LEN = MIN_INVITE_CODE_LEN

    @classmethod
    def _new_invitation_obj_instance(cls, invitee_email_addr, invitation_msg, creator):
        invitation = cls()
        invitation.invitee_email_addr = invitee_email_addr
        invitation.invitation_msg = invitation_msg
        invitation.creator = creator
        invitation.decision_date = None
        invitation.was_accepted = None
        invitation.creation_date = DateTimeUtil.datetime_now_utc_aware()
        return invitation

    @classmethod
    def validate_invitation_code_format(cls, invitation_code):
        if not cls.is_valid_invitation_code(invitation_code):
            raise Exception('Invite code must be at least %i characters (alphanumeric, hyphen, and underscore only)' % Invitation.MIN_INVITE_CODE_LEN)

    @staticmethod
    def is_valid_invitation_code(invitation_code):
        return len(invitation_code) >= Invitation.MIN_INVITE_CODE_LEN and util.is_hyphenated_alphanumeric_string(invitation_code)
    
    @staticmethod
    def generate_random_invitation_code(code_len=DEFAULT_INVITE_CODE_LEN):
        return util.generate_random_url_safe_string(code_len)
    
    #TODO: need a way to revoke invites

class MetaspaceInvitation(Invitation, PgPersistent):
    TABLE_NAME = '%s.metaspace_invitations' % SCHEMA_NAME
    PK_COL_NAME = 'metaspace_invitation_id'
    SEQ_NAME = '%s.metaspace_invitations_metaspace_invitation_id_seq' % SCHEMA_NAME
    FIELD_NAMES = ['metaspace_invitation_id', 'metaspace_invitation_code', 'invitee_email_addr', 'initial_metaspace_privileges', \
                    'invitation_msg', 'creator', 'creation_date', 'decision_date', 'was_accepted', 'new_user_id']
    
    @classmethod
    def create_new_invitation(cls, pgdb, metaspace_invitation_code, invitee_email_addr, initial_metaspace_privileges, invitation_msg, creator):
        invitation = cls._new_invitation_obj_instance(invitee_email_addr, invitation_msg, creator)
        metaspace_invitation_code = metaspace_invitation_code if metaspace_invitation_code is not None else cls.generate_random_invitation_code()  
        cls.validate_invitation_code_format(metaspace_invitation_code)
        invitation.metaspace_invitation_code = metaspace_invitation_code
        invitation.initial_metaspace_privileges = initial_metaspace_privileges if initial_metaspace_privileges is not None else MetaspacePrivilegeSet()
        invitation.new_user_id = None
        ins_params = invitation.__dict__.copy()
        ins_params['initial_metaspace_privileges'] = invitation.initial_metaspace_privileges.get_pg_string_literal() 
        invitation._ins_obj_instance_and_set_pk_att(pgdb, ins_params)
        return invitation if invitation.metaspace_invitation_id is not None else None
    
    def _massage_raw_pg_output_vals(self):
        self.initial_metaspace_privileges = MetaspacePrivilegeSet.create_from_pg_string_literal(self.initial_metaspace_privileges)
    
    @classmethod
    def get_existing_invitation(cls, pgdb, metaspace_invitation_code):
        where_clause_vars = {'metaspace_invitation_code': metaspace_invitation_code}
        return cls._get_single_obj_instance(pgdb, where_clause_vars)
    
    def _decide_on_invitation(self, pgdb, was_accepted, new_user_id):
        self.was_accepted = was_accepted
        self.decision_date = DateTimeUtil.datetime_now_utc_aware()
        self.new_user_id = new_user_id
        upd_params = {'was_accepted': self.was_accepted, 'decision_date': self.decision_date, 'new_user_id': self.new_user_id}
        pgdb.update(self.TABLE_NAME, where='metaspace_invitation_code = $metaspace_invitation_code', 
                    vars={'metaspace_invitation_code': self.metaspace_invitation_code}, **upd_params)
    
    def create_user_and_accept_invitation(self, db_tuple, username, cleartext_password, user_statement):
        pgdb, neodb = db_tuple
        user = User.create_new_user(db_tuple, self.invitee_email_addr, username, cleartext_password, user_statement, True, self.initial_metaspace_privileges, self.creator)
        self._decide_on_invitation(pgdb, True, user.user_id)
        return user
    
    def decline_invitation(self, pgdb):
        self._decide_on_invitation(pgdb, False, None)

class NodespaceAccessEntry(PgPersistent):
    TABLE_NAME = '%s.nodespace_access_map' % SCHEMA_NAME
    PK_COL_NAME = 'nodespace_access_id'
    SEQ_NAME = '%s.nodespace_access_map_nodespace_access_id_seq' % SCHEMA_NAME
    FIELD_NAMES = ['nodespace_access_id', 'user_id', 'nodespace_id', 'is_enabled', 'nodespace_privileges', 
                    'invitation_id', 'creator', 'creation_date', 'modifier', 'modification_date']
    
    def _massage_raw_pg_output_vals(self):
        self.nodespace_privileges = NodespacePrivilegeSet.create_from_pg_string_literal(self.nodespace_privileges)
    
    @classmethod
    def create_new_access_entry(cls, pgdb, nodespace_id, nodespace_privileges, granted_to_user_id, granted_by_user_id, invitation_id):
        access_entry = cls()
        access_entry.user_id = granted_to_user_id
        access_entry.nodespace_id = nodespace_id
        access_entry.is_enabled = True
        access_entry.nodespace_privileges = nodespace_privileges if nodespace_privileges is not None else NodespacePrivilegeSet()
        access_entry.invitation_id = invitation_id
        access_entry.creator = granted_by_user_id
        access_entry.creation_date = DateTimeUtil.datetime_now_utc_aware()
        ins_params = access_entry.__dict__.copy()
        ins_params['nodespace_privileges'] = nodespace_privileges.get_pg_string_literal()
        access_entry._ins_obj_instance_and_set_pk_att(pgdb, ins_params)
        return access_entry if access_entry.nodespace_access_id is not None else None
    
    @classmethod
    def get_existing_access_entry(cls, pgdb, nodespace_id, user_id):
        where_clause_vars = {'nodespace_id': nodespace_id, 'user_id': user_id}
        return cls._get_single_obj_instance(pgdb, where_clause_vars)
    
    def set_and_save_access_entry(self, pgdb, new_nodespace_privileges, is_enabled, modifier):
        self.nodespace_privileges = new_nodespace_privileges
        self.is_enabled = is_enabled
        self.modifier = modifier
        self.modification_date = DateTimeUtil.datetime_now_utc_aware()
        upd_params = {'nodespace_privileges': self.nodespace_privileges.get_pg_string_literal(), 'is_enabled': self.is_enabled, 
                        'modifier': self.modifier, 'modification_date': self.modification_date}
        pgdb.update(self.TABLE_NAME, where='nodespace_access_id = $nodespace_access_id', vars={'nodespace_access_id': self.nodespace_access_id}, **upd_params)
    
    def revoke_access_entry(self, pgdb):
        del_vars = {'nodespace_access_id': self.nodespace_access_id}
        pgdb.delete(self.TABLE_NAME, where='nodespace_access_id = $nodespace_access_id', vars=del_vars)
        self.user_id = None
        self.nodespace_id = None
        self.is_enabled = None
        self.nodespace_privileges = None
        self.invitation_id = None
        self.creator = None
        self.creation_date = None

class Nodespace(PgPersistent):
    TABLE_NAME = '%s.nodespaces' % SCHEMA_NAME
    PK_COL_NAME = 'nodespace_id'
    SEQ_NAME = '%s.nodespaces_nodespace_id_seq' % SCHEMA_NAME
    FIELD_NAMES = ['nodespace_id', 'nodespace_name', 'nodespace_description', 'creator', 'creation_date', 'modifier', 'modification_date']
    
    ACCESS_MAP_TABLE_NAME = '%s.nodespace_access_map' % SCHEMA_NAME
    ACCESS_MAP_SEQ_NAME = '%s.nodespace_access_map_nodespace_access_id_seq' % SCHEMA_NAME
    
    @staticmethod
    def is_valid_nodespace_name(proposed_name):
        return len(proposed_name) > 0
    
    @classmethod
    def _neo_create_nodespace(cls, db_tuple, nodespace_id, properties):
        pgdb, neodb = db_tuple
        stmt_list = []
        stmt_list.extend(NodespaceNode.create_new_nodespace_node(db_tuple, nodespace_id, properties, False))
        stmt_list.extend(RootCategoryNode.create_new_root_category_node(db_tuple, nodespace_id, properties, False))
        NeoUtil.run_gremlin_statements(neodb, stmt_list)
    
    @classmethod
    def create_new_nodespace(cls, db_tuple, nodespace_name, nodespace_description, creator):
        pgdb, neodb = db_tuple
        nodespace = cls()
        nodespace.nodespace_name = nodespace_name
        nodespace.nodespace_description = nodespace_description
        nodespace.creator = creator
        nodespace.creation_date = DateTimeUtil.datetime_now_utc_aware()
        nodespace.modifier = None
        nodespace.modification_date = None
        with pgdb.transaction():
            nodespace._ins_obj_instance_and_set_pk_att(pgdb)
            nodespace._neo_create_nodespace(db_tuple, nodespace.nodespace_id, {})
        return nodespace if nodespace.nodespace_id is not None else None
    
    @classmethod
    def get_existing_nodespace(cls, pgdb, nodespace_name):
        where_clause_vars = {'nodespace_name': nodespace_name}
        return cls._get_single_obj_instance(pgdb, where_clause_vars)
    
    @classmethod
    def get_existing_nodespace_by_id(cls, pgdb, nodespace_id):
        where_clause_vars = {'nodespace_id': nodespace_id}
        return cls._get_single_obj_instance(pgdb, where_clause_vars)
    
    def set_and_save_nodespace_settings(self, pgdb, nodespace_name, nodespace_description, modifier):
        self.nodespace_name = nodespace_name
        self.nodespace_description = nodespace_description
        self.modifier = modifier
        self.modification_date = DateTimeUtil.datetime_now_utc_aware()
        upd_params = {'nodespace_name': self.nodespace_name, 'nodespace_description': self.nodespace_description,
                        'modifier': self.modifier, 'modification_date': self.modification_date}
        pgdb.update(self.TABLE_NAME, where='nodespace_id = $nodespace_id', vars={'nodespace_id': self.nodespace_id}, **upd_params)
    
    @classmethod
    def get_accessible_nodespaces_by_user_id(cls, pgdb, user_id):
        query_sql = '''select ns.* 
                    from %(ns_acc_map_tbl)s nsam, 
                        %(ns_tbl)s ns 
                    where user_id = $user_id 
                    and nsam.nodespace_id = ns.nodespace_id;''' % {'ns_acc_map_tbl': NodespaceAccessEntry.TABLE_NAME, 'ns_tbl': cls.TABLE_NAME}
        where_clause_vars = {'user_id': user_id}
        query_results = pgdb.query(query_sql, vars=where_clause_vars)
        return cls._query_results_to_obj_list(query_results)
    
    @classmethod
    def get_all_nodespaces(cls, pgdb):
        return cls._get_obj_list(pgdb, {})
    
    @classmethod
    def grant_user_access_to_nodespace(cls, pgdb, nodespace_id, nodespace_privileges, granted_to_user_id, granted_by_user_id, invitation_id):
        return NodespaceAccessEntry.create_new_access_entry(pgdb, nodespace_id, nodespace_privileges, granted_to_user_id, granted_by_user_id, invitation_id)

    def get_nodespace_access_for_user(self, pgdb, user_id):
        return NodespaceAccessEntry.get_existing_access_entry(pgdb, self.nodespace_id, user_id)
    
    @classmethod
    def do_users_share_nodespace_access(cls, pgdb, user_id_1, user_id_2):
        query_sql = '''select case when count(1) > 0 then true else false end have_common_access
                from (select nodespace_id
                    from %s
                    where (user_id = $user_id_1 or user_id = $user_id_2)
                    group by nodespace_id
                    having count(1) > 1) common_nodespaces;''' % NodespaceAccessEntry.TABLE_NAME
        where_clause_vars = {'user_id_1': user_id_1, 'user_id_2': user_id_2, 'schema_name': SCHEMA_NAME}
        query_result = pgdb.query(query_sql, vars=where_clause_vars)[0]
        return query_result['have_common_access']

class NodespaceInvitation(Invitation, PgPersistent):
    TABLE_NAME = '%s.nodespace_invitations' % SCHEMA_NAME
    PK_COL_NAME = 'nodespace_invitation_id'
    SEQ_NAME = '%s.nodespace_invitations_nodespace_invitation_id_seq' % SCHEMA_NAME
    FIELD_NAMES = ['nodespace_invitation_id', 'nodespace_invitation_code', 'invitee_email_addr', 'nodespace_id', 'initial_nodespace_privileges', \
                    'invitation_msg', 'creator', 'creation_date', 'decision_date', 'was_accepted', 'user_id']
    
    def _massage_raw_pg_output_vals(self):
        self.initial_nodespace_privileges = NodespacePrivilegeSet.create_from_pg_string_literal(self.initial_nodespace_privileges)
    
    @classmethod
    def create_new_invitation(cls, pgdb, nodespace_invitation_code, invitee_email_addr, nodespace_id, initial_nodespace_privileges, invitation_msg, creator):
        invitation = cls._new_invitation_obj_instance(invitee_email_addr, invitation_msg, creator)
        nodespace_invitation_code = nodespace_invitation_code if nodespace_invitation_code is not None else cls.generate_random_invitation_code()
        cls.validate_invitation_code_format(nodespace_invitation_code)
        invitation.nodespace_invitation_code = nodespace_invitation_code
        invitation.nodespace_id = nodespace_id
        invitation.initial_nodespace_privileges = initial_nodespace_privileges if initial_nodespace_privileges is not None else NodespacePrivilegeSet()
        invitation.user_id = None
        ins_params = invitation.__dict__.copy()
        ins_params['initial_nodespace_privileges'] = invitation.initial_nodespace_privileges.get_pg_string_literal()
        invitation._ins_obj_instance_and_set_pk_att(pgdb, ins_params)
        return invitation if invitation.nodespace_invitation_id is not None else None

    @classmethod
    def get_existing_invitation(cls, pgdb, nodespace_invitation_code):
        where_clause_vars = {'nodespace_invitation_code': nodespace_invitation_code}
        return cls._get_single_obj_instance(pgdb, where_clause_vars)

    def _decide_on_invitation(self, pgdb, was_accepted, user_id):
        self.was_accepted = was_accepted
        self.decision_date = DateTimeUtil.datetime_now_utc_aware()
        self.user_id = user_id
        upd_params = {'was_accepted': self.was_accepted, 'decision_date': self.decision_date, 'user_id': self.user_id}
        pgdb.update(self.TABLE_NAME, where='nodespace_invitation_code = $nodespace_invitation_code', 
                    vars={'nodespace_invitation_code': self.nodespace_invitation_code}, **upd_params)

    def accept_invitation(self, pgdb, user_id):
        self._decide_on_invitation(pgdb, True, user_id)
        Nodespace.grant_user_access_to_nodespace(pgdb, self.nodespace_id, self.initial_nodespace_privileges, user_id, self.creator, self.nodespace_invitation_id)
    
    def create_user_and_accept_invitation(self, db_tuple, username, cleartext_password, user_statement):
        pgdb, neodb = db_tuple
        #first, create a metaspace invite behind the scenes and accept that
        ms_invitation = MetaspaceInvitation.create_new_invitation(pgdb, None, self.invitee_email_addr, None, self.invitation_msg, self.creator)
        user = ms_invitation.create_user_and_accept_invitation(db_tuple, username, cleartext_password, user_statement)
        self.accept_invitation(pgdb, user.user_id)
        return user
    
    def decline_invitation(self, pgdb):
        self._decide_on_invitation(pgdb, False, None)

class MetaspaceSession(PgPersistent):
    TABLE_NAME = '%s.metaspace_sessions' % SCHEMA_NAME
    PK_COL_NAME = 'metaspace_session_id'
    FIELD_NAMES = ['metaspace_session_id', 'user_id', 'creation_date', 'last_visit']
    
    # specified in seconds
    MAX_SESSION_IDLE_TIME = 3600 #session expiry after 1 hr inactivity
    MAX_SESSION_AGE = 43200 #session expiry after 12 hrs, regardless of activity
    
    SESSION_ID_TOKEN_LEN = 40
    
    @classmethod
    def create_new_session(cls, pgdb, user_id):
        ms_session = cls()
        #note that we prepend user_id to the session token, mostly to guard against the possibility of token collision
        ms_session.metaspace_session_id = '%i,%s' % (user_id, util.generate_random_url_safe_string(cls.SESSION_ID_TOKEN_LEN))
        ms_session.user_id = user_id
        ms_session.creation_date = DateTimeUtil.datetime_now_utc_aware()
        ms_session.last_visit = ms_session.creation_date
        ins_params = ms_session.__dict__.copy()
        with pgdb.transaction():
            pgdb.insert(cls.TABLE_NAME, seqname=False, **ins_params)
            AuthEvent.add_new_auth_event(pgdb, user_id, AuthEvent.SESSION_CREATED, ms_session.creation_date)
        return ms_session
    
    @classmethod
    def get_existing_session(cls, pgdb, metaspace_session_id):
        where_clause_vars = {'metaspace_session_id': metaspace_session_id}
        return cls._get_single_obj_instance(pgdb, where_clause_vars)
    
    def is_session_valid(self):
        cur_time = DateTimeUtil.datetime_now_utc_aware()
        return ((cur_time - self.last_visit).seconds < self.MAX_SESSION_IDLE_TIME) and ((cur_time - self.creation_date).seconds < self.MAX_SESSION_AGE)
    
    def touch_session(self, pgdb):
        self.last_visit = DateTimeUtil.datetime_now_utc_aware()
        upd_params = {'last_visit': self.last_visit}
        pgdb.update(self.TABLE_NAME, where='metaspace_session_id = $metaspace_session_id', 
                    vars={'metaspace_session_id': self.metaspace_session_id}, **upd_params)
    
    def kill_session(self, pgdb):
        del_vars = {'metaspace_session_id': self.metaspace_session_id}
        with pgdb.transaction():
            pgdb.delete(self.TABLE_NAME, where='metaspace_session_id = $metaspace_session_id', vars=del_vars)
            AuthEvent.add_new_auth_event(pgdb, self.user_id, AuthEvent.SESSION_KILLED, DateTimeUtil.datetime_now_utc_aware())
        self.metaspace_session_id = None
        self.user_id = None
        self.creation_date = None
        self.last_visit = None

    @classmethod
    def kill_session_for_user_id(cls, pgdb, user_id):
        del_vars = {'user_id': user_id}
        with pgdb.transaction():
            pgdb.delete(cls.TABLE_NAME, where='user_id = $user_id', vars=del_vars)
            AuthEvent.add_new_auth_event(pgdb, user_id, AuthEvent.SESSION_KILLED, DateTimeUtil.datetime_now_utc_aware())
        
    @classmethod
    def force_create_new_session(cls, pgdb, user_id):
        #purposefully not making this a transaction for now, seems unnecessary
        cls.kill_session_for_user_id(pgdb, user_id)
        return cls.create_new_session(pgdb, user_id)
    
    @classmethod
    def cleanup_old_sessions(cls, pgdb):
        cur_time = DateTimeUtil.datetime_now_utc_aware()
        del_vars = {'cur_time': cur_time, 'cleanup_age': cls.MAX_SESSION_AGE*2}
        where_clause = "(((timestamp with time zone '$cur_time') - creation_date) > (interval '$cleanup_age seconds'))"
        #TODO: need to be logging this in auth events, though it's not actually used at the moment anyway
        pgdb.delete(cls.TABLE_NAME, where=where_clause, vars=del_vars)


