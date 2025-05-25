from django.core.management.base import BaseCommand
from apps.posts.crawler import run_crawler, batch_crawl
import csv
from pathlib import Path

class Command(BaseCommand):
    help = 'Crawl websites and extract blog posts'
    
    def add_arguments(self, parser):
        parser.add_argument('--domain', type=str, help='Single domain to crawl')
        parser.add_argument('--file', type=str, help='CSV file with domains to crawl')
    
    def handle(self, *args, **options):
        if options['domain']:
            success = run_crawler(options['domain'])
            if success:
                self.stdout.write(self.style.SUCCESS(f"Successfully crawled {options['domain']}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to crawl {options['domain']}"))
        
        elif options['file']:
            file_path = Path(options['file'])
            if not file_path.exists():
                self.stdout.write(self.style.ERROR(f"File {file_path} not found"))
                return
            
            domains = []
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        domains.append(row[0].strip())
            
            if not domains:
                self.stdout.write(self.style.ERROR("No domains found in file"))
                return
            
            results = batch_crawl(domains)
            for domain, success in results:
                if success:
                    self.stdout.write(self.style.SUCCESS(f"Successfully crawled {domain}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to crawl {domain}"))
        
        else:
            self.stdout.write(self.style.ERROR("Please provide either --domain or --file argument"))