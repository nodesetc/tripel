import org.neo4j.graphdb.PropertyContainer
import org.neo4j.graphdb.Node
import org.neo4j.graphdb.Relationship
import org.neo4j.graphdb.RelationshipType
import org.neo4j.graphdb.DynamicRelationshipType
import org.neo4j.graphdb.index.Index

class GremlinUtils {
	static def execInTransaction(Neo4jGraph g, Closure closure) {
		//pretty much ripped off https://gist.github.com/espeed/1654077
		
		g.setMaxBufferSize(0)
		g.startTransaction()
		try {
			def retVal = closure()
			g.stopTransaction(TransactionalGraph.Conclusion.SUCCESS)
			return retVal
		} catch (ex) {
			g.stopTransaction(TransactionalGraph.Conclusion.FAILURE)
			throw ex
		}
	}
	
	static Index getEdgeIndex(Neo4jGraph g, String indexName) {
		return g.getRawGraph().index().forRelationships(indexName)
	}
	
	static Index getNodeIndex(Neo4jGraph g, String indexName) {
		return g.getRawGraph().index().forNodes(indexName)
	}
	
	//TODO: be able to specify uniqueness (and expose flag in addEdgeToIndexes and addVertexToIndexes)
	static def addPropertyContainerToIndexes(Neo4jGraph g, PropertyContainer pc, Map fieldsToIndex, Closure getIndexFn) {
		for (fieldToIndex in fieldsToIndex) {
			String indexName = fieldToIndex.key
			List<String> indexedFieldNameList = fieldToIndex.value
			Index curIdx = getIndexFn(indexName)
			assert (curIdx != null), 'no index found for indexName='+indexName
			for (indexedFieldName in indexedFieldNameList) {
				assert (pc.getProperty(indexedFieldName) != null), 'no prop for indexedFieldName=\''+indexedFieldName+'\'; indexedFieldNameList=\''+indexedFieldNameList+'\''
				curIdx.add(pc, indexedFieldName, pc.getProperty(indexedFieldName))
			}
		}
		return null
	}
	
	static def addEdgeToIndexes(Neo4jGraph g, Neo4jEdge e, Map fieldsToIndex) {
		Relationship relationshipToIndex = e.getRawEdge()
		assert (relationshipToIndex != null), 'no relationshipToIndex'
		Closure getIndexFn = {String indexName -> return getEdgeIndex(g, indexName)}
		return addPropertyContainerToIndexes(g, relationshipToIndex, fieldsToIndex, getIndexFn)
	}
	
	static def addVertexToIndexes(Neo4jGraph g, Neo4jVertex v, Map fieldsToIndex) {
		Node nodeToIndex = v.getRawVertex()
		assert (nodeToIndex != null), 'no nodeToIndex'
		Closure getIndexFn = {String indexName -> return getNodeIndex(g, indexName)}
		return addPropertyContainerToIndexes(g, nodeToIndex, fieldsToIndex, getIndexFn)
	}
	
	static Neo4jVertex getUniquelyIndexedVertex(Neo4jGraph g, String indexName, String indexKey, String indexValue) {
		return new Neo4jVertex(getNodeIndex(g, indexName).get(indexKey, indexValue).getSingle(), g)
	}
	
	static def setPropertyContainerProperties(PropertyContainer pc, Map properties) {
		for (prop in properties) {
			pc.setProperty(prop.key, prop.value)
		}
		return null
	}
	
	static Neo4jVertex createVertex(Neo4jGraph g, Map vertexProperties) {
		def neo4j = g.getRawGraph()
		def rawNode = neo4j.createNode()
		setPropertyContainerProperties(rawNode, vertexProperties)
		return new Neo4jVertex(rawNode, g)
	}
	
	static RelationshipType getRelationshipType(String edgeType) {
		return DynamicRelationshipType.withName(edgeType) 
	}
	
	static Neo4jEdge createEdge(Neo4jGraph g, Neo4jVertex outV, Neo4jVertex inV, String edgeType, Map edgeProperties) {
		Edge e = g.addEdge(null, outV, inV, edgeType)
		setPropertyContainerProperties(e.getRawEdge(), edgeProperties)
		return e
	}
	
	static Neo4jEdge createAndIndexEdge(Neo4jGraph g, Map outVLookupInfo, Map inVLookupInfo, String edgeType, Map edgeProperties, Map fieldsToIndex) {
		Neo4jVertex outV = getUniquelyIndexedVertex(g, outVLookupInfo['lookupIndexName'], outVLookupInfo['lookupKey'], (String) outVLookupInfo['lookupValue'])
		Neo4jVertex inV = getUniquelyIndexedVertex(g, inVLookupInfo['lookupIndexName'], inVLookupInfo['lookupKey'], (String) inVLookupInfo['lookupValue'])
		Neo4jEdge e = createEdge(g, outV, inV, edgeType, edgeProperties)
		addEdgeToIndexes(g, e, fieldsToIndex)
		return e
	}
	
	static Neo4jEdge[] createEdges(Neo4jGraph g, Neo4jVertex outV, Map[] edgeCreationInfoList) {
		def createdLinks = []
		for (edgeInfoMap in edgeCreationInfoList) {
			String edgeType = edgeInfoMap['edgeType']
			Map edgeProps = edgeInfoMap['edgeProperties']
			String inVLookupIdxName = edgeInfoMap['lookupIndexName']
			String inVLookupIdxKey = edgeInfoMap['lookupKey']
			String inVLookupIdxVal = edgeInfoMap['lookupValue']
			
			Neo4jVertex inV = getUniquelyIndexedVertex(g, inVLookupIdxName, inVLookupIdxKey, inVLookupIdxVal)
			Neo4jEdge edge = createEdge(g, outV, inV, edgeType, edgeProps)
			createdLinks.add(edge)
		}
		
		return createdLinks
	}
	
	static Node createAndIndexAndLinkNode(Neo4jGraph g, Map nodeProperties, Map<String, List> fieldsToIndex, Map[] edgeCreationInfoList) {
		def v = createVertex(g, nodeProperties)
		addVertexToIndexes(g, v, fieldsToIndex)
		createEdges(g, v, edgeCreationInfoList)
		return v.getRawVertex()
	}
	
	static Node createAndIndexNode(Neo4jGraph g, Map nodeProperties, Map<String, List> fieldsToIndex) {
		return createAndIndexAndLinkNode(g, nodeProperties, fieldsToIndex)
	}
}
