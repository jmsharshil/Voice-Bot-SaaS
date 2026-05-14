from rest_framework import serializers
from .models import Industry, AgentRoleTemplate, VoiceAgent


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRoleTemplate
        fields = ["id", "role_name", "description"]


class IndustrySerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True)

    class Meta:
        model = Industry
        fields = ["id", "name", "slug", "roles"]


# class CreateAgentSerializer(serializers.Serializer):
#     template_id = serializers.IntegerField()
#     agent_name = serializers.CharField()
#     company_name = serializers.CharField(required=False)



class CreateAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceAgent
        fields = [
            "industry",
            "role_template",
            "name",
            "company_name",
        ]

    def validate(self, data):
        if data["role_template"].industry != data["industry"]:
            raise serializers.ValidationError(
                "Selected role does not belong to selected industry."
            )
        return data

    def create(self, validated_data):
        request = self.context["request"]
        return VoiceAgent.objects.create(
            owner=request.user,
            **validated_data
        )



class AgentRoleTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRoleTemplate
        fields = ["id", "role_name", "description"]