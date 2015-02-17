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
    notifications = Notification.objects.filter(to_username=user.username, seen=False).order_by('-created')
    for notification in notifications:
        results.append({"message": notification.message, "from_user": notification.from_username, "link": notification.link})
    return results


def rpc_dismiss_notification(request, notification_id):
    from rdrf.models import Notification
    status = False
    try:
        notification = Notification.objects.get(pk=int(notification_id))
        notification.seen = True
        notification.save()
        status = True
    except Exception, ex:
        logger.error("could not mark notification with id %s as seen: %s" % (notification_id, ex))
    return status

