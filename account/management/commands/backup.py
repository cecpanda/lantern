'''
python manage.py --dest backup
'''

from django.apps import apps as django_apps
from django.db import connections, transaction
from django.db.utils import ConnectionDoesNotExist, OperationalError
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


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
        call_command('migrate', database=db)

        confirm = input(self.style.WARNING(f'Are you sure to trancate the database {db}? (y/n)'))
        if confirm == 'y':
            call_command('flush', database=db, interactive=False)
            self.stdout.write(self.style.SUCCESS(f'Database {db} had been trancated!'))
        else:
            exit('Backup cancled, bye...')

        # 将 default 数据库中的数据库写入 backup
        all_models = django_apps.all_models

        # contenttypes
        # migrate 的时候自动就添加数据了,
        # flush 的时候清空原来的，又创建新数据，所以主键改变了
        self.backup(model=all_models['contenttypes']['contenttype'], db=db)

        # auth - User
        # permission migrate 的时候自动添加了内容
        # flush 的时候清空原来的，又创建新数据，所以主键改变了
        self.backup(model=all_models['auth']['permission'], db=db)
        self.backup(model=all_models['auth']['group'], db=db)
        self.backup(model=all_models['auth']['group_permissions'], db=db)
        # self.backup(model=all_models['auth']['user'], db=db)

        # account
        # 顺序
        self.backup(model=all_models['account']['user'], db=db)
        self.backup(model=all_models['account']['user_groups'], db=db)
        self.backup(model=all_models['account']['user_user_permissions'], db=db)
        self.backup(model=all_models['account']['follow'], db=db)
        self.backup(model=all_models['account']['groupsetting'], db=db)

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

        self.stdout.write(self.style.SUCCESS('Backup Finished!'))


    def backup(self, model=None, db=None):
        # 自动添加的时间无效了
        # 接下来的主键 ID 不是想要的结果
        if db is None:
            exit(self.style.ERROR('Please confirm the db parameter'))
        try:
            with transaction.atomic(using=db):
                querysets = model.objects.using('default').all()
                model.objects.using(db).delete()  # 因为默认生成的数据主键变了
                # for SQLite where the default is such that at most 999 variables per query are used.
                model.objects.using(db).bulk_create(querysets)
        except Exception as e:
            transaction.rollback(using=db)
            self.stderr.write(self.style.ERROR(f'Something happened, transaction rollbak: {e}.'))
        else:
            self.stdout.write(self.style.SQL_TABLE(f'{model._meta.verbose_name} finished...'))
