from django.db import models


class ConversationMessage(models.Model):
    """Stores multi-turn conversation history for the AI agent."""

    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]

    thread_ts = models.CharField(max_length=100, db_index=True)
    channel_id = models.CharField(max_length=50, db_index=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["thread_ts", "channel_id"])]

    def __str__(self):
        return f"[{self.role}] {self.channel_id}/{self.thread_ts}: {self.content[:60]}"
