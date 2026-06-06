# import uuid
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from .models import Industry, AgentRoleTemplate, VoiceAgent
# from django.core.exceptions import ValidationError
# from rest_framework import status


# # ======================================================
# # AGENT MANAGEMENT (Admin APIs)
# # ======================================================

# class CreateAgentView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         industry_id = request.data.get("industry")
#         role_template_id = request.data.get("role_template")
#         name = request.data.get("name")
#         company_name = request.data.get("company_name", "")

#         if not all([industry_id, role_template_id, name]):
#             return Response(
#                 {"error": "industry, role_template and name are required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         industry = Industry.objects.filter(id=industry_id).first()
#         if not industry:
#             return Response({"error": "Industry not found"}, status=404)

#         role_template = AgentRoleTemplate.objects.filter(id=role_template_id).first()
#         if not role_template:
#             return Response({"error": "Role template not found"}, status=404)

#         if role_template.industry != industry:
#             return Response(
#                 {"error": "Selected role does not belong to selected industry"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             agent = VoiceAgent.objects.create(
#                 owner=request.user,
#                 industry=industry,
#                 role_template=role_template,
#                 name=name,
#                 company_name=company_name,
#             )
#         except ValidationError as e:
#             return Response({"error": str(e)}, status=400)

#         return Response({
#             "agent_id": str(agent.id),
#             "api_key": str(agent.api_key)
#         }, status=201)


# class ListUserAgentsView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         agents = VoiceAgent.objects.filter(owner=request.user)
#         return Response([
#             {
#                 "id": str(a.id),
#                 "name": a.name,
#                 "is_active": a.is_active,
#                 "api_key": str(a.api_key)
#             }
#             for a in agents
#         ])


# class ToggleAgentView(APIView):
#     permission_classes = [IsAuthenticated]

#     def patch(self, request, agent_id):
#         agent = VoiceAgent.objects.filter(id=agent_id, owner=request.user).first()
#         if not agent:
#             return Response({"error": "Not found"}, status=404)

#         agent.is_active = not agent.is_active
#         agent.save()
#         return Response({"is_active": agent.is_active})


# class RegenerateAPIKeyView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, agent_id):
#         agent = VoiceAgent.objects.filter(id=agent_id, owner=request.user).first()
#         if not agent:
#             return Response({"error": "Not found"}, status=404)

#         agent.api_key = uuid.uuid4()
#         agent.save()
#         return Response({"api_key": str(agent.api_key)})





















from django.shortcuts import render

# Create your agent views here.
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Industry, AgentRoleTemplate, VoiceAgent
from .serializers import IndustrySerializer, CreateAgentSerializer
from .services.template_resolver import resolve_prompt
from .serializers import AgentRoleTemplateSerializer
from django.core.exceptions import ValidationError
from rest_framework import status

class ListIndustriesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        industries = Industry.objects.prefetch_related("roles").all()
        return Response(IndustrySerializer(industries, many=True).data)


# class CreateAgentView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = CreateAgentSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         template = AgentRoleTemplate.objects.filter(
#             id=serializer.validated_data["template_id"]
#         ).first()

#         if not template:
#             return Response({"error": "Template not found"}, status=404)

#         resolved = resolve_prompt(
#             template,
#             serializer.validated_data["agent_name"],
#             serializer.validated_data.get("company_name", "")
#         )

#         agent = VoiceAgent.objects.create(
#             owner=request.user,
#             template=template,
#             name=serializer.validated_data["agent_name"],
#             company_name=serializer.validated_data.get("company_name", ""),
#             resolved_prompt=resolved
#         )

#         return Response({
#             "agent_id": str(agent.id),
#             "api_key": str(agent.api_key)
#         })


class CreateAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        industry_id = request.data.get("industry")
        role_template_id = request.data.get("role_template")
        name = request.data.get("name")
        company_name = request.data.get("company_name", "")

        if not all([industry_id, role_template_id, name]):
            return Response(
                {"error": "industry, role_template and name are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        industry = Industry.objects.filter(id=industry_id).first()
        if not industry:
            return Response({"error": "Industry not found"}, status=404)

        role_template = AgentRoleTemplate.objects.filter(id=role_template_id).first()
        if not role_template:
            return Response({"error": "Role template not found"}, status=404)

        # Validate role belongs to industry
        if role_template.industry != industry:
            return Response(
                {"error": "Selected role does not belong to selected industry"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            agent = VoiceAgent.objects.create(
                owner=request.user,
                industry=industry,
                role_template=role_template,
                name=name,
                company_name=company_name,
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

        return Response({
            "agent_id": str(agent.id),
            "api_key": str(agent.api_key)
        }, status=201)





class ListUserAgentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        is_admin = False
        if request.user.is_superuser:
            is_admin = True
        elif hasattr(request.user, 'profile') and request.user.profile.role:
            perms = request.user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(request.user, 'profile') and request.user.profile.custom_permissions:
            if request.user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

        if is_admin:
            agents = VoiceAgent.objects.all()
        else:
            # If the user has an assigned agent, let them see it as well
            assigned_agent = None
            if hasattr(request.user, 'profile') and request.user.profile.assigned_agent:
                assigned_agent = request.user.profile.assigned_agent

            if assigned_agent:
                # Merge querysets using |
                agents = VoiceAgent.objects.filter(owner=request.user) | VoiceAgent.objects.filter(id=assigned_agent.id)
            else:
                agents = VoiceAgent.objects.filter(owner=request.user)

        return Response([
            {
                "id": str(a.id),
                "name": a.name,
                "is_active": a.is_active,
                "api_key": str(a.api_key),
                "industry_name": a.industry.name if a.industry else "",
                "role_name": a.role_template.role_name if a.role_template else ""
            }
            for a in agents
        ])


class ToggleAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, agent_id):
        is_admin = False
        if request.user.is_superuser:
            is_admin = True
        elif hasattr(request.user, 'profile') and request.user.profile.role:
            perms = request.user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(request.user, 'profile') and request.user.profile.custom_permissions:
            if request.user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

        if is_admin:
            agent = VoiceAgent.objects.filter(id=agent_id).first()
        else:
            agent = VoiceAgent.objects.filter(id=agent_id, owner=request.user).first()

        if not agent:
            return Response({"error": "Not found"}, status=404)

        agent.is_active = not agent.is_active
        agent.save()
        return Response({"is_active": agent.is_active})


class RegenerateAPIKeyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id):
        is_admin = False
        if request.user.is_superuser:
            is_admin = True
        elif hasattr(request.user, 'profile') and request.user.profile.role:
            perms = request.user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(request.user, 'profile') and request.user.profile.custom_permissions:
            if request.user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

        if is_admin:
            agent = VoiceAgent.objects.filter(id=agent_id).first()
        else:
            agent = VoiceAgent.objects.filter(id=agent_id, owner=request.user).first()

        if not agent:
            return Response({"error": "Not found"}, status=404)

        agent.api_key = uuid.uuid4()
        agent.save()
        return Response({"api_key": str(agent.api_key)})
    


class RoleByIndustryAPIView(APIView):
    def get(self, request, industry_id):
        roles = AgentRoleTemplate.objects.filter(industry_id=industry_id)

        serializer = AgentRoleTemplateSerializer(roles, many=True)

        return Response(serializer.data)
    
class IndustryListAPIView(APIView):
    def get(self, request):
        industries = Industry.objects.all()

        data = [
            {
                "id": industry.id,
                "name": industry.name,
                "slug": industry.slug
            }
            for industry in industries
        ]

        return Response(data)


class DemoBotResolverAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        industry_id = request.GET.get("industry_id")
        role_id = request.GET.get("role_id")

        if not industry_id or not role_id:
            return Response(
                {"error": "industry_id and role_id are required"},
                status=400
            )

        bot = VoiceAgent.objects.filter(
            industry_id=industry_id,
            role_template_id=role_id,
            is_demo=True,
            is_active=True
        ).first()

        if not bot:
            return Response(
                {"error": "No demo bot found for this role"},
                status=404
            )

        return Response({
            "bot_id": str(bot.id),
            "name": bot.name,
            "api_key": str(bot.api_key)
        })