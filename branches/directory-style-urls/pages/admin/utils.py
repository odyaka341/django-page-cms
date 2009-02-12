from django.template import loader, Context, RequestContext, TemplateDoesNotExist
from django.template.loader_tags import ExtendsNode
from django.http import Http404
# must be imported like this for isinstance
from django.templatetags.pages_tags import PlaceholderNode
from django.core.urlresolvers import get_mod_func

from pages.views import details
from pages.models import Page, URL
from pages import settings

def create_url_for_page(page):
    """
    Insert URL Records for a given page based on page.get_url()
    """
    for language in settings.PAGE_LANGUAGES:
        url, new = URL.objects.get_or_create(
                       page=page, url=page.get_url(language[0])
                   )
        if new:
            url.save()

def get_placeholders(request, template_name):
    """
    Return a list of PlaceholderNode found in the given template
    """
    try:
        temp = loader.get_template(template_name)
    except TemplateDoesNotExist:
        return []
    try:
        context = details(request, only_context=True)
    except Http404:
        context = {}
    temp.render(RequestContext(request, context))
    list = []
    placeholders_recursif(temp.nodelist, list)
    return list

def placeholders_recursif(nodelist, list):
    """
    Recursively search into a template node list for PlaceholderNode node
    """
    for node in nodelist:
        if isinstance(node, PlaceholderNode):
            list.append(node)
            node.render(Context())
        for key in ('nodelist', 'nodelist_true', 'nodelist_false'):
            if hasattr(node, key):
                try:
                    placeholders_recursif(getattr(node, key), list)
                except:
                    pass
    for node in nodelist:
        if isinstance(node, ExtendsNode):
            placeholders_recursif(node.get_parent(Context()).nodelist, list)
            
def unique_slug_for_parent(slug, page_id, relationship):
    """
    Checks uniqueness of a slug in relation to other pages.
    """
    if relationship == 'sibling':
        target_page = Page.objects.get(pk=page_id)
        sibling_slugs = [sibling.slug() for sibling in target_page.get_siblings()]
        sibling_slugs.append(target_page.slug())
        if slug in sibling_slugs:
            return False
    elif relationship == 'parent':
        siblings = Page.objects.get(pk=page_id).get_children()
        if slug in [sibling.slug() for sibling in siblings]:
            return False
    return True

def get_connected_models():

    if not settings.PAGE_CONNECTED_MODELS:
        return []
    
    models = []
    for capp in settings.PAGE_CONNECTED_MODELS:
        model = {}
        mod_name, form_name = get_mod_func(capp['form'])
        f = getattr(__import__(mod_name, {}, {}, ['']), form_name)
        #print f.Meta
        model['form'] = f
        mod_name, model_name = get_mod_func(capp['model'])
        model['model_name'] = model_name
        m = getattr(__import__(mod_name, {}, {}, ['']), model_name)
        model['model'] = m
        model['fields'] = []
        for k, v in f.base_fields.iteritems():
            if k is not "page":
                model['fields'].append((model_name.lower() + '_' + k, k, v))
        models.append(model)
    
    return models