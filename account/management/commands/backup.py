from django.core.management.commands import dumpdata, loaddata
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Start testing....'

    def add_arguments(self, parser):
        # ? 只用一个
        # * 表示 0 到多个
        # +表示至少一个
        parser.add_argument('others', metavar='others', nargs='*')
        parser.add_argument('-D', '--dest', metavar='dest database', nargs='?', required=True)

    def handle(self, *args, **options):
        print(options)
        dumpdata.Command().run_from_argv('auth.group')
