from django.contrib import admin

from .models import AgentConversation, AgentFeedback, AgentMessage, AgentRun, AgentToolCall


class AgentMessageInline(admin.TabularInline):
    model = AgentMessage
    extra = 0
    readonly_fields = ("role", "content", "metadata", "created_at")
    can_delete = False


class AgentToolCallInline(admin.TabularInline):
    model = AgentToolCall
    extra = 0
    readonly_fields = ("tool_name", "arguments", "result", "status", "latency_ms", "error_message", "created_at")
    can_delete = False


@admin.register(AgentConversation)
class AgentConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "created_at", "updated_at")
    search_fields = ("title", "user__username")
    inlines = [AgentMessageInline]


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "user", "status", "provider", "model", "latency_ms", "created_at")
    search_fields = ("input_message", "final_answer", "user__username")
    list_filter = ("status", "provider", "model")
    readonly_fields = ("created_at",)
    inlines = [AgentToolCallInline]


@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "created_at")
    search_fields = ("content",)
    list_filter = ("role",)


@admin.register(AgentToolCall)
class AgentToolCallAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "tool_name", "status", "latency_ms", "created_at")
    search_fields = ("tool_name", "error_message")
    list_filter = ("status", "tool_name")


@admin.register(AgentFeedback)
class AgentFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "user", "rating", "created_at")
    list_filter = ("rating",)
