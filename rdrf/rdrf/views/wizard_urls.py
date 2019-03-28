def build_wizard_urls():
    url_patterns = []
    try:
        from rdrf.models.definition.models import Registry
        for registry_model in Registry.objects.all():
            for review_model in registry_model.reviews.all():
                try:
                    url_patterns.append(review_model.url_pattern)
                except:
                    pass

        return url_patterns
    except:
        return []
