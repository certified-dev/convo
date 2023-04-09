from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Count
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


def user_directory_path(instance, filename):
    return 'user_{0}/{1}'.format(instance.username, filename)


class User(AbstractUser):
    display_photo = models.ImageField(upload_to=user_directory_path, default='placeholder/image.jpeg')
    last_conversation = models.CharField(max_length=4, blank=True, null=True)
    # friends = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    @receiver(post_save, sender=settings.AUTH_USER_MODEL)
    def create_auth_token(sender, instance=None, created=False, **kwargs):
        if created:
            Token.objects.create(user=instance)

    def __str__(self):
        return self.username


class TrackingModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ConversationManager(models.Manager):
    def get_or_create_personal_conversation(self, first_user, second_user):
        conversations = self.get_queryset().filter(type='personal')
        conversations = conversations.filter(users__in=[first_user, second_user]).distinct()
        conversations = conversations.annotate(u_count=Count('users')).filter(u_count=2)

        if conversations.exists():
            return conversations.first()
        else:
            conversation = self.create(type='personal', name=f'{first_user}__{second_user}')
            conversation.users.add(first_user)
            conversation.users.add(second_user)
            conversation.name = f'{first_user}__{second_user}'
            return conversation

    def get_or_create_group_conversation(self, user, name):
        conversations = self.get_queryset().filter(type='group')
        conversations = conversations.filter(users__in=[user])

        if conversations.exists():
            return conversations.first()
        else:
            conversation = self.create(type='group', name=name)
            conversation.users.add(user)
            return conversation

    def by_user(self, user):
        return self.get_queryset().filter(users_in=[user])


class Conversation(TrackingModel):
    CONVERSATION_TYPE = (
        ('personal', 'Personal'),
        ('group', 'Group')
    )

    name = models.CharField(max_length=40, null=True, blank=True)
    type = models.CharField(max_length=15, choices=CONVERSATION_TYPE, default='group')
    users = models.ManyToManyField(User)
    online = models.ManyToManyField(User, related_name="online_users", blank=True)

    objects = ConversationManager()

    def __str__(self) -> str:
        if self.type == 'personal' and self.users.count() == 2:
            return f'{self.users.first()} and {self.users.last()}'
        return f'{self.name}'

    def get_unread_messages_count(self, user):
        return self.messages.filter(recipient=user, read=False).count()


class Message(TrackingModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', blank=True,
                                  null=True)
    content = models.CharField(max_length=1000)
    state = models.CharField(max_length=10, default="sent")
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self) -> str:
        if self.recipient:
            return f'{self.sender} -> {self.recipient} : {self.content} @ {self.created_at}'
        return f'{self.sender} : {self.content} @ {self.created_at}'
