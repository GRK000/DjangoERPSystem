# Generated manually for Aurora Operator.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agent_conversations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="AgentMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant"), ("system", "System"), ("tool", "Tool")], max_length=16)),
                ("content", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="aurora_agent.agentconversation")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="AgentRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("ok", "OK"), ("blocked", "Blocked"), ("error", "Error")], default="ok", max_length=16)),
                ("input_message", models.TextField()),
                ("final_answer", models.TextField(blank=True)),
                ("provider", models.CharField(blank=True, max_length=64)),
                ("model", models.CharField(blank=True, max_length=128)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                ("prompt_tokens", models.PositiveIntegerField(blank=True, null=True)),
                ("completion_tokens", models.PositiveIntegerField(blank=True, null=True)),
                ("total_tokens", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="aurora_agent.agentconversation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agent_runs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AgentToolCall",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tool_name", models.CharField(max_length=120)),
                ("arguments", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(max_length=32)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tool_calls", to="aurora_agent.agentconversation")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tool_calls", to="aurora_agent.agentrun")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="AgentFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.CharField(choices=[("useful", "Useful"), ("not_useful", "Not useful")], max_length=16)),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feedback", to="aurora_agent.agentrun")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agent_feedback", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("run", "user")}},
        ),
    ]
