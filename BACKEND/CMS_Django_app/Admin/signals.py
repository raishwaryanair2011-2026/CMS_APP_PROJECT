from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import Staff


@receiver(post_save, sender=Staff)
def assign_default_role(sender, instance, created, **kwargs):
    """
    Automatically assign default 'Staff' role
    when a Staff record is created.
    """

    if created:
        group, _ = Group.objects.get_or_create(name="Staff")
        instance.user.groups.add(group)