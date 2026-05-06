from django.conf import settings
from django.db import models


class AgentConversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_conversations")
    title = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.user})"


class AgentMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"
        TOOL = "tool", "Tool"

    conversation = models.ForeignKey(AgentConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"


class AgentRun(models.Model):
    class Status(models.TextChoices):
        OK = "ok", "OK"
        BLOCKED = "blocked", "Blocked"
        ERROR = "error", "Error"

    conversation = models.ForeignKey(AgentConversation, on_delete=models.CASCADE, related_name="runs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_runs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OK)
    input_message = models.TextField()
    final_answer = models.TextField(blank=True)
    provider = models.CharField(max_length=64, blank=True)
    model = models.CharField(max_length=128, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    prompt_tokens = models.PositiveIntegerField(null=True, blank=True)
    completion_tokens = models.PositiveIntegerField(null=True, blank=True)
    total_tokens = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Run {self.id} {self.status}"


class AgentToolCall(models.Model):
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="tool_calls")
    conversation = models.ForeignKey(AgentConversation, on_delete=models.CASCADE, related_name="tool_calls")
    tool_name = models.CharField(max_length=120)
    arguments = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32)
    latency_ms = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.tool_name} ({self.status})"


class AgentFeedback(models.Model):
    class Rating(models.TextChoices):
        USEFUL = "useful", "Useful"
        NOT_USEFUL = "not_useful", "Not useful"

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_feedback")
    rating = models.CharField(max_length=16, choices=Rating.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["run", "user"]

    def __str__(self):
        return f"{self.rating} for run {self.run_id}"
