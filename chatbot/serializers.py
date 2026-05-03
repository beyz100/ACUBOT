from rest_framework import serializers
from .models import Conversation, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'text', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'session_key', 'created_at', 'updated_at', 'messages', 'message_count']

    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    first_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'created_at', 'updated_at', 'message_count', 'first_message']

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_first_message(self, obj):
        first_msg = obj.messages.filter(role='user').first()
        if first_msg:
            preview = first_msg.text[:100]
            if len(first_msg.text) > 100:
                preview += "..."
            return preview
        return ""

