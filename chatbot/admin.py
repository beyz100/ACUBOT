from django.contrib import admin
from .models import Conversation, ChatMessage


class ChatMessageInline(admin.TabularInline):
    """Show messages inline within a Conversation in admin."""
    model = ChatMessage
    readonly_fields = ('role', 'text', 'created_at')
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_key_short', 'message_count', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('session_key', 'messages__text')
    readonly_fields = ('session_key', 'created_at', 'updated_at')
    inlines = [ChatMessageInline]

    @admin.display(description="Oturum Anahtarı")
    def session_key_short(self, obj):
        return obj.session_key[:16] + "…" if len(obj.session_key) > 16 else obj.session_key

    @admin.display(description="Mesaj Sayısı")
    def message_count(self, obj):
        return obj.messages.count()


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'text_preview', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('text',)
    readonly_fields = ('conversation', 'role', 'text', 'created_at')

    @admin.display(description="Mesaj Önizleme")
    def text_preview(self, obj):
        return obj.text[:100] + "…" if len(obj.text) > 100 else obj.text
