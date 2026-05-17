from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from resources.models import Resource


def delete_thumbnail_file_if_unused(file_name: str, exclude_pk: int | None = None) -> None:
    if not file_name:
        return

    queryset = Resource.objects.filter(thumbnail_url=file_name)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)

    if queryset.exists():
        return

    Resource._meta.get_field("thumbnail_url").storage.delete(file_name)


@receiver(pre_save, sender=Resource)
def delete_old_thumbnail_on_change(sender, instance: Resource, **kwargs) -> None:
    if not instance.pk:
        return

    try:
        old_thumbnail = sender.objects.only("thumbnail_url").get(pk=instance.pk).thumbnail_url
    except sender.DoesNotExist:
        return

    old_file_name = old_thumbnail.name
    new_file_name = instance.thumbnail_url.name

    if old_file_name and old_file_name != new_file_name:
        delete_thumbnail_file_if_unused(old_file_name, exclude_pk=instance.pk)


@receiver(post_delete, sender=Resource)
def delete_thumbnail_on_resource_delete(sender, instance: Resource, **kwargs) -> None:
    delete_thumbnail_file_if_unused(instance.thumbnail_url.name)
