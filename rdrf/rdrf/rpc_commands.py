import logging
logger = logging.getLogger('registry_log')


def rpc_visibility(request, element):
    user = request.user
    if user.can("see", element):
        return True


def rpc_check_notifications(request):
    from rdrf.models import Notification
    user = request.user
    results = []
    notifications = Notification.objects.filter(to_username=user.username).order_by('-created')
    for notification in notifications:
        results.append({"message": notification.message, "from_user": notification.from_username, "link": notification.link})
    return results

