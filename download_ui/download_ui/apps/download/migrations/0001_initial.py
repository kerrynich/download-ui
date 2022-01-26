# Generated by Django 3.2.11 on 2022-01-26 00:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source', models.CharField(choices=[('YT', 'YouTube'), ('TW', 'Twitch')], default='TW', max_length=2)),
                ('command', models.CharField(choices=[('YTDL', 'youtube-dl'), ('TWDL', 'twitch-dl')], default='TWDL', max_length=4)),
            ],
            options={
                'ordering': ['-created_at', '-updated_at'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Download',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('file_path', models.FilePathField(max_length=300, path='/home/magnolia3289/video-downloads')),
                ('url', models.URLField(max_length=300)),
                ('title', models.CharField(max_length=100)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='download.source')),
            ],
            options={
                'ordering': ['-created_at', '-updated_at'],
                'abstract': False,
            },
        ),
    ]