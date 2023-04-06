from django.contrib import admin
from django.contrib.auth.models import Group

from .models import User, Conversation, Message, TrackingModel

admin.site.register(User)
admin.site.register(Message)
admin.site.register(Conversation)
admin.site.unregister(Group)
