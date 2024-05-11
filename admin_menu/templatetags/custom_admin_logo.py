from django import template
from django.conf import settings

from AP01.models.core import T01Com10

register = template.Library()


@register.simple_tag
def get_custom_logo():
    return getattr(settings, "ADMIN_LOGO", None)


@register.simple_tag
def get_logo():
    data = T01Com10.objects.filter(parent=0).first()
    return data
