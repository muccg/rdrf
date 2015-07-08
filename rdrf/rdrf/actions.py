from rdrf import rpc_commands
import logging
logger = logging.getLogger("registry_log")


class ActionExecutor(object):

    def __init__(self, request, action_dict):
        self.action_dict = action_dict
        self.request = request

    def run(self):
        rpc_command = self.action_dict['rpc_command']
        rpc_args = self.action_dict['args']  # a list of values
        rpc_function = self._locate_command_function(rpc_command)
        client_response = {}

        if rpc_function:
            try:
                # always pass request (conventionally) as first argument
                args = [self.request] + rpc_args
                result = rpc_function(*args)
                client_response['result'] = result
                client_response['status'] = 'success'
            except Exception as ex:
                client_response['status'] = 'fail'
                client_response['error'] = ex.message
        else:
            client_response['status'] = 'fail'
            client_response['error'] = 'could not locate command: %s' % rpc_command

        logger.info("rpm command: %s args: %s result: %s" %
                    (rpc_command, rpc_args, client_response))
        return client_response

    def _locate_command_function(self, rpc_command):
        logger.info("%s looking for rpc_%s" % (self, rpc_command))
        command_name = "rpc_%s" % rpc_command
        if hasattr(rpc_commands, command_name):
            rpc_function = getattr(rpc_commands, command_name)
            if callable(rpc_function):
                return rpc_function
        else:
            logger.info("could not find a callable with that name")
