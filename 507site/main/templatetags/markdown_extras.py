from django import template
import markdown as md
import re

register = template.Library()

@register.filter(name='markdown')
def markdown_format(value):
    html = md.markdown(
        value,
        extensions=[
            'extra',
            'nl2br',
            'sane_lists',
        ]
    )
    
    html = re.sub(
        r'<li>\[ \] (.*?)</li>', 
        r'<li><input type="checkbox" class="task-checkbox"> \1</li>', 
        html
    )
    
    html = re.sub(
        r'<li>\[x\] (.*?)</li>', 
        r'<li><input type="checkbox" class="task-checkbox" checked> \1</li>', 
        html
    )
    
    return html