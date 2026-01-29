from neo4j import GraphDatabase
from datetime import datetime

class Neo4jStore:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def upsert_document(self, doc_id, filename):
        q = """
        MERGE (d:Document {id:$doc_id})
        SET d.filename=$filename, d.created_at=$created_at
        """
        with self.driver.session() as s:
            s.run(q, doc_id=doc_id, filename=filename, created_at=datetime.utcnow().isoformat())

    def upsert_chunks(self, doc_id, chunks):
        q = """
        MATCH (d:Document {id:$doc_id})
        UNWIND $chunks AS c
        MERGE (ch:Chunk {id:c.id})
        SET ch.doc_id=$doc_id, ch.page_start=c.page_start, ch.page_end=c.page_end,
            ch.text=c.text, ch.text_preview=c.text_preview
        MERGE (d)-[:HAS_CHUNK]->(ch)
        """
        with self.driver.session() as s:
            s.run(q, doc_id=doc_id, chunks=chunks)

    def link_concepts(self, chunk_id, concepts):
        q = """
        MATCH (ch:Chunk {id:$chunk_id})
        UNWIND $concepts AS k
        MERGE (c:Concept {name:k.name})
        MERGE (ch)-[r:MENTIONS]->(c)
        SET r.score = k.score
        """
        with self.driver.session() as s:
            s.run(q, chunk_id=chunk_id, concepts=concepts)

    def expand_from_chunk_ids(self, doc_id, chunk_ids, limit_chunks=12):
        # find concepts mentioned in retrieved chunks, then pull more chunks sharing those concepts
        q = """
        MATCH (ch:Chunk)-[:MENTIONS]->(c:Concept)
        WHERE ch.doc_id=$doc_id AND ch.id IN $chunk_ids
        WITH c
        MATCH (ch2:Chunk)-[:MENTIONS]->(c)
        WHERE ch2.doc_id=$doc_id
        RETURN DISTINCT ch2.id AS id, ch2.text AS text, ch2.page_start AS page_start, ch2.page_end AS page_end
        LIMIT $limit_chunks
        """
        with self.driver.session() as s:
            rows = s.run(q, doc_id=doc_id, chunk_ids=chunk_ids, limit_chunks=limit_chunks)
            return [r.data() for r in rows]
