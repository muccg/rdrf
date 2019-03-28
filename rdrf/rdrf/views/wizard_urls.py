from rdrf.models.definition.models import Registry


def build_wizard_urls():
    url_patterns = []
    for registry_model in Registry.objects.all():
        for review_model in registry_model.reviews.all():
            url_patterns.append(review_model.url_pattern)
    return url_patterns
