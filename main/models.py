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
            return  conversation


    def by_user(self, user):
        return self.get_queryset().filter(users_in=[user])


class Conversation(TrackingModel):
    CONVOS_TYPE = (
        ('personal','Personal'),
        ('group','Group')
    )

    name = models.CharField(max_length=20, null=True, blank=True)
    type = models.CharField(max_length=15, choices=CONVOS_TYPE, default='group')
    users = models.ManyToManyField(User)

    objects = ConversationManager()

    def __str__(self) -> str:
        if self.type == 'personal' and self.users.count() == 2:
            return  f'{self.users.first()} and {self.users.last()}'
        return f'{self.name}'


class Message(TrackingModel):
    conversation = models.ForeignKey(Conversation,on_delete=models.CASCADE ,related_name='messages')
    sender = models.ForeignKey(User,on_delete=models.CASCADE , related_name='messages')
    text  = models.CharField(max_length=3000, blank=True, null=True)


    class Meta:
        ordering = ['created_at']


    def __str__(self):
        reciever = self.conversation.users.exclude(username=self.sender.username).first()
        return f'{self.sender} -> {reciever} : {self.text}'