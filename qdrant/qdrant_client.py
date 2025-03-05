from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import logging

class QdrantService:
    def __init__(self, host="qdrant", port=6333, collection_name="messages", vector_size: int = 384):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_size = vector_size

    def create_collection(self):
        try:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vector_params=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )
            logging.info(f"Коллекция '{self.collection_name}' создана в Qdrant.")
        except Exception as e:
            logging.error(f"Ошибка при создании коллекции в Qdrant: {e}")

    def upsert_vector(self, record_id: int, vector: list, payload: dict):
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    {
                        "id": record_id,
                        "vector": vector,
                        "payload": payload
                    }
                ]
            )
            logging.info(f"Запись {record_id} обновлена/вставлена в коллекцию '{self.collection_name}'.")
        except Exception as e:
            logging.error(f"Ошибка при вставке в Qdrant: {e}")

    def search_vectors(self, vector: list, top: int = 5, filters: dict = None):
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=top,
                query_filter=filters
            )
            return results
        except Exception as e:
            logging.error(f"Ошибка при поиске в Qdrant: {e}")
            return []
