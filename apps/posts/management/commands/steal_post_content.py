from django.core.management.base import BaseCommand
from apps.posts.scraper import crawl_and_extract
import csv
from pathlib import Path

class Command(BaseCommand):
    help = 'Steal blog post content'
    
    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, help='Single url to crawl')
    
    def handle(self, *args, **options):
        if options['url']:
            success = crawl_and_extract(options['url'])
            if success:
                self.stdout.write(self.style.SUCCESS(f"Successfully added {options['url']}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to add {options['url']}"))
        
        else:
            self.stdout.write(self.style.ERROR("Please provide --url"))