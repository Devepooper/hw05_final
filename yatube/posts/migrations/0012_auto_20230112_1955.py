# Generated by Django 2.2.16 on 2023-01-12 19:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0011_auto_20230111_2211'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={},
        ),
        migrations.AlterField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, help_text='Загрузите сюда picture', null=True, upload_to='posts/', verbose_name='Картинка'),
        ),
    ]
