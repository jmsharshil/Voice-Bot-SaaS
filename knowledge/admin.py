from django.contrib import admin
from .models import KnowledgeFile, KnowledgeChunk
from .services.text_extractor import extract_text
from .services.chunker import chunk_text
from .services.indexer import build_agent_index

@admin.register(KnowledgeFile)
class KnowledgeFileAdmin(admin.ModelAdmin):
    list_display = ("id", "agent", "file")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.file:
            try:
                extracted = extract_text(obj.file)
                obj.extracted_text = extracted
                obj.save()

                chunks = chunk_text(extracted)
                KnowledgeChunk.objects.filter(knowledge_file=obj).delete()
                chunk_objs = [
                    KnowledgeChunk(
                        knowledge_file=obj,
                        chunk_index=idx,
                        content=c_text
                    )
                    for idx, c_text in enumerate(chunks)
                ]
                KnowledgeChunk.objects.bulk_create(chunk_objs)

                if obj.agent_id:
                  build_agent_index(str(obj.agent_id))
                  print(
                      f"[ADMIN OK] Processed {obj.file.name} ->"
                      f" {len(chunk_objs)} chunks & rebuilt FAISS index for agent"
                      f" {obj.agent_id}"
                  )
            except Exception as e:
                print(f"[ADMIN ERROR] Failed to process knowledge file: {e}")

@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "knowledge_file")