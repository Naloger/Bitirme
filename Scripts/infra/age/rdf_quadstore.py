# -*- coding: utf-8 -*-
"""RDF Quadstore Labeled Property Graph manager for Apache AGE."""

from typing import Dict, List, Any, Optional

# Add backend directory to Python path if running script directly
# PROJECT_ROOT = Path(__file__).resolve().parents[3]
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.append(str(PROJECT_ROOT))

from Libs.Config.config import AGE_MEMORY_DB, AGE_RDF_GRAPH
from Scripts.infra.age.age_helpers import (
    ensure_database_exists,
    get_age_connection,
    create_age_graph,
    drop_age_graph,
    parse_agtype,
    execute_cypher_param
)


class RDFQuadstore:
    """
    Manages an RDF based quadstore using Labeled Property Graphs in Apache AGE.
    Quads are represented as: (Subject:RDFResource) -[r:RDF_EDGE {predicate, context}]-> (Object:RDFResource|RDFLiteral)
    """

    def __init__(self, db_name: str = AGE_MEMORY_DB, graph_name: str = AGE_RDF_GRAPH):
        self.db_name = db_name
        self.graph_name = graph_name
        # Ensure database and graph are ready
        ensure_database_exists(self.db_name)
        conn = get_age_connection(self.db_name)
        try:
            create_age_graph(conn, self.graph_name)
        finally:
            conn.close()

    def add_quad(self, subject: Dict[str, str], predicate: str, obj: Dict[str, Any], context: str) -> None:
        """
        Add a single RDF quad to the quadstore.
        
        Args:
            subject: dict with keys:
                - 'type': 'iri' or 'bnode'
                - 'value': URI string or blank node ID
            predicate: URI string of the predicate
            obj: dict with keys:
                - 'type': 'iri', 'bnode' or 'literal'
                - 'value': URI string / blank node ID, or the string value of the literal
                - 'datatype': (Optional) string datatype URI for literals
                - 'lang': (Optional) string language tag for literals
            context: URI string of the named graph / context
        """
        conn = get_age_connection(self.db_name)
        try:
            with conn.cursor() as cur:
                is_literal = obj.get("type") == "literal"
                
                if is_literal:
                    params = {
                        "subject": {"value": subject["value"], "type": subject["type"]},
                        "predicate": predicate,
                        "object": {
                            "value": str(obj["value"]),
                            "datatype": str(obj.get("datatype") or "http://www.w3.org/2001/XMLSchema#string"),
                            "lang": str(obj.get("lang") or "")
                        },
                        "context": context
                    }
                    
                    query = """
                    MERGE (s:RDFResource {uri: $subject.value, type: $subject.type})
                    MERGE (o:RDFLiteral {value: $object.value, datatype: $object.datatype, lang: $object.lang})
                    MERGE (s)-[r:RDF_EDGE {predicate: $predicate, context: $context}]->(o)
                    RETURN id(r)
                    """
                else:
                    params = {
                        "subject": {"value": subject["value"], "type": subject["type"]},
                        "predicate": predicate,
                        "object": {"value": obj["value"], "type": obj["type"]},
                        "context": context
                    }
                    
                    query = """
                    MERGE (s:RDFResource {uri: $subject.value, type: $subject.type})
                    MERGE (o:RDFResource {uri: $object.value, type: $object.type})
                    MERGE (s)-[r:RDF_EDGE {predicate: $predicate, context: $context}]->(o)
                    RETURN id(r)
                    """
                
                execute_cypher_param(cur, self.graph_name, query, params, "as (r agtype)")
        finally:
            conn.close()

    def query_quads(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj_value: Optional[str] = None,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query quads matching the given patterns (None acts as wildcard).
        
        Returns:
            List of dicts representing matched quads:
            {
                "subject": {"type": ..., "value": ...},
                "predicate": ...,
                "object": {"type": ..., "value": ..., "datatype": ..., "lang": ...},
                "context": ...
            }
        """
        conn = get_age_connection(self.db_name)
        try:
            with conn.cursor() as cur:
                cypher_query = "MATCH (s:RDFResource)-[r:RDF_EDGE]->(o) "
                where_clauses = []
                params = {}

                if subject:
                    where_clauses.append("s.uri = $subject")
                    params["subject"] = subject

                if predicate:
                    where_clauses.append("r.predicate = $predicate")
                    params["predicate"] = predicate

                if context:
                    where_clauses.append("r.context = $context")
                    params["context"] = context

                if obj_value:
                    where_clauses.append("(o.uri = $obj_val OR o.value = $obj_val)")
                    params["obj_val"] = obj_value

                if where_clauses:
                    cypher_query += "WHERE " + " AND ".join(where_clauses) + " "

                cypher_query += (
                    "RETURN s.uri, s.type, r.predicate, r.context, "
                    "       o.uri, o.value, o.datatype, o.lang, labels(o)"
                )
                
                col_defs = "as (s_uri agtype, s_type agtype, r_pred agtype, r_ctx agtype, " \
                           "    o_uri agtype, o_val agtype, o_datatype agtype, o_lang agtype, o_labels agtype)"
                
                rows = execute_cypher_param(cur, self.graph_name, cypher_query, params, col_defs)
                
                results = []
                for r in rows:
                    s_uri = parse_agtype(r[0])
                    s_type = parse_agtype(r[1])
                    r_pred = parse_agtype(r[2])
                    r_ctx = parse_agtype(r[3])
                    o_uri = parse_agtype(r[4])
                    o_val = parse_agtype(r[5])
                    o_datatype = parse_agtype(r[6])
                    o_lang = parse_agtype(r[7])
                    o_labels = parse_agtype(r[8])
                    
                    is_literal = False
                    if o_labels and "RDFLiteral" in o_labels:
                        is_literal = True
                    
                    if is_literal:
                        obj_data = {
                            "type": "literal",
                            "value": o_val,
                            "datatype": o_datatype,
                            "lang": o_lang
                        }
                    else:
                        obj_data = {
                            "type": s_type or "iri",
                            "value": o_uri
                        }
                        
                    results.append({
                        "subject": {
                            "type": s_type or "iri",
                            "value": s_uri
                        },
                        "predicate": r_pred,
                        "object": obj_data,
                        "context": r_ctx
                    })
                return results
        finally:
            conn.close()

    def delete_quads(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj_value: Optional[str] = None,
        context: Optional[str] = None
    ) -> None:
        """Delete quads matching the given patterns."""
        conn = get_age_connection(self.db_name)
        try:
            with conn.cursor() as cur:
                cypher_query = "MATCH (s:RDFResource)-[r:RDF_EDGE]->(o) "
                where_clauses = []
                params = {}

                if subject:
                    where_clauses.append("s.uri = $subject")
                    params["subject"] = subject

                if predicate:
                    where_clauses.append("r.predicate = $predicate")
                    params["predicate"] = predicate

                if context:
                    where_clauses.append("r.context = $context")
                    params["context"] = context

                if obj_value:
                    where_clauses.append("(o.uri = $obj_val OR o.value = $obj_val)")
                    params["obj_val"] = obj_value

                if where_clauses:
                    cypher_query += "WHERE " + " AND ".join(where_clauses) + " "

                cypher_query += "DELETE r"
                
                execute_cypher_param(cur, self.graph_name, cypher_query, params, "as (a agtype)")
        finally:
            conn.close()

    def clear(self) -> None:
        """Clear all nodes and relationships from the quadstore graph."""
        conn = get_age_connection(self.db_name)
        try:
            drop_age_graph(conn, self.graph_name)
            create_age_graph(conn, self.graph_name)
        finally:
            conn.close()
