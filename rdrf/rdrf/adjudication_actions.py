from rdrf.notifications import Notifier


class AdjudicationAction(object):
    def __init__(self, adjudication):
        self.adjudication = adjudication
        self.notifier = Notifier()

    def run(self):
        message = self.adjudication.decision.summary
        self.notifier.send_system_notification(self.adjudication.definition.adjudicator_username,
                                        self.adjudication.requesting_username,
                                        message)

