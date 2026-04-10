from ninja.errors import HttpError


def get_object_or_404(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        raise HttpError(404, f"{model.__name__} tidak ditemukan")
