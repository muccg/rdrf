class AdjudicationCommand(object):
    def __init__(self, adjudication, notifier):
        self.adjudication= adjudication
        self.notifier = notifier

    def run(self):
        message = self.adjudication.decision.summary
        self.notifier.send_notification(self.adjudication.definition.a)





