'''
python manage.py --dest backup
'''

from django.apps import apps as django_apps
from django.db import connections, transaction
from django.db.utils import ConnectionDoesNotExist, OperationalError
from django.core.management.base import BaseCommand, CommandError
from django.core.management.commands import migrate, flush

from tft.models import ID


class Command(BaseCommand):
    help = 'Backup default database to destination database.'

    def add_arguments(self, parser):
        # ? 只用一个
        # * 表示 0 到多个
        # +表示至少一个
        parser.add_argument('others', metavar='others', nargs='*')
        parser.add_argument('-D', '--dest', metavar='dest database', nargs='?', default='backup')

    def handle(self, *args, **options):
        db = options['dest']

        if db == 'default':
            raise CommandError(f'This is the production database.')

        # 验证 backup 是否有效
        try:
            connection = connections[db]
            if not connection.is_usable():
                raise OperationalError('Not Usable!')
        except ConnectionDoesNotExist:
            raise CommandError(f'Database connection of {db} does not exist, please check settings.py.')
        except (OperationalError, AttributeError) as e:
            raise CommandError(f'Database {db} connecting failed: {e}.')

        # 同步并清空 备份数据库
        argv = ['manage.py', 'migrate', '--database', db]
        migrate.Command().run_from_argv(argv)
        flush.Command().run_from_argv(argv)

        # 将 default 数据库中的数据库写入 backup
        all_models = django_apps.all_models

        # contenttypes
        for model in all_models['contenttypes'].values():
            self.backup(model=model, db=db)

        # auth - User
        self.backup(model=all_models['auth']['permission'], db=db)
        self.backup(model=all_models['auth']['group_permissions'], db=db)
        self.backup(model=all_models['auth']['group'], db=db)

        # account
        for model in all_models['account'].values():
            self.backup(model=model, db=db)

        # sessiongs
        for model in all_models['sessions'].values():
            self.backup(model=model, db=db)

        # admin
        for model in all_models['admin'].values():
            self.backup(model=model, db=db)

        # xadmin
        for model in all_models['xadmin'].values():
            self.backup(model=model, db=db)

        # action
        for model in all_models['action'].values():
            self.backup(model=model, db=db)

        # tft
        for model in all_models['tft'].values():
            self.backup(model=model, db=db)

        self.stdout.write('Backup Finished!')


    def backup(self, model=None, db=None):
        if db is None:
            return
        # try:
        with transaction.atomic(using=db):
            querysets = model.objects.using('default').all()
            # for SQLite where the default is such that at most 999 variables per query are used.
            for queryset in querysets:
                queryset.save()
        # except Exception as e:
        #     transaction.rollback(using=db)
        #     self.stderr.write(f'Something happened, transaction rollbak: {e}.')
        # else:
        #     self.stdout.write(f'{str(model)} finished...')
