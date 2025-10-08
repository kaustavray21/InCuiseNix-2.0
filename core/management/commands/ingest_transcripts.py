from django.core.management.base import BaseCommand
from core.rag_utils import create_or_update_vector_store

class Command(BaseCommand):
    help = 'Loads video transcripts, creates embeddings, and stores them in the vector database.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting the transcript ingestion process...'))
        try:
            create_or_update_vector_store()
            self.stdout.write(self.style.SUCCESS('Successfully ingested all transcripts into the vector store.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred during ingestion: {e}'))