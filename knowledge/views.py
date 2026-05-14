# from django.shortcuts import render

# # Create your knowledge views here.
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from .models import KnowledgeFile
# from .serializers import KnowledgeUploadSerializer
# from .services.text_extractor import extract_text
# from agents.models import VoiceAgent
# from .services.chunker import chunk_text
# from .models import KnowledgeChunk


# class KnowledgeUploadView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, agent_id):
#         agent = VoiceAgent.objects.filter(
#             id=agent_id,
#             owner=request.user
#         ).first()

#         if not agent:
#             return Response({"error": "Agent not found"}, status=404)

#         serializer = KnowledgeUploadSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         knowledge = serializer.save(agent=agent)

#         # Extract text
#         extracted = extract_text(knowledge.file.path)
#         knowledge.extracted_text = extracted
#         knowledge.save()



#         chunks = chunk_text(extracted)

#         for chunk in chunks:
#             KnowledgeChunk.objects.create(
#                 knowledge_file=knowledge,
#                 content=chunk
#             )

#         return Response({
#             "message": "File uploaded successfully",
#             "text_length": len(extracted)
#         })







from django.shortcuts import render

# Create your knowledge views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import KnowledgeFile
from .serializers import KnowledgeUploadSerializer
from .services.text_extractor import extract_text
from agents.models import VoiceAgent
from .services.chunker import chunk_text
from .models import KnowledgeChunk
from .services.indexer import add_chunks_to_index


class KnowledgeUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        agent = VoiceAgent.objects.filter(
            id=agent_id,
            owner=request.user
        ).first()

        if not agent:
            return Response({"error": "Agent not found"}, status=404)

        serializer = KnowledgeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        knowledge = serializer.save(agent=agent)

        # Extract text
        extracted = extract_text(knowledge.file.path)
        knowledge.extracted_text = extracted
        knowledge.save()

        # Chunk text
        chunks = chunk_text(extracted)

        # Save chunks to DB
        chunk_objects = []
        for chunk in chunks:
            obj = KnowledgeChunk.objects.create(
                knowledge_file=knowledge,
                content=chunk
            )
            chunk_objects.append(obj)

        # Generate embeddings + add to FAISS index
        try:
            add_chunks_to_index(agent, chunk_objects)
        except Exception as e:
            print(f"⚠️ FAISS indexing failed (chunks saved but not indexed): {e}")

        return Response({
            "message": "File uploaded and indexed successfully",
            "text_length": len(extracted),
            "chunks_created": len(chunk_objects),
        })