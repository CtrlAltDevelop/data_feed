from django.core.management.base import BaseCommand
from apps.posts.crawler import add_site
import csv
from pathlib import Path

class Command(BaseCommand):
    help = 'Add website to sources'
    
    def add_arguments(self, parser):
        parser.add_argument('--domain', type=str, help='Single domain to crawl')
    
    def handle(self, *args, **options):
        if options['domain']:
            success = add_site(options['domain'])
            if success:
                self.stdout.write(self.style.SUCCESS(f"Successfully added {options['domain']}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to add {options['domain']}"))
        
        else:
            self.stdout.write(self.style.ERROR("Please provide --domain"))