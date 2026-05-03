from django.db import models


class Conversation(models.Model):
    session_key = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Sohbet"
        verbose_name_plural = "Sohbetler"

    def __str__(self):
        return f"Sohbet #{self.pk} ({self.session_key[:12]}…)"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'Kullanıcı'),
        ('assistant', 'ACUBOT'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Sohbet Mesajı"
        verbose_name_plural = "Sohbet Mesajları"

    def __str__(self):
        preview = self.text[:80] + "…" if len(self.text) > 80 else self.text
        return f"[{self.get_role_display()}] {preview}"
