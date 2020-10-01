import sys
import ftplib as ftp
from django.core.management.base import BaseCommand
from django.conf import settings
from rdrf.services.io.actions import deidentified_data_extract as dde


class Command(BaseCommand):
    help = 'Send deidentified data to CICAP'

    def add_arguments(self, parser):
        parser.add_argument('-r',
                            '--registry-code',
                            action='store',
                            dest='registry_code',
                            default=None,
                            help='registry code')

    def get_setting(self, key):
        if not hasattr(settings, key):
            self.stderr.write(f"Error: {key} not in settings")
            sys.exit(1)
        else:
            return getattr(settings, key)

    def handle(self, *args, **options):
        cicap_address = self.get_setting("CICAP_ADDRESS")
        cicap_user = self.get_setting("CICAP_USER")
        cicap_password = self.get_setting("CICAPP_PASSWORD")

        custom_action = None
        user = None

        remote_filename, bytes_io = dde.execute(custom_action, user, create_bytes_io=True)
        ftp_command = "STOR %s" % remote_filename
        ftp_conn = ftp.FTP(cicap_address, cicap_user, cicap_password)
        ftp_conn.storbinary(ftp_command, bytes_io)
        ftp_conn.close()
        bytes_io.close()
