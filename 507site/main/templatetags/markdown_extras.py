from django import template
import markdown as md

register = template.Library()

@register.filter(name='markdown')
def markdown_format(value):

    return md.markdown(
        value,
        extensions=[
            'extra',      # Enables tables, fenced code blocks, etc.
            'nl2br',      # Converts newlines to <br> tags
            'sane_lists'  # Better list handling
        ]
    )